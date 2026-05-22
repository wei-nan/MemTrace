"""
core/compat.py — Phase 6 backward-compatibility helpers.

During the one-sprint grace period after Phase 6, callers may still send
legacy bilingual field names.  The Pydantic models accept these aliases,
map them to canonical Phase-6 fields, and the routers set Deprecation
response headers so clients know to update.

Removal target: Phase 6.1 (see docs/dev/phase6-deprecation.md).
"""
from __future__ import annotations

# ── Public constants ──────────────────────────────────────────────────────────

LEGACY_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "title_zh",
        "title_en",
        "body_zh",
        "body_en",
        "name_zh",
        "name_en",
    }
)

#: RFC 8594 "Deprecation" header value  (boolean string)
DEPRECATION_HEADER = "Deprecation"

#: Informational header — lists the deprecated fields that were detected
DEPRECATED_FIELDS_HEADER = "X-Deprecated-Fields"

#: Human-readable notice injected into both the header and docs
DEPRECATION_NOTICE = (
    "title_zh, title_en, body_zh, body_en, name_zh, name_en are deprecated "
    "and will be removed in Phase 6.1. Use the canonical fields "
    "title, body, name instead."
)


def had_legacy_fields(model_fields_set: set[str]) -> bool:
    """Return True if the request included any legacy bilingual field names."""
    return bool(model_fields_set & LEGACY_FIELD_NAMES)


def inject_deprecation_headers(headers_mapping, *, used: bool = True) -> None:
    """
    Set RFC 8594 Deprecation + X-Deprecated-Fields on *headers_mapping*.

    Works with both FastAPI's ``Response.headers`` and a
    ``starlette.datastructures.MutableHeaders`` object.
    Only sets headers when *used* is True.
    """
    if used:
        headers_mapping[DEPRECATION_HEADER] = "true"
        headers_mapping[DEPRECATED_FIELDS_HEADER] = DEPRECATION_NOTICE
