from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ── Workspace ─────────────────────────────────────────────────────────────────

class WorkspaceCreate(BaseModel):
    name_zh: str
    name_en: str
    visibility: str = "private"   # public | restricted | private


class WorkspaceResponse(BaseModel):
    id: str
    name_zh: str
    name_en: str
    visibility: str
    owner_id: str
    created_at: datetime
    updated_at: datetime


# ── Node ──────────────────────────────────────────────────────────────────────

class NodeCreate(BaseModel):
    title_zh: str
    title_en: str
    content_type: str
    content_format: str = "plain"
    body_zh: str = ""
    body_en: str = ""
    tags: list[str] = []
    visibility: str = "private"


class NodeUpdate(BaseModel):
    title_zh: Optional[str] = None
    title_en: Optional[str] = None
    content_type: Optional[str] = None
    content_format: Optional[str] = None
    body_zh: Optional[str] = None
    body_en: Optional[str] = None
    tags: Optional[list[str]] = None
    visibility: Optional[str] = None


class NodeResponse(BaseModel):
    id: str
    schema_version: str
    workspace_id: str
    title_zh: str
    title_en: str
    content_type: str
    content_format: str
    body_zh: str
    body_en: str
    tags: list[str]
    visibility: str
    author: str
    created_at: datetime
    updated_at: Optional[datetime]
    signature: str
    source_type: str
    trust_score: float
    traversal_count: int
    unique_traverser_count: int


# ── Edge ──────────────────────────────────────────────────────────────────────

class EdgeCreate(BaseModel):
    from_id: str
    to_id: str
    relation: str          # depends_on | extends | related_to | contradicts
    weight: float = 1.0
    half_life_days: int = 30


class EdgeResponse(BaseModel):
    id: str
    workspace_id: str
    from_id: str
    to_id: str
    relation: str
    weight: float
    co_access_count: int
    last_co_accessed: datetime
    half_life_days: int
    min_weight: float
    traversal_count: int
    rating_avg: Optional[float]
    rating_count: int


# ── Traversal / Rating ────────────────────────────────────────────────────────

class TraverseEdgeRequest(BaseModel):
    note: Optional[str] = None


class RateEdgeRequest(BaseModel):
    rating: int    # 1–5
    note: Optional[str] = None
