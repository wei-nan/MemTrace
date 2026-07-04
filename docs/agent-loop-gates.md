# Agent Loop Stage Handoff Gates v2

This document is a readable repo-side pointer for LLMs and operators.
The source of truth is the Agent Loop KB (`ws_6aa957c3`).

## Canonical KB Nodes

- Gate general rules: `mem_929a4e9b`
- Gate verdict schema: `mem_2d23c205`
- G1 Plan to Dev: `mem_b86a48aa`
- G2 Dev to Verify: `mem_7d7fbdd2`
- G3 Verify to Coverage: `mem_50b2cd36`
- Agent Loop charter: `mem_c1cc4d99`
- Task loop workflow: `mem_1859526b`
- Task node schema: `mem_5e6a82ab`
- Takeover verification playbook (checking the previous stage's "done" claims): `mem_b3158737`

## Rule

Do not copy the full gate policy into model-specific files such as
`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, or system prompts. Those files
should only point models to the KB nodes above.

## Pipeline

```text
Plan -> G1 -> Dev -> G2 -> Verify -> G3 -> Coverage -> Converge
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
- the change does not violate trust or safety constraints.

## G3: Verify to Coverage

Coverage audit must question whether verification itself is meaningful:

- changed functions, branches, APIs, or data paths are listed;
- each changed point maps to unit or e2e coverage;
- new branches and edge cases have assertions, not only happy paths;
- existing tests were not weakened, skipped, or broadened just to pass;
- uncovered gaps are recorded as inquiry/follow-up nodes.

## Reject Handling

- `REJECT` must include `return_to`, `missing`, and `reasons`.
- The same gate rejected twice should escalate to an inquiry or human decision.
- A task cannot advance unless `gate_verdict.verdict` is `PASS`.
