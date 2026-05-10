from datetime import datetime
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field


ChangeType = Literal["create", "update", "delete", "split_suggestion"]
ActorType = Literal["human", "ai"]
ReviewDecision = Literal["accept", "reject", "comment"]


class AIReviewResult(BaseModel):
    decision: ReviewDecision
    confidence: float = Field(ge=0, le=1)
    reasoning: str = ""
    reviewer_id: str
    reviewed_at: datetime


class ReviewQueueResponse(BaseModel):
    id: str
    workspace_id: str
    can_review: bool = False
    change_type: ChangeType
    target_node_id: Optional[str] = None
    before_snapshot: Optional[dict[str, Any]] = None
    node_data: dict[str, Any]
    diff_summary: dict[str, Any]
    suggested_edges: list[dict[str, Any]] = Field(default_factory=list)
    status: str
    source_info: Optional[str] = None
    proposer_type: ActorType
    proposer_id: Optional[str] = None
    proposer_meta: Optional[dict[str, Any]] = None
    reviewer_type: Optional[ActorType] = None
    reviewer_id: Optional[str] = None
    ai_review: Optional[Union[AIReviewResult, dict[str, Any]]] = None
    review_notes: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None


class ReviewUpdate(BaseModel):
    node_data: Optional[dict[str, Any]] = None
    suggested_edges: Optional[list[dict[str, Any]]] = None
    review_notes: Optional[str] = None


class AIReviewerBase(BaseModel):
    name: str
    provider: str
    model: str
    system_prompt: str
    auto_accept_threshold: float = Field(ge=0, le=1, default=0.95)
    auto_reject_threshold: float = Field(ge=0, le=1, default=0.1)
    enabled: bool = True


class AIReviewerCreate(AIReviewerBase):
    pass


class AIReviewerUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    auto_accept_threshold: Optional[float] = Field(default=None, ge=0, le=1)
    auto_reject_threshold: Optional[float] = Field(default=None, ge=0, le=1)
    enabled: Optional[bool] = None


class AIReviewerResponse(AIReviewerBase):
    id: str
    workspace_id: str
    created_at: datetime


class NodeRevisionMetaResponse(BaseModel):
    id: str
    node_id: str
    workspace_id: str
    revision_no: int
    signature: str
    proposer_type: ActorType
    proposer_id: Optional[str] = None
    review_id: Optional[str] = None
    created_at: datetime


class NodeRevisionResponse(NodeRevisionMetaResponse):
    snapshot: dict[str, Any]

class ApplySplitRequest(BaseModel):
    # Optional override of the suggested split proposals
    proposals: list[dict[str, Any]]
