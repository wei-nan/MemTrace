import { useEffect, useMemo, useState } from "react";
import { Bot, Clock, Copy, ExternalLink, Info, Key, Link2, RefreshCw, Search, ShieldAlert, ShieldCheck, Trash2, UserPlus, Users, AlertTriangle, Brain } from "lucide-react";
import { ai, aiReviewers, workspaces, type AIReviewer, type AIReviewerPayload, type Invite, type JoinRequest, type Member, type Workspace, type WorkspaceAssociation, type PersonalApiKey } from "./api";
import { useTranslation } from "react-i18next";
import { useModal } from "./components/ModalContext";
import { ModalOverlay } from "./components/Modal";
import KbExportPanel from "./components/KbExportPanel";

const DEFAULT_AI_REVIEW_PROMPT = `You are an AI reviewer for a collaborative knowledge graph.
Return JSON with decision, confidence, and reasoning.
Accept only low-risk, well-supported changes.`;

function DeleteWorkspaceDialog({ ws, onConfirm, onCancel }: { ws: Workspace, onConfirm: () => void, onCancel: () => void }) {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const [typedName, setTypedName] = useState("");
  const expectedName = ws.name_zh || ws.name_en;
  const isValid = typedName === expectedName;

  return (
    <ModalOverlay onClose={onCancel}>
      <div style={{ padding: 24 }}>
        <div style={{ display: "flex", gap: 14, marginBottom: 20 }}>
          <div style={{ flexShrink: 0, width: 40, height: 40, borderRadius: 10, background: "var(--color-error-subtle)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <AlertTriangle size={20} color="var(--color-error)" />
          </div>
          <div style={{ flex: 1, paddingTop: 8 }}>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>{zh ? "確認刪除工作區" : "Delete Workspace"}</h3>
          </div>
        </div>
        <p style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: 16 }}>
          {zh ? "此操作不可復原。刪除後所有節點、邊、成員記錄將永久消失。" : "This action cannot be undone. All nodes, edges, and member records will be permanently deleted."}
          <br />
          {zh ? `請輸入工作區名稱「${expectedName}」以確認刪除：` : `Please type the workspace name "${expectedName}" to confirm:`}
        </p>
        <input
          className="mt-input"
          style={{ width: "100%", marginBottom: 24 }}
          value={typedName}
          onChange={e => setTypedName(e.target.value)}
          placeholder={expectedName}
          autoFocus
        />
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
          <button className="btn-secondary" onClick={onCancel}>{zh ? "取消" : "Cancel"}</button>
          <button 
            className="btn-primary" 
            style={{ background: isValid ? "var(--color-error)" : "var(--bg-elevated)", color: isValid ? "#fff" : "var(--text-muted)", border: "none", cursor: isValid ? "pointer" : "not-allowed" }}
            disabled={!isValid}
            onClick={onConfirm}
          >
            {zh ? "確認刪除" : "Confirm Delete"}
          </button>
        </div>
      </div>
    </ModalOverlay>
  );
}

