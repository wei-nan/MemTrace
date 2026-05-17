import sys
import os
import asyncio
import json
from datetime import datetime

# Add current directory to path so it can find packages
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "packages", "api"))

try:
    from dotenv import load_dotenv
    load_dotenv(".env")
except ImportError:
    pass

from packages.api.services.search import search_nodes_in_db
from packages.api.core.database import db_cursor

async def main():
    workspace_id = "ws_spec0001"
    golden_path = "packages/api/tests/golden_qa.jsonl"
    
    if not os.path.exists(golden_path):
        # Try relative to packages/api
        golden_path = "tests/golden_qa.jsonl"
        if not os.path.exists(golden_path):
            print(f"Golden QA file not found.")
            return

    with open(golden_path, "r", encoding="utf-8") as f:
        qa_pairs = [json.loads(line) for line in f]

    total = len(qa_pairs)
    stats = {
        "recall_at_5": 0.0,
        "recall_at_10": 0.0,
        "mrr": 0.0,
        "precision_at_5": 0.0,
        "count": 0,
        "by_difficulty": {
            "easy": {"recall_at_5": 0.0, "count": 0},
            "medium": {"recall_at_5": 0.0, "count": 0},
            "hard": {"recall_at_5": 0.0, "count": 0},
        }
    }
    
    low_hits = []

    print(f"Starting evaluation on {total} questions...")
    
    for qa in qa_pairs:
        query = qa.get("question_zh") or qa.get("question")
        expected = set(qa.get("expected_node_ids", []))
        diff = qa.get("difficulty", "medium")
        
        try:
            with db_cursor() as cur:
                # We use system user (None)
                results = await search_nodes_in_db(cur, workspace_id, query, limit=10, user=None)
                
            hit_ids = [r["id"] for r in results]
            
            # Debug: Check similarity of top result
            if results:
                sim = results[0].get("similarity", 0.0)
                # print(f"Query: {query[:30]}... | Top Result: {results[0]['id']} | Sim: {sim:.4f}")
            
            # Recall @ 5
            hit_5 = set(hit_ids[:5])
            found_5 = expected.intersection(hit_5)
            recall_5 = len(found_5) / len(expected) if expected else 0.0
            
            # Recall @ 10
            hit_10 = set(hit_ids)
            found_10 = expected.intersection(hit_10)
            recall_10 = len(found_10) / len(expected) if expected else 0.0
            
            # Precision @ 5
            prec_5 = len(found_5) / 5 if hit_5 else 0.0
            
            # MRR
            mrr = 0.0
            for i, h_id in enumerate(hit_ids):
                if h_id in expected:
                    mrr = 1 / (i + 1)
                    break
            
            # Update stats
            stats["recall_at_5"] += recall_5
            stats["recall_at_10"] += recall_10
            stats["precision_at_5"] += prec_5
            stats["mrr"] += mrr
            stats["count"] += 1
            
            if diff in stats["by_difficulty"]:
                stats["by_difficulty"][diff]["recall_at_5"] += recall_5
                stats["by_difficulty"][diff]["count"] += 1
                
            if recall_5 < 0.5:
                low_hits.append({
                    "query": query,
                    "expected": list(expected),
                    "actual": hit_ids[:5],
                    "recall_5": recall_5
                })
        except Exception as e:
            print(f"Error processing question '{query}': {e}")

    # Final summary
    count = stats["count"]
    if count == 0:
        print("No questions were processed successfully.")
        return

    print("\n" + "="*40)
    print("RETRIEVAL QUALITY EVALUATION REPORT")
    print("="*40)
    print(f"Total Questions: {count}")
    print(f"Overall Recall@5:    {stats['recall_at_5']/count:.4f}")
    print(f"Overall Recall@10:   {stats['recall_at_10']/count:.4f}")
    print(f"Overall Precision@5: {stats['precision_at_5']/count:.4f}")
    print(f"Overall MRR:         {stats['mrr']/count:.4f}")
    print("-" * 20)
    for d, d_stat in stats["by_difficulty"].items():
        if d_stat["count"] > 0:
            print(f"Difficulty {d:6}: Recall@5 = {d_stat['recall_at_5']/d_stat['count']:.4f} ({d_stat['count']} questions)")
            
    if low_hits:
        print("\nLow-hit Questions (Recall@5 < 0.5):")
        for lh in low_hits[:10]: # Top 10 fails
            print(f"- Query: {lh['query']}")
            print(f"  Expected: {lh['expected']}")
            print(f"  Actual:   {lh['actual']}")
            print(f"  Recall@5: {lh['recall_5']:.4f}")

if __name__ == "__main__":
    asyncio.run(main())
