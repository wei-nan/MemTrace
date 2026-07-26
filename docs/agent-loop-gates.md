# Agent Loop Stage Handoff Gates v2

This document is a readable repo-side pointer for LLMs and operators.
The source of truth is the Agent Loop KB (`ws_6aa957c3`).

## Canonical KB Nodes

- Gate general rules: `mem_929a4e9b`
- Gate verdict schema: `mem_2d23c205`
- G0 Data-plane gate (conditional — any live DB write: migration, backfill,
  seed write, `--write` scripts, raw SQL): `mem_e41ae3a5`
- G1 Plan to Dev: `mem_b86a48aa`
- G2 Dev to Verify: `mem_7d7fbdd2`
- G3 Verify to Coverage: `mem_50b2cd36`
- Agent Loop charter: `mem_c1cc4d99`
- Task loop workflow: `mem_1859526b`
- Planning triage (Plan-stage classify / strengthen / prioritize): `mem_0953dbd0`
- Task node schema: `mem_5e6a82ab`
- Takeover verification playbook (checking the previous stage's "done" claims): `mem_b3158737`
- Spec-Sync gate (G4, conditional — public spec / schema / API changes): `mem_5d8c6ff8`

## Rule

Do not copy the full gate policy into model-specific files such as
`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, or system prompts. Those files
should only point models to the KB nodes above.

## Pipeline

```text
Plan -> G1 -> Dev -> [G0 before any live DB write] -> G2 -> Verify -> G3 -> Coverage -> Converge
```

Each gate is checked by the next stage. The next stage should assume the
previous stage may be incomplete until the gate passes.

## Gate Verdict

Every gate must produce a `gate_verdict` artifact. Missing verdict means
the gate did not pass.

```json
{
  "gate": "G1 | G2 | G3 | custom",
  "from_stage": "plan | dev | verify | coverage",
  "to_stage": "dev | verify | coverage | converge",
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
  "return_to": "plan | dev | verify | human | null",
  "next_allowed_stage": "dev | verify | coverage | converge | null",
  "reviewer_model": "model or operator id",
  "ts": "ISO-8601 timestamp"
}
```

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

## G2: Dev to Verify

Verify must compare the plan and the diff in both directions:

- every plan item has an implementation/evidence match;
- every diff item is in scope or has a written reason;
- no unrelated formatting, dependency, or cleanup changes are mixed in;
- no data-integrity fields (signature, provenance, schema_version) are
  touched beyond what the plan requires;
- no unauthorized live-DB write path is introduced (new write branch, a
  batch operation that bypasses G0, an unconfirmed backfill/migration);
- if the change is a bug fix, it names the bug's *category* and shows the
  same pattern was checked elsewhere, not just at the original report site.

## G3: Verify to Coverage

Coverage audit must question whether verification itself is meaningful:

- changed functions, branches, APIs, or data paths are listed;
- each changed point maps to unit or e2e coverage;
- new branches and edge cases have assertions, not only happy paths;
- existing tests were not weakened, skipped, or broadened just to pass;
- uncovered gaps are recorded as inquiry/follow-up nodes.

## G4: Spec-Sync (conditional)

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

Mechanized as a blocking CI gate in `.github/workflows/spec-sync.yml`. After
editing seed JSON, refresh the generated SQL with `python scripts/seed_spec_kb.py --write`.

## Reject Handling

- `REJECT` must include `return_to`, `missing`, and `reasons`.
- The same gate rejected twice should escalate to an inquiry or human decision.
- A task cannot advance unless `gate_verdict.verdict` is `PASS`.
