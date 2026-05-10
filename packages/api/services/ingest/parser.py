import re
from typing import List, Tuple, Optional

# Constants
CHUNK_SIZE    = 6000   # characters per chunk sent to LLM
CHUNK_OVERLAP = 400    # overlap to preserve context across boundaries

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[Tuple[str, List[str]]]:
    """
    Split text into chunks based on Markdown headings.
    Returns list of (chunk_content, heading_chain).
    """
    # Identify headings
    heading_regex = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    
    # Identify code blocks to avoid splitting inside them
    code_blocks = []
    for m in re.finditer(r'^```[\s\S]*?^```', text, re.MULTILINE):
        code_blocks.append((m.start(), m.end()))
        
    def is_inside_code_block(pos: int):
        for s, e in code_blocks:
            if s <= pos < e: return True
        return False

    headings = []
    for m in heading_regex.finditer(text):
        if not is_inside_code_block(m.start()):
            headings.append({
                "level": len(m.group(1)),
                "title": m.group(2).strip(),
                "index": m.start()
            })
            
    if not headings:
        # Fallback to paragraph-based chunking if no headings found
        chunks = []
        raw_chunks = chunk_text_fallback(text, chunk_size, overlap)
        for c in raw_chunks:
            chunks.append((c, []))
        return chunks

    chunks = []
    current_chain = [] # list of (level, title)
    
    for i in range(len(headings)):
        h = headings[i]
        next_h = headings[i+1] if i+1 < len(headings) else None
        
        start = h.index
        end = next_h["index"] if next_h else len(text)
        
        # Update chain
        current_chain = [item for item in current_chain if item[0] < h["level"]]
        current_chain.append((h["level"], h["title"]))
        
        chain_titles = [item[1] for item in current_chain]
        content = text[start:end].strip()
        
        if len(content) > chunk_size + overlap:
            # Section too large, split by paragraphs
            sub_chunks = chunk_text_fallback(content, chunk_size, overlap)
            for sc in sub_chunks:
                chunks.append((sc, chain_titles))
        else:
            chunks.append((content, chain_titles))
            
    return chunks

def chunk_text_fallback(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Original paragraph-based chunking logic."""
    if len(text) <= chunk_size:
        return [text]

    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            bp = text.rfind("\n\n", start, end)
            if bp > start + chunk_size // 3:
                end = bp
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        next_start = end - overlap
        if next_start <= start:
            next_start = end
        start = next_start
    return chunks

def scan_api_endpoints(content: str) -> List[dict]:
    """
    Regex scan for API endpoints (e.g. GET /api/v1/users).
    Returns a list of seed node dicts.
    """
    patterns = [
        r'(GET|POST|PUT|DELETE|PATCH)\s+(/[a-zA-Z0-9_\-/{}]+)',
        r'API:\s+(GET|POST|PUT|DELETE|PATCH)\s+(/[a-zA-Z0-9_\-/{}]+)',
    ]
    found = set()
    for p in patterns:
        for m in re.finditer(p, content, re.IGNORECASE):
            method = m.group(1).upper()
            path = m.group(2)
            found.add(f"{method} {path}")
            
    nodes = []
    for api in found:
        nodes.append({
            "title_en": api,
            "title_zh": f"API 接口: {api}",
            "content_type": "factual",
            "body_zh": f"自動掃描發現的 API 接口種子節點: {api}。請在提取過程中補充詳細參數與邏輯。",
            "tags": ["api", "auto-scan"],
        })
    return nodes
