#!/usr/bin/env python3
"""Doc <-> code drift checker with a baseline ratchet.

Checks two lines that `spec-sync.yml` does not cover (it only guards
seed JSON <-> seed SQL <-> live public KB):

  1. docs/SPEC.md relation ENUM        <-> constants.VALID_RELATIONS
  2. docs/SPEC.md 409 specific-relation list <-> constants.SPECIFIC_RELATIONS
  3. mcp-contract.md Relations weight table  <-> mcp_tools.RELATION_WEIGHTS
     (compared against the effective value, i.e. RELATION_WEIGHTS.get(r, 1.0),
     since the runtime code falls back to 1.0 for relations with no explicit
     weight)
  4. mcp-contract.md tool-section coverage   <-> mcp_tools.TOOLS[].name
  5. mcp-contract.md **Input** field list    <-> TOOLS[].inputSchema.properties

Checks 1-3 are enforced strictly (no baseline): the repo state at the time
this checker was written has zero drift on these three, so any drift going
forward is a new regression. Checks 4-5 start with a large amount of existing
debt (see doc_drift_baseline.json) and use a baseline ratchet instead:

  - An item already in the baseline does not fail the build.
  - A *new* item (not in the baseline) fails the build.
  - A baseline item that gets *worse* (more missing params) fails the build.
  - A baseline item that gets *fixed* also fails the build, with a message to
    remove it from the baseline -- otherwise the baseline only ever grows.

`mcp_tools.py` cannot be imported directly here: importing it pulls in
`core.config`, which raises via pydantic if DATABASE_URL/SECRET_KEY are unset
(true for a bare CI checkout). So both `constants.py` and `mcp_tools.py` are
parsed with `ast` instead of imported. Anything this script cannot parse with
confidence is SKIPped and printed, never silently treated as a FAIL or a
silent PASS -- a false positive here would train people to ignore (or worse,
disable) the gate, which is worse than not having it.

See ws_spec_plan/mem_388cc8e4 (plan) and mem_3ff41f7b (originating gap).
"""
import argparse
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONSTANTS_PY = ROOT / "packages/api/core/constants.py"
MCP_TOOLS_PY = ROOT / "packages/api/services/mcp_tools.py"
SPEC_MD = ROOT / "docs/SPEC.md"
MCP_CONTRACT_MD = ROOT / "packages/api/docs/mcp-contract.md"
BASELINE_JSON = Path(__file__).resolve().parent / "doc_drift_baseline.json"


# ─── code-side extraction (ast, no import) ─────────────────────────────────


def _find_assign_value(tree: ast.AST, varname: str):
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == varname for t in node.targets
        ):
            return node.value
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == varname
        ):
            return node.value
    return None


def _frozenset_literal_strings(tree: ast.AST, varname: str):
    """Extract string elements from `VAR = frozenset({"a", "b", ...})`."""
    value = _find_assign_value(tree, varname)
    if not (isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "frozenset"):
        return None
    if not value.args or not isinstance(value.args[0], ast.Set):
        return None
    return {
        elt.value
        for elt in value.args[0].elts
        if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
    }


def extract_valid_relations():
    return _frozenset_literal_strings(ast.parse(CONSTANTS_PY.read_text()), "VALID_RELATIONS")


def extract_specific_relations():
    return _frozenset_literal_strings(ast.parse(CONSTANTS_PY.read_text()), "SPECIFIC_RELATIONS")


