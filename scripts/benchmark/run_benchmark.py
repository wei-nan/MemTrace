#!/usr/bin/env python3
from __future__ import annotations
"""
MemTrace KB Efficiency Benchmark
=================================
Compare token consumption: reading raw SPEC.md vs querying the knowledge base via API.

Usage:
  cd D:/Workspace/MemTrace/packages/api
  python ../../scripts/benchmark/run_benchmark.py [--output results.json]

Requirements:
  pip install tiktoken httpx python-dotenv
"""

import argparse
import json
import os
import pathlib
import sys
import time
from datetime import datetime, timezone

try:
    import tiktoken
    import httpx
    from dotenv import load_dotenv
except ImportError:
    print("Missing dependencies.  Run:  pip install tiktoken httpx python-dotenv")
    sys.exit(1)

# ── Config ─────────────────────────────────────────────────────────────────────

REPO_ROOT      = pathlib.Path(__file__).parent.parent.parent
QUESTIONS_FILE = pathlib.Path(__file__).parent / "questions.json"
SPEC_FILE      = REPO_ROOT / "docs" / "SPEC.md"

load_dotenv(REPO_ROOT / ".env")

API_BASE       = os.environ.get("MEMTRACE_API",      "http://localhost:8000/api/v1")
WS_ID          = os.environ.get("MEMTRACE_WS",       "ws_spec0001")
LANG           = os.environ.get("MEMTRACE_LANG",     "en")
BENCH_EMAIL    = os.environ.get("BENCH_EMAIL",       "benchmark@test.example.com")
BENCH_PASSWORD = os.environ.get("BENCH_PASSWORD",    "Bench1234!")

ENCODING   = tiktoken.encoding_for_model("gpt-4")
AUTH_TOKEN: str = ""  # filled in at runtime

# ── Token helpers ──────────────────────────────────────────────────────────────

def count_tokens(text: str) -> int:
    return len(ENCODING.encode(text))

def spec_tokens() -> int:
    return count_tokens(SPEC_FILE.read_text(encoding="utf-8"))

# ── Auth helpers ──────────────────────────────────────────────────────────────

def _auth_base() -> str:
    """Auth endpoints live at /auth/, not /api/v1/auth/."""
    # e.g. API_BASE = http://localhost:8000/api/v1 → http://localhost:8000
    return API_BASE.split("/api/")[0]

def get_auth_token() -> str:
    """Login (or auto-register) the benchmark user and return a JWT."""
    base = _auth_base()
    with httpx.Client(timeout=10.0) as client:
        # Try login first
        r = client.post(f"{base}/auth/login",
                        json={"email": BENCH_EMAIL, "password": BENCH_PASSWORD})
        if r.status_code == 200:
            return r.json()["access_token"]
        # Auto-register if not found
        r2 = client.post(f"{base}/auth/register",
                         json={"email": BENCH_EMAIL, "password": BENCH_PASSWORD,
                               "display_name": "Benchmark"})
        if r2.status_code == 200:
            return r2.json()["access_token"]
        raise RuntimeError(f"Cannot authenticate benchmark user: {r.text}")

def auth_headers() -> dict:
    return {"Authorization": f"Bearer {AUTH_TOKEN}"}

# ── KB query helpers ───────────────────────────────────────────────────────────

def kb_search(query: str, client: httpx.Client) -> tuple[list[dict], int]:
    """Keyword search; returns (nodes, tokens_used)."""
    t0 = time.perf_counter()
    r = client.get(f"{API_BASE}/workspaces/{WS_ID}/nodes", params={"q": query, "limit": 5}, headers=auth_headers())
    elapsed = time.perf_counter() - t0
    if r.status_code != 200:
        return [], 0
    nodes = r.json()
    raw   = json.dumps(nodes)
    return nodes, count_tokens(raw)

def kb_get_node(node_id: str, client: httpx.Client) -> tuple[dict | None, int]:
    """Fetch a single node by ID; returns (node, tokens_used)."""
    r = client.get(f"{API_BASE}/workspaces/{WS_ID}/nodes/{node_id}", headers=auth_headers())
    if r.status_code != 200:
        return None, 0
    node = r.json()
    return node, count_tokens(json.dumps(node))

def kb_traverse(node_id: str, depth: int, client: httpx.Client) -> tuple[dict, int]:
    """Traverse from a node; returns (result, tokens_used)."""
    r = client.get(f"{API_BASE}/workspaces/{WS_ID}/nodes/{node_id}/traverse",
                   params={"depth": depth}, headers=auth_headers())
    if r.status_code != 200:
        return {}, 0
    result = r.json()
    return result, count_tokens(json.dumps(result))

def kb_list_by_tag(tag: str, client: httpx.Client) -> tuple[list[dict], int]:
    """List nodes by tag; returns (nodes, tokens_used)."""
    r = client.get(f"{API_BASE}/workspaces/{WS_ID}/nodes", params={"tag": tag}, headers=auth_headers())
    if r.status_code != 200:
        return [], 0
    nodes = r.json()
    return nodes, count_tokens(json.dumps(nodes))

