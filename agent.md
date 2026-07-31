# MemTrace Agent Operating Guide

This file applies to every AI agent working in this repository, including
Codex, Claude, Gemini, and future model runners. It is a thin pointer, not a
copy of the process it points to — see "Why this file is short" at the end.

## Authority Order

1. Follow the active system, developer, and user instructions first.
2. Follow this `agent.md` for where the real rules live.
3. Query the private Agent Loop KB (`ws_6aa957c3`, workspace name "Agent
   Loop") for the current workflow, gate, handoff, and task-state rules.
   `docs/agent-loop-gates.md` is a repo-side index of the canonical KB node
   IDs for each gate — use it to find the right node, then query that node
   live, since the KB can change without this file or that index changing.
4. Query MemTrace 規格規劃 (`ws_spec_plan`) for product, architecture, and
   planning conclusions.
5. Use repo files, tests, and public spec artifacts as implementation
   evidence.

When these surfaces conflict, do not silently pick one. Record the conflict,
ask for human direction if it changes product behavior, and write the
unresolved item back to `ws_spec_plan`.

## Before non-trivial planning, coding, or review work

- Read this file and `docs/agent-loop-gates.md`.
- Query `ws_6aa957c3` for the workflow/gate/handoff rules that apply, and
  `ws_spec_plan` for product/spec context. Don't rely on a prior session's
  memory of what the gates require — the KB is the source of truth and it
  changes (gates have been merged and added before without this file
  changing).
- Inspect the current repository state before trusting older memory or
  prior conclusions; repo state wins over stale KB or chat recollection.

For read-only answers and trivial non-behavioral fixes, use judgment and keep
this lightweight. For changes to product behavior, schema, public API,
migrations, KB semantics, or cross-agent workflow, follow the KB's process in
full — including its task-claim/submit_outcome mechanics, not a paraphrase of
them.

## MCP setup

MCP access is configured per machine, not committed to git: copy
`.mcp.json.example` to `.mcp.json` and fill in the real MemTrace URL and API
key.

## If MemTrace MCP is unavailable or erroring

Tell the user directly: you cannot reach MemTrace, so you cannot follow the
Agent Loop KB's process right now. Do not fabricate KB content, claim a gate
passed, or claim a task is done without an actual KB write succeeding. Ask
the user how they want to proceed (skip the loop for this change, wait until
MCP is configured/fixed, or file the problem as a KB node yourself once
reachable). This is ordinary AI-human interaction, not a special procedure —
no separate blocker-node choreography needs to live in this file; once you're
back in the KB, its own `全域行為約束` node already covers what to record.

## Why this file is short

Workflow stages, gates, the task state machine, checkpoints, the
done-definition, Release Loop, and public-spec-sync rules live in the KB
(`ws_6aa957c3`) and its repo-side index (`docs/agent-loop-gates.md`) — not
here. A full copy used to live in this file, and it caused real drift: the
KB has merged and added gates since (G2+G3 merged 2026-07-29, Release Loop
added 2026-07-30) without this file being updated to match, so agents reading
only this file were working from a stale process. The KB's own behavioral
rules already say private entry files must not copy the gate rules, only
point to them — this file previously violated that. Query the KB live
instead of trusting this file's memory of it.

Knowledge written back to any KB follows that KB's own 全域行為約束 node
(Traditional Chinese for node content, PII rules, source_type marking). This
file and other repo docs may be in English; the KB constraint governs KB
writes, not repo files.
