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
    embedding_model: Optional[str] = None                # P4.1-E: user-chosen model; None = auto-resolve
    qa_archive_mode: str = "manual_review"               # auto_active | manual_review
    extraction_provider: Optional[str] = None            # preferred LLM for ingestion; None = user default


class WorkspaceResponse(BaseModel):
    id: str
    name_zh: str
    name_en: str
    visibility: str
    kb_type: str
    owner_id: str
    archive_window_days: int
    min_traversals: int
    embedding_model: str = "text-embedding-3-small"      # P4.1-A: locked at creation
    embedding_dim: int = 1536                            # P4.1-A: locked at creation
    qa_archive_mode: str
    extraction_provider: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    my_role: Optional[str] = None  # effective role of the requesting user: 'admin'|'editor'|'viewer'|None


class WorkspaceAssociationResponse(BaseModel):
    id: str
    source_ws_id: str
    target_ws_id: str
    target_name_en: str
    target_name_zh: str
    created_at: datetime


class WorkspacePurgeResponse(BaseModel):
    deleted_nodes_count: int
    deleted_edges_count: int


# ── Node ──────────────────────────────────────────────────────────────────────

class SuggestedEdge(BaseModel):
    to_id: str
    relation: str
    weight: float = 1.0

class NodeCreate(BaseModel):
    title_zh: str = ""
    title_en: str
    content_type: str
    content_format: str = "plain"
    body_zh: str = ""
    body_en: str = ""
    tags: list[str] = []
    visibility: str = "private"
    copied_from_node: Optional[str] = None
    copied_from_ws: Optional[str] = None
    source_type: Literal["human", "ai"] = "human"
    suggested_edges: list[SuggestedEdge] = []


class NodeUpdate(BaseModel):
    title_zh: Optional[str] = None
    title_en: Optional[str] = None
    content_type: Optional[str] = None
    content_format: Optional[str] = None
    body_zh: Optional[str] = None
    body_en: Optional[str] = None
    tags: Optional[list[str]] = None
    visibility: Optional[str] = None
    source_type: Literal["human", "ai"] = "human"
    suggested_edges: list[SuggestedEdge] = []


class NodeResponse(BaseModel):
    id: str
    schema_version: str
    workspace_id: str
    title_zh: str
    title_en: str
    content_type: str
    content_format: str
    body_zh: Optional[str]
    body_en: Optional[str]
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
    validity_confirmed_at: Optional[datetime] = None
    validity_confirmed_by: Optional[str] = None
    content_stripped: bool = False
    ask_count: int = 0
    miss_count: int = 0


class ValidityConfirmationResponse(BaseModel):
    confirmed_at: datetime
    confirmed_by: str


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
    qa_archive_mode: Optional[Literal["auto_active", "manual_review"]] = None
    extraction_provider: Optional[str] = None


class TableViewResponse(BaseModel):
    nodes: list[NodeResponse]
    total_count: int

class AnalyticsTopNode(BaseModel):
    id: str
    title: str
    traversal_count: int

class TraversalTrendPoint(BaseModel):
    date: str
    count: int

class WorkspaceAnalyticsResponse(BaseModel):
    total_nodes: int
    active_edges: int
    orphan_node_count: int
    avg_trust_score: float
    faded_edge_ratio: float
    monthly_traversal_count: int
    kb_type: str
    top_nodes: list[AnalyticsTopNode]
    kb_type_metrics: dict[str, float] = {}
    traversal_trend: list[TraversalTrendPoint] = []

class TokenEfficiencyResponse(BaseModel):
    avg_tokens_per_query: int
    estimated_full_doc_tokens: int
    savings_ratio: float
    monthly_query_count: int

class VoteTrustRequest(BaseModel):
    accuracy: int
    utility: int


class WorkspaceCloneRequest(BaseModel):
    name_zh: Optional[str] = None
    name_en: Optional[str] = None
    new_embedding_model: Optional[str] = None
    visibility: Optional[str] = None    # 'public' | 'private' | 'restricted'; None = 'private'


class WorkspaceCloneJobResponse(BaseModel):
    id: str
    source_ws_id: str
    target_ws_id: str
    status: str
    total_nodes: int
    processed_nodes: int
    is_fork: bool = False            # P4.1-F: True when triggered by a public KB fork
    error_msg: Optional[str] = None
    cancelled_at: Optional[datetime] = None   # P4.1-F: set when user cancels
    created_at: datetime
    updated_at: datetime


class ForkWorkspaceRequest(BaseModel):
    """P4.1-F: Fork a public workspace into the current user's account."""
    name_zh: str
    name_en: str
    embedding_model: Optional[str] = None     # None = inherit source workspace model
