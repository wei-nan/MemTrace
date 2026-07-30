#!/usr/bin/env python3
"""
Release Loop agent (G4 executor).

Closes the gap that spec-sync.yml does not cover: spec-sync.yml only checks
that examples/spec-as-kb/ is internally consistent (seed JSON <-> generated
SQL <-> live public KB). It never fires when a router/constants/migration
change alters public behavior without anyone touching the seed at all. This
script is the other half — given a PR whose diff touches a trigger path, it
either reviews spec content the PR already added, or drafts the missing
content via Gemini, then writes a G4 gate_verdict to ws_spec_plan.

Design record: ws_6aa957c3/mem_cc085a90 (Release Loop), mem_5d8c6ff8 (G4).
Not yet wired to the `pull_request` trigger in release-loop.yml — run it
manually via workflow_dispatch first and read the output before flipping
that on.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import pathlib
import secrets as _secrets
import subprocess
import sys
import urllib.error
import urllib.request

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
API_ROOT = REPO_ROOT / "packages" / "api"
ZH_DIR = REPO_ROOT / "examples" / "spec-as-kb" / "nodes" / "zh"
EN_DIR = REPO_ROOT / "examples" / "spec-as-kb" / "nodes" / "en"

# Trigger paths confirmed 2026-07-30 (ws_6aa957c3/mem_cc085a90) — keep in
# sync with the `paths:` filter in release-loop.yml. Duplicated here (not
# imported) because the workflow's path filter and this script's mode
# detection run in different processes.
TRIGGER_PATHS = (
    "examples/spec-as-kb/",
    "packages/api/core/constants.py",
    "packages/api/migrations/",
    "packages/api/services/mcp_tools.py",
    "packages/api/routers/kb.py",
    "packages/api/routers/mcp.py",
    "packages/api/routers/auth.py",
    "packages/api/routers/registration.py",
    "packages/api/routers/api_keys.py",
    "packages/api/routers/openai_compat.py",
    "packages/api/routers/exports.py",
)
SEED_PREFIX = "examples/spec-as-kb/"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
MEMTRACE_API_KEY = os.environ.get("MEMTRACE_API_KEY")
MEMTRACE_BASE_URL = os.environ.get("MEMTRACE_BASE_URL")  # e.g. https://api.memtrace.example.com
WS_SPEC_PLAN = os.environ.get("MEMTRACE_SPEC_PLAN_WORKSPACE_ID", "ws_spec_plan")


class GateReject(Exception):
    """Raised to short-circuit straight to a REJECT verdict."""


def sh(*args: str, check: bool = True) -> str:
    r = subprocess.run(args, cwd=REPO_ROOT, text=True, capture_output=True)
    if check and r.returncode != 0:
        print(r.stdout, file=sys.stderr)
        print(r.stderr, file=sys.stderr)
        raise SystemExit(f"command failed ({r.returncode}): {' '.join(args)}")
    return r.stdout.strip()


# ─── Preconditions ──────────────────────────────────────────────────────────

def require_env() -> None:
    missing = [
        name
        for name in ("GEMINI_API_KEY", "MEMTRACE_API_KEY", "MEMTRACE_BASE_URL")
        if not os.environ.get(name)
    ]
    if missing:
        raise SystemExit(
            "Release Loop agent missing required env var(s): "
            + ", ".join(missing)
            + ". GEMINI_API_KEY and MEMTRACE_API_KEY are repo secrets (set "
            "2026-07-30). MEMTRACE_BASE_URL is new — it's the server hostname "
            "for REST calls (e.g. https://api.memtrace.example.com), not yet "
            "configured anywhere. Add it as a repo *variable* (not secret — "
            "it's not sensitive) under Settings > Secrets and variables > "
            "Actions > Variables."
        )


def verify_model() -> None:
    """Fail loudly if GEMINI_MODEL isn't a real, currently-available model id.
    This project has a standing "no hardcoded model id" policy
    (ws_spec_plan/mem_6ee3ee82) precisely because these strings drift; do not
    silently fall back to a different model if the configured one is stale.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.load(resp)
    except urllib.error.URLError as e:
        raise SystemExit(f"could not reach Gemini model list endpoint: {e}")
    ids = sorted(m["name"].replace("models/", "") for m in data.get("models", []))
    if GEMINI_MODEL not in ids:
        raise SystemExit(
            f"GEMINI_MODEL={GEMINI_MODEL!r} is not in the live Gemini model "
            f"list ({len(ids)} models available). Refusing to guess a "
            f"substitute. Update the GEMINI_MODEL env var in "
            f"release-loop.yml. Sample available ids: {ids[:10]}"
        )


# ─── Diff detection ─────────────────────────────────────────────────────────

def changed_files(base_ref: str, head_ref: str = "HEAD") -> list[str]:
    out = sh("git", "diff", "--name-only", f"{base_ref}...{head_ref}")
    return [line for line in out.splitlines() if line]


