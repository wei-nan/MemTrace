# Agent Loop Stage Handoff Gates v4

This document is a readable repo-side pointer for LLMs and operators.
The source of truth is the Agent Loop KB (`ws_6aa957c3`).

**IMPORTANT (2026-07-30):** `gate_state`, `current_stage`, `required_gate`,
`next_allowed_stage`, and `reject_count` are documentation-only conventions.
None of them are read, written, or validated by any server code in
`packages/api/` — confirmed by a full-text search that returned zero hits.
`claim_task`/`release_task` (in-memory TTL) and `submit_outcome` (writes an
`answered_by` edge + `status` column) are the only parts of this that are
actually enforced. Treat the gate pipeline below as agent self-discipline
backed by documentation, not a technical guarantee. See
`ws_spec_plan/mem_c9c4affd`.

## Canonical KB Nodes

- Gate general rules: `mem_929a4e9b`
- Gate verdict schema: `mem_2d23c205`
- G0 Data-plane gate (conditional — any live DB write: migration, backfill,
  seed write, `--write` scripts, raw SQL): `mem_e41ae3a5`
- G1 Plan to Dev: `mem_b86a48aa`
- G2 Dev to Converge (merged, 2026-07-29 — see below): `mem_a39b9b57`
  - Superseded: former G2 Dev to Verify (`mem_7d7fbdd2`), former G3 Verify to
    Coverage (`mem_50b2cd36`). Kept as `resolution_status: superseded` for
    history; do not use them as current policy.
