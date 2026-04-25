import { useEffect, useMemo, useState } from "react";
import { Bot, Copy, ExternalLink, Key, Link2, RefreshCw, Search, ShieldCheck, Trash2, UserPlus, Users } from "lucide-react";
import { aiReviewers, users, workspaces, type AIReviewer, type AIReviewerPayload, type Invite, type JoinRequest, type Member, type Workspace, type WorkspaceAssociation, type PersonalApiKey } from "./api";
import { useTranslation } from "react-i18next";
import { useModal } from "./components/ModalContext";
import KbExportPanel from "./components/KbExportPanel";

const DEFAULT_AI_REVIEW_PROMPT = `You are an AI reviewer for a collaborative knowledge graph.
Return JSON with decision, confidence, and reasoning.
Accept only low-risk, well-supported changes.`;

function SectionCard({ children }: { children: React.ReactNode }) {
  return (
    <section style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 14, padding: 18 }}>
      {children}
    </section>
  );
}

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

  useEffect(() => {
    load();
  }, [wsId]);

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
      <SectionCard>
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
      </SectionCard>

      <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {items.map((item) => (
          <div key={item.id} style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 12, padding: 14, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
            <div>
              <div style={{ fontWeight: 600 }}>{item.name}</div>
              <div style={{ color: "var(--text-muted)", fontSize: 13 }}>{item.provider} / {item.model}</div>
              <div style={{ color: "var(--text-muted)", fontSize: 12, marginTop: 4 }}>
                accept ≥ {item.auto_accept_threshold}, reject ≤ {item.auto_reject_threshold}
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

function APIKeysSettings({ wsId }: { wsId: string }) {
  const { confirm, toast, alert } = useModal();
  const [keys, setKeys] = useState<PersonalApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [newKeyName, setNewKeyName] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const all = await users.apiKeys.list();
      setKeys(all.filter(k => !k.workspace_id || k.workspace_id === wsId));
    } catch (e) {
      toast({ message: String(e), variant: "error" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [wsId]);

  const handleCreate = async () => {
    if (!newKeyName.trim()) return;
    try {
      const res = await users.apiKeys.create({ name: newKeyName, scopes: ["read", "write"], workspace_id: wsId });
      setNewKeyName("");
      await load();
      alert({
        title: "New API Key Created",
        message: (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <p>Please copy your new API key now. You won't be able to see it again!</p>
            <div style={{ display: "flex", gap: 8 }}>
              <input className="mt-input" readOnly value={res.key} style={{ flex: 1, fontFamily: "monospace" }} />
              <button className="btn-secondary" onClick={() => {
                navigator.clipboard.writeText(res.key);
                toast({ message: "Key copied", variant: "success" });
              }}><Copy size={16} /></button>
            </div>
          </div>
        )
      });
    } catch (e) {
      toast({ message: String(e), variant: "error" });
    }
  };

  const handleRotate = async (id: string) => {
    const ok = await confirm({ title: "Rotate API Key", message: "This will revoke the current key and generate a new one. Continue?", variant: "warning", confirmLabel: "Rotate" });
    if (!ok) return;
    try {
      const res = await users.apiKeys.rotate(id);
      await load();
      alert({
        title: "API Key Rotated",
        message: (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <p>Your new API key is shown below. Update your clients immediately!</p>
            <div style={{ display: "flex", gap: 8 }}>
              <input className="mt-input" readOnly value={res.key} style={{ flex: 1, fontFamily: "monospace" }} />
              <button className="btn-secondary" onClick={() => {
                navigator.clipboard.writeText(res.key);
                toast({ message: "Key copied", variant: "success" });
              }}><Copy size={16} /></button>
            </div>
          </div>
        )
      });
    } catch (e) {
      toast({ message: String(e), variant: "error" });
    }
  };

  const handleRevoke = async (id: string) => {
    const ok = await confirm({ title: "Revoke API Key", message: "Are you sure? This action cannot be undone.", variant: "danger", confirmLabel: "Revoke" });
    if (!ok) return;
    try {
      await users.apiKeys.revoke(id);
      await load();
      toast({ message: "API key revoked", variant: "success" });
    } catch (e) {
      toast({ message: String(e), variant: "error" });
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <SectionCard>
        <h3 style={{ margin: "0 0 16px", display: "flex", alignItems: "center", gap: 8 }}><Key size={18} /> Manage API Keys</h3>
        <div style={{ display: "flex", gap: 10 }}>
          <input className="mt-input" placeholder="Key name (e.g. My Script)" value={newKeyName} onChange={e => setNewKeyName(e.target.value)} style={{ flex: 1 }} />
          <button className="btn-primary" onClick={handleCreate}>Generate Key</button>
        </div>
      </SectionCard>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {keys.map(k => (
          <div key={k.id} style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 12, padding: 16, display: "flex", justifyContent: "space-between", alignItems: "center", opacity: k.revoked_at ? 0.6 : 1 }}>
            <div>
              <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 8 }}>
                {k.name} {k.revoked_at && <span className="tag" style={{ color: "var(--color-error)" }}>Revoked</span>}
              </div>
              <div style={{ fontSize: 13, color: "var(--text-muted)", fontFamily: "monospace", marginTop: 4 }}>{k.prefix}********************</div>
              <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 6 }}>
                Created: {new Date(k.created_at).toLocaleDateString()} · Last used: {k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : "Never"}
              </div>
            </div>
            {!k.revoked_at && (
              <div style={{ display: "flex", gap: 8 }}>
                <button className="btn-secondary" onClick={() => handleRotate(k.id)} title="Rotate Key"><RefreshCw size={14} /></button>
                <button className="btn-secondary" onClick={() => handleRevoke(k.id)}><Trash2 size={14} /></button>
              </div>
            )}
          </div>
        ))}
        {!loading && keys.length === 0 && <div style={{ color: "var(--text-muted)", textAlign: "center", padding: 20 }}>No API keys for this workspace.</div>}
      </div>
    </div>
  );
}