def diff_excerpt(base_ref: str, paths: list[str], head_ref: str = "HEAD", max_chars: int = 20000) -> str:
    out = sh("git", "diff", f"{base_ref}...{head_ref}", "--", *paths)
    return out[:max_chars]


def determine_mode(files: list[str]) -> tuple[str, list[str]]:
    """Returns (mode, touched_trigger_paths). mode is one of:
    - "skip": diff touches no trigger path, G4 is N/A PASS.
    - "review": diff touches examples/spec-as-kb/ already — review, don't draft.
    - "draft": diff touches a behavior path but not the seed — author it.
    """
    touched = [f for f in files if any(f.startswith(p) for p in TRIGGER_PATHS)]
    if not touched:
        return "skip", []
    if any(f.startswith(SEED_PREFIX) for f in touched):
        return "review", touched
    return "draft", touched


# ─── Gemini call ────────────────────────────────────────────────────────────

def call_gemini(prompt: str, response_schema: dict) -> dict:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": response_schema,
        },
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Gemini generateContent failed ({e.code}): {e.read()[:500]}")
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise SystemExit(f"Gemini response missing expected content: {data}")
    return json.loads(text)


REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "semantically_correct": {"type": "boolean"},
        "translation_faithful": {"type": "boolean"},
        "issues": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["semantically_correct", "translation_faithful", "issues"],
}

DRAFT_SCHEMA = {
    "type": "object",
    "properties": {
        "nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title_zh": {"type": "string"},
                    "title_en": {"type": "string"},
                    "body_zh": {"type": "string"},
                    "body_en": {"type": "string"},
                    "content_type": {
                        "type": "string",
                        "enum": ["factual", "procedural", "context"],
                    },
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title_zh", "title_en", "body_zh", "body_en", "content_type", "tags"],
            },
        },
        "notes": {"type": "string"},
    },
    "required": ["nodes", "notes"],
}


# ─── Seed authoring ─────────────────────────────────────────────────────────

def compute_signature(title, content, tags, author) -> str:
    sys.path.insert(0, str(API_ROOT))
    from core.security import compute_signature as _compute_signature  # noqa: E402
    return _compute_signature(title, content, tags, author)


def write_node_pair(drafted: dict) -> str:
    """Writes a zh/en node pair to the seed dirs. Returns the node id.

    Deliberately computes the en signature independently from its own
    (title_en, content_en, tags, author) rather than copying the zh
    signature — some existing seed files have identical zh/en signatures,
    which only makes sense if the en signature is meant to say "translated
    from this zh source" rather than "hash of this en content". That's a
    pre-existing data-quality question outside this script's scope; this
    script follows compute_signature()'s actual definition (a content
    integrity hash) rather than replicating what may be a bug.
    """
    node_id = f"mem_{_secrets.token_hex(4)}"
    author = "release-loop-agent"
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    tags = sorted(drafted["tags"])

    content_zh = {"type": drafted["content_type"], "format": "markdown", "body": drafted["body_zh"]}
    content_en = {"type": drafted["content_type"], "format": "markdown", "body": drafted["body_en"]}

    zh_node = {
        "id": node_id,
        "schema_version": "1.0",
        "language": "zh-TW",
        "title": drafted["title_zh"],
        "content": content_zh,
        "tags": tags,
        "visibility": "public",
        "provenance": {
            "author": author,
            "created_at": now,
            "signature": compute_signature(drafted["title_zh"], content_zh, tags, author),
            "source_type": "ai",
        },
        "traversal": {"count": 0, "unique_traversers": 0},
    }
    en_node = {
        "id": f"{node_id}_en",
        "schema_version": "1.0",
        "language": "en",
        "title": drafted["title_en"],
        "content": content_en,
        "tags": tags,
        "visibility": "public",
        "provenance": {
            "author": author,
            "created_at": now,
            "signature": compute_signature(drafted["title_en"], content_en, tags, author),
            "source_type": "ai",
        },
        "traversal": {"count": 0, "unique_traversers": 0},
    }

    (ZH_DIR / f"{node_id}.json").write_text(json.dumps(zh_node, indent=2, ensure_ascii=False) + "\n")
    (EN_DIR / f"{node_id}_en.json").write_text(json.dumps(en_node, indent=2, ensure_ascii=False) + "\n")
    return node_id


# ─── MemTrace write-back ────────────────────────────────────────────────────

