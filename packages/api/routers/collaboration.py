from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from datetime import datetime, timedelta, timezone
import secrets

from core.database import db_cursor
from core.deps import get_current_user
from core.security import generate_id
from models.collaboration import MemberResponse, InviteCreate, InviteResponse
from routers.kb import _require_ws_access

router = APIRouter(prefix="/workspaces", tags=["collaboration"])

@router.get("/{ws_id}/members", response_model=List[MemberResponse])
def list_members(ws_id: str, user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        # Fetch owner
        cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (ws_id,))
        owner_id = cur.fetchone()["owner_id"]
        
        cur.execute("""
            SELECT u.id as user_id, u.display_name, u.email, m.role, m.joined_at
            FROM workspace_members m
            JOIN users u ON m.user_id = u.id
            WHERE m.workspace_id = %s
            UNION
            SELECT u.id as user_id, u.display_name, u.email, 'owner' as role, u.created_at as joined_at
            FROM workspaces w
            JOIN users u ON w.owner_id = u.id
            WHERE w.id = %s
        """, (ws_id, ws_id))
        return cur.fetchall()

@router.post("/{ws_id}/invites", response_model=InviteResponse, status_code=201)
def create_invite(ws_id: str, body: InviteCreate, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        # Only owner can invite (actually SPEC says owner, but maybe editors too? Let's stick to owner for now)
        cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (ws_id,))
        ws = cur.fetchone()
        if not ws or ws["owner_id"] != user["sub"]:
             raise HTTPException(status_code=403, detail="Only workspace owner can create invites")
        
        invite_id = generate_id("inv")
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        cur.execute("""
            INSERT INTO workspace_invites (id, workspace_id, email, role, token, inviter_id, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (invite_id, ws_id, body.email, body.role, token, user["sub"], expires_at))
        return cur.fetchone()

@router.get("/{ws_id}/invites", response_model=List[InviteResponse])
def list_invites(ws_id: str, user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (ws_id,))
        ws = cur.fetchone()
        if not ws or ws["owner_id"] != user["sub"]:
             raise HTTPException(status_code=403, detail="Only workspace owner can list invites")
        
        cur.execute("SELECT * FROM workspace_invites WHERE workspace_id = %s AND accepted_at IS NULL", (ws_id,))
        return cur.fetchall()

@router.post("/invites/{token}/accept")
def accept_invite(token: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT * FROM workspace_invites WHERE token = %s AND accepted_at IS NULL", (token,))
        invite = cur.fetchone()
        if not invite:
            raise HTTPException(status_code=404, detail="Invite not found or already accepted")
        
        if invite["expires_at"] < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Invite has expired")
        
        # Add to members
        cur.execute("""
            INSERT INTO workspace_members (workspace_id, user_id, role)
            VALUES (%s, %s, %s)
            ON CONFLICT (workspace_id, user_id) DO UPDATE SET role = EXCLUDED.role
        """, (invite["workspace_id"], user["sub"], invite["role"]))
        
        # Mark invite as accepted
        cur.execute("UPDATE workspace_invites SET accepted_at = now() WHERE id = %s", (invite["id"],))
        
        return {"message": "Invite accepted", "workspace_id": invite["workspace_id"]}

@router.delete("/invites/{id}")
def delete_invite(id: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT workspace_id FROM workspace_invites WHERE id = %s", (id,))
        invite = cur.fetchone()
        if not invite:
            raise HTTPException(status_code=404, detail="Invite not found")
            
        cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (invite["workspace_id"],))
        ws = cur.fetchone()
        if not ws or ws["owner_id"] != user["sub"]:
             raise HTTPException(status_code=403, detail="Only workspace owner can delete invites")
        
        cur.execute("DELETE FROM workspace_invites WHERE id = %s", (id,))
        return {"message": "Invite deleted"}
