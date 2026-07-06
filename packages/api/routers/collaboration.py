from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from datetime import datetime, timedelta, timezone
import secrets

from core.database import db_cursor
from core.deps import get_current_user
from core.config import settings
from core.security import generate_id
from models.collaboration import (
    MemberCreate,
    MemberResponse,
    InviteCreate,
    InviteResponse,
    JoinRequestCreate,
    JoinRequestResponse,
    UserCandidateResponse,
)
from services.workspaces import get_effective_role as _get_effective_role, require_ws_access as _require_ws_access

router = APIRouter(prefix="/api/v1/workspaces", tags=["collaboration"])


def _require_workspace_admin(cur, ws_id: str, user: dict):
    cur.execute("SELECT owner_id, visibility, name FROM workspaces WHERE id = %s", (ws_id,))
    ws = cur.fetchone()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
    if role != "admin":
        raise HTTPException(status_code=403, detail="Only workspace admin can manage members")
    return ws


def _notify_member_added(cur, *, ws_id: str, ws_name: str, recipient_id: str, inviter: dict, role: str):
    cur.execute(
        """
        INSERT INTO notifications
            (id, workspace_id, recipient_id, source_type, source_id,
             category, severity, title, body)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            generate_id("ntf"),
            ws_id,
            recipient_id,
            "workspace_member",
            ws_id,
            "membership",
            "low",
            f"You were added to {ws_name}",
            f"{inviter.get('email') or inviter.get('sub')} added you as {role}. You can leave this workspace from Members & Access.",
        ),
    )

@router.get("/{ws_id}/members", response_model=List[MemberResponse])
def list_members(ws_id: str, user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        # Fetch owner
        cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (ws_id,))
        owner_id = cur.fetchone()["owner_id"]
        
        cur.execute("""
            SELECT u.id as user_id, u.display_name, u.email, m.role::text as role, m.joined_at
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

@router.get("/{ws_id}/user-candidates", response_model=List[UserCandidateResponse])
def list_user_candidates(
    ws_id: str,
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user),
):
    with db_cursor() as cur:
        ws = _require_workspace_admin(cur, ws_id, user)
        if ws["visibility"] == "private":
            raise HTTPException(status_code=400, detail="Private workspaces cannot add members")
        like = f"%{q.strip()}%"
        cur.execute(
            """
            SELECT u.id, u.display_name, u.email
            FROM users u
            WHERE (u.id ILIKE %s OR u.email ILIKE %s OR u.display_name ILIKE %s)
              AND u.id <> %s
              AND NOT EXISTS (
                  SELECT 1 FROM workspace_members wm
                  WHERE wm.workspace_id = %s AND wm.user_id = u.id
              )
            ORDER BY u.email ASC
            LIMIT %s
            """,
            (like, like, like, ws["owner_id"], ws_id, limit),
        )
        return cur.fetchall()

@router.post("/{ws_id}/members", response_model=MemberResponse, status_code=201)
def add_existing_member(ws_id: str, body: MemberCreate, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        ws = _require_workspace_admin(cur, ws_id, user)
        if ws["visibility"] == "private":
            raise HTTPException(status_code=400, detail="Private workspaces cannot add members")
        if body.user_id == ws["owner_id"]:
            raise HTTPException(status_code=409, detail="User is already the workspace owner")

        cur.execute("SELECT id, display_name, email FROM users WHERE id = %s", (body.user_id,))
        target = cur.fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="User not found")

        cur.execute(
            "SELECT 1 FROM workspace_members WHERE workspace_id = %s AND user_id = %s",
            (ws_id, body.user_id),
        )
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="User is already a member")

        cur.execute(
            """
            INSERT INTO workspace_members (workspace_id, user_id, role)
            VALUES (%s, %s, %s)
            RETURNING user_id, role::text AS role, joined_at
            """,
            (ws_id, body.user_id, body.role),
        )
        member = dict(cur.fetchone())
        _notify_member_added(
            cur,
            ws_id=ws_id,
            ws_name=ws["name"],
            recipient_id=body.user_id,
            inviter=user,
            role=body.role,
        )
        return {
            "user_id": member["user_id"],
            "display_name": target["display_name"],
            "email": target["email"],
            "role": member["role"],
            "joined_at": member["joined_at"],
        }

