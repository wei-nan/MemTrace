"""Unit tests for check_doc_drift.py. Run: python3 -m pytest scripts/test_check_doc_drift.py -q

Two kinds of coverage on purpose:
  - extractors run against the *real* repo files, so a genuine future drift
    (e.g. someone adds a relation to constants.py but not SPEC.md) is caught
    here too, not just by the CLI in CI.
  - the ratchet/diff logic (A2-A4 scenarios) is tested against synthetic
    in-memory data, not by mutating real repo files -- corrupting
    constants.py to prove a negative case is exactly the kind of stunt this
    checker exists to make unnecessary.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_doc_drift as cdd


# ─── extractors against the real repo (smoke + real-drift coverage) ───────


def test_valid_relations_matches_spec_enum():
    code = cdd.extract_valid_relations()
    doc = cdd.extract_spec_relation_enum(cdd.SPEC_MD.read_text())
    assert code is not None and doc is not None
    assert code == doc


def test_specific_relations_matches_spec_409_list():
    code = cdd.extract_specific_relations()
    doc = cdd.extract_spec_specific_relations(cdd.SPEC_MD.read_text())
    assert code is not None and doc is not None
    assert code == doc


def test_relation_weights_match_effective_value_including_fallback():
    code = cdd.extract_relation_weights()
    doc = cdd.extract_contract_relation_weights(cdd.MCP_CONTRACT_MD.read_text())
    valid_relations = cdd.extract_valid_relations()
    assert code is not None and doc is not None and valid_relations is not None
    for relation in valid_relations:
        assert doc.get(relation) == code.get(relation, 1.0), relation


def test_negative_weight_literal_is_read_correctly():
    # contradicts: -1.0 is a UnaryOp(USub, Constant) in ast, not a plain
    # Constant -- regression test for that parsing edge case specifically.
    code = cdd.extract_relation_weights()
    assert code["contradicts"] == -1.0


def test_tools_extraction_is_nonempty_and_well_formed():
    tools = cdd.extract_tools()
    assert tools is not None
    assert "get_node" in tools
    assert "workspace_id" in tools["get_node"]["properties"]
    assert "node_id" in tools["get_node"]["required"]


def test_baseline_file_is_internally_consistent_with_current_repo_state():
    """The checked-in baseline must equal what --update-baseline would produce
    right now. If this fails, someone edited the baseline by hand without
    running --update-baseline, or forgot to refresh it after a fix."""
    baseline = cdd.load_baseline()
    tools = cdd.extract_tools()
    tool_sections = cdd.extract_contract_tool_sections(cdd.MCP_CONTRACT_MD.read_text())
    assert tools is not None
    current_missing = sorted(name for name in tools if name not in tool_sections)
    assert current_missing == sorted(baseline.get("missing_tool_sections", []))


# ─── parse_input_fields: table form, inline form, low-confidence SKIP ─────


def test_parse_input_fields_table_form():
    section = """Some description.

**Input**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `workspace_id` | string | required | Workspace ID |
| `limit` | integer | | Max results |

**Output**: stuff
"""
    fields, confident = cdd.parse_input_fields(section)
    assert confident is True
    assert fields == {"workspace_id", "limit"}


def test_parse_input_fields_inline_form_with_type_annotation():
    section = "**Input**: `workspace_id`, `node_ids: string[]`, `new_author_id`\n\n---\n"
    fields, confident = cdd.parse_input_fields(section)
    assert confident is True
    assert fields == {"workspace_id", "node_ids", "new_author_id"}


def test_parse_input_fields_none_marker():
    section = "**Input**: _(none)_\n\n**Output**: stuff\n"
    fields, confident = cdd.parse_input_fields(section)
    assert confident is True
    assert fields == set()


def test_parse_input_fields_missing_input_line_is_low_confidence():
    section = "Some description with no Input line at all.\n\n**Output**: stuff\n"
    fields, confident = cdd.parse_input_fields(section)
    assert confident is False
    assert fields is None


def test_parse_input_fields_unparseable_inline_prose_is_low_confidence():
    # A description sentence that happens to contain backticked non-identifier
    # text on the **Input** line must not be guessed at.
    section = "**Input**: see `POST /api/v1/mcp` for the full envelope.\n\n---\n"
    fields, confident = cdd.parse_input_fields(section)
    assert confident is False
    assert fields is None


# ─── ratchet logic: A2-A4 scenarios via synthetic data (no file mutation) ─


def test_a2_new_item_not_in_baseline_fails():
    # Simulates: constants.py gains a relation SPEC.md doesn't document yet.
    current_missing_sections = {"a_fake_new_tool"}
    baseline = set()
    newly, fixed = cdd.diff_baseline_set(current_missing_sections, baseline)
    assert newly == ["a_fake_new_tool"]
    assert fixed == []


def test_a3_baseline_entry_removed_while_still_drifting_fails():
    # Simulates: someone hand-edits the baseline to drop a tool that is
    # actually still undocumented -- diff must still flag it as "newly bad"
    # relative to the (now smaller) baseline.
    current_missing_sections = {"still_broken_tool"}
    baseline = set()  # entry was manually removed from baseline
    newly, fixed = cdd.diff_baseline_set(current_missing_sections, baseline)
    assert "still_broken_tool" in newly


def test_a4_baseline_entry_fixed_but_not_removed_fails():
    # Simulates: someone documents a baseline tool's missing param but leaves
    # the baseline entry in place -- the ratchet must demand its removal.
    current_param_drift = {}  # `foo_tool` no longer has a missing `bar` param
    baseline_param_drift = {"foo_tool": ["bar"]}
    messages = cdd.diff_baseline_params(current_param_drift, baseline_param_drift)
    assert any("foo_tool" in m and "移除" in m for m in messages)


def test_baseline_worsening_beyond_existing_entry_fails():
    # A baseline tool that was missing 1 param is now missing 2 -- the extra
    # one must fail even though the tool itself is already in the baseline.
    current_param_drift = {"foo_tool": ["bar", "baz"]}
    baseline_param_drift = {"foo_tool": ["bar"]}
    messages = cdd.diff_baseline_params(current_param_drift, baseline_param_drift)
    assert any("foo_tool" in m and "baz" in m for m in messages)


def test_baseline_entry_unchanged_produces_no_message():
    current_param_drift = {"foo_tool": ["bar"]}
    baseline_param_drift = {"foo_tool": ["bar"]}
    messages = cdd.diff_baseline_params(current_param_drift, baseline_param_drift)
    assert messages == []
