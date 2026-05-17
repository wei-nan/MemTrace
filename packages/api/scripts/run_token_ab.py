import sys
import os
import asyncio
import json
import logging
from typing import List, Dict, Any

# Setup path for imports
sys.path.append("packages/api")

from core.ai import chat_completion, resolve_provider, strip_fences, estimate_tokens
from core.database import db_cursor
from services.search import search_nodes_in_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("token_ab")

SPEC_PATH = "docs/SPEC.md"
GOLDEN_PATH = "tests/golden_qa.jsonl"

async def run_ab_test(ws_id: str, limit: int = 5):
    # 1. Load SPEC.md
    if not os.path.exists(SPEC_PATH):
        logger.error(f"SPEC.md not found at {SPEC_PATH}")
        return
    with open(SPEC_PATH, "r", encoding="utf-8") as f:
        spec_content = f.read()
    
    # 2. Load Golden Q&A
    if not os.path.exists(GOLDEN_PATH):
        logger.error(f"Golden QA not found at {GOLDEN_PATH}")
        return
    
    golden_data = []
    with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                golden_data.append(json.loads(line))
    
    logger.info(f"Loaded {len(golden_data)} golden questions.")
    
    # Use a few samples for quick test if too many
    samples = golden_data[:3] 
    
    results = []
    
    # Resolve providers
    chat_prov = resolve_provider("system", "extraction") # Use extraction/chat provider
    judge_prov = resolve_provider("system", "extraction") # Use same for judge for now
    
    for i, item in enumerate(samples):
        qid = item.get("qid", f"Q{i+1}")
        q_text = item["question"]
        logger.info(f"Processing {qid}: {q_text}")
        
        # --- Baseline (Full SPEC) ---
        baseline_prompt = f"Context (Full Specification):\n{spec_content}\n\nQuestion: {q_text}\nAnswer strictly based on context."
        ans_a, tokens_a = await chat_completion(chat_prov, [{"role": "user", "content": baseline_prompt}])
        
        # --- MemTrace (Retrieve top-k) ---
        with db_cursor() as cur:
            # We use a dummy user dict for require_ws_access
            hits = await search_nodes_in_db(cur, ws_id, q_text, limit=limit, user={"sub": "system"})
        
        context_b = "\n---\n".join([f"Node: {h.get('title_zh') or h.get('title_en')}\n{h.get('body_zh') or h.get('body_en')}" for h in hits])
        memtrace_prompt = f"Context (Retrieved Nodes):\n{context_b}\n\nQuestion: {q_text}\nAnswer strictly based on context."
        ans_b, tokens_b = await chat_completion(chat_prov, [{"role": "user", "content": memtrace_prompt}])
        
        # --- Judge ---
        judge_prompt = f"""Compare two answers to the question: "{q_text}"
Expected Facts: {", ".join(item.get("expected_facts", []))}

Answer A (Baseline): {ans_a}
Answer B (MemTrace): {ans_b}

Score each answer 1-5 for accuracy and completeness relative to Expected Facts.
Return JSON: {{"score_a": X, "score_b": Y, "reason": "..."}}"""
        
        judge_raw, _ = await chat_completion(judge_prov, [{"role": "user", "content": judge_prompt}])
        try:
            scores = json.loads(strip_fences(judge_raw))
        except:
            scores = {"score_a": 0, "score_b": 0, "reason": "Failed to parse judge response"}
            
        results.append({
            "qid": qid,
            "tokens_baseline": tokens_a,
            "tokens_memtrace": tokens_b,
            "score_baseline": scores.get("score_a", 0),
            "score_memtrace": scores.get("score_b", 0),
            "saving": 1 - (tokens_b / tokens_a) if tokens_a > 0 else 0
        })

    # Summary
    avg_tokens_a = sum(r["tokens_baseline"] for r in results) / len(results)
    avg_tokens_b = sum(r["tokens_memtrace"] for r in results) / len(results)
    avg_score_a = sum(r["score_baseline"] for r in results) / len(results)
    avg_score_b = sum(r["score_memtrace"] for r in results) / len(results)
    avg_saving = sum(r["saving"] for r in results) / len(results)
    
    print("\n" + "="*40)
    print("A/B TEST SUMMARY")
    print("="*40)
    print(f"Baseline Avg Tokens:  {avg_tokens_a:,.0f}")
    print(f"MemTrace Avg Tokens:  {avg_tokens_b:,.0f}")
    print(f"Avg Token Saving:     {avg_saving*100:.1f}%")
    print(f"Baseline Avg Score:   {avg_score_a:.2f}/5")
    print(f"MemTrace Avg Score:   {avg_score_b:.2f}/5")
    print(f"Correctness Ratio:    {(avg_score_b/avg_score_a)*100 if avg_score_a > 0 else 0:.1f}%")
    print("="*40)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(".env")
    ws_id = sys.argv[1] if len(sys.argv) > 1 else "ws_spec0001"
    asyncio.run(run_ab_test(ws_id))
