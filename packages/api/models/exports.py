from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class KBExportRequest(BaseModel):
    include_markdown: bool = True
    include_archived: bool = False
    tags: Optional[List[str]] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None

class KBExportResponse(BaseModel):
    id: str
    workspace_id: str
    status: str
    download_url: Optional[str] = None
    file_path: Optional[str] = None
    filter_params: Optional[dict] = None
    error_msg: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

class KBImportResponse(BaseModel):
    imported_nodes: int
    skipped: int
    failed: int
    errors: List[str]
