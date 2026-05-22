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
    "title", "content_type", "content_format",
    "body", "tags", "visibility",
    "suggested_edges", "source_segment", "confidence_score",
    "content",
    # cluster assignment (Phase 6 single-lang; also accept legacy bilingual keys for compat)
    "cluster_name", "cluster_name_en", "cluster_name_zh",
}

# Priority order of keys to try as a title source
TITLE_CANDIDATE_KEYS = [
    "title", "section_title", "section", "name", "label",
    "heading", "description", "summary", "api_version",
]

def normalize_nodes(nodes: List[dict], filename: str, language: str = "zh-TW") -> List[dict]:
    """Flatten nested/structured nodes and remap AI-invented content_type values."""
    normalized = []
    for n in nodes:
        # 1. Flatten spec-as-kb nested format
        if "title" in n and isinstance(n["title"], dict):
            t = n.pop("title")
            n["title"] = t.get(language) or t.get("zh-TW") or t.get("zh") or t.get("en") or ""
        elif "title" in n:
            pass
        elif "title_zh" in n or "title_en" in n:
            n["title"] = n.get("title_zh") if language == "zh-TW" else n.get("title_en")
            if not n.get("title"):
                n["title"] = n.get("title_zh") or n.get("title_en") or ""
                
        if "content" in n and isinstance(n["content"], dict):
            c = n.pop("content")
            body = c.get("body", {})
            n["content_type"] = c.get("type", "")
            n["content_format"] = c.get("format", "markdown")
            if isinstance(body, dict):
                n["body"] = body.get(language) or body.get("zh-TW") or body.get("zh") or body.get("en") or ""
            else:
                n["body"] = str(body)
        elif "body" in n:
            pass
        elif "body_zh" in n or "body_en" in n:
            n["body"] = n.get("body_zh") if language == "zh-TW" else n.get("body_en")
            if not n.get("body"):
                n["body"] = n.get("body_zh") or n.get("body_en") or ""

        # 2. Derive title from any available candidate key
        if not n.get("title"):
            method   = str(n.get("method", "")).strip()
            endpoint = str(n.get("endpoint", "")).strip()
            if method and endpoint:
                n["title"] = f"{method} {endpoint}"
                desc = str(n.get("description", "") or "").strip()
                if desc and language == "zh-TW":
                    n["title"] = desc
            else:
                raw = ""
                for key in TITLE_CANDIDATE_KEYS:
                    v = n.get(key)
                    if v and isinstance(v, str) and v.strip():
                        raw = v.strip()
                        break
                if raw:
                    n["title"] = raw

        # 3. Build body from non-standard payload keys if body still missing
        if not n.get("body"):
            extra = {k: v for k, v in n.items() if k not in EXTRACTION_STANDARD_KEYS}
            if extra:
                n["body"] = json.dumps(extra, ensure_ascii=False, indent=2)

        # 4. Drop nodes that still lack title OR body
        if not n.get("title") or not n.get("body"):
            continue

        # 5. Normalise content_type
        ct = (n.get("content_type") or "").lower().strip()
        if ct not in VALID_CONTENT_TYPES:
            mapped = CONTENT_TYPE_MAP.get(ct, "factual")
            n["content_type"] = mapped
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
