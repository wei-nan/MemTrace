import json
import re
from typing import List, Tuple, Optional, Dict

CONTENT_TYPE_MAP = {
    "requirement":      "factual",
    "requirements":     "factual",
    "feature":          "factual",
    "functional":       "factual",
    "specification":    "factual",
    "rule":             "factual",
    "business_rule":    "factual",
    "business rule":    "factual",
    "data":             "factual",
    "concept":          "factual",
    "definition":       "factual",
    "constraint":       "preference",
    "non_functional":   "preference",
    "nonfunctional":    "preference",
    "config":           "preference",
    "configuration":    "preference",
    "workflow":         "procedural",
    "process":          "procedural",
    "use_case":         "procedural",
    "user_story":       "procedural",
    "step":             "procedural",
    "api":              "procedural",
    "background":       "context",
    "note":             "context",
    "overview":         "context",
}

VALID_CONTENT_TYPES = {"factual", "procedural", "preference", "context", "inquiry"}

# Standard keys in the extraction flat format
EXTRACTION_STANDARD_KEYS = {
    "title_zh", "title_en", "content_type", "content_format",
    "body_zh", "body_en", "tags", "visibility",
    "suggested_edges", "source_segment", "confidence_score",
    "title", "content",
}

# Priority order of keys to try as a title source
TITLE_CANDIDATE_KEYS = [
    "title", "section_title", "section", "name", "label",
    "heading", "description", "summary", "api_version",
]

def split_bilingual_title(title: str) -> Tuple[str, str]:
    """Split 'Chinese text (English text)' → (title_zh, title_en)."""
    m = re.match(r"^(.+?)\s*\(([A-Za-z][^)]{2,})\)\s*$", title)
    if m:
        left = m.group(1).strip()
        right = m.group(2).strip()
        has_zh = any("一" <= c <= "鿿" for c in left)
        if has_zh:
            return left, right
    has_zh = any("一" <= c <= "鿿" for c in title)
    return (title, "") if has_zh else ("", title)

def normalize_nodes(nodes: List[dict], filename: str) -> List[dict]:
    """Flatten nested/structured nodes and remap AI-invented content_type values."""
    normalized = []
    for n in nodes:
        # 1. Flatten spec-as-kb nested format
        if "title" in n and isinstance(n["title"], dict):
            t = n.pop("title")
            n = {**n,
                 "title_zh": t.get("zh-TW") or t.get("zh") or "",
                 "title_en": t.get("en") or ""}
        if "content" in n and isinstance(n["content"], dict):
            c = n.pop("content")
            body = c.get("body", {})
            n = {**n,
                 "content_type":   c.get("type", ""),
                 "content_format": c.get("format", "markdown"),
                 "body_zh": body.get("zh-TW") or body.get("zh") or "",
                 "body_en": body.get("en") or ""}

        # 2. Derive title from any available candidate key
        if not (n.get("title_zh") or n.get("title_en")):
            method   = str(n.get("method", "")).strip()
            endpoint = str(n.get("endpoint", "")).strip()
            if method and endpoint:
                t_en = f"{method} {endpoint}"
                desc = str(n.get("description", "") or "").strip()
                t_zh = desc if desc else t_en
                n = {**n, "title_zh": t_zh, "title_en": t_en}
            else:
                raw = ""
                for key in TITLE_CANDIDATE_KEYS:
                    v = n.get(key)
                    if v and isinstance(v, str) and v.strip():
                        raw = v.strip()
                        break
                if raw:
                    t_zh, t_en = split_bilingual_title(raw)
                    if not t_zh and not t_en:
                        t_zh = raw
                    n = {**n, "title_zh": t_zh, "title_en": t_en}

        # 3. Build body from non-standard payload keys if body still missing
        if not (n.get("body_zh") or n.get("body_en")):
            extra = {k: v for k, v in n.items() if k not in EXTRACTION_STANDARD_KEYS}
            if extra:
                n = {**n, "body_zh": json.dumps(extra, ensure_ascii=False, indent=2), "body_en": ""}

        # 4. Drop nodes that still lack title OR body
        if not (n.get("title_zh") or n.get("title_en")):
            continue
        if not (n.get("body_zh") or n.get("body_en")):
            continue

        # 5. Normalise content_type
        ct = (n.get("content_type") or "").lower().strip()
        if ct not in VALID_CONTENT_TYPES:
            mapped = CONTENT_TYPE_MAP.get(ct, "factual")
            n = {**n, "content_type": mapped}
        normalized.append(n)
    return normalized

def extract_objects_partial(text: str) -> List[dict]:
    """Scan text char-by-char and recover every syntactically valid JSON object."""
    objects: List[dict] = []
    depth = 0
    start: Optional[int] = None
    in_string = False
    escape_next = False

    for i, ch in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth = max(depth - 1, 0)
            if depth == 0 and start is not None:
                try:
                    obj = json.loads(text[start : i + 1])
                    if isinstance(obj, dict):
                        objects.append(obj)
                except json.JSONDecodeError:
                    pass
                start = None
    return objects