- Agent Loop charter: `mem_c1cc4d99`
- Task loop workflow: `mem_1859526b`
- Planning triage (Plan-stage classify / strengthen / prioritize): `mem_0953dbd0`
- Task node schema: `mem_5e6a82ab`
- Takeover verification playbook (checking the previous stage's "done" claims): `mem_b3158737`
- Spec-Sync gate (G4, conditional — public spec / schema / API changes),
  now executed via Release Loop: `mem_5d8c6ff8`
- Release Loop (PR-to-main, CI-bound agent, trigger paths, workflow split
  from `spec-sync.yml`): `mem_cc085a90`
- Adoption record / rationale for the G2+G3 merge: `ws_spec_plan/mem_bc49c5d1`
- Gap: gate_state mechanism unimplemented server-side: `ws_spec_plan/mem_c9c4affd`

## Rule

Do not copy the full gate policy into model-specific files such as
`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, or system prompts. Those files
should only point models to the KB nodes above.

## Two Pipelines (v4, 2026-07-30)

```text
Agent Loop (dev loop, runs on a feature branch):
  Plan -> G1 -> Dev -> [G0 before any live DB write] -> G2 (merged) -> Converge
                                                                          |
                                                                          v (commit/push)
                                                      CI/CD (clean-env rerun, non-blocking, outside the loop)

Release Loop (runs on PR -> main):
  PR touches trigger paths -> CI-bound agent -> G4 -> blocks merge (no retroactive option)
```

`Verify` and `Coverage` are no longer separate stages in the Agent Loop. Dev
runs its own tests (deterministic work); `G2` audits both scope-fidelity
(former G2) and test-coverage-adequacy (former G3) in one pass, using the
actual test command + output as evidence — a "tests passed" claim is not
sufficient. CI/CD moved outside the Agent Loop entirely: it is a
clean-environment regression check that runs after commit/push, not a gate an
agent waits on mid-loop. A CI failure after a task has already reached
`Converge` is a **retroactive REJECT**: the task moves `status:done` ->
`status:gate-rejected`, `reject_count` increments, and the merged `G2` gate
reruns. Two consecutive REJECTs (including a CI-triggered one) still escalate
to human decision per the existing rule.

**G4/Release Loop does not follow this retroactive pattern** — see the G4
section below for why public-spec sync must block the merge, not follow it.

Each gate is checked by the next stage. The next stage should assume the
previous stage may be incomplete until the gate passes.

## Gate Verdict

Every gate must produce a `gate_verdict` artifact. Missing verdict means
the gate did not pass.

```json
{
  "gate": "G1 | G2 | custom",
  "from_stage": "plan | dev",
  "to_stage": "dev | converge",
  "verdict": "PASS | REJECT",
  "checked": [
    {
      "criterion": "check item",
      "status": "pass | fail | not_applicable",
      "evidence_refs": ["node_id", "file:path", "command:...", "commit:..."]
    }
  ],
  "reasons": ["decision reasons"],
  "missing": ["missing input, evidence, tests, or decisions"],
  "return_to": "plan | dev | human | null",
  "next_allowed_stage": "dev | converge | null",
  "reviewer_model": "model or operator id",
  "ts": "ISO-8601 timestamp"
}
```

A CI-triggered retroactive REJECT (see Pipeline above) reuses this same
schema with `from_stage: "converge"`, `return_to: "dev"`.

## G0: Data-Plane (conditional)

Fires before any action that writes to the live DB: migration, backfill,
seed write, a script run with `--write`, or raw SQL. Otherwise `N/A PASS`,
same convention as G4. Full policy: `mem_e41ae3a5`.

Requires all four:

- scope stated explicitly: `WHERE` clause, affected workspaces, expected row
  count;
- a dry-run first, reporting actual affected row count — mismatch vs.
  expected is REJECT;
- a reversibility statement: backup exists, or the action is explicitly
  marked irreversible;
- human authorization in-session (the SQL/WHERE clause pasted into chat for
  the user to confirm) — an agent may never self-PASS this gate.

## G1: Plan to Dev

Dev must reject the plan unless all are true:

- affected files or modules are listed specifically;
- every requirement has observable acceptance criteria;
- scope boundaries say what is not included;
- dependencies and prerequisites are named;
- open questions are either resolved or recorded as non-blocking inquiries.

## G2: Dev to Converge (merged, 2026-07-29)

One audit, two directions. Full policy: `mem_a39b9b57`. Dev has already run
the tests itself before this gate — the gate requires the actual command +
output as evidence, not a "tests passed" claim.

Scope-fidelity (former G2):

- every plan item has an implementation/evidence match;
- every diff item is in scope or has a written reason;
- no unrelated formatting, dependency, or cleanup changes are mixed in;
- no data-integrity fields (signature, provenance, schema_version) are
  touched beyond what the plan requires;
- no unauthorized live-DB write path is introduced (new write branch, a
  batch operation that bypasses G0, an unconfirmed backfill/migration);
- if the change is a bug fix, it names the bug's *category* and shows the
  same pattern was checked elsewhere, not just at the original report site.

Coverage-adequacy (former G3) — do not skip this half just because scope
fidelity passed; read the test diff itself, a green run or high coverage %
is not sufficient (coverage measures lines executed, not assertion
strength):

- changed functions, branches, APIs, or data paths are listed;
- each changed point maps to unit or e2e coverage;
- new branches and edge cases have assertions, not only happy paths;
- existing tests were not weakened, skipped, or broadened just to pass;
- uncovered gaps are recorded as inquiry/follow-up nodes.

## G4: Spec-Sync (conditional, runs in the Release Loop — not inline in Dev)

A conditional gate that fires only when a change touches public product
behavior, schema, API/MCP contracts, or public spec content; otherwise its
verdict is automatically `N/A PASS`. The seed JSON under `examples/spec-as-kb/`
is the single source of truth — `packages/api/migrations/003_seed_spec_kb.sql`
(the sole canonical output; not in MANIFEST.txt, applied manually per
docs/DEPLOYMENT.md) and the live public KB are generated from it. G4 requires:

- if the public surface changed, the seed JSON changed too (else REJECT);
- the committed seed SQL equals `generate(seed)` — `python scripts/seed_spec_kb.py --check`
  is byte-identical (deterministic);
- zh/en node parity: no en node without a zh source (fail); zh-without-en is a warning;
- new or changed node content is semantically correct (LLM);
- en is a faithful translation of zh (LLM — the only non-deterministic leg);
- schema changes: a fresh install (new baseline) and an existing upgrade
  (incremental migration) converge to the same schema — enforced by
  `core/database.py::assert_schema_version()` at API startup.

**As of 2026-07-30, G4 no longer runs inside a feature branch's Dev stage.**
It runs in the **Release Loop**, triggered on PR-to-`main` by a CI-bound agent,
when the diff touches one of the trigger paths listed below. Full design,
rationale, and the CI-agent execution flow: KB node `mem_cc085a90`
(`ws_6aa957c3`). This is a separate workflow from `spec-sync.yml`:

- `spec-sync.yml` (existing, unchanged): triggers on
  `examples/spec-as-kb/**` / seed SQL / generator changes, runs `--check`,
  blocking. Only guards seed-JSON ↔ seed-SQL ↔ live-KB internal consistency —
  it has no router paths in its trigger list, so it never fires when code
  changes public behavior without touching the seed.
- `release-loop.yml` (new, drafted but **not yet enabled** — needs secrets and
  commit-back permissions review before merging): triggers on PR-to-`main`
  when the diff touches `examples/spec-as-kb/**`, `packages/api/core/constants.py`,
  `packages/api/migrations/**`, `packages/api/services/mcp_tools.py`, or
  `packages/api/routers/{kb,mcp,auth,registration,api_keys,openai_compat,exports}.py`.
  This is what closes the gap above: it runs a CI-bound agent to draft/review
  the zh/en spec content itself, not just check internal consistency.

**Blocking semantics differ from the regular Agent Loop CI backstop above.**
The Agent Loop's post-Converge CI failure is a retroactive REJECT — the task
was already marked done and gets reopened, acceptable because regression tests
are cheap to rerun. G4/Release Loop is a pre-merge hard gate with no
retroactive option: a public spec is an external commitment and must not reach
`main` in a wrong state in the first place.

After editing seed JSON by hand, refresh the generated SQL with
`python scripts/seed_spec_kb.py --write`.

## Reject Handling

- `REJECT` must include `return_to`, `missing`, and `reasons`.
- The same gate rejected twice should escalate to an inquiry or human decision.
- A task cannot advance unless `gate_verdict.verdict` is `PASS`.
- A CI failure discovered after `Converge` counts as a REJECT of that task's
  merged `G2` (retroactive): `status:done` -> `status:gate-rejected`,
  `reject_count` increments, same two-strikes escalation rule applies.
