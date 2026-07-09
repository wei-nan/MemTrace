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

MCP access is configured per machine, not committed to git: copy
`.mcp.json.example` to `.mcp.json` and fill in the real MemTrace URL and API
key. A fresh checkout without this step has no KB access — treat that as the
blocker case above.

Knowledge written back to any KB follows the KB's own 全域行為約束 node
(Traditional Chinese for node content, PII rules, source_type marking). This
file and other repo docs may be in English; the KB constraint governs KB
writes, not repo files.

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

## Task State Machine (Hard Rules)

The Agent Loop is enforced through the MemTrace task tools, not by narrative
discipline. For any work that changes code, schema, migrations, public docs,
KB semantics, or cross-agent workflow, the following are mandatory:

1. **A task node must exist before development starts.** The accepted plan is
   recorded as an inquiry node in the Agent Loop KB (`ws_6aa957c3`). If no
   task node exists, create one first — that node is the `G1` artifact. Use
   `get_next_task` to pick up pending work together with its context bundle.
2. **Claim before touching code.** Call `claim_task` on the inquiry node. If
   it returns `claimed=false`, another agent owns it — do not work on it.
   Claims expire after 30 minutes; re-claim during long-running tasks.
3. **Completion happens only through `submit_outcome`.**
   - `success` / `partial` requires an `implementation_node_id`: the node
     recording what changed, the commands run, and verification evidence —
     the `G2`/`G3` artifact. This evidence, together with the gate verdicts,
     lives in the domain KB (`ws_spec_plan`), linked by edges to the plan and
     development nodes, not in the Agent Loop. `implementation_node_id` may
     therefore be a cross-workspace reference; `submit_outcome` keeps it in the
     task metadata (the `answered_by` edge only forms when both nodes share a
     workspace). Agent Loop retains only the task skeleton and `gate_state`
     control flags. See KB node `mem_41fba6c5` (verification/gate-verdict
     placement).
   - `failed` must still be submitted — it flags the visited playbooks for
     human review instead of hiding the failure.
   - Include `node_sequence` (the nodes consulted) so path reinforcement
     works.
4. **No `submit_outcome`, no done.** A task described as finished in chat or
   in a commit message but lacking a submitted outcome is, by definition, not
   done.
5. **Blocked means release.** When a checkpoint fires or context is missing,
   call `release_task`, write the blocker as an inquiry or decision-draft
   node, and stop.
6. **Gate verdicts are KB artifacts.** A `gate_verdict` exists only if it is
   recorded in the KB (as a node or inside the implementation node). Verbal
   PASS statements in a chat session do not count.

Lightweight path: read-only questions and trivial non-behavioral fixes may
skip the state machine, but any diff that touches product behavior obligates
it — when in doubt, claim.

## Planning Rules

Before editing code or specs, produce or retrieve a plan that names:

- affected files, modules, workspaces, or KB nodes;
- acceptance criteria with observable behavior;
- scope boundaries, especially what is intentionally not included;
- dependencies, credentials, data, or external services needed;
- open questions and whether they block work.

When planning produces many issues or a complex, divergent plan, run the
Plan-stage triage step before `G1`: decompose into independent issues,
strengthen under-specified ones, and classify each by priority tier
(security > correctness > functionality > optimization). Security jumps to the
front; functionality issues pause for a human decision only when a trade-off is
involved. The full rule lives in the Agent Loop KB node `mem_0953dbd0`.

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

When linking KB nodes with `create_edge`, pick the most specific relation that
fits before falling back to the generic `related_to`: use `answered_by` (an
inquiry resolved by an answer), `depends_on` (needs the other to be valid),
`extends` (refines/builds on, directional), or `contradicts`. Do not add a
`related_to` to a pair that already carries one of these — the write path
rejects it. `related_to` / `similar_to` are direction-less: never create both
`a→b` and `b→a`.

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

The verification/acceptance node — and the full gate verdicts, including
`REJECT` records (tag them `gate-reject`) — live in `ws_spec_plan`, linked by
edges to the plan and development nodes. The Agent Loop keeps only the task
skeleton and `gate_state`; it references these domain nodes by id rather than
copying their content. See KB node `mem_41fba6c5`.

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

## Checkpoints: When To Stop And Ask

Stop and ask the user before proceeding when any of these applies:

- an irreversible or outward-facing action (pushing to a shared branch,
  deleting data, releasing/deploying, calling external services) that has not
  been explicitly authorized for this specific instance;
- a trade-off only the user can make: product direction, spending money,
  expanding or cutting scope;
- the same gate has been rejected twice;
- a new conclusion contradicts a high-trust KB node;
- context is insufficient to start and cannot be filled from the KB or the
  repo.

In an interactive session, ask directly and wait for the answer. In
unattended/harness mode, write an inquiry or decision-draft node, mark the
task `status:blocked`, and stop — do not guess and continue.

## Done Definition

A task can be called done only when:

- the task's `submit_outcome` has been recorded (`success`, `partial`, or
  `failed`) per the Task State Machine above;
- the relevant Agent Loop gates have passed or a justified lightweight path was
  used;
- implementation and verification evidence are available;
- discussion, planning, development, and acceptance outcomes have been written
  back to `ws_spec_plan` when meaningful;
- public spec and seed artifacts have been updated when public behavior changed;
- remaining gaps are explicitly recorded instead of hidden.