def _numeric_literal(node):
    """Read a numeric literal, including negative ones (`-1.0` parses as a
    UnaryOp(USub, Constant(1.0)) in ast, not a plain Constant)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, ast.USub)
        and isinstance(node.operand, ast.Constant)
        and isinstance(node.operand.value, (int, float))
    ):
        return -node.operand.value
    return None


def extract_relation_weights():
    """Extract {relation: weight} from `RELATION_WEIGHTS = {...}` (literal values only)."""
    value = _find_assign_value(ast.parse(MCP_TOOLS_PY.read_text()), "RELATION_WEIGHTS")
    if not isinstance(value, ast.Dict):
        return None
    weights = {}
    for k, v in zip(value.keys, value.values):
        if not (isinstance(k, ast.Constant) and isinstance(k.value, str)):
            continue
        num = _numeric_literal(v)
        if num is not None:
            weights[k.value] = num
    return weights


def _dict_literal_to_ast_map(node):
    """dict AST node -> {literal_str_key: value_ast_node}, skipping non-literal keys."""
    if not isinstance(node, ast.Dict):
        return {}
    out = {}
    for k, v in zip(node.keys, node.values):
        if isinstance(k, ast.Constant) and isinstance(k.value, str):
            out[k.value] = v
    return out


def extract_tools():
    """Return {tool_name: {"properties": set[str], "required": set[str]}}.

    Only string-literal dict keys are read; non-literal values elsewhere in
    the same dict (e.g. an `enum` built via `sorted(list(...))`) are ignored
    since only property *names*, not their schemas, are compared.
    """
    value = _find_assign_value(ast.parse(MCP_TOOLS_PY.read_text()), "TOOLS")
    if not isinstance(value, ast.List):
        return None
    tools = {}
    for elt in value.elts:
        entry = _dict_literal_to_ast_map(elt)
        name_node = entry.get("name")
        if not isinstance(name_node, ast.Constant) or not isinstance(name_node.value, str):
            continue
        name = name_node.value
        props, required = set(), set()
        schema_map = _dict_literal_to_ast_map(entry.get("inputSchema"))
        props_node = schema_map.get("properties")
        if isinstance(props_node, ast.Dict):
            for pk in props_node.keys:
                if isinstance(pk, ast.Constant) and isinstance(pk.value, str):
                    props.add(pk.value)
        required_node = schema_map.get("required")
        if isinstance(required_node, ast.List):
            for rk in required_node.elts:
                if isinstance(rk, ast.Constant) and isinstance(rk.value, str):
                    required.add(rk.value)
        tools[name] = {"properties": props, "required": required}
    return tools


# ─── doc-side extraction (regex, best-effort with confidence gating) ──────


def extract_spec_relation_enum(text: str):
    m = re.search(r"\|\s*`relation`\s*\|\s*ENUM\s*\|\s*(.+?)\s*\|\s*$", text, re.MULTILINE)
    if not m:
        return None
    cell = re.sub(r"_\([^)]*\)_", "", m.group(1))
    parts = [p.strip().strip("`") for p in cell.split("/")]
    parts = [p for p in parts if p]
    return set(parts) if parts else None


def extract_spec_specific_relations(text: str):
    m = re.search(
        r"on a pair already joined by a specific relation\s*\((.+?)\)\s*[—-]",
        text,
        re.DOTALL,
    )
    if not m:
        return None
    names = re.findall(r"`([a-z_]+)`", m.group(1))
    return set(names) if names else None


def extract_contract_relation_weights(text: str):
    parts = text.split("### Relations", 1)
    if len(parts) < 2:
        return None
    body = parts[1].split("\n### ", 1)[0].split("\n## ", 1)[0]
    weights = {}
    for line in body.splitlines():
        m = re.match(r"\|\s*`([a-z_]+)`\s*\|\s*(-?[\d.]+)\s*\|", line.strip())
        if m:
            weights[m.group(1)] = float(m.group(2))
    return weights or None


TOOL_HEADER_RE = re.compile(r"(?m)^### `([a-zA-Z_][a-zA-Z0-9_]*)`\s*$")


def extract_contract_tool_sections(text: str):
    ref = text.split("## Tool Reference", 1)
    if len(ref) < 2:
        return {}
    body = ref[1].split("\n## Schemas", 1)[0]
    parts = TOOL_HEADER_RE.split(body)
    sections = {}
    for i in range(1, len(parts), 2):
        sections[parts[i]] = parts[i + 1]
    return sections


INPUT_TABLE_ROW = re.compile(r"^\|\s*`([a-zA-Z_][a-zA-Z0-9_]*)`\s*\|")


def parse_input_fields(section_text: str):
    """Return (fields: set|None, confident: bool).

    Table form is tried first (matches the majority of tool docs); inline
    prose form (`` **Input**: `a`, `b` (optional) ``) is the fallback. If
    neither can be read with confidence, return (None, False) -- the caller
    must SKIP, not guess.
    """
    m = re.search(r"\*\*Input\*\*:(.*?)(?=\n\*\*Output\*\*|\Z)", section_text, re.DOTALL)
    if not m:
        return None, False
    block = m.group(1)
    stripped = block.strip()
    if stripped.startswith("_(none)_"):
        return set(), True

    fields, found_table = set(), False
    for line in block.splitlines():
        row = INPUT_TABLE_ROW.match(line.strip())
        if row:
            found_table = True
            fields.add(row.group(1))
    if found_table:
        return fields, True

    first_line = stripped.splitlines()[0] if stripped else ""
    tokens = re.findall(r"`([^`]+)`", first_line)
    if not tokens:
        return None, False
    fields = set()
    for tok in tokens:
        name = tok.split(":", 1)[0].strip()
        if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
            fields.add(name)
        else:
            return None, False
    return fields, True


# ─── pure comparison helpers (unit-testable without touching real files) ──


def diff_baseline_set(current: set, baseline: set):
    """-> (newly_bad, now_fixed). `current` is items that ARE a problem now."""
    return sorted(current - baseline), sorted(baseline - current)


def diff_baseline_params(current: dict, baseline: dict):
    """current/baseline: {tool_name: [missing_param, ...]}.

    -> list of FAIL message strings.
    """
    messages = []
    for name, missing in current.items():
        base_missing = set(baseline.get(name, []))
        new_missing = set(missing) - base_missing
        if new_missing:
            messages.append(
                f"`{name}` 新增未文件化參數（不在 baseline）: {sorted(new_missing)}"
            )
    for name, base_missing in baseline.items():
        cur_missing = set(current.get(name, []))
        resolved = set(base_missing) - cur_missing
        if resolved:
            messages.append(
                f"`{name}` 的 baseline 缺漏欄位已補文件（{sorted(resolved)}），需從 baseline 移除"
            )
    return messages


# ─── main ───────────────────────────────────────────────────────────────


def load_baseline():
    if BASELINE_JSON.exists():
        return json.loads(BASELINE_JSON.read_text())
    return {"missing_tool_sections": [], "param_drift": {}}


def run(update_baseline: bool) -> int:
    skips, strict_failures = [], []
    baseline = load_baseline()

    valid_relations = extract_valid_relations()
    specific_relations = extract_specific_relations()
    relation_weights = extract_relation_weights()
    tools = extract_tools()

    spec_text = SPEC_MD.read_text()
    contract_text = MCP_CONTRACT_MD.read_text()

    spec_relations = extract_spec_relation_enum(spec_text)
    spec_specific = extract_spec_specific_relations(spec_text)
    contract_weights = extract_contract_relation_weights(contract_text)
    tool_sections = extract_contract_tool_sections(contract_text)

    # Check 1
    if valid_relations is None or spec_relations is None:
        skips.append("check1: relation ENUM 無法解析（code 或 doc 端），SKIP")
    elif valid_relations != spec_relations:
        strict_failures.append(
            "check1: SPEC.md relation ENUM 與 constants.VALID_RELATIONS 不一致 — "
            f"doc-only={sorted(spec_relations - valid_relations)}, "
            f"code-only={sorted(valid_relations - spec_relations)}"
        )

    # Check 2
    if specific_relations is None or spec_specific is None:
        skips.append("check2: 409 specific-relation 清單無法解析，SKIP")
    elif specific_relations != spec_specific:
        strict_failures.append(
            "check2: SPEC.md 409 規則清單與 constants.SPECIFIC_RELATIONS 不一致 — "
            f"doc-only={sorted(spec_specific - specific_relations)}, "
            f"code-only={sorted(specific_relations - spec_specific)}"
        )

    # Check 3 (compared against the runtime-effective weight, fallback = 1.0)
    if relation_weights is None or contract_weights is None or valid_relations is None:
        skips.append("check3: relation weight 表無法解析，SKIP")
    else:
        for relation in sorted(valid_relations):
            effective = relation_weights.get(relation, 1.0)
            documented = contract_weights.get(relation)
            if documented is None:
                strict_failures.append(f"check3: mcp-contract.md Relations 表缺少 `{relation}`")
            elif documented != effective:
                strict_failures.append(
                    f"check3: `{relation}` weight 不符 — code(effective, incl. .get(r,1.0) fallback)={effective}, doc={documented}"
                )

    # Check 4 + 5 (baseline-ratcheted)
    current_missing_sections = []
    current_param_drift = {}
    if tools is None:
        skips.append("check4/5: TOOLS 清單無法解析，SKIP")
    else:
        current_missing_sections = sorted(name for name in tools if name not in tool_sections)
        for name, schema in tools.items():
            if name not in tool_sections:
                continue
            fields, confident = parse_input_fields(tool_sections[name])
            if not confident:
                skips.append(f"check5: `{name}` 的 **Input** 格式無法自信解析，SKIP")
                continue
            missing = sorted(schema["properties"] - fields)
            if missing:
                current_param_drift[name] = missing

    baseline_failures = []
    if tools is not None:
        newly, fixed = diff_baseline_set(
            set(current_missing_sections), set(baseline.get("missing_tool_sections", []))
        )
        if newly:
            baseline_failures.append(f"check4: 新增未文件化 tool（不在 baseline）: {newly}")
        if fixed:
            baseline_failures.append(f"check4: baseline 內的 tool 已補文件，需從 baseline 移除: {fixed}")
        baseline_failures.extend(
            f"check5: {msg}"
            for msg in diff_baseline_params(current_param_drift, baseline.get("param_drift", {}))
        )

    for s in skips:
        print(f"SKIP: {s}")

    if update_baseline:
        if tools is not None:
            BASELINE_JSON.write_text(
                json.dumps(
                    {
                        "missing_tool_sections": current_missing_sections,
                        "param_drift": {k: sorted(v) for k, v in current_param_drift.items()},
                    },
                    indent=2,
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )
            print(f"Baseline updated: {BASELINE_JSON}")
        else:
            print("Baseline NOT updated: TOOLS could not be parsed.")
        for f in strict_failures:
            print(f"FAIL (not baseline-eligible, still blocking): {f}")
        return 1 if strict_failures else 0

    all_failures = strict_failures + baseline_failures
    for f in all_failures:
        print(f"FAIL: {f}")
    if all_failures:
        return 1
    print("OK: no drift beyond baseline")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check for drift (default action)")
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Recompute doc_drift_baseline.json from current repo state (checks 4-5 only)",
    )
    args = parser.parse_args()
    if args.update_baseline:
        return run(update_baseline=True)
    return run(update_baseline=False)


if __name__ == "__main__":
    sys.exit(main())