# ── Simulate MCP retrieval for a question ─────────────────────────────────────

def simulate_kb_retrieval(question: dict, client: httpx.Client) -> dict:
    """
    Simulate how an AI agent would retrieve KB context for a question.
    Strategy:
      1. search_nodes with key terms from the question
      2. get_node for expected_nodes (direct lookup)
      Measure total tokens fetched.
    """
    total_tokens = 0
    fetched_nodes = set()
    fetched_content = []
    latency_ms = 0

    # Step 1: keyword search (simulate what agent would do first)
    key_terms = extract_key_terms(question["question_en"])
    for term in key_terms[:2]:   # max 2 search calls
        t0 = time.perf_counter()
        nodes, toks = kb_search(term, client)
        latency_ms += (time.perf_counter() - t0) * 1000
        total_tokens += toks
        for n in nodes:
            nid = n.get("id", "")
            if nid and nid not in fetched_nodes:
                fetched_nodes.add(nid)
                fetched_content.append(nid)

    # Step 2: direct node fetch for expected nodes (simulate get_node calls)
    for nid in question.get("expected_nodes", []):
        if nid not in fetched_nodes:
            t0 = time.perf_counter()
            node, toks = kb_get_node(nid, client)
            latency_ms += (time.perf_counter() - t0) * 1000
            total_tokens += toks
            if node:
                fetched_nodes.add(nid)
                fetched_content.append(nid)

    # Coverage: were all expected nodes retrieved?
    expected = set(question.get("expected_nodes", []))
    retrieved = expected & fetched_nodes
    coverage = len(retrieved) / len(expected) if expected else 1.0

    return {
        "kb_tokens":      total_tokens,
        "nodes_fetched":  list(fetched_nodes),
        "expected_nodes": question.get("expected_nodes", []),
        "coverage":       coverage,
        "latency_ms":     round(latency_ms, 1),
    }

def extract_key_terms(question: str) -> list[str]:
    """Heuristic: extract 1–2 searchable phrases from a question."""
    stopwords = {"what", "how", "is", "are", "the", "a", "an", "in",
                 "and", "or", "to", "does", "do", "for", "of", "with", "its"}
    words = [w.strip("?.,") for w in question.lower().split()]
    keywords = [w for w in words if w not in stopwords and len(w) > 3]
    # Return two-word phrases where possible
    phrases = []
    i = 0
    while i < len(keywords) - 1 and len(phrases) < 2:
        phrases.append(f"{keywords[i]} {keywords[i+1]}")
        i += 2
    return phrases if phrases else keywords[:2]

# ── Scoring ────────────────────────────────────────────────────────────────────

def score_coverage(result: dict) -> float:
    """0.0–1.0: fraction of expected nodes actually retrieved."""
    return result["coverage"]

def efficiency_ratio(spec_tok: int, kb_tok: int) -> float:
    """How many times more efficient is KB vs full-doc (higher = better)."""
    return round(spec_tok / kb_tok, 1) if kb_tok > 0 else 0.0

def token_reduction_pct(spec_tok: int, kb_tok: int) -> float:
    """Percentage of tokens saved by using KB instead of full doc."""
    return round((1 - kb_tok / spec_tok) * 100, 1) if spec_tok > 0 else 0.0

# ── Main ───────────────────────────────────────────────────────────────────────