function CloneWorkspaceDialog({ ws, onConfirm, onCancel }: { ws: Workspace, onConfirm: (data: { name_zh?: string; name_en?: string; new_embedding_model?: string; visibility?: string }) => void, onCancel: () => void }) {
  const { t, i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const [nameZh, setNameZh] = useState(`${ws.name_zh} (副本)`);
  const [nameEn, setNameEn] = useState(`${ws.name_en} (Clone)`);
  const [selectedModel, setSelectedModel] = useState(ws.embedding_model);
  const [visibility, setVisibility] = useState<'private' | 'restricted' | 'conditional_public' | 'public'>('private');
  const [models, setModels] = useState<any[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);

  useEffect(() => {
    const fetchModels = async () => {
      setLoadingModels(true);
      try {
        const resolved = await ai.getResolvedModel('embedding');
        const ms = await ai.listModels(resolved.provider);
        setModels(ms.filter(m => m.model_type === 'embedding'));
      } catch (e) {
        console.error("Failed to fetch models", e);
      } finally {
        setLoadingModels(false);
      }
    };
    fetchModels();
  }, []);

  const needsRebuild = selectedModel !== ws.embedding_model;

  return (
    <ModalOverlay onClose={onCancel}>
      <div style={{ padding: 24 }}>
        <div style={{ display: "flex", gap: 14, marginBottom: 20 }}>
          <div style={{ flexShrink: 0, width: 40, height: 40, borderRadius: 10, background: "var(--color-primary-subtle)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Copy size={20} color="var(--color-primary)" />
          </div>
          <div style={{ flex: 1, paddingTop: 8 }}>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>{zh ? "複製工作區 (Clone & Rebuild)" : "Clone Workspace"}</h3>
          </div>
        </div>
        
        <div style={{ display: "flex", flexDirection: "column", gap: 14, marginBottom: 24 }}>
          <div>
            <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 6 }}>{zh ? "中文名稱" : "Chinese Name"}</label>
            <input className="mt-input" style={{ width: "100%" }} value={nameZh} onChange={e => setNameZh(e.target.value)} />
          </div>
          <div>
            <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 6 }}>{zh ? "英文名稱" : "English Name"}</label>
            <input className="mt-input" style={{ width: "100%" }} value={nameEn} onChange={e => setNameEn(e.target.value)} />
          </div>
          <div>
            <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 6 }}>{zh ? "向量模型 (Embedding Model)" : "Embedding Model"}</label>
            <select 
              className="mt-input" 
              style={{ width: "100%" }} 
              value={selectedModel} 
              onChange={e => setSelectedModel(e.target.value)}
              disabled={loadingModels}
            >
              <option value={ws.embedding_model}>{ws.embedding_model} ({zh ? "當前" : "Current"})</option>
              {models.filter(m => m.id !== ws.embedding_model).map(m => (
                <option key={m.id} value={m.id}>{m.display_name || m.id}</option>
              ))}
            </select>
            {needsRebuild && (
              <div style={{ marginTop: 8, fontSize: 11, color: "var(--color-warning)", display: "flex", alignItems: "center", gap: 4 }}>
                <RefreshCw size={12} className="animate-spin-slow" />
                {zh ? "更換模型後將自動執行全量 Re-embed (可能產生較多 Token 消耗)" : "Changing model will trigger a full Re-embed (may consume significant tokens)"}
              </div>
            )}
          </div>

          {/* Visibility */}
          <div>
            <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 8 }}>
              {zh ? "可見度" : "Visibility"}
            </label>
            <select
              className="mt-input"
              value={visibility}
              onChange={e => setVisibility(e.target.value as any)}
              style={{ width: '100%' }}
            >
              <option value="private">{t('ws_settings.vis_private')}</option>
              <option value="restricted">{t('ws_settings.vis_restricted')}</option>
              <option value="conditional_public">{t('ws_settings.vis_conditional_public')}</option>
              <option value="public">{t('ws_settings.vis_public')}</option>
            </select>
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
          <button className="btn-secondary" onClick={onCancel}>{zh ? "取消" : "Cancel"}</button>
          <button
            className="btn-primary"
            onClick={() => onConfirm({ name_zh: nameZh, name_en: nameEn, new_embedding_model: selectedModel, visibility })}
          >
            {zh ? "開始複製" : "Start Clone"}
          </button>
        </div>
      </div>
    </ModalOverlay>
  );
}

function SectionCard({ children }: { children: React.ReactNode }) {
  return (
    <section style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 14, padding: 18 }}>
      {children}
    </section>
  );
}

