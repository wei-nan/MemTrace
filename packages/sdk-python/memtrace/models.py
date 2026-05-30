from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class Workspace(BaseModel):
    id: str
    name: str
    language: str
    visibility: str
    kb_type: str
    owner_id: str
    archive_window_days: int
    min_traversals: int
    embedding_model: str
    embedding_dim: int
    qa_archive_mode: str
    extraction_provider: Optional[str] = None
    embedding_provider: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {
        "extra": "ignore"
    }

class SuggestedEdge(BaseModel):
    to_id: str
    relation: str
    weight: float = 1.0

class Node(BaseModel):
    id: str
    workspace_id: str
    title: str
    content_type: str
    content_format: str
    body: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    visibility: str
    author: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    trust_score: float = 0.5
    traversal_count: int = 0
    unique_traverser_count: int = 0
    status: str = "active"

    model_config = {
        "extra": "ignore"
    }

class Edge(BaseModel):
    id: str
    workspace_id: str
    from_id: str
    to_id: str
    relation: str
    weight: float = 1.0
    half_life_days: int = 30
    pinned: bool = False

    model_config = {
        "extra": "ignore"
    }
