"""
scripts/ab_token_compare.py ? ?? A/B Token ????

??????
  A: Full-doc  ? ?? SPEC.md ?? prompt????? MemTrace?
  B: MemTrace  ? ?? + ??????? top-5 ??
  C: No-context ? ????????? KB ??

?????
  - ?? token ??context?
  - ?? token ??LLM answer?
  - LLM Judge ??????1-5 ??
  - ????? = 1 - B_input / A_input

?????
  reports/ab_YYYYMMDD_HHMMSS.json
  reports/ab_YYYYMMDD_HHMMSS_answers.md  ???????
"""
from __future__ import annotations

import sys
import os
import asyncio
import json
import random
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from dotenv import load_dotenv
load_dotenv(".env")

from core.ai import (
    resolve_provider, chat_completion, estimate_tokens, AIProviderUnavailable
)
from core.database import db_cursor
from services.search import search_nodes_in_db

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("ab_compare")

# --- Config ------------------------------------------------------------------

WORKSPACE_ID    = "ws_spec0001"
GOLDEN_PATH     = "tests/golden_qa.jsonl"
SPEC_PATH       = "docs/SPEC.md"
REPORTS_DIR     = Path("reports")
SAMPLE_PER_DIFF = 5   # 5 easy + 5 medium + 5 hard = 15 total
RETRIEVE_TOP_K  = 5
LLM_MAX_TOKENS  = 300  # limit answer length to reduce test cost

# qwen2.5:7b has ~32k context. Reserve 2k for system prompt + question + answer.
# Full-doc is truncated to this limit for the LLM call only;
# token_count metrics always report the TRUE untruncated size.
MODEL_MAX_CONTEXT_TOKENS = 28000

SYSTEM_PROMPT = (
    "You are a precise technical assistant. "
    "Answer the question using ONLY the provided context. "
    "If the context does not contain the answer, say 'Not in context'. "
    "Keep your answer under 150 words."
)

JUDGE_PROMPT_TEMPLATE = """\
Question: {question}
Expected facts: {expected_facts}

Answer A (given full specification document):
{ans_a}

Answer B (given MemTrace retrieved nodes):
{ans_b}

Answer C (no context provided):
{ans_c}

For each answer, rate 1-5 where:
  5 = All expected facts covered, accurate
  3 = Some expected facts covered
  1 = Wrong or missing expected facts

Return ONLY valid JSON (no markdown fences):
{{"score_a": <int>, "score_b": <int>, "score_c": <int>, "notes": "<brief reason>"}}"""


# --- Helpers -----------------------------------------------------------------

def load_golden(path: str, per_diff: int) -> list[dict]:
    """Load stratified sample from golden_qa.jsonl."""
    by_diff: dict[str, list] = {"easy": [], "medium": [], "hard": []}
    with open(path, encoding="utf-8") as f:
        for line in f:
            qa = json.loads(line)
            d = qa.get("difficulty", "medium")
            if d in by_diff:
                by_diff[d].append(qa)

    sampled = []
    for diff, items in by_diff.items():
        chosen = random.sample(items, min(per_diff, len(items)))
        sampled.extend(chosen)
        print(f"  {diff}: {len(chosen)} questions sampled (pool={len(items)})")
    random.shuffle(sampled)
    return sampled


def load_full_doc(spec_path: str, cur, ws_id: str) -> str:
    """Load full-doc baseline: SPEC.md if present, else concatenate all KB nodes."""
    if os.path.exists(spec_path):
        with open(spec_path, encoding="utf-8") as f:
            content = f.read()
        print(f"  Full-doc source: {spec_path} ({len(content):,} chars)")
        return content

    # Fallback: dump all active nodes
    cur.execute("""
        SELECT title_en, title_zh, body_en, body_zh
        FROM memory_nodes
        WHERE workspace_id = %s AND status = 'active'
        ORDER BY updated_at DESC
    """, (ws_id,))
    rows = cur.fetchall()
    parts = []
    for r in rows:
        title = r["title_en"] or r["title_zh"] or ""
        body  = (r["body_en"] or "") + "\n" + (r["body_zh"] or "")
        parts.append(f"## {title}\n{body.strip()}")
    content = "\n\n---\n\n".join(parts)
    print(f"  Full-doc source: KB nodes ({len(rows)} nodes, {len(content):,} chars)")
    return content


