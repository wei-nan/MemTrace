#!/usr/bin/env python3
"""
run_loop.py — Single planner + developer loop harness (Sprint D-1).

Wires together the Phase-6 MCP spine in one cycle:
  1. converge_check   — should we run another iteration?
  2. get_next_task    — planner picks a task (exclusive=True auto-claims it)
  3. get_playbook     — planner fetches relevant how-to guide
  4. develop()        — STUB: replace with your real agent / AI call
  5. propose_decision — developer records the result into review_queue
  6. submit_outcome   — links answered_by, triggers C3 if feature is complete
  7. emit_residue     — records new gaps discovered this round

Usage:
    pip install httpx
    python run_loop.py \\
        --ws ws_abc123 \\
        --url http://localhost:8000 \\
        --token mt_yourApiKeyHere \\
        [--tag agent-loop] \\
        [--max-loops 3] \\
        [--dry-run]

To use a real agent, subclass WorkLoop and override develop():

    class MyAgentLoop(WorkLoop):
        async def develop(self, task, playbooks):
            answer = await my_claude_agent(task, playbooks)
            return {
                "title":      answer.title,
                "body":       answer.body,
                "confidence": answer.confidence,
                "risk_level": answer.risk,
                "residues":   answer.new_gaps,
            }

    asyncio.run(MyAgentLoop(...).run_once())
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any, Optional

try:
    import httpx
except ImportError:
    sys.exit("httpx is required:  pip install httpx")


class WorkLoop:
    def __init__(
        self,
        ws_id: str,
        base_url: str,
        token: str,
        tag: Optional[str] = None,
        dry_run: bool = False,
    ):
        self.ws_id    = ws_id
        self.base_url = base_url.rstrip("/")
        self.tag      = tag
        self.dry_run  = dry_run
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        }
        self._client  = httpx.AsyncClient(headers=self._headers, timeout=60)
        self._call_id = 0

    async def close(self):
        await self._client.aclose()

    async def _call(self, tool: str, **kwargs: Any) -> Any:
        """Call one MCP tool via the Streamable HTTP transport (POST /api/v1/mcp/mcp)."""
        self._call_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id":      self._call_id,
            "method":  "tools/call",
            "params":  {
                "name":      tool,
                "arguments": {"workspace_id": self.ws_id, **kwargs},
            },
        }
        if self.dry_run:
            print(f"  [dry-run] {tool}({kwargs})")
            return {}

        resp = await self._client.post(
            f"{self.base_url}/api/v1/mcp/mcp",
            content=json.dumps(payload),
        )
        resp.raise_for_status()
        rpc = resp.json()
        if "error" in rpc:
            raise RuntimeError(f"MCP error from {tool}: {rpc['error']}")
        content = rpc.get("result", {}).get("content", [{}])
        return json.loads(content[0].get("text", "{}")) if content else {}

    # ── D2: convergence decision ──────────────────────────────────────────────

    async def should_loop(self) -> bool:
        """Ask the server if another loop iteration is warranted."""
        kwargs: dict = {}
        if self.tag:
            kwargs["tag"] = self.tag
        result = await self._call("converge_check", **kwargs)
        rec    = result.get("recommendation", "continue")
        stats  = result.get("stats", {})
        print(f"  converge_check → {rec}  {stats}")
        return rec == "continue"

    # ── D2/D3: planning-stage proposal convergence ────────────────────────────

    async def converge_proposals(self, proposals: list[str], task_node_id: str | None = None) -> str:
        """
        For multi-agent planning (D3): given competing planner proposals, ask the
        server (which reuses the consult synthesizer) whether they converge or should
        escalate to a human. Returns 'converge' or 'escalate'.

        With a single planner there is one proposal, so this returns 'converge'.
        """
        kwargs: dict = {"proposals": proposals}
        if task_node_id:
            kwargs["task_node_id"] = task_node_id
        result = await self._call("converge_proposals", **kwargs)
        rec = result.get("recommendation", "converge")
        print(f"  converge_proposals → {rec}  ({result.get('reasoning', '')[:80]})")
        return rec

    # ── Planner ───────────────────────────────────────────────────────────────

    async def plan(self) -> tuple[dict | None, list]:
        """Pick the next task and its playbook. Exclusive mode prevents duplicate picks."""
        kwargs: dict = {"limit": 1, "exclusive": True}
        if self.tag:
            kwargs["tag"] = self.tag
        bundle   = await self._call("get_next_task", **kwargs)
        tasks    = bundle.get("tasks", [])
        if not tasks:
            return None, []
        task = tasks[0]

        pb_kwargs: dict = {"situation": task["task"]["title"]}
        if self.tag:
            pb_kwargs["tag"] = self.tag
        pb_result = await self._call("get_playbook", **pb_kwargs)
        playbooks = pb_result.get("playbooks", [])
        return task, playbooks

    # ── Developer (STUB) ──────────────────────────────────────────────────────

    async def develop(self, task: dict, playbooks: list) -> dict:
        """
        STUB — replace with your real agent / AI call.

        Must return a dict:
            title      (str)   title for the proposed knowledge node
            body       (str)   implementation detail / rationale
            confidence (float) 0.0–1.0
            risk_level (str)   "low" | "medium" | "high"
            residues   (list)  [{"title": ..., "body": ..., "tags": [...]}]
        """
        t = task["task"]
        print(f"  task:      {t['title']}")
        print(f"  ancestors: {[a['title'] for a in task.get('ancestors', [])]}")
        print(f"  playbooks: {[p['title'] for p in playbooks]}")
        return {
            "title":      f"Implementation: {t['title']}",
            "body":       "(stub — override WorkLoop.develop() with your agent)",
            "confidence": 0.5,
            "risk_level": "medium",
            "residues":   [],
        }

    # ── Accept (write results back) ───────────────────────────────────────────

    async def accept(self, task: dict, result: dict) -> None:
        task_id = task["task"]["id"]

        # propose_decision → review_queue (human gate unless low-risk + high confidence)
        proposal = await self._call(
            "propose_decision",
            title=result["title"],
            body=result["body"],
            task_node_id=task_id,
            confidence_score=result.get("confidence", 0.7),
            risk_level=result.get("risk_level", "medium"),
            tags=task["task"].get("tags", []),
        )
        impl_id = proposal.get("node_id")
        print(f"  propose_decision → review_id={proposal.get('review_id')}  "
              f"status={proposal.get('status', 'pending')}")

        # submit_outcome → reinforcement + B2/C3 side-effects
        outcome_kwargs: dict = {
            "task_node_id": task_id,
            "outcome":      "success",
            "message":      result["title"],
        }
        if impl_id:
            outcome_kwargs["implementation_node_id"] = impl_id
        outcome = await self._call("submit_outcome", **outcome_kwargs)
        print(f"  submit_outcome  → outcome={outcome.get('outcome')}  "
              f"feature_complete={outcome.get('feature_complete_triggered', False)}")

        # emit_residue → new pending inquiries for the next loop
        residues = result.get("residues") or []
        if residues:
            emitted = await self._call(
                "emit_residue",
                residues=residues,
                parent_task_id=task_id,
            )
            print(f"  emit_residue    → {emitted.get('count', 0)} new inquiry(ies)")

    # ── One full cycle ────────────────────────────────────────────────────────

    async def run_once(self) -> bool:
        """
        Run one planner+developer cycle.
        Returns False when no pending tasks are found.
        """
        task, playbooks = await self.plan()
        if task is None:
            print("  No pending tasks.")
            return False

        result = await self.develop(task, playbooks)
        await self.accept(task, result)
        return True


# ── CLI entry point ───────────────────────────────────────────────────────────

async def _main():
    ap = argparse.ArgumentParser(
        description="Agent-loop harness — planner + developer cycles",
    )
    ap.add_argument("--ws",        required=True,        help="Workspace ID")
    ap.add_argument("--url",       required=True,        help="MemTrace API base URL")
    ap.add_argument("--token",     required=True,        help="API Bearer token (mt_...)")
    ap.add_argument("--tag",       default=None,         help="Filter tasks by tag")
    ap.add_argument("--max-loops", type=int, default=1,  help="Max iterations (default 1)")
    ap.add_argument("--dry-run",   action="store_true",  help="Print calls without executing")
    args = ap.parse_args()

    loop = WorkLoop(
        ws_id=args.ws,
        base_url=args.url,
        token=args.token,
        tag=args.tag,
        dry_run=args.dry_run,
    )
    try:
        for i in range(args.max_loops):
            print(f"\n─── iteration {i + 1}/{args.max_loops} ───")
            if not await loop.should_loop():
                print("Convergence check says stop.")
                break
            if not await loop.run_once():
                break
        print("\nDone.")
    finally:
        await loop.close()


if __name__ == "__main__":
    asyncio.run(_main())