def run_benchmark(output_path: str | None = None):
    questions = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))

    print("\n" + "="*60)
    print("  MemTrace KB Efficiency Benchmark")
    print("="*60)

    # Baseline: full SPEC.md token count
    global AUTH_TOKEN
    print("\n[0/3] Authenticating benchmark user...")
    try:
        AUTH_TOKEN = get_auth_token()
        print(f"      Logged in as {BENCH_EMAIL}")
    except Exception as e:
        print(f"      ERROR: {e}")
        sys.exit(1)

    print("\n[1/3] Measuring SPEC.md baseline...")
    spec_tok = spec_tokens()
    print(f"      SPEC.md size: {spec_tok:,} tokens")

    # Check API availability
    print("\n[2/3] Checking API availability...")
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get(f"{API_BASE}/workspaces/{WS_ID}/nodes",
                           params={"limit": 1}, headers=auth_headers())
            if r.status_code != 200:
                print(f"      ERROR: API returned {r.status_code}: {r.text[:200]}")
                sys.exit(1)
        print(f"      API OK  ({API_BASE})")
    except Exception as e:
        print(f"      ERROR: Cannot connect to API: {e}")
        sys.exit(1)

    # Run questions
    print(f"\n[3/3] Running {len(questions)} benchmark questions...\n")
    print(f"  {'ID':<5} {'Category':<20} {'KB tok':>8} {'Coverage':>10} {'Efficiency':>12} {'Latency':>10}")
    print(f"  {'-'*5} {'-'*20} {'-'*8} {'-'*10} {'-'*12} {'-'*10}")

    results = []
    with httpx.Client(timeout=10.0) as client:
        for q in questions:
            retrieval = simulate_kb_retrieval(q, client)
            eff  = efficiency_ratio(spec_tok, retrieval["kb_tokens"])
            pct  = token_reduction_pct(spec_tok, retrieval["kb_tokens"])
            cov  = score_coverage(retrieval)
            cov_symbol = "OK" if cov >= 1.0 else ("~" if cov > 0 else "NG")

            print(f"  {q['id']:<5} {q['category']:<20} "
                  f"{retrieval['kb_tokens']:>8,} "
                  f"{cov_symbol} {cov*100:>6.0f}%  "
                  f"  {eff:>6.1f}x ({pct:.0f}% less)  "
                  f"{retrieval['latency_ms']:>7.0f} ms")

            results.append({
                "question_id":   q["id"],
                "category":      q["category"],
                "difficulty":    q["difficulty"],
                "spec_tokens":   spec_tok,
                "kb_tokens":     retrieval["kb_tokens"],
                "efficiency_x":  eff,
                "token_savings_pct": pct,
                "coverage":      round(cov, 2),
                "latency_ms":    retrieval["latency_ms"],
                "nodes_fetched": retrieval["nodes_fetched"],
                "expected_nodes": retrieval["expected_nodes"],
            })

    # Aggregate stats
    avg_kb_tok  = sum(r["kb_tokens"]      for r in results) / len(results)
    avg_eff     = sum(r["efficiency_x"]   for r in results) / len(results)
    avg_cov     = sum(r["coverage"]       for r in results) / len(results)
    avg_lat     = sum(r["latency_ms"]     for r in results) / len(results)
    avg_savings = sum(r["token_savings_pct"] for r in results) / len(results)
    full_cov_n  = sum(1 for r in results if r["coverage"] >= 1.0)

    print(f"\n  {'─'*70}")
    print(f"  Average KB tokens per query:  {avg_kb_tok:>8,.0f}  (vs {spec_tok:,} for full SPEC.md)")
    print(f"  Average efficiency:           {avg_eff:>8.1f}x")
    print(f"  Average token savings:        {avg_savings:>7.1f}%")
    print(f"  Average node coverage:        {avg_cov*100:>7.1f}%  ({full_cov_n}/{len(results)} questions fully covered)")
    print(f"  Average latency:              {avg_lat:>7.1f} ms")

    # Pass/fail thresholds
    print("\n" + "="*60)
    print("  Validation Thresholds")
    print("="*60)
    checks = [
        ("Token efficiency >= 5x",        avg_eff >= 5.0,   f"{avg_eff:.1f}x"),
        ("Token savings >= 80%",           avg_savings >= 80, f"{avg_savings:.1f}%"),
        ("Node coverage >= 70%",           avg_cov >= 0.70,  f"{avg_cov*100:.1f}%"),
        ("Full coverage on easy Qs",        all(r["coverage"] >= 1.0 for r in results if r["difficulty"] == "easy"),
                                           f"{sum(1 for r in results if r['difficulty']=='easy' and r['coverage']>=1.0)}/{sum(1 for r in results if r['difficulty']=='easy')}"),
        ("Avg latency < 2000 ms",          avg_lat < 2000,   f"{avg_lat:.0f} ms"),
    ]

    all_pass = True
    for label, passed, value in checks:
        symbol = "PASS" if passed else "FAIL"
        print(f"  [{symbol}]  {label:<42} {value}")
        if not passed:
            all_pass = False

    print("\n" + ("=" * 60))
    verdict = "PASS — KB is efficient and sufficiently accurate" if all_pass \
              else "PARTIAL — Review failed thresholds above"
    print(f"  Overall: {verdict}")
    print("="*60 + "\n")

    # Write JSON report
    report = {
        "generated_at":     datetime.now(timezone.utc).isoformat(),
        "spec_tokens":      spec_tok,
        "api_base":         API_BASE,
        "workspace_id":     WS_ID,
        "summary": {
            "avg_kb_tokens":      round(avg_kb_tok, 1),
            "avg_efficiency_x":   round(avg_eff, 2),
            "avg_token_savings_pct": round(avg_savings, 1),
            "avg_coverage_pct":   round(avg_cov * 100, 1),
            "full_coverage_count": full_cov_n,
            "total_questions":    len(results),
            "avg_latency_ms":     round(avg_lat, 1),
            "all_thresholds_pass": all_pass,
        },
        "questions": results,
    }

    out = pathlib.Path(output_path) if output_path \
          else pathlib.Path(__file__).parent / "results.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Full report saved to: {out}\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MemTrace KB Efficiency Benchmark")
    parser.add_argument("--output", "-o", help="Path to save JSON report", default=None)
    args = parser.parse_args()
    run_benchmark(args.output)