def build_context_b(hits: list[dict]) -> str:
    """Format retrieved nodes into a context block."""
    parts = []
    for h in hits:
        title = h.get("title_en") or h.get("title_zh") or "(untitled)"
        body  = (h.get("body_en") or "") + "\n" + (h.get("body_zh") or "")
        sim   = h.get("similarity", 0.0)
        parts.append(f"[Node: {title} | similarity={sim:.3f}]\n{body.strip()}")
    return "\n\n---\n\n".join(parts)


# --- Main ---------------------------------------------------------------------

async def run(seed: int = 42, dry_run: bool = False, sample_per_diff: int = SAMPLE_PER_DIFF):
    random.seed(seed)
    REPORTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    print("\n=== A/B Token Compare ===")
    print(f"Workspace : {WORKSPACE_ID}")
    print(f"Timestamp : {ts}")
    print(f"Seed      : {seed}")

    # 1. Load data
    print("\n[1] Loading golden questions...")
    samples = load_golden(GOLDEN_PATH, sample_per_diff)
    print(f"  Total sampled: {len(samples)}")

    print("\n[2] Loading full-doc baseline...")
    with db_cursor() as cur:
        full_doc = load_full_doc(SPEC_PATH, cur, WORKSPACE_ID)
    full_doc_tokens = estimate_tokens(full_doc)
    print(f"  Full-doc tokens (tiktoken): {full_doc_tokens:,}")

    # 2. Resolve LLM provider
    print("\n[3] Resolving LLM provider...")
    try:
        chat_prov = resolve_provider("system", "extraction", preferred_provider="ollama")
        print(f"  LLM: {chat_prov.provider.name} / {chat_prov.model}")
        llm_available = True
    except Exception as e:
        print(f"  No LLM available ({e}). Running token-only mode.")
        chat_prov = None
        llm_available = False

    # 3. Per-question evaluation
    print(f"\n[4] Running {len(samples)} questions...")
    results = []
    human_review_lines = [
        f"# A/B Test Human Review ? {ts}",
        f"LLM: {chat_prov.provider.name}/{chat_prov.model if llm_available else 'N/A'}",
        "",
    ]

    for i, qa in enumerate(samples):
        q = qa.get("question_zh") or qa.get("question", "")
        expected = qa.get("expected_node_ids", [])
        facts = qa.get("expected_facts", [])
        diff = qa.get("difficulty", "medium")
        cross = qa.get("cross_node", False)

        print(f"  [{i+1:02d}/{len(samples)}] [{diff}] {q[:60]}...")

        # --- Condition A: Full-doc ---
        # For token COUNTING we always report the true full-doc size.
        # For the LLM CALL we must truncate to MODEL_MAX_CONTEXT_TOKENS to avoid
        # context-overflow timeouts. The truncation is documented in the report.
        tokens_a_input = estimate_tokens(SYSTEM_PROMPT) + estimate_tokens(q) + full_doc_tokens
        budget_for_doc = MODEL_MAX_CONTEXT_TOKENS - estimate_tokens(SYSTEM_PROMPT) - estimate_tokens(q)
        # Approximate truncation by chars (tiktoken rate ~4 chars/token for EN)
        char_budget = budget_for_doc * 4
        prompt_a_context = full_doc[:char_budget] if len(full_doc) > char_budget else full_doc
        truncated_a = len(full_doc) > char_budget
        msgs_a = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"Context (partial — {len(prompt_a_context):,}/{len(full_doc):,} chars):\n{prompt_a_context}\n\nQuestion: {q}"},
        ]

        # --- Condition B: MemTrace retrieval ---
        with db_cursor() as cur:
            hits = await search_nodes_in_db(cur, WORKSPACE_ID, q, limit=RETRIEVE_TOP_K, user=None)
        context_b = build_context_b(hits)
        tokens_b_input = estimate_tokens(SYSTEM_PROMPT) + estimate_tokens(q) + estimate_tokens(context_b)
        msgs_b = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"Context:\n{context_b}\n\nQuestion: {q}"},
        ]

        # --- Condition C: No context ---
        tokens_c_input = estimate_tokens(SYSTEM_PROMPT) + estimate_tokens(q)
        msgs_c = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"Question: {q}"},
        ]

        ans_a = ans_b = ans_c = "(token-only mode)"
        tokens_a_output = tokens_b_output = tokens_c_output = 0
        score_a = score_b = score_c = None
        judge_notes = ""

        if llm_available and not dry_run:
            # Condition A: skip LLM call when full-doc TRULY exceeds context window.
            # This is itself a key finding: local LLMs cannot handle large KBs directly.
            if truncated_a:
                ans_a = f"[OVERFLOW] Full KB ({full_doc_tokens:,} tokens) exceeds model context window ({MODEL_MAX_CONTEXT_TOKENS:,} tokens). LLM call skipped — condition A is NOT viable with this model."
                score_a = 0  # Cannot answer when context overflows
            else:
                try:
                    ans_a, tokens_a_output = await chat_completion(chat_prov, msgs_a, max_tokens=LLM_MAX_TOKENS)
                except Exception as exc:
                    ans_a = f"[ERROR] {exc}"
                    score_a = 0

            try:
                ans_b, tokens_b_output = await chat_completion(chat_prov, msgs_b, max_tokens=LLM_MAX_TOKENS)
                ans_c, tokens_c_output = await chat_completion(chat_prov, msgs_c, max_tokens=LLM_MAX_TOKENS)

                # Judge: compare B vs C (A may be OVERFLOW)
                judge_msgs = [{"role": "user", "content": JUDGE_PROMPT_TEMPLATE.format(
                    question=q,
                    expected_facts=", ".join(facts) if facts else "(see expected nodes)",
                    ans_a=ans_a[:200],  # may be OVERFLOW message
                    ans_b=ans_b[:500],
                    ans_c=ans_c[:500],
                )}]
                judge_raw, _ = await chat_completion(chat_prov, judge_msgs, max_tokens=200)
                try:
                    raw = judge_raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
                    scores = json.loads(raw)
                    if score_a is None:   # only override if not already set to 0
                        score_a = scores.get("score_a")
                    score_b = scores.get("score_b")
                    score_c = scores.get("score_c")
                    judge_notes = scores.get("notes", "")
                except Exception:
                    judge_notes = f"Parse failed: {judge_raw[:100]}"
            except Exception as exc:
                ans_b = ans_c = f"LLM error: {exc}"

        # Compute savings
        savings_vs_fulldoc = (
            1.0 - tokens_b_input / tokens_a_input
            if tokens_a_input > 0 else 0.0
        )

        rec = {
            "question": q,
            "difficulty": diff,
            "cross_node": cross,
            "expected_node_ids": expected,
            "expected_facts": facts,
            "retrieved_node_ids": [h["id"] for h in hits],
            "tokens_a_input": tokens_a_input,
            "tokens_b_input": tokens_b_input,
            "tokens_c_input": tokens_c_input,
            "tokens_a_output": tokens_a_output,
            "tokens_b_output": tokens_b_output,
            "tokens_c_output": tokens_c_output,
            "full_doc_truncated_for_llm": truncated_a,
            "savings_vs_fulldoc": round(savings_vs_fulldoc, 4),
            "score_a": score_a,
            "score_b": score_b,
            "score_c": score_c,
            "judge_notes": judge_notes,
        }
        results.append(rec)

        # Human review markdown
        human_review_lines += [
            f"---",
            f"## Q{i+1} [{diff}{'.cross' if cross else ''}] {q}",
            f"**Expected facts**: {', '.join(facts) if facts else '(see expected nodes)'}",
            f"",
            f"**Answer A (Full-doc, {tokens_a_input:,} input tokens{', truncated for LLM' if truncated_a else ''})**",
            f"> {ans_a}",
            f"",
            f"**Answer B (MemTrace, {tokens_b_input:,} input tokens, saving={savings_vs_fulldoc:.0%})**",
            f"> {ans_b}",
            f"",
            f"**Answer C (No-context, {tokens_c_input:,} input tokens)**",
            f"> {ans_c}",
            f"",
            f"**Judge**: A={score_a} B={score_b} C={score_c} | {judge_notes}",
            f"",
        ]

    # 4. Aggregate
    n = len(results)
    avg_a_in   = sum(r["tokens_a_input"] for r in results) / n
    avg_b_in   = sum(r["tokens_b_input"] for r in results) / n
    avg_c_in   = sum(r["tokens_c_input"] for r in results) / n
    avg_saving = sum(r["savings_vs_fulldoc"] for r in results) / n

    scored = [r for r in results if r["score_a"] is not None]
    avg_score_a = sum(r["score_a"] for r in scored) / len(scored) if scored else None
    avg_score_b = sum(r["score_b"] for r in scored) / len(scored) if scored else None
    avg_score_c = sum(r["score_c"] for r in scored) / len(scored) if scored else None

    summary = {
        "timestamp": ts,
        "workspace_id": WORKSPACE_ID,
        "llm": f"{chat_prov.provider.name}/{chat_prov.model}" if llm_available else "N/A",
        "sample_size": n,
        "full_doc_tokens": full_doc_tokens,
        "avg_tokens_a_full_doc": round(avg_a_in),
        "avg_tokens_b_memtrace": round(avg_b_in),
        "avg_tokens_c_no_ctx":   round(avg_c_in),
        "avg_token_saving_vs_fulldoc": round(avg_saving, 4),
        "dod_target_saving": 0.70,
        "dod_met": avg_saving >= 0.70,
        "avg_score_a": round(avg_score_a, 2) if avg_score_a is not None else None,
        "avg_score_b": round(avg_score_b, 2) if avg_score_b is not None else None,
        "avg_score_c": round(avg_score_c, 2) if avg_score_c is not None else None,
        "results": results,
    }

    # 5. Write reports
    json_path = REPORTS_DIR / f"ab_{ts}.json"
    md_path   = REPORTS_DIR / f"ab_{ts}_answers.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(human_review_lines))

    # 6. Print summary
    print("\n" + "=" * 55)
    print("A/B COMPARISON SUMMARY")
    print("=" * 55)
    print(f"Sample size          : {n} questions")
    print(f"Full-doc tokens      : {full_doc_tokens:>8,}  (SPEC.md, tiktoken)")
    print(f"Avg input A (full-doc): {avg_a_in:>7,.0f}  tokens")
    print(f"Avg input B (MemTrace): {avg_b_in:>7,.0f}  tokens")
    print(f"Avg input C (no ctx)  : {avg_c_in:>7,.0f}  tokens")
    print(f"Real token saving     : {avg_saving:>7.1%}  (B vs A)")
    print(f"DoD >= 70%             : {'[PASS] PASS' if avg_saving >= 0.70 else '[FAIL] FAIL'}")
    if scored:
        print(f"LLM judge avg scores  : A={avg_score_a:.2f}  B={avg_score_b:.2f}  C={avg_score_c:.2f}  /5")
        quality_delta = (avg_score_b - avg_score_a) if (avg_score_a and avg_score_b) else 0
        print(f"MemTrace vs Full-doc  : {quality_delta:+.2f} score delta")
    print(f"\nReports written to:")
    print(f"  {json_path}")
    print(f"  {md_path}  <- ?????????")
    print("=" * 55)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="A/B token comparison for MemTrace")
    p.add_argument("--seed",    type=int,  default=42,    help="Random seed for sampling")
    p.add_argument("--dry-run", action="store_true",      help="Skip LLM calls, token counts only")
    p.add_argument("--sample",  type=int,  default=SAMPLE_PER_DIFF, help="Questions per difficulty level")
    args = p.parse_args()

    asyncio.run(run(seed=args.seed, dry_run=args.dry_run, sample_per_diff=args.sample))
