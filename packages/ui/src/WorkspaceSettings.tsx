import { useEffect, useMemo, useState } from "react";
import { Bot, Clock, Copy, ExternalLink, Info, Key, Link2, RefreshCw, Search, ShieldAlert, ShieldCheck, Trash2, UserPlus, Users } from "lucide-react";
import { aiReviewers, workspaces, type AIReviewer, type AIReviewerPayload, type Invite, type JoinRequest, type Member, type Workspace, type WorkspaceAssociation, type PersonalApiKey } from "./api";
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
  const { t } = useTranslation();
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
        <h3 style={{ marginTop: 0, display: "flex", alignItems: "center", gap: 8 }}><Bot size={18} /> {t('ws_settings.create_reviewer_title')}</h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
          <input className="mt-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder={t('ws_settings.members')} />
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
          <button className="btn-primary" onClick={save}>{t('ws_settings.create')}</button>
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
              }}>{item.enabled ? t('common.disable') : t('common.enable')}</button>
              <button className="btn-secondary" onClick={async () => {
                await aiReviewers.delete(wsId, item.id);
                await load();
              }}><Trash2 size={16} /></button>
            </div>
          </div>
        ))}
        {!items.length && <div style={{ color: "var(--text-muted)" }}>{t('ws_settings.no_reviewers')}</div>}
      </section>
    </div>
  );
}