def write_gate_verdict(verdict: dict) -> None:
    url = f"{MEMTRACE_BASE_URL}/api/v1/workspaces/{WS_SPEC_PLAN}/nodes"
    body = {
        "title": f"G4 Gate Verdict ({verdict['verdict']}) — Release Loop {verdict['ts']}",
        "content_type": "factual",
        "content_format": "markdown",
        "body": "```json\n" + json.dumps(verdict, indent=2, ensure_ascii=False) + "\n```",
        "tags": ["gate-verdict", "g4", "release-loop", "ai"] + (["gate-reject"] if verdict["verdict"] == "REJECT" else []),
        "visibility": "team",
        "source_type": "ai",
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MEMTRACE_API_KEY}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            json.load(resp)
    except urllib.error.HTTPError as e:
        # Do not let a KB write failure silently turn a REJECT into a PASS,
        # and do not let it silently swallow a PASS either — surface it.
        print(f"WARNING: failed to write gate_verdict to MemTrace ({e.code}): {e.read()[:300]}", file=sys.stderr)


# ─── Main ───────────────────────────────────────────────────────────────────

def build_verdict(gate_status: str, checked: list[dict], reasons: list[str], missing: list[str]) -> dict:
    return {
        "gate": "G4",
        "from_stage": "converge",
        "to_stage": "converge" if gate_status == "PASS" else None,
        "verdict": gate_status,
        "checked": checked,
        "reasons": reasons,
        "missing": missing,
        "return_to": None if gate_status == "PASS" else "dev",
        "next_allowed_stage": "converge" if gate_status == "PASS" else None,
        "reviewer_model": f"gemini:{GEMINI_MODEL}",
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


def main() -> int:
    require_env()

    base_ref = os.environ.get("RELEASE_LOOP_BASE_REF", "origin/main")
    files = changed_files(base_ref)
    mode, touched = determine_mode(files)

    if mode == "skip":
        print("Release Loop: diff touches no trigger path — G4 is N/A PASS.")
        return 0

    print(f"Release Loop: mode={mode}, touched trigger paths={touched}")
    verify_model()

    checked: list[dict] = []
    reasons: list[str] = []
    missing: list[str] = []

    if mode == "review":
        excerpt = diff_excerpt(base_ref, touched)
        result = call_gemini(
            "You are reviewing a pull request's changes to a public knowledge-base "
            "spec (bilingual zh-TW/en). Check two things only: (1) is the new/changed "
            "content semantically correct given the accompanying code diff, and (2) "
            "is the English text a faithful translation of the Chinese text (not the "
            "reverse). Do not comment on formatting or style.\n\n"
            f"Diff:\n{excerpt}",
            REVIEW_SCHEMA,
        )
        checked.append({"criterion": "content semantically correct", "status": "pass" if result["semantically_correct"] else "fail", "evidence_refs": []})
        checked.append({"criterion": "en is faithful translation of zh", "status": "pass" if result["translation_faithful"] else "fail", "evidence_refs": []})
        if not result["semantically_correct"] or not result["translation_faithful"]:
            missing.extend(result["issues"])
            reasons.append("Gemini review flagged semantic or translation issues — see missing[]")

    elif mode == "draft":
        excerpt = diff_excerpt(base_ref, touched)
        result = call_gemini(
            "You are drafting bilingual (zh-TW, English) knowledge-base spec nodes "
            "for a code change that alters public product behavior. Given the diff "
            "below, propose one or more short spec nodes (factual/procedural/context) "
            "describing the new public behavior, in both languages. Keep each node "
            "focused on one fact (this project's convention is small nodes, more "
            "edges). Do not invent behavior not shown in the diff.\n\n"
            f"Diff:\n{excerpt}",
            DRAFT_SCHEMA,
        )
        if not result["nodes"]:
            missing.append("Gemini did not draft any spec content for this diff — needs human review, not auto-authored.")
            reasons.append(result.get("notes") or "no nodes drafted")
        else:
            ids = [write_node_pair(n) for n in result["nodes"]]
            checked.append({"criterion": "public surface change has seed content", "status": "pass", "evidence_refs": ids})
            sh("python3", "scripts/seed_spec_kb.py", "--write")
            checked.append({"criterion": "seed SQL regenerated", "status": "pass", "evidence_refs": ["command:seed_spec_kb.py --write"]})

    # Final deterministic re-check — do not trust the agent's self-report.
    check = subprocess.run(
        ["python3", "scripts/seed_spec_kb.py", "--check"], cwd=REPO_ROOT, text=True, capture_output=True
    )
    checked.append({
        "criterion": "seed JSON == generated SQL (byte-identical)",
        "status": "pass" if check.returncode == 0 else "fail",
        "evidence_refs": ["command:seed_spec_kb.py --check"],
    })
    if check.returncode != 0:
        missing.append("seed_spec_kb.py --check failed after this run — seed/SQL drift.")
        reasons.append(check.stdout[-1000:] or check.stderr[-1000:])

    gate_status = "REJECT" if missing else "PASS"
    verdict = build_verdict(gate_status, checked, reasons, missing)
    print(json.dumps(verdict, indent=2, ensure_ascii=False))
    write_gate_verdict(verdict)

    return 0 if gate_status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