function ReembedAllButton({ wsId, zh }: { wsId: string; zh: boolean }) {
  const [state, setState] = useState<'idle' | 'loading' | 'done' | 'error'>('idle');
  const [queued, setQueued] = useState<number | null>(null);

  const handleClick = async () => {
    setState('loading');
    try {
      const res = await workspaces.reembedAll(wsId);
      setQueued(res.queued);
      setState('done');
    } catch {
      setState('error');
    }
  };

  if (state === 'done') {
    return (
      <span style={{ fontSize: 11, color: 'var(--color-success)' }}>
        {zh ? `已排入 ${queued} 個節點` : `${queued} nodes queued`}
      </span>
    );
  }
  if (state === 'error') {
    return <span style={{ fontSize: 11, color: 'var(--color-error)' }}>{zh ? '失敗，請重試' : 'Failed'}</span>;
  }

  return (
    <button
      className="btn-secondary"
      style={{ fontSize: 11, padding: '2px 8px', height: 24, display: 'flex', alignItems: 'center', gap: 4 }}
      onClick={handleClick}
      disabled={state === 'loading'}
    >
      <RefreshCw size={11} className={state === 'loading' ? 'animate-spin' : ''} />
      {zh ? '重新嵌入所有節點' : 'Re-embed All'}
    </button>
  );
}

