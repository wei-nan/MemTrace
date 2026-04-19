from __future__ import annotations

from difflib import ndiff
from typing import Any


NODE_DIFF_FIELDS = [
    "title_zh",
    "title_en",
    "content_type",
    "content_format",
    "body_zh",
    "body_en",
    "tags",
    "visibility",
]


def _normalize_snapshot(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    data = snapshot or {}
    return {
        "title_zh": data.get("title_zh", ""),
        "title_en": data.get("title_en", ""),
        "content_type": data.get("content_type", ""),
        "content_format": data.get("content_format", ""),
        "body_zh": data.get("body_zh", ""),
        "body_en": data.get("body_en", ""),
        "tags": list(data.get("tags") or []),
        "visibility": data.get("visibility", "private"),
    }


def _line_diff(before: str, after: str) -> list[dict[str, str]]:
    lines: list[dict[str, str]] = []
    for line in ndiff(before.splitlines(), after.splitlines()):
        prefix = line[:2]
        value = line[2:]
        if prefix == "- ":
            lines.append({"op": "remove", "text": value})
        elif prefix == "+ ":
            lines.append({"op": "add", "text": value})
        elif prefix == "  ":
            lines.append({"op": "keep", "text": value})
    return lines


def build_node_diff(
    before_snapshot: dict[str, Any] | None,
    after_snapshot: dict[str, Any] | None,
    change_type: str,
) -> dict[str, Any]:
    before = _normalize_snapshot(before_snapshot)
    after = _normalize_snapshot(after_snapshot)

    fields: dict[str, Any] = {}
    changed_fields: list[str] = []

    for field in NODE_DIFF_FIELDS:
        prev = before.get(field)
        nxt = after.get(field)
        if change_type == "create":
            if field in ("body_zh", "body_en"):
                fields[field] = {
                    "type": "text",
                    "before": "",
                    "after": nxt,
                    "line_diff": _line_diff("", nxt or ""),
                }
            elif field == "tags":
                fields[field] = {"type": "set", "added": list(nxt or []), "removed": []}
            else:
                fields[field] = {"type": "scalar", "before": None, "after": nxt}
            changed_fields.append(field)
            continue

        if change_type == "delete":
            if field in ("body_zh", "body_en"):
                fields[field] = {
                    "type": "text",
                    "before": prev,
                    "after": "",
                    "line_diff": _line_diff(prev or "", ""),
                }
            elif field == "tags":
                fields[field] = {"type": "set", "added": [], "removed": list(prev or [])}
            else:
                fields[field] = {"type": "scalar", "before": prev, "after": None}
            changed_fields.append(field)
            continue

        if field == "tags":
            added = [tag for tag in (nxt or []) if tag not in (prev or [])]
            removed = [tag for tag in (prev or []) if tag not in (nxt or [])]
            if added or removed:
                fields[field] = {"type": "set", "added": added, "removed": removed}
                changed_fields.append(field)
            continue

        if field in ("body_zh", "body_en"):
            if (prev or "") != (nxt or ""):
                fields[field] = {
                    "type": "text",
                    "before": prev,
                    "after": nxt,
                    "line_diff": _line_diff(prev or "", nxt or ""),
                }
                changed_fields.append(field)
            continue

        if prev != nxt:
            fields[field] = {"type": "scalar", "before": prev, "after": nxt}
            changed_fields.append(field)

    return {
        "change_type": change_type,
        "changed_fields": changed_fields,
        "field_count": len(changed_fields),
        "fields": fields,
    }

