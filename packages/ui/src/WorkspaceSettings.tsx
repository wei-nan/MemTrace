import { useEffect, useState } from "react";
import { Bot, ExternalLink, Trash2, UserPlus, Users } from "lucide-react";
import { aiReviewers, workspaces, type AIReviewer, type AIReviewerPayload, type Invite, type JoinRequest, type Member, type Workspace } from "./api";
import { useModal } from "./components/ModalContext";
import KbExportPanel from "./components/KbExportPanel";

const DEFAULT_AI_REVIEW_PROMPT = `You are an AI reviewer for a collaborative knowledge graph.
Return JSON with decision, confidence, and reasoning.
Accept only low-risk, well-supported changes.`;

function AIReviewerSettings({ wsId }: { wsId: string }) {
  const { toast } = useModal();
  const [items, setItems] = useState<AIReviewer[]>([]);
  const [form, setForm] = useState<AIReviewerPayload>({
    name: "",
    provider: "openai",
    model: "gpt-4o-mini",
    system_prompt: DEFAULT_AI_REVIEW_PROMPT,
    auto_accept_threshold: 0.95,
    auto_reject_threshold: 0.1,
    enabled: true,
  });

  const load = async () => {
    try {
      setItems(await aiReviewers.list(wsId));
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    }
  };

  useEffect(() => { load(); }, [wsId]);

  const save = async () => {
    try {
      await aiReviewers.create(wsId, form);
      setForm({ ...form, name: "" });
      await load();
      toast({ message: "AI reviewer created", variant: "success" });
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      <section style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 14, padding: 18 }}>
        <h3 style={{ marginTop: 0, display: "flex", alignItems: "center", gap: 8 }}><Bot size={18} /> Create AI Reviewer</h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
          <input className="mt-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Name" />
          <input className="mt-input" value={form.provider} onChange={(e) => setForm({ ...form, provider: e.target.value })} placeholder="Provider" />
          <input className="mt-input" value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} placeholder="Model" />
        </div>
        <textarea className="mt-input" style={{ minHeight: 120, marginTop: 10 }} value={form.system_prompt} onChange={(e) => setForm({ ...form, system_prompt: e.target.value })} />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: 10, marginTop: 10 }}>
          <input className="mt-input" type="number" step="0.01" min="0" max="1" value={form.auto_accept_threshold} onChange={(e) => setForm({ ...form, auto_accept_threshold: Number(e.target.value) })} placeholder="Auto accept threshold" />
          <input className="mt-input" type="number" step="0.01" min="0" max="1" value={form.auto_reject_threshold} onChange={(e) => setForm({ ...form, auto_reject_threshold: Number(e.target.value) })} placeholder="Auto reject threshold" />
          <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={form.enabled} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} />
            Enabled
          </label>
        </div>
        <div style={{ marginTop: 12 }}>
          <button className="btn-primary" onClick={save}>Create Reviewer</button>
        </div>
      </section>

      <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {items.map((item) => (
          <div key={item.id} style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 12, padding: 14, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
            <div>
              <div style={{ fontWeight: 600 }}>{item.name}</div>
              <div style={{ color: "var(--text-muted)", fontSize: 13 }}>{item.provider} · {item.model}</div>
              <div style={{ color: "var(--text-muted)", fontSize: 12, marginTop: 4 }}>
                accept ≥ {item.auto_accept_threshold}, reject ≥ {item.auto_reject_threshold}
              </div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn-secondary" onClick={async () => {
                await aiReviewers.update(wsId, item.id, { enabled: !item.enabled });
                await load();
              }}>{item.enabled ? "Disable" : "Enable"}</button>
              <button className="btn-secondary" onClick={async () => {
                await aiReviewers.delete(wsId, item.id);
                await load();
              }}><Trash2 size={16} /></button>
            </div>
          </div>
        ))}
        {!items.length && <div style={{ color: "var(--text-muted)" }}>No AI reviewers configured yet.</div>}
      </section>
    </div>
  );
}