function APIKeysSettings({ wsId }: { wsId: string }) {
  const { t, i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const { confirm, toast, alert } = useModal();
  const [keys, setKeys] = useState<PersonalApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyScope, setNewKeyScope] = useState("kb:read");

  const load = async () => {
    setLoading(true);
    try {
      const all = await workspaces.listApiKeys(wsId);
      setKeys(all);
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
      const res = await workspaces.createApiKey(wsId, { name: newKeyName, scope: newKeyScope });
      setNewKeyName("");
      await load();
      alert({
        title: t('ws_settings.new_key_title'),
        message: (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <p>{t('ws_settings.new_key_msg')}</p>
            <div style={{ display: "flex", gap: 8 }}>
              <input className="mt-input" readOnly value={res.key} style={{ flex: 1, fontFamily: "monospace" }} />
              <button className="btn-secondary" onClick={() => {
                navigator.clipboard.writeText(res.key);
                toast({ message: t('common.copied'), variant: "success" });
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
    const ok = await confirm({ title: t('ws_settings.rotate_key_title'), message: t('ws_settings.rotate_key_msg'), variant: "warning", confirmLabel: t('common.rotate') });
    if (!ok) return;
    try {
      const res = await workspaces.rotateApiKey(wsId, id);
      await load();
      alert({
        title: t('ws_settings.rotated_key_title'),
        message: (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <p>{t('ws_settings.rotated_key_msg')}</p>
            <div style={{ display: "flex", gap: 8 }}>
              <input className="mt-input" readOnly value={res.key} style={{ flex: 1, fontFamily: "monospace" }} />
              <button className="btn-secondary" onClick={() => {
                navigator.clipboard.writeText(res.key);
                toast({ message: t('common.copied'), variant: "success" });
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
    const ok = await confirm({ title: t('ws_settings.revoke_key_title'), message: t('ws_settings.revoke_key_msg'), variant: "danger", confirmLabel: t('common.revoke') });
    if (!ok) return;
    try {
      await workspaces.revokeApiKey(wsId, id);
      await load();
      toast({ message: t('ws_settings.revoke'), variant: "success" });
    } catch (e) {
      toast({ message: String(e), variant: "error" });
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <SectionCard>
        <h3 style={{ margin: "0 0 16px", display: "flex", alignItems: "center", gap: 8 }}><Key size={18} /> {t('ws_settings.service_tokens')}</h3>
        <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 16 }}>
          {zh ? "服務 Token 用於自動化任務，如 API 攝入或外部整合。" : "Service tokens are used for automated tasks like API ingestion or external integrations."}
        </p>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <input className="mt-input" placeholder={zh ? "名稱 (例: Ingestion Bot)" : "Key name (e.g. Ingestion Bot)"} value={newKeyName} onChange={e => setNewKeyName(e.target.value)} style={{ flex: 2, minWidth: 200 }} />
          <select className="mt-input" value={newKeyScope} onChange={e => setNewKeyScope(e.target.value)} style={{ flex: 1, minWidth: 140 }}>
            <option value="kb:read">kb:read</option>
            <option value="kb:propose">kb:propose</option>
            <option value="kb:write">kb:write</option>
          </select>
          <button className="btn-primary" onClick={handleCreate}>{zh ? "產生 Token" : "Generate Token"}</button>
        </div>
      </SectionCard>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {keys.map(k => (
          <div key={k.id} style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 12, padding: 16, display: "flex", justifyContent: "space-between", alignItems: "center", opacity: k.revoked_at ? 0.6 : 1 }}>
            <div>
              <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 8 }}>
                {k.name} 
                <span className="tag" style={{ color: "var(--color-primary)", background: "var(--color-primary-subtle)" }}>{k.scopes.join(', ')}</span>
                {k.revoked_at && <span className="tag" style={{ color: "var(--color-error)" }}>Revoked</span>}
              </div>
              <div style={{ fontSize: 13, color: "var(--text-muted)", fontFamily: "monospace", marginTop: 4 }}>{k.prefix}********************</div>
              <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 6 }}>
                Created: {new Date(k.created_at).toLocaleDateString()} · Last used: {k.last_used_at ? new Date(k.last_used_at).toLocaleString() : "Never"}
              </div>
            </div>
            {!k.revoked_at && (
              <div style={{ display: "flex", gap: 8 }}>
                <button className="btn-secondary" onClick={() => handleRotate(k.id)} title="Rotate Token"><RefreshCw size={14} /></button>
                <button className="btn-secondary" onClick={() => handleRevoke(k.id)}><Trash2 size={14} /></button>
              </div>
            )}
          </div>
        ))}
        {!loading && keys.length === 0 && <div style={{ color: "var(--text-muted)", textAlign: "center", padding: 20 }}>{t('ws_settings.noRequests')}</div>}
      </div>
    </div>
  );
}

type MainTab = "general" | "members" | "export" | "assoc" | "ai_review" | "apikeys";
type AccessTab = "members" | "invites" | "requests";

export default function WorkspaceSettings({ wsId, userId }: { wsId: string; userId?: string }) {
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
  const [decayStats, setDecayStats] = useState<any>(null);
  const [healthReport, setHealthReport] = useState<any>(null);

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

      // Fetch admin-only decay stats if we are the owner
      if (w.owner_id === userId) {
        workspaces.getDecayStats(wsId).then(setDecayStats).catch(() => {});
      }
      // Fetch health report
      workspaces.getHealthReport(wsId).then(setHealthReport).catch(() => {});
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
        {ws?.owner_id === userId && (
          <button onClick={() => setTab("apikeys")} style={{ padding: "12px 4px", background: "none", border: "none", cursor: "pointer", fontSize: 14, fontWeight: 600, color: tab === "apikeys" ? "var(--color-primary)" : "var(--text-muted)", borderBottom: tab === "apikeys" ? "2px solid var(--color-primary)" : "2px solid transparent" }}>{t('ws_settings.apiKeys')}</button>
        )}
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
                <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
                  {t('ws_settings.visibility')}
                  <div className="info-tooltip-wrapper">
                    <Info size={14} style={{ color: "var(--color-primary)", cursor: "help" }} />
                    <div className="info-tooltip">
                      <div style={{ marginBottom: 12, fontWeight: 700, fontSize: 14 }}>{t('ws_settings.visibility_guide')}</div>
                      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                        <div><b>{t('ws_settings.vis_private')}</b>: {t('ws_settings.vis_private_desc')}</div>
                        <div><b>{t('ws_settings.vis_restricted')}</b>: {t('ws_settings.vis_restricted_desc')}</div>
                        <div><b>{t('ws_settings.vis_conditional_public')}</b>: {t('ws_settings.vis_conditional_public_desc')}</div>
                        <div><b>{t('ws_settings.vis_public')}</b>: {t('ws_settings.vis_public_desc')}</div>
                      </div>
                    </div>
                  </div>
                </div>
                <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{t('ws_settings.visibilityDesc')}</div>
              </div>
              <select className="mt-input" value={ws?.visibility ?? "private"} style={{ width: 180 }} onChange={async (e) => {
                try {
                  await workspaces.update(wsId, { visibility: e.target.value });
                  await loadData();
                  toast({ message: t('ws_settings.vis_updated'), variant: "success" });
                } catch (err) {
                  toast({ message: err instanceof Error ? err.message : String(err), variant: "error" });
                }
              }}>
                <option value="private">{t('ws_settings.vis_private')}</option>
                <option value="restricted">{t('ws_settings.vis_restricted')}</option>
                <option value="conditional_public">{t('ws_settings.vis_conditional_public')}</option>
                <option value="public">{t('ws_settings.vis_public')}</option>
              </select>
            </div>
          </SectionCard>

          {/* P6 - Decay Status */}
          {decayStats && (
            <SectionCard>
              <h3 style={{ fontSize: 16, margin: "0 0 16px", display: "flex", alignItems: "center", gap: 8 }}><Clock size={18} /> {t('ws_settings.edge_decay_status')}</h3>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
                <div>
                  <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{t('ws_settings.last_decay_run')}</div>
                  <div style={{ fontWeight: 600 }}>{decayStats.last_decay_at ? new Date(decayStats.last_decay_at).toLocaleString() : (zh ? "從未執行" : "Never")}</div>
                </div>
                <div>
                  <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{t('ws_settings.faded_edges')}</div>
                  <div style={{ fontWeight: 600 }}>{decayStats.faded_edge_count ?? 0}</div>
                </div>
                <div>
                  <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{t('ws_settings.low_weight_edges')}</div>
                  <div style={{ fontWeight: 600, color: decayStats.low_weight_edge_count > 0 ? "var(--color-warning)" : undefined }}>{decayStats.low_weight_edge_count ?? 0}</div>
                </div>
              </div>
            </SectionCard>
          )}

          {/* P3 - Health Report */}
          {healthReport && (
            <SectionCard>
              <h3 style={{ fontSize: 16, margin: "0 0 16px", display: "flex", alignItems: "center", gap: 8 }}><ShieldAlert size={18} /> {t('ws_settings.health_report')}</h3>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", background: "var(--bg-elevated)", borderRadius: 8 }}>
                  <span>{t('ws_settings.total_nodes')}</span>
                  <span style={{ fontWeight: 600 }}>{healthReport.total}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", background: "var(--bg-elevated)", borderRadius: 8 }}>
                  <span>{t('ws_settings.empty_body')}</span>
                  <span className="tag" style={{ background: healthReport.empty_body > 0 ? "var(--color-error-subtle)" : "var(--color-success-subtle)", color: healthReport.empty_body > 0 ? "var(--color-error)" : "var(--color-success)" }}>{healthReport.empty_body}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", background: "var(--bg-elevated)", borderRadius: 8 }}>
                  <span>{t('ws_settings.low_trust')}</span>
                  <span className="tag" style={{ background: healthReport.low_trust > 0 ? "var(--color-warning-subtle)" : "var(--color-success-subtle)", color: healthReport.low_trust > 0 ? "var(--color-warning)" : "var(--color-success)" }}>{healthReport.low_trust}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", background: "var(--bg-elevated)", borderRadius: 8 }}>
                  <span>{t('ws_settings.orphan_nodes')}</span>
                  <span className="tag" style={{ background: healthReport.no_edges > 0 ? "var(--color-warning-subtle)" : "var(--color-success-subtle)", color: healthReport.no_edges > 0 ? "var(--color-warning)" : "var(--color-success)" }}>{healthReport.no_edges}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", background: "var(--bg-elevated)", borderRadius: 8 }}>
                  <span>{t('ws_settings.no_embedding')}</span>
                  <span className="tag" style={{ background: (healthReport.no_embedding ?? 0) > 0 ? "var(--color-warning-subtle)" : "var(--color-success-subtle)", color: (healthReport.no_embedding ?? 0) > 0 ? "var(--color-warning)" : "var(--color-success)" }}>{healthReport.no_embedding ?? 0}</span>
                </div>
              </div>
            </SectionCard>
          )}
        </div>
      ) : tab === "assoc" ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <SectionCard>
            <h3 style={{ fontSize: 16, margin: "0 0 16px", display: "flex", alignItems: "center", gap: 8 }}><ExternalLink size={18} style={{ color: "var(--color-primary)" }} /> {t('ws_settings.add_assoc_title')}</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{ position: "relative" }}>
                <Search size={15} style={{ position: "absolute", left: 12, top: 12, color: "var(--text-muted)" }} />
                <input className="mt-input" placeholder={t('ws_settings.searchWs')} value={workspaceSearch} onChange={(e) => setWorkspaceSearch(e.target.value)} style={{ paddingLeft: 36 }} />
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
                            toast({ message: t('ws_settings.assoc_created'), variant: "success" });
                          } catch (e) {
                            toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
                          }
                        }}
                      >
                        {associationIds.has(result.id) ? t('ws_settings.added') : t('ws_settings.associate')}
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
            {!associations.length && <div style={{ color: "var(--text-muted)" }}>{t('ws_settings.no_assoc_found')}</div>}
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
              <h3 style={{ fontSize: 16, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}><Users size={18} style={{ color: "var(--color-primary)" }} /> {t('ws_settings.ws_members')}</h3>
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
                <h3 style={{ fontSize: 16, margin: "0 0 16px", display: "flex", alignItems: "center", gap: 8 }}><Link2 size={18} style={{ color: "var(--color-primary)" }} /> {t('ws_settings.create_invite_link')}</h3>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: 10 }}>
                  <select className="mt-input" value={inviteRole} onChange={(e) => setInviteRole(e.target.value)}>
                    <option value="viewer">Viewer</option>
                    <option value="editor">Editor</option>
                  </select>
                  <select className="mt-input" value={inviteDays} onChange={(e) => setInviteDays(Number(e.target.value))}>
                    <option value={3}>{zh ? "3 天" : "3 days"}</option>
                    <option value={7}>{zh ? "7 天" : "7 days"}</option>
                    <option value={30}>{zh ? "30 天" : "30 days"}</option>
                  </select>
                  <button className="btn-primary" onClick={async () => {
                    try {
                      const invite = await workspaces.createInvite(wsId, { role: inviteRole, expires_in_days: inviteDays });
                      setLatestInvite(invite);
                      await loadData();
                      toast({ message: t('ws_settings.invites'), variant: "success" });
                    } catch (e) {
                      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
                    }
                  }}>
                    {zh ? "產生" : "Generate"}
                  </button>
                </div>
                {latestInvite?.invite_url && (
                  <div style={{ marginTop: 14, display: "flex", gap: 8 }}>
                    <input className="mt-input" readOnly value={latestInvite.invite_url} style={{ flex: 1 }} />
                    <button className="btn-secondary" onClick={async () => {
                      await navigator.clipboard.writeText(latestInvite.invite_url ?? "");
                      toast({ message: t('common.copied'), variant: "success" });
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
                      <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{zh ? "到期時間 " : "Expires "}{new Date(invite.expires_at).toLocaleString()}</div>
                    </div>
                    <div style={{ display: "flex", gap: 8 }}>
                      {invite.invite_url && (
                        <button className="btn-secondary" onClick={async () => {
                          await navigator.clipboard.writeText(invite.invite_url ?? "");
                          toast({ message: t('common.copied'), variant: "success" });
                        }}>
                          <Copy size={14} />
                        </button>
                      )}
                      <button className="btn-secondary" onClick={async () => {
                        const ok = await confirm({ title: t('ws_settings.revoke'), message: zh ? "確定要撤銷此邀請連結嗎？" : "Revoke this invite link?", variant: "warning", confirmLabel: t('ws_settings.revoke') });
                        if (!ok) return;
                        await workspaces.deleteInvite(invite.id);
                        await loadData();
                      }}>
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                ))}
                {!invites.length && <div style={{ color: "var(--text-muted)" }}>{t('ws_settings.no_invites_found')}</div>}
              </section>
            </div>
          )}

          {accessTab === "requests" && (
            <section>
              <h3 style={{ fontSize: 16, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}><UserPlus size={18} style={{ color: "var(--color-primary)" }} /> {t('ws_settings.join_requests')}</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {joinRequests.map((req) => (
                  <div key={req.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 12 }}>
                    <div>
                      <div style={{ fontWeight: 600 }}>User: {req.user_id}</div>
                      <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{new Date(req.requested_at).toLocaleString()}</div>
                      {req.message && <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>{req.message}</div>}
                    </div>
                    <div style={{ display: "flex", gap: 8 }}>
                      <button className="btn-secondary" onClick={async () => { await workspaces.rejectJoinRequest(wsId, req.id); await loadData(); }}>{t('common.reject')}</button>
                      <button className="btn-primary" onClick={async () => { await workspaces.approveJoinRequest(wsId, req.id); await loadData(); }}>{t('common.approve')}</button>
                    </div>
                  </div>
                ))}
                {!joinRequests.length && <div style={{ color: "var(--text-muted)" }}>{t('ws_settings.no_requests_found')}</div>}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