@router.post("/{ws_id}/invites", response_model=InviteResponse, status_code=201)
def create_invite(ws_id: str, body: InviteCreate, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (ws_id,))
        ws = cur.fetchone()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
        if role != "admin":
             raise HTTPException(status_code=403, detail="Only workspace admin can create invites")
        
        invite_id = generate_id("inv")
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=max(1, body.expires_in_days))
        
        cur.execute("""
            INSERT INTO workspace_invites (id, workspace_id, email, role, token, inviter_id, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (invite_id, ws_id, body.email, body.role, token, user["sub"], expires_at))
        row = dict(cur.fetchone())
        row["invite_url"] = f"{settings.app_url.rstrip('/')}/join/{token}"
        return row

@router.get("/{ws_id}/invites", response_model=List[InviteResponse])
def list_invites(ws_id: str, user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (ws_id,))
        ws = cur.fetchone()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
        if role != "admin":
             raise HTTPException(status_code=403, detail="Only workspace admin can list invites")
        
        cur.execute("SELECT * FROM workspace_invites WHERE workspace_id = %s AND status = 'pending' AND expires_at > NOW()", (ws_id,))
        rows = []
        for row in cur.fetchall():
            item = dict(row)
            item["invite_url"] = f"{settings.app_url.rstrip('/')}/join/{item['token']}"
            rows.append(item)
        return rows

@router.delete("/{ws_id}/invites/{token}", status_code=200)
def revoke_invite(ws_id: str, token: str, user: dict = Depends(get_current_user)):
    """B3: Revoke an invite by setting its status to 'revoked'."""
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (ws_id,))
        ws = cur.fetchone()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
        if role != "admin":
             raise HTTPException(status_code=403, detail="Only workspace admin can revoke invites")
        
        cur.execute(
            "UPDATE workspace_invites SET status = 'revoked' WHERE workspace_id = %s AND token = %s RETURNING id",
            (ws_id, token)
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Invite not found")
            
        return {"message": "Invite revoked"}

@router.post("/invites/{token}/accept")
def accept_invite(token: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT * FROM workspace_invites WHERE token = %s AND status = 'pending'", (token,))
        invite = cur.fetchone()
        if not invite:
            raise HTTPException(status_code=404, detail="Invite not found, already used, or revoked")
        
        if invite["expires_at"] < datetime.now(timezone.utc):
            cur.execute("UPDATE workspace_invites SET status = 'expired' WHERE id = %s", (invite["id"],))
            raise HTTPException(status_code=400, detail="Invite has expired")

        cur.execute("SELECT 1 FROM workspace_members WHERE workspace_id = %s AND user_id = %s", (invite["workspace_id"], user["sub"]))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="User is already a member")
        
        # Add to members
        cur.execute("""
            INSERT INTO workspace_members (workspace_id, user_id, role)
            VALUES (%s, %s, %s)
            ON CONFLICT (workspace_id, user_id) DO UPDATE SET role = EXCLUDED.role
        """, (invite["workspace_id"], user["sub"], invite["role"]))
        
        # Mark invite as used
        cur.execute("UPDATE workspace_invites SET status = 'used', accepted_at = now() WHERE id = %s", (invite["id"],))
        
        return {"message": "Invite accepted", "workspace_id": invite["workspace_id"]}

@router.delete("/invites/{id}")
def delete_invite(id: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT workspace_id FROM workspace_invites WHERE id = %s OR token = %s", (id, id))
        invite = cur.fetchone()
        if not invite:
            raise HTTPException(status_code=404, detail="Invite not found")
            
        cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (invite["workspace_id"],))
        ws = cur.fetchone()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        role = _get_effective_role(cur, invite["workspace_id"], ws["owner_id"], user["sub"])
        if role != "admin":
             raise HTTPException(status_code=403, detail="Only workspace admin can delete invites")
        
        cur.execute("DELETE FROM workspace_invites WHERE id = %s OR token = %s", (id, id))
        return {"message": "Invite deleted"}

@router.put("/{ws_id}/members/{user_id}")
def update_member_role(ws_id: str, user_id: str, body: dict, user: dict = Depends(get_current_user)):
    # role is expected in body["role"]
    new_role = body.get("role")
    if new_role not in ["viewer", "editor"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'viewer' or 'editor'")
        
    with db_cursor(commit=True) as cur:
        # Verify requester is owner
        cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (ws_id,))
        ws = cur.fetchone()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
        if role != "admin":
             raise HTTPException(status_code=403, detail="Only workspace admin can update member roles")
             
        # Owners cannot have their role changed via this endpoint
        if user_id == ws["owner_id"]:
            raise HTTPException(status_code=400, detail="Cannot change role of workspace owner")
            
        cur.execute("""
            UPDATE workspace_members 
            SET role = %s 
            WHERE workspace_id = %s AND user_id = %s
            RETURNING user_id
        """, (new_role, ws_id, user_id))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Member not found")
        
        return {"message": "Member role updated"}

@router.delete("/{ws_id}/members/me")
def leave_workspace(ws_id: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (ws_id,))
        ws = cur.fetchone()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if user["sub"] == ws["owner_id"]:
            raise HTTPException(status_code=400, detail="Workspace owner cannot leave their own workspace")

        cur.execute(
            "DELETE FROM workspace_members WHERE workspace_id = %s AND user_id = %s RETURNING user_id",
            (ws_id, user["sub"]),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Membership not found")
        return {"message": "Left workspace"}

@router.delete("/{ws_id}/members/{user_id}")
def remove_member(ws_id: str, user_id: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        # Verify requester is owner
        cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (ws_id,))
        ws = cur.fetchone()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
        if role != "admin":
             raise HTTPException(status_code=403, detail="Only workspace admin can remove members")
             
        # Owners cannot be removed
        if user_id == ws["owner_id"]:
            raise HTTPException(status_code=400, detail="Cannot remove workspace owner")
            
        cur.execute("DELETE FROM workspace_members WHERE workspace_id = %s AND user_id = %s RETURNING user_id", (ws_id, user_id))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Member not found")
        
        return {"message": "Member removed"}

# ── Join Requests ─────────────────────────────────────────────────────────────

@router.post("/{ws_id}/join-requests", response_model=JoinRequestResponse, status_code=201)
def create_join_request(ws_id: str, body: JoinRequestCreate, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        # Check if workspace is conditional_public
        cur.execute("SELECT visibility FROM workspaces WHERE id = %s", (ws_id,))
        ws = cur.fetchone()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if ws["visibility"] != "conditional_public":
             raise HTTPException(status_code=403, detail="Join requests are only available for conditional public workspaces")
        
        # Check if already a member
        cur.execute("SELECT * FROM workspace_members WHERE workspace_id = %s AND user_id = %s", (ws_id, user["sub"]))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="You are already a member")

        req_id = generate_id("req")
        try:
            cur.execute("""
                INSERT INTO join_requests (id, workspace_id, user_id, message)
                VALUES (%s, %s, %s, %s)
                RETURNING *
            """, (req_id, ws_id, user["sub"], body.message))
            return cur.fetchone()
        except Exception as e:
            if "unique" in str(e).lower():
                raise HTTPException(status_code=400, detail="You already have a pending request")
            raise

@router.get("/{ws_id}/join-requests", response_model=List[JoinRequestResponse])
def list_join_requests(ws_id: str, status: str = Query("pending"), user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        # Verify requester is owner or admin
        cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (ws_id,))
        ws = cur.fetchone()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
        if role != "admin":
             raise HTTPException(status_code=403, detail="Only workspace admin can list join requests")
             
        cur.execute("SELECT * FROM join_requests WHERE workspace_id = %s AND status = %s ORDER BY requested_at DESC", (ws_id, status))
        return cur.fetchall()

@router.post("/{ws_id}/join-requests/{req_id}/approve", response_model=JoinRequestResponse)
def approve_join_request(ws_id: str, req_id: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (ws_id,))
        ws = cur.fetchone()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
        if role != "admin":
             raise HTTPException(status_code=403, detail="Only workspace admin can approve requests")
             
        cur.execute("SELECT * FROM join_requests WHERE id = %s AND workspace_id = %s", (req_id, ws_id))
        req = cur.fetchone()
        if not req or req["status"] != "pending":
            raise HTTPException(status_code=400, detail="Join request not found or not pending")
            
        # Add member as viewer by default
        cur.execute("""
            INSERT INTO workspace_members (workspace_id, user_id, role)
            VALUES (%s, %s, 'viewer')
            ON CONFLICT (workspace_id, user_id) DO NOTHING
        """, (ws_id, req["user_id"]))
        
        cur.execute("""
            UPDATE join_requests SET status = 'approved', reviewed_at = now(), reviewed_by = %s
            WHERE id = %s RETURNING *
        """, (user["sub"], req_id))
        return cur.fetchone()

@router.post("/{ws_id}/join-requests/{req_id}/reject", response_model=JoinRequestResponse)
def reject_join_request(ws_id: str, req_id: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (ws_id,))
        ws = cur.fetchone()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
        if role != "admin":
             raise HTTPException(status_code=403, detail="Only workspace admin can reject requests")
             
        cur.execute("""
            UPDATE join_requests SET status = 'rejected', reviewed_at = now(), reviewed_by = %s
            WHERE id = %s AND workspace_id = %s AND status = 'pending' RETURNING *
        """, (user["sub"], req_id, ws_id))
        
        req = cur.fetchone()
        if not req:
            raise HTTPException(status_code=400, detail="Join request not found or not pending")
        return req