export default function WorkspaceSettings({ wsId }: { wsId: string }) {
  const { confirm, toast } = useModal();
  const [ws, setWs] = useState<Workspace | null>(null);
  const [joinRequests, setJoinRequests] = useState<JoinRequest[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("viewer");
  const [associations, setAssociations] = useState<any[]>([]);
  const [assocTargetId, setAssocTargetId] = useState("");
  const [tab, setTab] = useState<"members" | "export" | "assoc" | "ai_review">("members");

  const loadData = async () => {
    try {
      const [m, i, w, reqs, as] = await Promise.all([
        workspaces.members(wsId),
        workspaces.invites(wsId),
        workspaces.get(wsId),
        workspaces.joinRequests(wsId),
        workspaces.listAssociations(wsId),
      ]);
      setMembers(m);
      setInvites(i);
      setWs(w);
      setJoinRequests(reqs);
      setAssociations(as);
    } catch {
      // Keep current UI state if some fetch fails.
    }
  };

  useEffect(() => { loadData(); }, [wsId]);

  return (
    <div style={{ padding: "0 20px", display: "flex", flexDirection: "column", gap: 24 }}>
      <div style={{ display: "flex", gap: 20, borderBottom: "1px solid var(--border-subtle)", marginBottom: 8, flexWrap: "wrap" }}>
        <button onClick={() => setTab("members")} style={{ padding: "12px 4px", background: "none", border: "none", cursor: "pointer", fontSize: 14, fontWeight: 600, color: tab === "members" ? "var(--color-primary)" : "var(--text-muted)", borderBottom: tab === "members" ? "2px solid var(--color-primary)" : "2px solid transparent" }}>Members & Access</button>
        <button onClick={() => setTab("export")} style={{ padding: "12px 4px", background: "none", border: "none", cursor: "pointer", fontSize: 14, fontWeight: 600, color: tab === "export" ? "var(--color-primary)" : "var(--text-muted)", borderBottom: tab === "export" ? "2px solid var(--color-primary)" : "2px solid transparent" }}>Data Export</button>
        <button onClick={() => setTab("assoc")} style={{ padding: "12px 4px", background: "none", border: "none", cursor: "pointer", fontSize: 14, fontWeight: 600, color: tab === "assoc" ? "var(--color-primary)" : "var(--text-muted)", borderBottom: tab === "assoc" ? "2px solid var(--color-primary)" : "2px solid transparent" }}>KB Associations</button>
        <button onClick={() => setTab("ai_review")} style={{ padding: "12px 4px", background: "none", border: "none", cursor: "pointer", fontSize: 14, fontWeight: 600, color: tab === "ai_review" ? "var(--color-primary)" : "var(--text-muted)", borderBottom: tab === "ai_review" ? "2px solid var(--color-primary)" : "2px solid transparent" }}>AI Reviewers</button>
      </div>

      {tab === "assoc" ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <section>
            <h3 style={{ fontSize: 16, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}><ExternalLink size={18} style={{ color: "var(--color-primary)" }} /> Add KB Association</h3>
            <div style={{ display: "flex", gap: 10, background: "var(--bg-surface)", padding: 16, borderRadius: 12, border: "1px solid var(--border-default)" }}>
              <input className="mt-input" placeholder="Paste target KB ID" value={assocTargetId} onChange={(e) => setAssocTargetId(e.target.value)} style={{ flex: 1 }} />
              <button className="btn-primary" onClick={async () => {
                try {
                  await workspaces.createAssociation(wsId, assocTargetId);
                  setAssocTargetId("");
                  await loadData();
                  toast({ message: "Association created", variant: "success" });
                } catch (e) {
                  toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
                }
              }}>Associate</button>
            </div>
          </section>

          <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {associations.map((association) => (
              <div key={association.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 12 }}>
                <div>
                  <div style={{ fontWeight: 600 }}>{association.target_name_en}</div>
                  <div style={{ fontSize: 12, color: "var(--text-muted)" }}>ID: {association.target_ws_id}</div>
                </div>
                <button className="btn-secondary" onClick={async () => {
                  await workspaces.deleteAssociation(wsId, association.target_ws_id);
                  await loadData();
                }}><Trash2 size={16} /></button>
              </div>
            ))}
            {!associations.length && <div style={{ color: "var(--text-muted)" }}>No linked knowledge bases yet.</div>}
          </section>
        </div>
      ) : tab === "export" ? (
        <KbExportPanel wsId={wsId} zh={false} />
      ) : tab === "ai_review" ? (
        <AIReviewerSettings wsId={wsId} />
      ) : (
        <>
          <section style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 12, padding: 16 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <div style={{ fontWeight: 600 }}>Visibility</div>
                <div style={{ fontSize: 12, color: "var(--text-muted)" }}>Control who can access this workspace.</div>
              </div>
              <select className="mt-input" value={ws?.visibility ?? "private"} style={{ width: 160 }} onChange={async (e) => {
                try {
                  await workspaces.update(wsId, { visibility: e.target.value });
                  await loadData();
                  toast({ message: "Visibility updated", variant: "success" });
                } catch (err) {
                  toast({ message: err instanceof Error ? err.message : String(err), variant: "error" });
                }
              }}>
                <option value="private">Private</option>
                <option value="restricted">Restricted</option>
                <option value="conditional_public">Conditional Public</option>
                <option value="public">Public</option>
              </select>
            </div>
          </section>

          {joinRequests.length > 0 && (
            <section>
              <h3 style={{ fontSize: 16, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}><UserPlus size={18} style={{ color: "var(--color-primary)" }} /> Join Requests</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {joinRequests.map((req) => (
                  <div key={req.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 12 }}>
                    <div>
                      <div style={{ fontWeight: 600 }}>User: {req.user_id}</div>
                      {req.message && <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{req.message}</div>}
                    </div>
                    <div style={{ display: "flex", gap: 8 }}>
                      <button className="btn-secondary" onClick={async () => { await workspaces.rejectJoinRequest(wsId, req.id); await loadData(); }}>Reject</button>
                      <button className="btn-primary" onClick={async () => { await workspaces.approveJoinRequest(wsId, req.id); await loadData(); }}>Approve</button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          <section>
            <h3 style={{ fontSize: 16, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}><UserPlus size={18} style={{ color: "var(--color-primary)" }} /> Invite Member</h3>
            <div style={{ display: "flex", gap: 10, background: "var(--bg-surface)", padding: 16, borderRadius: 12, border: "1px solid var(--border-default)" }}>
              <input className="mt-input" placeholder="email@example.com" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} style={{ flex: 1 }} />
              <select className="mt-input" value={inviteRole} onChange={(e) => setInviteRole(e.target.value)} style={{ width: 120 }}>
                <option value="viewer">Viewer</option>
                <option value="editor">Editor</option>
              </select>
              <button className="btn-primary" onClick={async () => {
                await workspaces.createInvite(wsId, { email: inviteEmail, role: inviteRole });
                setInviteEmail("");
                await loadData();
                toast({ message: "Invite sent", variant: "success" });
              }}>Send</button>
            </div>
          </section>

          {invites.length > 0 && (
            <section style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {invites.map((invite) => (
                <div key={invite.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 14px", background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: 8, fontSize: 13 }}>
                  <div>{invite.email} <span style={{ opacity: 0.6 }}>({invite.role})</span></div>
                  <button className="btn-secondary" onClick={async () => {
                    const ok = await confirm({ title: "Revoke invite", message: `Revoke invite for ${invite.email}?`, variant: "warning", confirmLabel: "Revoke" });
                    if (!ok) return;
                    await workspaces.deleteInvite(invite.id);
                    await loadData();
                  }}><Trash2 size={14} /></button>
                </div>
              ))}
            </section>
          )}

          <section>
            <h3 style={{ fontSize: 16, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}><Users size={18} style={{ color: "var(--color-primary)" }} /> Workspace Members</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {members.map((member) => (
                <div key={member.user_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 12 }}>
                  <div>
                    <div style={{ fontWeight: 600 }}>{member.display_name}</div>
                    <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{member.email}</div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <select className="mt-input" value={member.role} style={{ width: 120 }} onChange={async (e) => {
                      await workspaces.updateMember(wsId, member.user_id, e.target.value);
                      await loadData();
                    }}>
                      <option value="viewer">Viewer</option>
                      <option value="editor">Editor</option>
                      <option value="owner">Owner</option>
                    </select>
                    <button className="btn-secondary" onClick={async () => {
                      await workspaces.removeMember(wsId, member.user_id);
                      await loadData();
                    }}><Trash2 size={14} /></button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

