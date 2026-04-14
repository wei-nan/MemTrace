from pydantic import BaseModel, EmailStr
from typing import Literal, Optional
from datetime import datetime

class MemberResponse(BaseModel):
    user_id: str
    display_name: str
    email: str
    role: Literal["viewer", "editor", "owner"]
    joined_at: datetime

class InviteCreate(BaseModel):
    email: EmailStr
    role: Literal["viewer", "editor"] = "viewer"

class InviteResponse(BaseModel):
    id: str
    workspace_id: str
    email: str
    role: str
    token: str
    inviter_id: str
    created_at: datetime
    expires_at: datetime
    accepted_at: Optional[datetime]

class JoinRequestCreate(BaseModel):
    message: Optional[str] = None

class JoinRequestResponse(BaseModel):
    id: str
    workspace_id: str
    user_id: str
    message: Optional[str]
    status: Literal["pending", "approved", "rejected"]
    requested_at: datetime
    reviewed_at: Optional[datetime]
    reviewed_by: Optional[str]
