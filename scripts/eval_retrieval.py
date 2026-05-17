#!/usr/bin/env python3
import argparse
import json
import os
import sys
import requests
import numpy as np

def main():
    parser = argparse.ArgumentParser(description="Evaluate retrieval quality (Recall@5, MRR)")
    parser.add_argument("--golden", required=True, help="Path to golden_qa.jsonl")
    parser.add_argument("--workspace", required=True, help="Workspace ID to test against")
    parser.add_argument("--api-url", default="http://localhost:8000/api", help="Base API URL")
    parser.add_argument("--token", help="Bearer token for auth (if needed)")
    args = parser.parse_args()

    if not os.path.exists(args.golden):
        print(f"Error: {args.golden} not found")
        sys.exit(1)

    headers = {}
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"

    questions = []
    with open(args.golden, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))

    print(f"Loaded {len(questions)} questions from {args.golden}")

    recalls_at_5 = []
    recalls_at_10 = []
    ranks = []

    for i, q in enumerate(questions):
        query = q["question"]
        expected_ids = set(q["expected_node_ids"])
        
        # Call search API (keyword search to avoid CSRF)
        try:
            url = f"{args.api_url}/workspaces/{args.workspace}/nodes-search"
            resp = requests.get(url, params={"query": query, "limit": 10}, headers=headers)
            resp.raise_for_status()
            results = resp.json()
            if isinstance(results, dict):
                results = results.get("results", [])
            
            hit_ids = [r["id"] for r in results]
            
            # Recall@5
            top_5 = set(hit_ids[:5])
            recall_5 = len(expected_ids & top_5) / len(expected_ids) if expected_ids else 0
            recalls_at_5.append(recall_5)

            # Recall@10
            top_10 = set(hit_ids)
            recall_10 = len(expected_ids & top_10) / len(expected_ids) if expected_ids else 0
            recalls_at_10.append(recall_10)

            # MRR (Mean Reciprocal Rank)
            rank = 0
            for idx, hid in enumerate(hit_ids):
                if hid in expected_ids:
                    rank = 1 / (idx + 1)
                    break
            ranks.append(rank)

            if i % 10 == 0:
                print(f"Processed {i}/{len(questions)}...")

        except Exception as e:
            print(f"Error processing question '{query}': {e}")
            recalls_at_5.append(0)
            recalls_at_10.append(0)
            ranks.append(0)

    print("\n" + "="*40)
    print("RETRIEVAL EVALUATION RESULTS")
    print("="*40)
    print(f"Recall@5:  {np.mean(recalls_at_5):.4f}")
    print(f"Recall@10: {np.mean(recalls_at_10):.4f}")
    print(f"MRR:       {np.mean(ranks):.4f}")
    print("="*40)

if __name__ == "__main__":
    main()
