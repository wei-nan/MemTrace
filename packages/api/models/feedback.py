from pydantic import BaseModel
from typing import Literal
from datetime import datetime


# ── Feedback (MVP: submission + self-query only) ───────────────────────────

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