type MainTab = "general" | "members" | "export" | "assoc" | "ai_review" | "apikeys";
type AccessTab = "members" | "invites" | "requests";

export default function WorkspaceSettings({ wsId }: { wsId: string }) {
  const { t, i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const { confirm, toast } = useModal();
  const [ws, setWs] = useState<Workspace | null>(null);
  const [joinRequests, setJoinRequests] = useState<JoinRequest[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [inviteRole, setInviteRole] = useState("viewer");
  const [inviteDays, setInviteDays] = useState(7);
  const [latestInvite, setLatestInvite] = useState<Invite | null>(null);
  const [associations, setAssociations] = useState<WorkspaceAssociation[]>([]);
  const [workspaceSearch, setWorkspaceSearch] = useState("");
  const [workspaceResults, setWorkspaceResults] = useState<Workspace[]>([]);
  const [tab, setTab] = useState<MainTab>("general");
  const [accessTab, setAccessTab] = useState<AccessTab>("members");

  const [nameZh, setNameZh] = useState("");
  const [nameEn, setNameEn] = useState("");
  const [isSaving, setIsSaving] = useState(false);

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
      setNameZh(w.name_zh);
      setNameEn(w.name_en);
      setJoinRequests(reqs);
      setAssociations(as);
    } catch {
      // Keep current UI state if some fetch fails.
    }
  };

  useEffect(() => {
    loadData();
  }, [wsId]);

  useEffect(() => {
    let active = true;
    if (workspaceSearch.trim().length < 2) {
      setWorkspaceResults([]);
      return;
    }
    workspaces.list(workspaceSearch.trim()).then((result) => {
      if (!active) return;
      setWorkspaceResults(result.filter((item) => item.id !== wsId));
    }).catch(() => {
      if (active) setWorkspaceResults([]);
    });
    return () => {
      active = false;
    };
  }, [workspaceSearch, wsId]);

  const associationIds = useMemo(() => new Set(associations.map((item) => item.target_ws_id)), [associations]);

  const renderAccessTabs = (
    <div style={{ display: "flex", gap: 10, marginBottom: 8, flexWrap: "wrap" }}>
      {([
        ["members", t('ws_settings.membersAccess')],
        ["invites", t('ws_settings.invites')],
        ["requests", t('ws_settings.requests')],
      ] as Array<[AccessTab, string]>).map(([value, label]) => (
        <button
          key={value}
          className={`tag ${accessTab === value ? "tag-active" : ""}`}
          onClick={() => setAccessTab(value)}
        >
          {label}
        </button>
      ))}
    </div>
  );

  return (
    <div style={{ padding: "0 20px", display: "flex", flexDirection: "column", gap: 24 }}>
      <div style={{ display: "flex", gap: 20, borderBottom: "1px solid var(--border-subtle)", marginBottom: 8, flexWrap: "wrap" }}>
        <button onClick={() => setTab("general")} style={{ padding: "12px 4px", background: "none", border: "none", cursor: "pointer", fontSize: 14, fontWeight: 600, color: tab === "general" ? "var(--color-primary)" : "var(--text-muted)", borderBottom: tab === "general" ? "2px solid var(--color-primary)" : "2px solid transparent" }}>{t('ws_settings.general')}</button>
        <button onClick={() => setTab("members")} style={{ padding: "12px 4px", background: "none", border: "none", cursor: "pointer", fontSize: 14, fontWeight: 600, color: tab === "members" ? "var(--color-primary)" : "var(--text-muted)", borderBottom: tab === "members" ? "2px solid var(--color-primary)" : "2px solid transparent" }}>{t('ws_settings.membersAccess')}</button>
        <button onClick={() => setTab("export")} style={{ padding: "12px 4px", background: "none", border: "none", cursor: "pointer", fontSize: 14, fontWeight: 600, color: tab === "export" ? "var(--color-primary)" : "var(--text-muted)", borderBottom: tab === "export" ? "2px solid var(--color-primary)" : "2px solid transparent" }}>{t('ws_settings.dataExport')}</button>
        <button onClick={() => setTab("assoc")} style={{ padding: "12px 4px", background: "none", border: "none", cursor: "pointer", fontSize: 14, fontWeight: 600, color: tab === "assoc" ? "var(--color-primary)" : "var(--text-muted)", borderBottom: tab === "assoc" ? "2px solid var(--color-primary)" : "2px solid transparent" }}>{t('ws_settings.kbAssoc')}</button>
        <button onClick={() => setTab("ai_review")} style={{ padding: "12px 4px", background: "none", border: "none", cursor: "pointer", fontSize: 14, fontWeight: 600, color: tab === "ai_review" ? "var(--color-primary)" : "var(--text-muted)", borderBottom: tab === "ai_review" ? "2px solid var(--color-primary)" : "2px solid transparent" }}>{t('ws_settings.aiReviewers')}</button>
        <button onClick={() => setTab("apikeys")} style={{ padding: "12px 4px", background: "none", border: "none", cursor: "pointer", fontSize: 14, fontWeight: 600, color: tab === "apikeys" ? "var(--color-primary)" : "var(--text-muted)", borderBottom: tab === "apikeys" ? "2px solid var(--color-primary)" : "2px solid transparent" }}>{t('ws_settings.apiKeys')}</button>
      </div>

      {tab === "general" ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <SectionCard>
            <h3 style={{ fontSize: 16, margin: "0 0 16px" }}>{t('ws_settings.general')}</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div>
                <label style={{ display: "block", fontSize: 13, marginBottom: 6, color: "var(--text-muted)" }}>{t('ws_settings.kbNameZh')}</label>
                <input className="mt-input" value={nameZh} onChange={e => setNameZh(e.target.value)} style={{ width: "100%" }} />
              </div>
              <div>
                <label style={{ display: "block", fontSize: 13, marginBottom: 6, color: "var(--text-muted)" }}>{t('ws_settings.kbNameEn')}</label>
                <input className="mt-input" value={nameEn} onChange={e => setNameEn(e.target.value)} style={{ width: "100%" }} />
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 8 }}>
                <button className="btn-primary" disabled={isSaving || (nameZh === ws?.name_zh && nameEn === ws?.name_en)} onClick={async () => {
                  setIsSaving(true);
                  try {
                    await workspaces.update(wsId, { name_zh: nameZh, name_en: nameEn });
                    await loadData();
                    toast({ message: "Workspace name updated", variant: "success" });
                  } catch (err) {
                    toast({ message: err instanceof Error ? err.message : String(err), variant: "error" });
                  } finally {
                    setIsSaving(false);
                  }
                }}>{t('ws_settings.save')}</button>
              </div>
            </div>
          </SectionCard>

          <SectionCard>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <div style={{ fontWeight: 600 }}>{t('ws_settings.visibility')}</div>
                <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{t('ws_settings.visibilityDesc')}</div>
              </div>
              <select className="mt-input" value={ws?.visibility ?? "private"} style={{ width: 180 }} onChange={async (e) => {
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
          </SectionCard>
        </div>
      ) : tab === "assoc" ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <SectionCard>
            <h3 style={{ fontSize: 16, margin: "0 0 16px", display: "flex", alignItems: "center", gap: 8 }}><ExternalLink size={18} style={{ color: "var(--color-primary)" }} /> Add KB Association</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{ position: "relative" }}>
                <Search size={15} style={{ position: "absolute", left: 12, top: 12, color: "var(--text-muted)" }} />
                <input className="mt-input" placeholder="Search workspace name" value={workspaceSearch} onChange={(e) => setWorkspaceSearch(e.target.value)} style={{ paddingLeft: 36 }} />
              </div>
              {workspaceResults.length > 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {workspaceResults.slice(0, 8).map((result) => (
                    <div key={result.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, border: "1px solid var(--border-subtle)", borderRadius: 10, padding: "10px 12px" }}>
                      <div>
                        <div style={{ fontWeight: 600 }}>{result.name_en}</div>
                        <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{result.name_zh} / {result.visibility}</div>
                      </div>
                      <button
                        className="btn-primary"
                        disabled={associationIds.has(result.id)}
                        onClick={async () => {
                          try {
                            await workspaces.createAssociation(wsId, result.id);
                            setWorkspaceSearch("");
                            setWorkspaceResults([]);
                            await loadData();
                            toast({ message: "Association created", variant: "success" });
                          } catch (e) {
                            toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
                          }
                        }}
                      >
                        {associationIds.has(result.id) ? "Added" : "Associate"}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </SectionCard>

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
        <KbExportPanel wsId={wsId} zh={zh} />
      ) : tab === "ai_review" ? (
        <AIReviewerSettings wsId={wsId} />
      ) : tab === "apikeys" ? (
        <APIKeysSettings wsId={wsId} />
      ) : (
        <>
          {renderAccessTabs}

          {accessTab === "members" && (
            <section>
              <h3 style={{ fontSize: 16, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}><Users size={18} style={{ color: "var(--color-primary)" }} /> Workspace Members</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {members.map((member) => (
                  <div key={member.user_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 12 }}>
                    <div>
                      <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 8 }}>
                        {member.display_name}
                        {member.role === "owner" && <span className="tag"><ShieldCheck size={12} /> Owner</span>}
                      </div>
                      <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{member.email}</div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <select
                        className="mt-input"
                        value={member.role}
                        style={{ width: 120 }}
                        disabled={member.role === "owner"}
                        onChange={async (e) => {
                          await workspaces.updateMember(wsId, member.user_id, e.target.value);
                          await loadData();
                        }}
                      >
                        <option value="viewer">Viewer</option>
                        <option value="editor">Editor</option>
                        <option value="owner">Owner</option>
                      </select>
                      <button
                        className="btn-secondary"
                        disabled={member.role === "owner"}
                        onClick={async () => {
                          const ok = await confirm({ title: "Remove member", message: `Remove ${member.email}?`, variant: "warning", confirmLabel: "Remove" });
                          if (!ok) return;
                          await workspaces.removeMember(wsId, member.user_id);
                          await loadData();
                        }}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {accessTab === "invites" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
              <SectionCard>
                <h3 style={{ fontSize: 16, margin: "0 0 16px", display: "flex", alignItems: "center", gap: 8 }}><Link2 size={18} style={{ color: "var(--color-primary)" }} /> Create Invite Link</h3>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: 10 }}>
                  <select className="mt-input" value={inviteRole} onChange={(e) => setInviteRole(e.target.value)}>
                    <option value="viewer">Viewer</option>
                    <option value="editor">Editor</option>
                  </select>
                  <select className="mt-input" value={inviteDays} onChange={(e) => setInviteDays(Number(e.target.value))}>
                    <option value={3}>3 days</option>
                    <option value={7}>7 days</option>
                    <option value={30}>30 days</option>
                  </select>
                  <button className="btn-primary" onClick={async () => {
                    try {
                      const invite = await workspaces.createInvite(wsId, { role: inviteRole, expires_in_days: inviteDays });
                      setLatestInvite(invite);
                      await loadData();
                      toast({ message: "Invite link created", variant: "success" });
                    } catch (e) {
                      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
                    }
                  }}>
                    Generate
                  </button>
                </div>
                {latestInvite?.invite_url && (
                  <div style={{ marginTop: 14, display: "flex", gap: 8 }}>
                    <input className="mt-input" readOnly value={latestInvite.invite_url} style={{ flex: 1 }} />
                    <button className="btn-secondary" onClick={async () => {
                      await navigator.clipboard.writeText(latestInvite.invite_url ?? "");
                      toast({ message: "Invite link copied", variant: "success" });
                    }}>
                      <Copy size={15} />
                    </button>
                  </div>
                )}
              </SectionCard>

              <section style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {invites.map((invite) => (
                  <div key={invite.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, padding: "12px 14px", background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: 10 }}>
                    <div>
                      <div style={{ fontWeight: 600 }}>{invite.role}</div>
                      <div style={{ fontSize: 12, color: "var(--text-muted)" }}>Expires {new Date(invite.expires_at).toLocaleString()}</div>
                    </div>
                    <div style={{ display: "flex", gap: 8 }}>
                      {invite.invite_url && (
                        <button className="btn-secondary" onClick={async () => {
                          await navigator.clipboard.writeText(invite.invite_url ?? "");
                          toast({ message: "Invite link copied", variant: "success" });
                        }}>
                          <Copy size={14} />
                        </button>
                      )}
                      <button className="btn-secondary" onClick={async () => {
                        const ok = await confirm({ title: "Revoke invite", message: "Revoke this invite link?", variant: "warning", confirmLabel: "Revoke" });
                        if (!ok) return;
                        await workspaces.deleteInvite(invite.id);
                        await loadData();
                      }}>
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                ))}
                {!invites.length && <div style={{ color: "var(--text-muted)" }}>No active invite links.</div>}
              </section>
            </div>
          )}

          {accessTab === "requests" && (
            <section>
              <h3 style={{ fontSize: 16, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}><UserPlus size={18} style={{ color: "var(--color-primary)" }} /> Join Requests</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {joinRequests.map((req) => (
                  <div key={req.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 12 }}>
                    <div>
                      <div style={{ fontWeight: 600 }}>User: {req.user_id}</div>
                      <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{new Date(req.requested_at).toLocaleString()}</div>
                      {req.message && <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>{req.message}</div>}
                    </div>
                    <div style={{ display: "flex", gap: 8 }}>
                      <button className="btn-secondary" onClick={async () => { await workspaces.rejectJoinRequest(wsId, req.id); await loadData(); }}>Reject</button>
                      <button className="btn-primary" onClick={async () => { await workspaces.approveJoinRequest(wsId, req.id); await loadData(); }}>Approve</button>
                    </div>
                  </div>
                ))}
                {!joinRequests.length && <div style={{ color: "var(--text-muted)" }}>No pending join requests.</div>}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
