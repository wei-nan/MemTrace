from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime


# ── Feedback (MVP: submission + admin listing) ──────────────────────────────

class FeedbackCreate(BaseModel):
    type: Literal["bug-report", "feature-request"]
    title: str
    body: str = ""


class FeedbackCreateResponse(BaseModel):
    id: str
    status: str


class FeedbackItem(BaseModel):
    id: str
    type: str
    title: str
    resolution_status: str
    created_at: datetime


class AdminFeedbackItem(BaseModel):
    id: str
    type: str
    title: str
    body: str
    resolution_status: str
    created_at: datetime
    author_id: str
    author_name: Optional[str] = None
    author_email: Optional[str] = None
