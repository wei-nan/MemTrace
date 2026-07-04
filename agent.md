# MemTrace Agent Operating Guide

This file applies to every AI agent working in this repository, including
Codex, Claude, Gemini, and future model runners. Treat it as the local project
entry point for agent behavior.

## Authority Order

1. Follow the active system, developer, and user instructions first.
2. Follow this `agent.md` for repository-specific operating rules.
3. Use the private Agent Loop KB as the source of truth for workflow mechanics.
4. Use MemTrace 規格規劃 (`ws_spec_plan`) as the source of truth for product,
   architecture, and planning conclusions.
5. Use repo files, tests, and public spec artifacts as implementation evidence.

When these surfaces conflict, do not silently choose one. Record the conflict,
ask for human direction if the conflict changes product behavior, and write the
unresolved item back to `ws_spec_plan`.

## Required Knowledge Sources

Before non-trivial planning, coding, or review work:

- Read this file.
- Read `docs/agent-loop-gates.md`.
- Query the private Agent Loop workspace (`ws_6aa957c3`, "Agent Loop") for the
  current workflow, gate, handoff, and task-state rules.
- Query `ws_spec_plan` for product/spec context related to the requested work.
- Inspect the current repository state before trusting older memory or prior
  conclusions.

If MemTrace tools are unavailable, record that as a blocker or limitation in the
handoff. Do not claim that KB read/write-back happened unless it actually did.

## Agent Loop Workflow

Use the Agent Loop pipeline for meaningful project work:

```text
Plan -> G1 -> Dev -> G2 -> Verify -> G3 -> Coverage -> Converge
```

The gate rules live in the private Agent Loop KB and are summarized in
`docs/agent-loop-gates.md`. The short rule is:

- `G1` checks whether the plan is specific enough to implement.
- `G2` checks whether the diff faithfully matches the plan and did not add
  unrelated work.
- `G3` checks whether verification meaningfully covers the changed behavior.
- Every gate needs a `gate_verdict` artifact.
- Missing `gate_verdict` means the stage did not pass.
- Only `PASS` may advance to the next stage.

For small read-only answers, use judgment and keep the process lightweight. For
changes to product behavior, schema, public API, public docs, migrations, KB
semantics, or cross-agent workflow, run the full loop.

## Planning Rules

Before editing code or specs, produce or retrieve a plan that names:

- affected files, modules, workspaces, or KB nodes;
- acceptance criteria with observable behavior;
- scope boundaries, especially what is intentionally not included;
- dependencies, credentials, data, or external services needed;
- open questions and whether they block work.

If the problem is still a discussion or research topic, keep it in planning.
Do not open or execute a development task until the scope has passed `G1`.

All meaningful discussion and planning outcomes must be written back to
`ws_spec_plan` as one of:

- a settled decision;
- an inquiry;
- an implementation gap;
- a development handoff;
- an acceptance or verification result.

Keep Agent Loop and `ws_spec_plan` separate: Agent Loop stores process mechanics,
handoff state, gates, and workflow trials; `ws_spec_plan` stores product and
architecture decisions.

## Development Rules

During implementation:

- Keep changes scoped to the accepted plan.
- Do not mix unrelated refactors, formatting, dependency churn, or cleanup into
  a feature/fix unless the plan explicitly includes them.
- Prefer existing project patterns over new abstractions.
- Update tests with the same risk level as the change.
- Preserve user or collaborator changes already present in the worktree.
- Record important implementation evidence for `G2`: files changed, commands
  run, tests added, and behavior observed.

If you discover new product questions during development, pause or split the
work. Write the question to `ws_spec_plan` instead of burying it in code.

## Verification And Acceptance

Verification is not complete until it can answer both questions:

- Did the implementation satisfy every accepted requirement?
- Did the implementation avoid changes outside the accepted scope?

Coverage review is not complete until it can answer:

- Which changed functions, APIs, branches, data paths, or user workflows were
  tested?
- Which changed points are still uncovered, and why?
- Were any tests weakened, skipped, or broadened only to make the run pass?

Development and acceptance outcomes must be written back to `ws_spec_plan`.
Include concise evidence: diff summary, test commands, pass/fail status, known
gaps, and the final acceptance decision.

## Public Spec Synchronization

When final development changes public product behavior, schema, API contracts,
MCP contracts, workflow semantics, or user-visible guarantees, the work is not
done until the public specification surfaces are updated.

Update all applicable surfaces:

- public Chinese spec KB: `ws_spec0001`;
- public English spec KB: `ws_spec0001_en`;
- repo public specification document: `docs/SPEC.md`;
- bilingual seed nodes under `examples/spec-as-kb/nodes/zh/` and
  `examples/spec-as-kb/nodes/en/`;
- seed edges under `examples/spec-as-kb/edges/`;
- seed or migration helpers such as `scripts/seed_spec_kb.py` and
  `docs/schema-history/` when the change affects bootstrap data or schema
  history.

Do not copy private planning text directly into public specs. Convert it into
stable public product language, in Chinese and English, and preserve private
discussion details in `ws_spec_plan`.

## Done Definition

A task can be called done only when:

- the relevant Agent Loop gates have passed or a justified lightweight path was
  used;
- implementation and verification evidence are available;
- discussion, planning, development, and acceptance outcomes have been written
  back to `ws_spec_plan` when meaningful;
- public spec and seed artifacts have been updated when public behavior changed;
- remaining gaps are explicitly recorded instead of hidden.

