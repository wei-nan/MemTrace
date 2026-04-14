from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime


# ── Workspace ─────────────────────────────────────────────────────────────────

class WorkspaceCreate(BaseModel):
    name_zh: str
    name_en: str
    visibility: str = "private"                          # public | restricted | private
    kb_type: Literal["evergreen", "ephemeral"] = "evergreen"  # immutable after creation
    archive_window_days: int = 90
    min_traversals: int = 1


class WorkspaceResponse(BaseModel):
    id: str
    name_zh: str
    name_en: str
    visibility: str
    kb_type: str
    owner_id: str
    archive_window_days: int
    min_traversals: int
    created_at: datetime
    updated_at: datetime


class WorkspaceAssociationResponse(BaseModel):
    id: str
    source_ws_id: str
    target_ws_id: str
    target_name_en: str
    target_name_zh: str
    created_at: datetime


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
    copied_from_node: Optional[str] = None
    copied_from_ws: Optional[str] = None


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
    dim_accuracy: float
    dim_freshness: float
    dim_utility: float
    dim_author_rep: float
    traversal_count: int
    unique_traverser_count: int
    status: str
    archived_at: Optional[datetime]
    copied_from_node: Optional[str]
    copied_from_ws: Optional[str]


# ── Edge ──────────────────────────────────────────────────────────────────────

class EdgeCreate(BaseModel):
    from_id: str
    to_id: str
    relation: str          # depends_on | extends | related_to | contradicts
    weight: float = 1.0
    half_life_days: int = 30
    pinned: bool = False


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
    status: str
    pinned: bool


# ── Traversal / Rating ────────────────────────────────────────────────────────

class TraverseEdgeRequest(BaseModel):
    note: Optional[str] = None


class RateEdgeRequest(BaseModel):
    rating: int    # 1–5
    note: Optional[str] = None
# ── Graph Preview ─────────────────────────────────────────────────────────────

class NodePreview(BaseModel):
    preview_id: str
    content_type: str

class EdgePreview(BaseModel):
    from_preview_id: str
    to_preview_id: str
    relation: str

class GraphPreviewResponse(BaseModel):
    nodes: list[NodePreview]
    edges: list[EdgePreview]

class WorkspaceUpdate(BaseModel):
    name_zh: Optional[str] = None
    name_en: Optional[str] = None
    visibility: Optional[str] = None
    kb_type: Optional[Literal["evergreen", "ephemeral"]] = None
    archive_window_days: Optional[int] = None
    min_traversals: Optional[int] = None

