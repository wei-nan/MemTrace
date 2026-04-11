from pydantic import BaseModel
from typing import List, Optional

class ExtractionRequest(BaseModel):
    text: str
    workspace_id: str
