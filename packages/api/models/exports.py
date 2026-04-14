from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class KBExportRequest(BaseModel):
    include_markdown: bool = True
    tags: Optional[List[str]] = None

class KBExportResponse(BaseModel):
    id: str
    workspace_id: str
    status: str
    download_url: Optional[str] = None
    error_msg: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
