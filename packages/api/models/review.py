from pydantic import BaseModel
from typing import Literal, Optional, List, Any
from datetime import datetime

class ReviewQueueResponse(BaseModel):
    id: str
    workspace_id: str
    node_data: dict
    suggested_edges: List[dict]
    status: str
    source_info: Optional[str]
    created_at: datetime
    reviewed_at: Optional[datetime]
    reviewer_id: Optional[str]

class ReviewUpdate(BaseModel):
    node_data: Optional[dict] = None
    suggested_edges: Optional[List[dict]] = None