function LinkDetectionButton({ wsId, zh }: { wsId: string; zh: boolean }) {
  const [state, setState] = useState<'idle' | 'loading' | 'done' | 'error'>('idle');
  const [checked, setChecked] = useState<number | null>(null);

  const handleClick = async () => {
    setState('loading');
    try {
      const res = await workspaces.detectLinks(wsId);
      setChecked(res.nodes_checked);
      setState('done');
    } catch {
      setState('error');
    }
  };

  if (state === 'done') {
    return (
      <span style={{ fontSize: 12, color: 'var(--color-success)', fontWeight: 600 }}>
        {zh ? `已啟動背景掃描 (${checked} 個節點)` : `Scan started (${checked} nodes)`}
      </span>
    );
  }
  if (state === 'error') {
    return <span style={{ fontSize: 12, color: 'var(--color-error)' }}>{zh ? '失敗' : 'Failed'}</span>;
  }

  return (
    <button
      className="btn-secondary"
      style={{ height: 36, display: 'flex', alignItems: 'center', gap: 8 }}
      onClick={handleClick}
      disabled={state === 'loading'}
    >
      {state === 'loading' ? <RefreshCw size={14} className="animate-spin" /> : <Link2 size={14} />}
      {zh ? '執行跨文件關聯掃描' : 'Scan Cross-file Links'}
    </button>
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
  const [models, setModels] = useState<any[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);

  const fetchModels = async (p: string) => {
    setLoadingModels(true);
    try {
      const res = await ai.listModels(p);
      setModels(res);
      if (res.length > 0 && !res.find(m => m.id === form.model)) {
        setForm(f => ({ ...f, model: res[0].id }));
      }
    } catch {
      setModels([]);
    } finally {
      setLoadingModels(false);
    }
  };

  useEffect(() => {
    fetchModels(form.provider);
  }, [form.provider]);

  const providers = [
    { value: 'openai', label: 'OpenAI' },
    { value: 'anthropic', label: 'Anthropic' },
    { value: 'gemini', label: 'Gemini' },
    { value: 'ollama', label: 'Ollama' },
  ];

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
        <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr 1fr", gap: 10 }}>
          <input className="mt-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder={t('ws_settings.members')} />
          <select className="mt-input" value={form.provider} onChange={(e) => setForm({ ...form, provider: e.target.value })}>
            {providers.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
          </select>
          <div style={{ display: 'flex', gap: 4 }}>
            <select className="mt-input" style={{ flex: 1 }} value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })}>
              {models.map(m => <option key={m.id} value={m.id}>{m.display_name}</option>)}
              {!models.length && <option value={form.model}>{form.model}</option>}
            </select>
            <button className="btn-secondary" style={{ padding: '0 8px' }} onClick={() => fetchModels(form.provider)} title="Refresh models" disabled={loadingModels}>
              <RefreshCw size={14} className={loadingModels ? "spin" : ""} />
            </button>
          </div>
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
      toast({ message: zh ? "API 金鑰已刪除" : "API key deleted", variant: "success" });
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
          <div key={k.id} style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 12, padding: 16, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 8 }}>
                {k.name} 
                <span className="tag" style={{ color: "var(--color-primary)", background: "var(--color-primary-subtle)" }}>{k.scopes.join(', ')}</span>
              </div>
              <div style={{ fontSize: 13, color: "var(--text-muted)", fontFamily: "monospace", marginTop: 4 }}>{k.prefix}********************</div>
              <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 6 }}>
                Created: {new Date(k.created_at).toLocaleDateString()} · Last used: {k.last_used_at ? new Date(k.last_used_at).toLocaleString() : "Never"}
              </div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn-secondary" onClick={() => handleRotate(k.id)} title="Rotate Token"><RefreshCw size={14} /></button>
              <button className="btn-secondary" onClick={() => handleRevoke(k.id)} title={zh ? "刪除" : "Delete"}><Trash2 size={14} /></button>
            </div>
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
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showCloneDialog, setShowCloneDialog] = useState(false);
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

          <SectionCard>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
                  {t('ws_settings.qa_archive_mode')}
                </div>
                <div style={{ fontSize: 12, color: "var(--text-muted)", maxWidth: 400 }}>{t('ws_settings.qa_archive_mode_desc')}</div>
              </div>
              <select className="mt-input" value={ws?.qa_archive_mode ?? "manual_review"} style={{ width: 180 }} onChange={async (e) => {
                try {
                  await workspaces.update(wsId, { qa_archive_mode: e.target.value as any });
                  await loadData();
                  toast({ message: t('common.save'), variant: "success" });
                } catch (err) {
                  toast({ message: err instanceof Error ? err.message : String(err), variant: "error" });
                }
              }}>
                <option value="manual_review">{t('ws_settings.manual_review')}</option>
                <option value="auto_active">{t('ws_settings.auto_active')}</option>
              </select>
            </div>
          </SectionCard>

          <SectionCard>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600 }}>{zh ? "文件擷取模型" : "Extraction Provider"}</div>
                <div style={{ fontSize: 12, color: "var(--text-muted)", maxWidth: 400 }}>
                  {zh ? "上傳文件時使用的 LLM。設為「自動」時沿用帳號預設。" : "LLM used when ingesting documents. 'Auto' falls back to your account default."}
                </div>
              </div>
              <select
                className="mt-input"
                value={ws?.extraction_provider ?? ""}
                style={{ width: 160 }}
                onChange={async (e) => {
                  try {
                    await workspaces.update(wsId, { extraction_provider: e.target.value || null } as any);
                    await loadData();
                    toast({ message: t('common.save'), variant: "success" });
                  } catch (err) {
                    toast({ message: err instanceof Error ? err.message : String(err), variant: "error" });
                  }
                }}
              >
                <option value="">{zh ? "自動 (帳號預設)" : "Auto (account default)"}</option>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="gemini">Gemini</option>
                <option value="ollama">Ollama</option>
              </select>
            </div>
          </SectionCard>

          <SectionCard>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ width: 40, height: 40, borderRadius: 10, background: "var(--color-primary-subtle)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Brain size={20} color="var(--color-primary)" />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 600 }}>{zh ? "向量模型 (已鎖定)" : "Embedding Model (Locked)"}</div>
                <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                  {ws?.embedding_model} ({ws?.embedding_dim}d)
                </div>
              </div>
              <div className="info-tooltip-wrapper">
                <Info size={14} style={{ color: "var(--text-muted)", cursor: "help" }} />
                <div className="info-tooltip" style={{ width: 240 }}>
                  {zh 
                    ? "為確保知識圖譜語義一致，工作區建立後向量模型即鎖定，不可更改。更換模型需建立新工作區並匯入資料。" 
                    : "To ensure semantic consistency, the embedding model is locked after workspace creation. To use a different model, create a new workspace and import your data."}
                </div>
              </div>
            </div>
          </SectionCard>

          <SectionCard>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ width: 40, height: 40, borderRadius: 10, background: "var(--color-primary-subtle)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Copy size={20} color="var(--color-primary)" />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 600 }}>{zh ? "複製此工作區" : "Clone this Workspace"}</div>
                <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                  {zh ? "建立完整副本，可選擇不同的向量模型進行重新索引。" : "Create a full copy, optionally with a new embedding model for re-indexing."}
                </div>
              </div>
              <button 
                className="btn-secondary" 
                style={{ height: 36 }}
                onClick={() => setShowCloneDialog(true)}
              >
                {zh ? "立即複製" : "Clone Now"}
              </button>
            </div>
          </SectionCard>

          {showCloneDialog && ws && (
            <CloneWorkspaceDialog 
              ws={ws} 
              onCancel={() => setShowCloneDialog(false)}
              onConfirm={async (data) => {
                setShowCloneDialog(false);
                try {
                  await workspaces.clone(wsId, data);
                  toast({ message: zh ? "複製任務已啟動" : "Clone job started", variant: "success" });
                } catch (err) {
                  toast({ message: err instanceof Error ? err.message : String(err), variant: "error" });
                }
              }}
            />
          )}

          <SectionCard>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ width: 40, height: 40, borderRadius: 10, background: "var(--color-primary-subtle)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Link2 size={20} color="var(--color-primary)" />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 600 }}>{zh ? "跨文件關聯偵測" : "Cross-file Link Detection"}</div>
                <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                  {zh ? "掃描現有節點內容，根據標題提及自動建立跨文件的關聯邊。" : "Scan existing nodes and automatically create cross-file associations based on title mentions."}
                </div>
              </div>
              <LinkDetectionButton wsId={wsId} zh={zh} />
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
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 12px", background: "var(--bg-elevated)", borderRadius: 8 }}>
                  <span>{t('ws_settings.no_embedding')}</span>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span className="tag" style={{ background: (healthReport.no_embedding ?? 0) > 0 ? "var(--color-warning-subtle)" : "var(--color-success-subtle)", color: (healthReport.no_embedding ?? 0) > 0 ? "var(--color-warning)" : "var(--color-success)" }}>{healthReport.no_embedding ?? 0}</span>
                    {(healthReport.no_embedding ?? 0) > 0 && ws?.owner_id === userId && (
                      <ReembedAllButton wsId={ws!.id} zh={zh} />
                    )}
                  </div>
                </div>
              </div>
            </SectionCard>
          )}

          {ws?.owner_id === userId && (
            <SectionCard>
              <h3 style={{ fontSize: 16, margin: "0 0 12px", color: "var(--color-error)", display: "flex", alignItems: "center", gap: 8 }}>
                <ShieldAlert size={18} /> {zh ? "危險區域" : "Danger Zone"}
              </h3>
              <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 16 }}>
                {zh ? "刪除工作區後所有資料將永久消失且無法復原。" : "Deleting the workspace will permanently erase all data. This cannot be undone."}
              </p>
              <div style={{ display: "flex", justifyContent: "flex-start" }}>
                <button 
                  className="btn-secondary" 
                  style={{ color: "var(--color-error)", borderColor: "var(--color-error-subtle)" }}
                  onClick={() => setShowDeleteDialog(true)}
                >
                  {zh ? "刪除工作區" : "Delete Workspace"}
                </button>
              </div>
            </SectionCard>
          )}

          {showDeleteDialog && ws && (
            <DeleteWorkspaceDialog 
              ws={ws} 
              onCancel={() => setShowDeleteDialog(false)} 
              onConfirm={async () => {
                setShowDeleteDialog(false);
                try {
                  await workspaces.delete(wsId);
                  toast({ message: zh ? `工作區「${ws.name_zh || ws.name_en}」已刪除` : `Workspace "${ws.name_zh || ws.name_en}" deleted`, variant: "success" });
                  // Trigger a global refresh or navigation - App.tsx should handle the state update
                  window.dispatchEvent(new CustomEvent('workspace-deleted', { detail: { wsId } }));
                } catch (e) {
                  toast({ message: String(e), variant: "error" });
                }
              }} 
            />
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
