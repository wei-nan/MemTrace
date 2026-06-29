import { useEffect, useMemo, useState } from "react";
import { Brain, Clock, Copy, ExternalLink, Info, Key, Link2, RefreshCw, Search, ShieldAlert, ShieldCheck, Trash2, UserPlus, Users, AlertTriangle, Sparkles, Cpu } from "lucide-react";
import { ai, workspaces, review, type Invite, type JoinRequest, type Member, type Workspace, type WorkspaceAssociation, type PersonalApiKey, type ModelBinding, type ReviewPolicy, type PolicyMember } from "./api";
import { useTranslation } from "react-i18next";
import { useModal } from "./components/ModalContext";
import { ModalOverlay } from "./components/Modal";
import KbExportPanel from "./components/KbExportPanel";
import ConnectorSettings from "./components/ConnectorSettings";
import { Button, Input, Card } from "./components/ui";
import { Plus, Check, Pause, Play, X } from "lucide-react";


function DeleteWorkspaceDialog({ ws, onConfirm, onCancel }: { ws: Workspace, onConfirm: () => void, onCancel: () => void }) {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const [typedName, setTypedName] = useState("");
  const expectedName = ws.name;
  const isValid = typedName === expectedName;

  return (
    <ModalOverlay onClose={onCancel}>
      <div style={{ padding: 24 }}>
        <div style={{ display: "flex", gap: 14, marginBottom: 20 }}>
          <div style={{ flexShrink: 0, width: 40, height: 40, borderRadius: 10, background: "var(--color-error-subtle)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <AlertTriangle size={20} color="var(--color-error)" />
          </div>
          <div style={{ flex: 1, paddingTop: 8 }}>
            <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>{zh ? "確認刪除工作區" : "Delete Workspace"}</h3>
          </div>
        </div>
        <p style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: 16 }}>
          {zh ? "此操作不可復原。刪除後所有節點、邊、成員記錄將永久消失。" : "This action cannot be undone. All nodes, edges, and member records will be permanently deleted."}
        </p>
        <Input
          label={zh ? `請輸入工作區名稱「${expectedName}」以確認刪除：` : `Please type the workspace name "${expectedName}" to confirm:`}
          value={typedName}
          onChange={e => setTypedName(e.target.value)}
          placeholder={expectedName}
          autoFocus
        />
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 24 }}>
          <Button variant="secondary" onClick={onCancel}>{zh ? "取消" : "Cancel"}</Button>
          <Button 
            variant="danger"
            disabled={!isValid}
            onClick={onConfirm}
          >
            {zh ? "確認刪除" : "Confirm Delete"}
          </Button>
        </div>
      </div>
    </ModalOverlay>
  );
}

function CloneWorkspaceDialog({ ws, onConfirm, onCancel }: { ws: Workspace, onConfirm: (data: { name?: string; new_embedding_model?: string; visibility?: string }) => void, onCancel: () => void }) {
  const { t, i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const [name, setName] = useState(`${ws.name} (Clone)`);
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
            <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>{zh ? "複製工作區 (Clone & Rebuild)" : "Clone Workspace"}</h3>
          </div>
        </div>
        
        <div style={{ display: "flex", flexDirection: "column", gap: 14, marginBottom: 24 }}>
          <Input 
            label={zh ? "工作區名稱" : "Workspace Name"} 
            value={name} 
            onChange={e => setName(e.target.value)} 
          />
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
          <Button variant="secondary" onClick={onCancel}>{zh ? "取消" : "Cancel"}</Button>
          <Button
            variant="primary"
            onClick={() => onConfirm({ name, new_embedding_model: selectedModel, visibility })}
          >
            {zh ? "開始複製" : "Start Clone"}
          </Button>
        </div>
      </div>
    </ModalOverlay>
  );
}

function SectionCard({ children }: { children: React.ReactNode }) {
  return (
    <Card variant="surface" padding="md" style={{ border: "1px solid var(--border-default)", overflow: "visible" }}>
      {children}
    </Card>
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
    <Button
      variant="secondary"
      size="sm"
      onClick={handleClick}
      loading={state === 'loading'}
      leftIcon={<RefreshCw size={11} />}
    >
      {zh ? '重新嵌入所有節點' : 'Re-embed All'}
    </Button>
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
    <Button
      variant="secondary"
      onClick={handleClick}
      loading={state === 'loading'}
      leftIcon={<Link2 size={14} />}
    >
      {zh ? '執行跨文件關聯掃描' : 'Scan Cross-file Links'}
    </Button>
  );
}

function AIReviewerSettings({
  wsId,
  ws,
  isOwner,
  zh,
  loadData,
}: {
  wsId: string;
  ws: Workspace | null;
  isOwner: boolean;
  zh: boolean;
  loadData: () => void;
}) {
  const { t } = useTranslation();
  const { toast, confirm } = useModal();

  const [policy, setPolicy] = useState<ReviewPolicy | null>(null);
  const [bindings, setBindings] = useState<ModelBinding[]>([]);
  const [policyMembers, setPolicyMembers] = useState<PolicyMember[]>([]);
  const [userKeys, setUserKeys] = useState<any[]>([]);

  const [policyMode, setPolicyMode] = useState<string>("manual_only");
  const [inheritSystemDefault, setInheritSystemDefault] = useState<boolean>(true);
  const [minimumSuccess, setMinimumSuccess] = useState<number>(1);
  const [savingPolicy, setSavingPolicy] = useState<boolean>(false);

  const [offeringKeyId, setOfferingKeyId] = useState<string>("");
  const [offeringUsages, setOfferingUsages] = useState<string[]>(["review"]);
  const [offeringPriority, setOfferingPriority] = useState<number>(0);
  const [offering, setOffering] = useState<boolean>(false);

  const [loading, setLoading] = useState<boolean>(true);
  const [maintenanceLoading, setMaintenanceLoading] = useState<string | null>(null);

  const loadGovernanceData = async () => {
    setLoading(true);
    try {
      const [p, bList, mList, keys] = await Promise.all([
        review.getPolicy(wsId),
        review.listBindings(wsId),
        review.getPolicyMembers(wsId),
        ai.listKeys(),
      ]);
      setPolicy(p);
      setPolicyMode(p.mode);
      setInheritSystemDefault(p.inherit_system_default);
      setMinimumSuccess(p.minimum_success);

      setBindings(bList);
      setPolicyMembers(mList);
      setUserKeys(keys);

      if (keys.length > 0) {
        setOfferingKeyId(keys[0].id);
      }
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGovernanceData();
  }, [wsId]);

  const savePolicy = async () => {
    setSavingPolicy(true);
    try {
      const p = await review.updatePolicy(wsId, {
        mode: policyMode,
        inherit_system_default: inheritSystemDefault,
        minimum_success: minimumSuccess,
      });
      setPolicy(p);
      toast({ message: zh ? "審核政策已更新" : "Review policy updated", variant: "success" });
      await loadGovernanceData();
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    } finally {
      setSavingPolicy(false);
    }
  };

  const offerKey = async () => {
    if (!offeringKeyId) {
      toast({ message: zh ? "請選擇要綁定的 API 金鑰" : "Please select an API key to bind", variant: "warning" });
      return;
    }
    setOffering(true);
    try {
      await review.createBinding(wsId, {
        model_account_id: offeringKeyId,
        allowed_usages: offeringUsages,
        priority: offeringPriority,
      });
      toast({ message: zh ? "金鑰綁定提案已提交" : "API key binding offered successfully", variant: "success" });
      await loadGovernanceData();
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    } finally {
      setOffering(false);
    }
  };

  const approveBinding = async (bindingId: string) => {
    try {
      await review.updateBinding(wsId, bindingId, {});
      toast({ message: zh ? "綁定已核准並啟用" : "Binding approved and activated", variant: "success" });
      await loadGovernanceData();
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    }
  };

  const toggleBindingStatus = async (bindingId: string, currentStatus: string) => {
    const nextStatus = currentStatus === "active" ? "paused" : "active";
    try {
      await review.updateBinding(wsId, bindingId, { status: nextStatus });
      toast({ message: zh ? "綁定狀態已更新" : "Binding status updated", variant: "success" });
      await loadGovernanceData();
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    }
  };

  const revokeBinding = async (bindingId: string) => {
    const ok = await confirm({
      title: zh ? "確認撤銷此模型授權？" : "Revoke model binding?",
      message: zh
        ? "撤銷後，此金鑰將無法再用於此工作區的 AI 審核，正在進行的審核也將被捨棄。"
        : "Once revoked, this key will no longer be used for AI reviews, and active attempts will be discarded.",
      confirmLabel: zh ? "確認撤銷" : "Revoke",
      variant: "danger",
    });
    if (!ok) return;

    try {
      await review.deleteBinding(wsId, bindingId);
      toast({ message: zh ? "模型綁定已撤銷" : "Model binding revoked", variant: "success" });
      await loadGovernanceData();
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    }
  };

  const addPolicyMember = async (bindingId: string) => {
    if (policyMembers.some(m => m.binding_id === bindingId)) {
      toast({ message: zh ? "該模型已是政策成員" : "Model is already a member", variant: "warning" });
      return;
    }
    const updatedMembers = [
      ...policyMembers.map(m => ({ binding_id: m.binding_id, priority: m.priority, is_required: m.is_required })),
      { binding_id: bindingId, priority: 0, is_required: false }
    ];
    try {
      await review.updatePolicyMembers(wsId, updatedMembers);
      toast({ message: zh ? "已加入審核成員" : "Added policy member", variant: "success" });
      await loadGovernanceData();
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    }
  };

  const removePolicyMember = async (bindingId: string) => {
    const updatedMembers = policyMembers
      .filter(m => m.binding_id !== bindingId)
      .map(m => ({ binding_id: m.binding_id, priority: m.priority, is_required: m.is_required }));
    try {
      await review.updatePolicyMembers(wsId, updatedMembers);
      toast({ message: zh ? "已移除審核成員" : "Removed policy member", variant: "success" });
      await loadGovernanceData();
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    }
  };

  const updateMemberSetting = async (bindingId: string, priority: number, isRequired: boolean) => {
    const updatedMembers = policyMembers.map(m => {
      if (m.binding_id === bindingId) {
        return { binding_id: m.binding_id, priority, is_required: isRequired };
      }
      return { binding_id: m.binding_id, priority: m.priority, is_required: m.is_required };
    });
    try {
      await review.updatePolicyMembers(wsId, updatedMembers);
      toast({ message: zh ? "審核成員設定已儲存" : "Member setting updated", variant: "success" });
      await loadGovernanceData();
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    }
  };

  const runSummary = async () => {
    setMaintenanceLoading("summary");
    try {
      const res = await workspaces.summarizeCluster(wsId, []);
      if (res?.summary_node_id) {
        toast({ message: zh ? `已產生摘要節點（ID: ${res.summary_node_id}）` : `Summary node created (ID: ${res.summary_node_id})`, variant: "success" });
      } else {
        toast({ message: zh ? "找不到可整合的群組（節點數需 ≥ 3 且共用標籤）" : "No clusters found (need ≥ 3 nodes sharing a tag)", variant: "warning" });
      }
    } catch (e) { toast({ message: String(e), variant: "error" }); }
    finally { setMaintenanceLoading(null); }
  };

  const runEdgeSuggestion = async () => {
    setMaintenanceLoading("edges");
    try {
      const res = await workspaces.suggestEdges(wsId, "");
      const count: number = (res as any)?.proposed ?? 0;
      toast({
        message: count > 0
          ? (zh ? `已找到 ${count} 個潛在關聯，送入審查佇列` : `${count} potential edges queued for review`)
          : (zh ? "未發現新的潛在關聯（嵌入向量覆蓋率不足或相似度未達門檻）" : "No new potential edges found (low embedding coverage or below threshold)"),
        variant: count > 0 ? "success" : "info",
      });
    } catch (e) { toast({ message: String(e), variant: "error" }); }
    finally { setMaintenanceLoading(null); }
  };

  const activeMembersCount = policyMembers.filter(m => m.binding_status === "active").length;
  const isDegraded = policyMode !== "manual_only" && activeMembersCount === 0;
  const effectiveMode = isDegraded ? "manual_only" : policyMode;

  if (loading && bindings.length === 0) {
    return <div style={{ display: "flex", justifyContent: "center", padding: 40 }}><RefreshCw size={24} className="animate-spin" /></div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

      {/* ── Consult 設定 ─────────────────────────────────────────────── */}
      <SectionCard>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 14, display: "flex", alignItems: "center", gap: 8 }}>
          <Cpu size={16} color="var(--color-primary)" />
          {zh ? "Consult AI 設定" : "Consult AI Settings"}
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600, fontSize: 13 }}>{t('ws_settings.consult_provider')}</div>
            <div style={{ fontSize: 12, color: "var(--text-muted)", maxWidth: 460 }}>
              {t('ws_settings.consult_provider_desc')}
            </div>
          </div>
          <select
            className="mt-input"
            value={ws?.consult_provider ?? ""}
            disabled={!isOwner}
            style={{ width: 160 }}
            onChange={async (e) => {
              try {
                await workspaces.update(wsId, { consult_provider: e.target.value || null });
                loadData();
                toast({ message: t('common.save'), variant: "success" });
              } catch (err) {
                toast({ message: err instanceof Error ? err.message : String(err), variant: "error" });
              }
            }}
          >
            <option value="">{zh ? "自動 (系統預設)" : "Auto (system default)"}</option>
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
            <option value="gemini">Gemini</option>
            <option value="ollama">Ollama</option>
          </select>
        </div>
      </SectionCard>

      {/* ── 審核政策設定 (Review Policy Settings) ───────────────────────── */}
      <SectionCard>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 14, display: "flex", alignItems: "center", gap: 8 }}>
          <Brain size={16} color="var(--color-primary)" />
          {zh ? `工作區審核政策 (v${policy?.policy_version || 1})` : `Workspace Review Policy (v${policy?.policy_version || 1})`}
        </div>

        {isDegraded ? (
          <div style={{ display: "flex", gap: 10, padding: "12px 14px", background: "var(--color-error-subtle)", color: "var(--color-error)", borderRadius: 8, fontSize: 13, marginBottom: 16, border: "1px solid var(--color-error)" }}>
            <ShieldAlert size={18} style={{ flexShrink: 0, marginTop: 1 }} />
            <div>
              <div style={{ fontWeight: 600 }}>{zh ? "政策已安全降級為：僅限人工審核" : "Policy Degraded to: Manual Only"}</div>
              <div style={{ opacity: 0.85, marginTop: 4, fontSize: 12 }}>
                {zh ? "原因：當前審核政策中沒有任何「啟用中 (active)」的模型綁定。為保障知識圖譜品質，已自動切回人工審核。" : "Reason: No active model bindings are configured in this review policy. Automatically fallback to manual review to maintain data quality."}
              </div>
            </div>
          </div>
        ) : (
          <div style={{ display: "flex", gap: 10, padding: "10px 12px", background: "var(--color-success-subtle)", color: "var(--color-success)", borderRadius: 8, fontSize: 13, marginBottom: 16 }}>
            <ShieldCheck size={18} style={{ flexShrink: 0 }} />
            <div>
              {zh ? `生效審核模式：${effectiveMode}` : `Effective review mode: ${effectiveMode}`}
            </div>
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
            <input
              type="checkbox"
              checked={inheritSystemDefault}
              disabled={!isOwner}
              onChange={(e) => setInheritSystemDefault(e.target.checked)}
            />
            {zh ? "繼承系統預設審核設定" : "Inherit system default review settings"}
          </label>

          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 4 }}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600 }}>{zh ? "審核執行模式" : "Review Execution Mode"}</div>
              <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
                {zh ? "決定如何調度 AI 審核員及是否進行自動裁決。" : "Determines how to coordinate AI reviewers and whether to perform automatic rulings."}
              </div>
            </div>
            <select
              className="mt-input"
              value={policyMode}
              disabled={!isOwner || inheritSystemDefault}
              style={{ width: 220 }}
              onChange={(e) => setPolicyMode(e.target.value)}
            >
              <option value="manual_only">{zh ? "僅限人工審核 (manual_only)" : "Manual Only (manual_only)"}</option>
              <option value="fallback_advisory">{zh ? "後備建議模式 (fallback_advisory)" : "Fallback Advisory (fallback_advisory)"}</option>
              <option value="panel_advisory">{zh ? "專家小組建議 (panel_advisory)" : "Panel Advisory (panel_advisory)"}</option>
              <option value="consensus_automatic" disabled>{zh ? "自動共識裁決 (暫未開放)" : "Consensus Automatic (Disabled)"}</option>
            </select>
          </div>

          {(policyMode !== "manual_only") && (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderTop: "1px solid var(--border-subtle)", paddingTop: 12 }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600 }}>{zh ? "最少成功模型數" : "Minimum Success Count"}</div>
                <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
                  {zh ? "至少需要多少個模型成功返回建議才算審核成功。" : "Minimum number of models that must return suggestions successfully."}
                </div>
              </div>
              <Input
                type="number"
                min="1"
                max="10"
                style={{ width: 80 }}
                value={minimumSuccess}
                disabled={!isOwner || inheritSystemDefault}
                onChange={(e) => setMinimumSuccess(parseInt(e.target.value) || 1)}
              />
            </div>
          )}

          {isOwner && (
            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 8 }}>
              <Button variant="primary" loading={savingPolicy} onClick={savePolicy}>
                {zh ? "儲存政策變更" : "Save Policy"}
              </Button>
            </div>
          )}
        </div>
      </SectionCard>

      {/* ── 政策成員設定 (Policy Members) ─────────────────────────────────── */}
      {policyMode !== "manual_only" && (
        <SectionCard>
          <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 14, display: "flex", alignItems: "center", gap: 8 }}>
            <Users size={16} color="var(--color-primary)" />
            {zh ? "本政策參與的模型審核員" : "Policy Reviewer Members"}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {policyMembers.map((member) => (
              <div key={member.binding_id} style={{ background: "var(--bg-app)", border: "1px solid var(--border-subtle)", borderRadius: 8, padding: "10px 14px", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13, display: "flex", alignItems: "center", gap: 6 }}>
                    {member.provider} / {member.model}
                    <span style={{ fontSize: 11, padding: "1px 5px", borderRadius: 4, background: member.binding_status === "active" ? "var(--color-success-subtle)" : "var(--bg-elevated)", color: member.binding_status === "active" ? "var(--color-success)" : "var(--text-muted)", border: "1px solid var(--border-default)" }}>
                      {member.binding_status}
                    </span>
                  </div>
                  <div style={{ color: "var(--text-muted)", fontSize: 12, marginTop: 4 }}>
                    {zh ? `提供者：${member.offered_by_name} (${member.key_hint})` : `Offered by: ${member.offered_by_name} (${member.key_hint})`}
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontSize: 12, color: "var(--text-muted)" }}>{zh ? "優先級:" : "Priority:"}</span>
                    <select
                      className="mt-input"
                      style={{ padding: "2px 6px", height: 26, fontSize: 12, width: 60 }}
                      value={member.priority}
                      disabled={!isOwner}
                      onChange={(e) => updateMemberSetting(member.binding_id, parseInt(e.target.value) || 0, member.is_required)}
                    >
                      {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(p => (
                        <option key={p} value={p}>{p}</option>
                      ))}
                    </select>
                  </div>

                  <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, cursor: "pointer" }}>
                    <input
                      type="checkbox"
                      checked={member.is_required}
                      disabled={!isOwner}
                      onChange={(e) => updateMemberSetting(member.binding_id, member.priority, e.target.checked)}
                    />
                    {zh ? "必要" : "Required"}
                  </label>

                  {isOwner && (
                    <button
                      onClick={() => removePolicyMember(member.binding_id)}
                      style={{ background: "none", border: "none", color: "var(--color-error)", cursor: "pointer", padding: 4 }}
                      title={zh ? "移除成員" : "Remove member"}
                    >
                      <X size={16} />
                    </button>
                  )}
                </div>
              </div>
            ))}

            {policyMembers.length === 0 && (
              <div style={{ color: "var(--text-muted)", fontSize: 13, textAlign: "center", padding: "12px 0" }}>
                {zh ? "尚未設定任何參與審核的模型。請從下方可用模型中加入。" : "No reviewer models added to this policy. Add active models from the list below."}
              </div>
            )}

            {isOwner && bindings.filter(b => b.status === "active" && !policyMembers.some(m => m.binding_id === b.id)).length > 0 && (
              <div style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 8, borderTop: "1px solid var(--border-subtle)", paddingTop: 12 }}>
                <span style={{ fontSize: 13, color: "var(--text-muted)" }}>{zh ? "新增審核員模型：" : "Add Reviewer Model:"}</span>
                <select
                  className="mt-input"
                  style={{ flex: 1 }}
                  defaultValue=""
                  onChange={(e) => {
                    if (e.target.value) {
                      addPolicyMember(e.target.value);
                      e.target.value = "";
                    }
                  }}
                >
                  <option value="" disabled>{zh ? "選擇一個啟用中的綁定模型..." : "Select an active model binding..."}</option>
                  {bindings
                    .filter(b => b.status === "active" && !policyMembers.some(m => m.binding_id === b.id))
                    .map(b => (
                      <option key={b.id} value={b.id}>{b.provider} / {b.model} ({b.key_hint}) - {b.offered_by_name}</option>
                    ))
                  }
                </select>
              </div>
            )}
          </div>
        </SectionCard>
      )}

      {/* ── 模型綁定與憑證管理 (Model Bindings) ─────────────────────────── */}
      <SectionCard>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 14, display: "flex", alignItems: "center", gap: 8 }}>
          <Key size={16} color="var(--color-primary)" />
          {zh ? "工作區模型綁定管理" : "Workspace Model Bindings"}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 20 }}>
          {bindings.map((b) => {
            const hasConsentPending = b.consent_status === "pending";
            const hasApprovalPending = b.approval_status === "pending";
            
            let statusColor = "var(--text-muted)";
            let statusBg = "var(--bg-elevated)";
            if (b.status === "active") {
              statusColor = "var(--color-success)";
              statusBg = "var(--color-success-subtle)";
            } else if (b.status === "paused") {
              statusColor = "var(--color-warning)";
              statusBg = "var(--color-warning-subtle)";
            } else if (b.status === "offered") {
              statusColor = "var(--color-info)";
              statusBg = "var(--color-info-subtle)";
            } else if (b.status === "revoked") {
              statusColor = "var(--color-error)";
              statusBg = "var(--color-error-subtle)";
            }

            return (
              <div key={b.id} style={{ border: "1px solid var(--border-subtle)", borderRadius: 8, padding: 14, display: "flex", flexDirection: "column", gap: 10, background: "var(--bg-app)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 14, display: "flex", alignItems: "center", gap: 8 }}>
                      {b.provider} / {b.model}
                      <span style={{ fontSize: 11, padding: "2px 6px", borderRadius: 4, color: statusColor, background: statusBg, fontWeight: 600 }}>
                        {b.status.toUpperCase()}
                      </span>
                    </div>
                    <div style={{ color: "var(--text-muted)", fontSize: 12, marginTop: 4, display: "flex", flexWrap: "wrap", gap: "8px 12px" }}>
                      <span>{zh ? `金鑰提示：${b.key_hint}` : `Key Hint: ${b.key_hint}`}</span>
                      <span>•</span>
                      <span>{zh ? `提供者：${b.offered_by_name}` : `Offered by: ${b.offered_by_name}`}</span>
                      <span>•</span>
                      <span>{zh ? `權限範圍：${b.allowed_usages.join(", ")}` : `Usages: ${b.allowed_usages.join(", ")}`}</span>
                    </div>
                  </div>

                  <div style={{ display: "flex", gap: 8 }}>
                    {(b.status === "active" || b.status === "paused") && isOwner && (
                      <Button
                        variant="secondary"
                        onClick={() => toggleBindingStatus(b.id, b.status)}
                        leftIcon={b.status === "active" ? <Pause size={14} /> : <Play size={14} />}
                      >
                        {b.status === "active" ? (zh ? "暫停" : "Pause") : (zh ? "啟用" : "Resume")}
                      </Button>
                    )}

                    {b.status !== "revoked" && (
                      <Button
                        variant="secondary"
                        onClick={() => revokeBinding(b.id)}
                        leftIcon={<Trash2 size={14} />}
                      />
                    )}
                  </div>
                </div>

                {(hasConsentPending || hasApprovalPending) && (
                  <div style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-default)", borderRadius: 6, padding: "8px 12px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
                    <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                      {hasConsentPending && <div>⚠️ {zh ? "等待金鑰擁有者同意授權" : "Waiting for key owner consent"}</div>}
                      {hasApprovalPending && <div>⚠️ {zh ? "等待工作區管理員核准啟用" : "Waiting for workspace owner approval"}</div>}
                    </div>

                    {((hasApprovalPending && isOwner) || hasConsentPending) && (
                      <Button variant="primary" size="sm" onClick={() => approveBinding(b.id)} leftIcon={<Check size={12} />}>
                        {zh ? "同意並核准" : "Approve & Consent"}
                      </Button>
                    )}
                  </div>
                )}
              </div>
            );
          })}

          {bindings.length === 0 && (
            <div style={{ color: "var(--text-muted)", fontSize: 13, textAlign: "center", padding: "16px 0" }}>
              {zh ? "目前沒有任何模型綁定。" : "No model bindings configured yet."}
            </div>
          )}
        </div>

        <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: 16 }}>
          <h4 style={{ margin: "0 0 12px 0", fontSize: 13, fontWeight: 600 }}>
            {zh ? "綁定我的 API 金鑰至此工作區" : "Bind My API Key to Workspace"}
          </h4>

          {userKeys.length === 0 ? (
            <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
              {zh ? "您尚未設定任何個人 API 金鑰。請先前往「API 金鑰」設定頁新增。" : "You have not set up any personal API keys. Go to 'API Keys' tab to add keys first."}
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 120px", gap: 10 }}>
                <div>
                  <label style={{ fontSize: 11, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>
                    {zh ? "選擇個人金鑰" : "Select Personal Key"}
                  </label>
                  <select
                    className="mt-input"
                    style={{ width: "100%" }}
                    value={offeringKeyId}
                    onChange={(e) => setOfferingKeyId(e.target.value)}
                  >
                    {userKeys.map(k => (
                      <option key={k.id} value={k.id}>[{k.provider}] {k.default_chat_model || "(No model)"} - {k.key_hint}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: 11, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>
                    {zh ? "綁定優先級" : "Priority"}
                  </label>
                  <Input
                    type="number"
                    value={offeringPriority}
                    onChange={(e) => setOfferingPriority(parseInt(e.target.value) || 0)}
                  />
                </div>
              </div>

              <div>
                <label style={{ fontSize: 11, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>
                  {zh ? "允許使用範圍" : "Allowed Usages"}
                </label>
                <div style={{ display: "flex", gap: 14 }}>
                  {["review", "chat", "extraction"].map(scope => (
                    <label key={scope} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12 }}>
                      <input
                        type="checkbox"
                        checked={offeringUsages.includes(scope)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setOfferingUsages([...offeringUsages, scope]);
                          } else {
                            setOfferingUsages(offeringUsages.filter(u => u !== scope));
                          }
                        }}
                      />
                      {scope}
                    </label>
                  ))}
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 4 }}>
                <Button variant="primary" loading={offering} onClick={offerKey} leftIcon={<Plus size={14} />}>
                  {zh ? "提交綁定申請" : "Submit Binding Request"}
                </Button>
              </div>
            </div>
          )}
        </div>
      </SectionCard>

      {/* ── 智慧維護 ──────────────────────────────────────────────────── */}
      <SectionCard>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 14, display: "flex", alignItems: "center", gap: 8 }}>
          <Sparkles size={16} color="var(--color-primary)" />
          {zh ? "智慧維護" : "Smart Maintenance"}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, fontWeight: 600 }}>{zh ? "智慧階層綜整" : "Intelligent Hierarchical Synthesis"}</div>
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                {zh ? "自動掃描孤立或零散節點並產生摘要節點，優化知識結構。" : "Automatically scan isolated nodes and generate summaries to optimize graph structure."}
              </div>
            </div>
            <Button variant="secondary" loading={maintenanceLoading === "summary"} onClick={runSummary}>
              {zh ? "執行掃描" : "Run Scan"}
            </Button>
          </div>

          <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: 12, display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, fontWeight: 600 }}>{zh ? "潛在關聯預測" : "Predict Potential Edges"}</div>
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                {zh ? "基於語義相似度主動發現節點間的關聯，建議送入審查佇列。" : "Discover potential edges between nodes by semantic similarity and queue for review."}
              </div>
            </div>
            <Button variant="secondary" loading={maintenanceLoading === "edges"} onClick={runEdgeSuggestion}>
              {zh ? "執行預測" : "Run Prediction"}
            </Button>
          </div>
        </div>
      </SectionCard>
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
          <div style={{ display: "flex", gap: 12 }}>
            <p>{t('ws_settings.new_key_msg')}</p>
            <div style={{ display: "flex", gap: 8 }}>
              <Input readOnly value={res.key} style={{ flex: 1, fontFamily: "monospace" }} />
              <Button variant="secondary" onClick={() => {
                navigator.clipboard.writeText(res.key);
                toast({ message: t('common.copied'), variant: "success" });
              }} leftIcon={<Copy size={16} />} />
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
              <Input readOnly value={res.key} style={{ flex: 1, fontFamily: "monospace" }} />
              <Button variant="secondary" onClick={() => {
                navigator.clipboard.writeText(res.key);
                toast({ message: t('common.copied'), variant: "success" });
              }} leftIcon={<Copy size={16} />} />
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

  const mcpUrl  = `${window.location.origin}/mcp`;
  const sseUrl  = `${window.location.origin}/sse`;

  const claudeSnippet = JSON.stringify({
    mcpServers: {
      memtrace: {
        type: "streamable-http",
        url: mcpUrl,
        headers: { Authorization: "Bearer YOUR_API_KEY" },
      }
    }
  }, null, 2);

  const sseSnippet = JSON.stringify({
    mcpServers: {
      memtrace: {
        type: "sse",
        url: sseUrl,
        headers: { Authorization: "Bearer YOUR_API_KEY" },
      }
    }
  }, null, 2);

  const copyText = (text: string) => {
    navigator.clipboard.writeText(text);
    toast({ message: zh ? "已複製" : "Copied", variant: "success" });
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

      {/* ── MCP 接入指引 ────────────────────────────────────────────── */}
      <SectionCard>
        <h3 style={{ fontSize: 14, fontWeight: 600, margin: "0 0 4px", display: "flex", alignItems: "center", gap: 8 }}>
          <Link2 size={18} style={{ color: "var(--color-primary)" }} />
          {zh ? "MCP 接入指引" : "MCP Connection Guide"}
        </h3>
        <p style={{ fontSize: 13, color: "var(--text-muted)", margin: "0 0 18px" }}>
          {zh
            ? "將以下設定貼入 Claude Code（或其他 MCP 客戶端）的 settings.json，再替換 API 金鑰後即可連線。"
            : "Paste the config below into your MCP client's settings.json, then replace the API key."}
        </p>

        {/* Streamable HTTP (recommended) */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)" }}>
              {zh ? "Streamable HTTP（推薦）" : "Streamable HTTP (Recommended)"}
            </span>
            <span style={{ fontSize: 11, padding: "1px 7px", borderRadius: 20, background: "var(--color-primary-subtle)", color: "var(--color-primary)", fontWeight: 600 }}>
              Claude Code / Cursor / Windsurf
            </span>
          </div>
          <div style={{ position: "relative" }}>
            <pre style={{
              margin: 0, padding: "12px 14px", borderRadius: 8, fontSize: 12,
              background: "var(--bg-app)", border: "1px solid var(--border-default)",
              overflowX: "auto", color: "var(--text-primary)", lineHeight: 1.6,
            }}>
              {claudeSnippet}
            </pre>
            <button
              onClick={() => copyText(claudeSnippet)}
              style={{
                position: "absolute", top: 8, right: 8,
                background: "var(--bg-surface)", border: "1px solid var(--border-default)",
                borderRadius: 6, cursor: "pointer", padding: "4px 8px",
                fontSize: 11, color: "var(--text-muted)", display: "flex", alignItems: "center", gap: 4,
              }}
            >
              <Copy size={12} /> {zh ? "複製" : "Copy"}
            </button>
          </div>
        </div>

        {/* SSE fallback */}
        <details style={{ marginBottom: 16 }}>
          <summary style={{ fontSize: 12, color: "var(--text-muted)", cursor: "pointer", userSelect: "none" }}>
            {zh ? "SSE 設定（舊版客戶端）" : "SSE config (legacy clients)"}
          </summary>
          <div style={{ position: "relative", marginTop: 8 }}>
            <pre style={{
              margin: 0, padding: "12px 14px", borderRadius: 8, fontSize: 12,
              background: "var(--bg-app)", border: "1px solid var(--border-default)",
              overflowX: "auto", color: "var(--text-primary)", lineHeight: 1.6,
            }}>
              {sseSnippet}
            </pre>
            <button
              onClick={() => copyText(sseSnippet)}
              style={{
                position: "absolute", top: 8, right: 8,
                background: "var(--bg-surface)", border: "1px solid var(--border-default)",
                borderRadius: 6, cursor: "pointer", padding: "4px 8px",
                fontSize: 11, color: "var(--text-muted)", display: "flex", alignItems: "center", gap: 4,
              }}
            >
              <Copy size={12} /> {zh ? "複製" : "Copy"}
            </button>
          </div>
        </details>

        {/* Scope table */}
        <div style={{ background: "var(--bg-app)", borderRadius: 8, border: "1px solid var(--border-subtle)", overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ background: "var(--bg-surface)" }}>
                <th style={{ textAlign: "left", padding: "8px 12px", fontWeight: 700, color: "var(--text-muted)", borderBottom: "1px solid var(--border-subtle)" }}>{zh ? "權限" : "Scope"}</th>
                <th style={{ textAlign: "left", padding: "8px 12px", fontWeight: 700, color: "var(--text-muted)", borderBottom: "1px solid var(--border-subtle)" }}>{zh ? "說明" : "Description"}</th>
              </tr>
            </thead>
            <tbody>
              {[
                { scope: "kb:read",    desc: zh ? "唯讀：搜尋、讀取節點" : "Read-only: search and retrieve nodes" },
                { scope: "kb:propose", desc: zh ? "可提案：新增節點須人工審核" : "Propose: node additions go to review queue" },
                { scope: "kb:write",   desc: zh ? "完整寫入：直接新增/修改節點" : "Full write: create and edit nodes directly" },
              ].map(({ scope, desc }, i) => (
                <tr key={scope} style={{ borderBottom: i < 2 ? "1px solid var(--border-subtle)" : "none" }}>
                  <td style={{ padding: "8px 12px", fontFamily: "monospace", color: "var(--color-primary)", fontWeight: 600 }}>{scope}</td>
                  <td style={{ padding: "8px 12px", color: "var(--text-secondary)" }}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p style={{ fontSize: 12, color: "var(--text-muted)", margin: "12px 0 0", display: "flex", alignItems: "center", gap: 6 }}>
          <Info size={13} />
          {zh
            ? "在下方「服務 Token」區塊產生金鑰，再將 YOUR_API_KEY 替換成實際金鑰值。"
            : 'Generate a key in the "Service Tokens" section below, then replace YOUR_API_KEY.'}
        </p>
      </SectionCard>

      <SectionCard>
        <h3 style={{ fontSize: 14, fontWeight: 600, margin: "0 0 16px", display: "flex", alignItems: "center", gap: 8 }}><Key size={18} /> {t('ws_settings.service_tokens')}</h3>
        <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 16 }}>
          {zh ? "服務 Token 用於自動化任務，如 API 攝入或外部整合。" : "Service tokens are used for automated tasks like API ingestion or external integrations."}
        </p>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <Input placeholder={zh ? "名稱 (例: Ingestion Bot)" : "Key name (e.g. Ingestion Bot)"} value={newKeyName} onChange={e => setNewKeyName(e.target.value)} style={{ flex: 2, minWidth: 200 }} />
          <select className="mt-input" value={newKeyScope} onChange={e => setNewKeyScope(e.target.value)} style={{ flex: 1, minWidth: 140 }}>
            <option value="kb:read">kb:read</option>
            <option value="kb:propose">kb:propose</option>
            <option value="kb:write">kb:write</option>
          </select>
          <Button variant="primary" onClick={handleCreate}>{zh ? "產生 Token" : "Generate Token"}</Button>
        </div>
      </SectionCard>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {keys.map(k => (
          <div key={k.id} style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 10, padding: 16, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 8 }}>
                {k.name} 
                <span className="tag" style={{ color: "var(--color-primary)", background: "var(--color-primary-subtle)" }}>{((k as any).scopes || []).join(', ')}</span>
              </div>
              <div style={{ fontSize: 13, color: "var(--text-muted)", fontFamily: "monospace", marginTop: 4 }}>{k.prefix}********************</div>
              <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 6 }}>
                Created: {new Date(k.created_at).toLocaleDateString()} · Last used: {k.last_used_at ? new Date(k.last_used_at).toLocaleString() : "Never"}
              </div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <Button variant="secondary" onClick={() => handleRotate(k.id)} title="Rotate Token" leftIcon={<RefreshCw size={14} />} />
              <Button variant="secondary" onClick={() => handleRevoke(k.id)} title={zh ? "刪除" : "Delete"} leftIcon={<Trash2 size={14} />} />
            </div>
          </div>
        ))}
        {!loading && keys.length === 0 && <div style={{ color: "var(--text-muted)", textAlign: "center", padding: 20 }}>{t('ws_settings.noRequests')}</div>}
      </div>
    </div>
  );
}

type MainTab = "general" | "members" | "export" | "assoc" | "ai_review" | "apikeys" | "connectors";
type AccessTab = "members" | "invites" | "requests";

// ── Workspace AI Model Settings Tab ──────────────────────────────────────────

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

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [language, setLanguage] = useState<"zh-TW" | "en">("zh-TW");
  const [isSaving, setIsSaving] = useState(false);
  const [decayStats, setDecayStats] = useState<any>(null);
  const [healthReport, setHealthReport] = useState<any>(null);

  // Embedding Model State
  const [embedProvider, setEmbedProvider] = useState("openai");
  const [pendingEmbedModel, setPendingEmbedModel] = useState("");
  const [embedModels, setEmbedModels] = useState<any[]>([]);
  const [loadingEmbedModels, setLoadingEmbedModels] = useState(false);
  const [failedEmbeddings, setFailedEmbeddings] = useState(0);
  const [retrying, setRetrying] = useState(false);
  const isOwner = ws?.owner_id === userId;

  useEffect(() => {
    if (!ws) return;
    setEmbedProvider(ws.embedding_provider || "openai");
    setPendingEmbedModel(ws.embedding_model || "");
  }, [ws]);

  useEffect(() => {
    if (!embedProvider) return;
    let active = true;
    setLoadingEmbedModels(true);
    ai.listModels(embedProvider).then(ms => {
      if (active) setEmbedModels(ms.filter(m => m.model_type === 'embedding'));
    }).catch(() => {
      if (active) setEmbedModels([]);
    }).finally(() => {
      if (active) setLoadingEmbedModels(false);
    });
    return () => { active = false; };
  }, [embedProvider]);

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
      setName(w.name);
      setDescription(w.description || "");
      setLanguage(w.language);
      setJoinRequests(reqs);
      setAssociations(as);

      // Fetch admin-only decay stats if we are the owner
      if (w.owner_id === userId) {
        workspaces.getDecayStats(wsId).then(setDecayStats).catch(() => {});
        workspaces.getFailedEmbeddings(wsId).then(res => setFailedEmbeddings(res.count)).catch(() => {});
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
        <button onClick={() => setTab("general")} style={{ padding: "12px 4px", background: "none", border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600, color: tab === "general" ? "var(--color-primary)" : "var(--text-muted)", borderBottom: tab === "general" ? "2px solid var(--color-primary)" : "2px solid transparent" }}>{t('ws_settings.general')}</button>
        <button onClick={() => setTab("members")} style={{ padding: "12px 4px", background: "none", border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600, color: tab === "members" ? "var(--color-primary)" : "var(--text-muted)", borderBottom: tab === "members" ? "2px solid var(--color-primary)" : "2px solid transparent" }}>{t('ws_settings.membersAccess')}</button>
        <button onClick={() => setTab("export")} style={{ padding: "12px 4px", background: "none", border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600, color: tab === "export" ? "var(--color-primary)" : "var(--text-muted)", borderBottom: tab === "export" ? "2px solid var(--color-primary)" : "2px solid transparent" }}>{t('ws_settings.dataExport')}</button>
        <button onClick={() => setTab("assoc")} style={{ padding: "12px 4px", background: "none", border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600, color: tab === "assoc" ? "var(--color-primary)" : "var(--text-muted)", borderBottom: tab === "assoc" ? "2px solid var(--color-primary)" : "2px solid transparent" }}>{t('ws_settings.kbAssoc')}</button>
        <button onClick={() => setTab("ai_review")} style={{ padding: "12px 4px", background: "none", border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600, color: tab === "ai_review" ? "var(--color-primary)" : "var(--text-muted)", borderBottom: tab === "ai_review" ? "2px solid var(--color-primary)" : "2px solid transparent" }}>{zh ? "AI 管理" : "AI Management"}</button>
        <button onClick={() => setTab("connectors")} style={{ padding: "12px 4px", background: "none", border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600, color: tab === "connectors" ? "var(--color-primary)" : "var(--text-muted)", borderBottom: tab === "connectors" ? "2px solid var(--color-primary)" : "2px solid transparent" }}>{zh ? "外部整合" : "Connectors"}</button>
        {ws?.owner_id === userId && (
          <button onClick={() => setTab("apikeys")} style={{ padding: "12px 4px", background: "none", border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600, color: tab === "apikeys" ? "var(--color-primary)" : "var(--text-muted)", borderBottom: tab === "apikeys" ? "2px solid var(--color-primary)" : "2px solid transparent" }}>{t('ws_settings.apiKeys')}</button>
        )}
      </div>

      {tab === "general" ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {!isOwner && ws && (
            <div style={{ padding: "12px 16px", background: "var(--color-warning-subtle)", color: "var(--color-warning)", borderRadius: 8, fontSize: 13, fontWeight: 500, border: "1px solid var(--border-warning-subtle)" }}>
              {zh ? "⚠️ 您不是此工作區的擁有者，無法修改設定。" : "⚠️ You are not the owner of this workspace and cannot modify settings."}
            </div>
          )}
          <SectionCard>
            <h3 style={{ fontSize: 14, margin: "0 0 16px" }}>{t('ws_settings.general')}</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16 }}>
                <div>
                  <label style={{ display: "block", fontSize: 13, marginBottom: 6, color: "var(--text-muted)" }}>{zh ? "工作區名稱" : "Workspace Name"}</label>
                  <input className="mt-input" value={name} onChange={e => setName(e.target.value)} disabled={!isOwner} style={{ width: "100%" }} />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: 13, marginBottom: 6, color: "var(--text-muted)" }}>{zh ? "語言" : "Language"}</label>
                  <select
                    className="mt-input"
                    value={language}
                    disabled={!isOwner}
                    onChange={e => setLanguage(e.target.value as any)}
                    style={{ width: "100%", height: 38 }}
                  >
                    <option value="zh-TW">繁體中文</option>
                    <option value="en">English</option>
                  </select>
                </div>
              </div>
              <div>
                <label style={{ display: "block", fontSize: 13, marginBottom: 6, color: "var(--text-muted)" }}>{zh ? "描述" : "Description"}</label>
                <textarea
                  className="mt-input"
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                  disabled={!isOwner}
                  placeholder={zh ? "簡單介紹這個知識庫的用途…" : "Briefly describe what this knowledge base is about…"}
                  style={{ width: "100%", height: 72, resize: "vertical", fontFamily: "inherit", fontSize: 14 }}
                />
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 8 }}>
                <Button variant="primary" disabled={!isOwner || isSaving || (name === ws?.name && language === ws?.language && description === (ws?.description || ""))} loading={isSaving} onClick={async () => {
                  setIsSaving(true);
                  try {
                    await workspaces.update(wsId, { name, language, description: description || null });
                    await loadData();
                    toast({ message: "Workspace settings updated", variant: "success" });
                  } catch (err) {
                    toast({ message: err instanceof Error ? err.message : String(err), variant: "error" });
                  } finally {
                    setIsSaving(false);
                  }
                }}>{t('ws_settings.save')}</Button>
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
              <select className="mt-input" value={ws?.visibility ?? "private"} disabled={!isOwner} style={{ width: 180 }} onChange={async (e) => {
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
              <select className="mt-input" value={ws?.qa_archive_mode ?? "manual_review"} disabled={!isOwner} style={{ width: 180 }} onChange={async (e) => {
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
                disabled={!isOwner}
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
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div>
                <div style={{ fontWeight: 600 }}>{zh ? "向量模型 (Embedding Model)" : "Embedding Model"}</div>
                <div style={{ fontSize: 12, color: "var(--text-muted)", maxWidth: 500 }}>
                  {zh ? "選擇用於語義檢索的模型。若更改模型，系統將在背景執行重新嵌入 (migration)，此期間可能影響檢索品質且產生 Token 消耗。" : "Select the model for semantic search. Changing it triggers a background migration (re-embed)."}
                </div>
                {ws?.migration_status === 'in_progress' && (
                  <div style={{ marginTop: 8, padding: "8px 12px", background: "var(--color-primary-subtle)", color: "var(--color-primary)", borderRadius: 8, fontSize: 13, display: "flex", alignItems: "center", gap: 6 }}>
                    <RefreshCw size={14} className="animate-spin" />
                    {zh ? `正在轉移至 ${ws.migrating_to_provider}/${ws.migrating_to_model}...` : `Migrating to ${ws.migrating_to_provider}/${ws.migrating_to_model}...`}
                  </div>
                )}
              </div>
              
              <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr auto", gap: 10, alignItems: "end" }}>
                <div>
                  <label style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 6, display: "block" }}>Provider</label>
                  <select
                    className="mt-input"
                    value={embedProvider}
                    disabled={!isOwner || ws?.migration_status === 'in_progress'}
                    onChange={e => {
                      setEmbedProvider(e.target.value);
                      setPendingEmbedModel("");
                    }}
                    style={{ width: "100%" }}
                  >
                    <option value="openai">OpenAI</option>
                    <option value="anthropic">Anthropic</option>
                    <option value="gemini">Gemini</option>
                    <option value="ollama">Ollama</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 6, display: "block" }}>Model</label>
                  <select
                    className="mt-input"
                    disabled={!isOwner || ws?.migration_status === 'in_progress' || loadingEmbedModels}
                    style={{ width: "100%" }}
                    value={ws?.migration_status === 'in_progress' ? ws?.migrating_to_model || "" : pendingEmbedModel}
                    onChange={e => setPendingEmbedModel(e.target.value)}
                  >
                    <option value="">{loadingEmbedModels ? (zh ? "載入中..." : "Loading...") : (zh ? "— 請選擇模型 —" : "— Select a model —")}</option>
                    {embedProvider === ws?.embedding_provider && ws?.embedding_model && (
                      <option value={ws.embedding_model}>{ws.embedding_model} ({zh ? "當前" : "Current"})</option>
                    )}
                    {embedModels.filter(m => m.id !== ws?.embedding_model || embedProvider !== ws?.embedding_provider).map(m => (
                      <option key={m.id} value={m.id}>{m.display_name || m.id}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <Button
                    size="sm"
                    variant="primary"
                    disabled={
                      !isOwner ||
                      !pendingEmbedModel ||
                      ws?.migration_status === 'in_progress' ||
                      (pendingEmbedModel === ws?.embedding_model && embedProvider === ws?.embedding_provider)
                    }
                    onClick={async () => {
                      if (!pendingEmbedModel) return;
                      const ok = await confirm({
                        title: zh ? "確認更換向量模型？" : "Change Embedding Model?",
                        message: zh
                          ? `確定要將模型更改為 ${embedProvider} / ${pendingEmbedModel}？系統將在背景重新計算所有節點。`
                          : `Change to ${embedProvider} / ${pendingEmbedModel}? All nodes will be re-embedded in the background.`,
                        confirmLabel: zh ? "開始轉移" : "Start Migration",
                        variant: "warning"
                      });
                      if (!ok) return;
                      try {
                        await workspaces.update(wsId, {
                          migrating_to_provider: embedProvider,
                          migrating_to_model: pendingEmbedModel,
                          migration_status: 'in_progress'
                        });
                        await loadData();
                        toast({ message: zh ? "開始轉移" : "Migration started", variant: "success" });
                      } catch (err: any) {
                        toast({ message: err.message || String(err), variant: "error" });
                      }
                    }}
                  >
                    {zh ? "套用" : "Apply"}
                  </Button>
                </div>
              </div>

              {/* Failed embeddings retry */}
              {isOwner && failedEmbeddings > 0 && (
                <div style={{ marginTop: 12, padding: "12px 16px", background: "var(--color-error-subtle)", borderRadius: 8, border: "1px solid var(--border-error-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div>
                    <div style={{ fontWeight: 600, color: "var(--color-error)" }}>{zh ? "嵌入失敗節點" : "Failed Embeddings"}</div>
                    <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
                      {zh ? `目前有 ${failedEmbeddings} 個節點嵌入失敗。系統將自動重試，您也可以手動立即重試。` : `${failedEmbeddings} nodes failed to embed. The system will retry automatically, or you can retry now.`}
                    </div>
                  </div>
                  <Button 
                    variant="secondary" 
                    size="sm"
                    loading={retrying}
                    leftIcon={<RefreshCw size={14} />}
                    onClick={async () => {
                      setRetrying(true);
                      try {
                        const res = await workspaces.retryFailedEmbeddings(wsId);
                        toast({ message: zh ? `已重排 ${res.queued} 個節點` : `Queued ${res.queued} nodes`, variant: "success" });
                        setFailedEmbeddings(0);
                      } catch (err) {
                        toast({ message: String(err), variant: "error" });
                      } finally {
                        setRetrying(false);
                      }
                    }}
                  >
                    {zh ? "立即重試" : "Retry Now"}
                  </Button>
                </div>
              )}
            </div>
          </SectionCard>
          
          {/* P4.8-S9-5: Node Complexity & Auto-split */}
          <SectionCard>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
                    {t('ws_settings.auto_split')}
                    <span className="tag" style={{ background: "var(--color-primary-subtle)", color: "var(--color-primary)" }}>Pro</span>
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-muted)", maxWidth: 400 }}>
                    {zh ? "當節點內容過長或包含多個獨立主題時，AI 將自動提議拆分為多個原子節點。" : "Automatically suggest splitting long or multi-topic nodes into smaller atomic ones."}
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <label className="mt-switch" style={{ opacity: isOwner ? 1 : 0.5 }}>
                    <input 
                      type="checkbox" 
                      checked={ws?.auto_split ?? false} 
                      disabled={!isOwner}
                      onChange={async (e) => {
                        try {
                          await workspaces.update(wsId, { auto_split: e.target.checked });
                          await loadData();
                          toast({ message: t('common.save'), variant: "success" });
                        } catch (err) {
                          toast({ message: String(err), variant: "error" });
                        }
                      }} 
                    />
                    <span className="mt-switch-slider round"></span>
                  </label>
                </div>
              </div>
              
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, borderTop: "1px solid var(--border-subtle)", paddingTop: 16 }}>
                <div>
                  <label style={{ display: "block", fontSize: 12, marginBottom: 6, color: "var(--text-muted)" }}>
                    {t('ws_settings.complexity_threshold')}
                  </label>
                  <input 
                    className="mt-input" 
                    type="number" 
                    value={ws?.settings?.node_complexity?.char_threshold ?? 600} 
                    disabled={!isOwner}
                    style={{ width: "100%" }}
                    onChange={async (e) => {
                      const val = parseInt(e.target.value);
                      if (isNaN(val)) return;
                      const newSettings = { 
                        ...ws?.settings, 
                        node_complexity: { ...ws?.settings?.node_complexity, char_threshold: val } 
                      };
                      try {
                        const updatedWs = await workspaces.update(wsId, { settings: newSettings });
                        setWs(updatedWs);
                      } catch (err) { toast({ message: String(err), variant: "error" }); }
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: 12, marginBottom: 6, color: "var(--text-muted)" }}>
                    {t('ws_settings.dedup_threshold')}
                  </label>
                  <input 
                    className="mt-input" 
                    type="number" 
                    step="0.01"
                    value={ws?.settings?.auto_dedup_threshold ?? 0.92} 
                    disabled={!isOwner}
                    style={{ width: "100%" }}
                    onChange={async (e) => {
                      const val = parseFloat(e.target.value);
                      if (isNaN(val)) return;
                      const newSettings = { ...ws?.settings, auto_dedup_threshold: val };
                      try {
                        const updatedWs = await workspaces.update(wsId, { settings: newSettings });
                        setWs(updatedWs);
                      } catch (err) { toast({ message: String(err), variant: "error" }); }
                    }}
                  />
                </div>
              </div>
            </div>
          </SectionCard>

          {/* P4.8-S9-7: MCP Ingestion Settings */}
          <SectionCard>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600 }}>{t('ws_settings.mcp_ingestion')}</div>
                  <div style={{ fontSize: 12, color: "var(--text-muted)", maxWidth: 400 }}>
                    {zh ? "允許透過 MCP 協定 (如 IDE 插件) 直接將內容寫入此工作區。" : "Allow direct content ingestion via MCP protocol (e.g., from IDE plugins)."}
                  </div>
                </div>
                <label className="mt-switch" style={{ opacity: isOwner ? 1 : 0.5 }}>
                  <input 
                    type="checkbox" 
                    checked={ws?.settings?.mcp_ingest_enabled ?? false} 
                    disabled={!isOwner} 
                    onChange={async (e) => {
                      const newSettings = { ...ws?.settings, mcp_ingest_enabled: e.target.checked };
                      try {
                        const updatedWs = await workspaces.update(wsId, { settings: newSettings });
                        setWs(updatedWs);
                        toast({ message: t('common.save'), variant: "success" });
                      } catch (err) { toast({ message: String(err), variant: "error" }); }
                    }} 
                  />
                  <span className="mt-switch-slider round"></span>
                </label>
              </div>
              
              {ws?.settings?.mcp_ingest_enabled && (
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderTop: "1px solid var(--border-subtle)", paddingTop: 16 }}>
                   <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                     {t('ws_settings.mcp_daily_quota')}
                   </div>
                   <input 
                     className="mt-input" 
                     type="number" 
                     value={ws?.settings?.mcp_ingest_daily_quota ?? 5} 
                     disabled={!isOwner}
                     style={{ width: 80 }}
                     onChange={async (e) => {
                       const val = parseInt(e.target.value);
                       if (isNaN(val)) return;
                       const newSettings = { ...ws?.settings, mcp_ingest_daily_quota: val };
                       try {
                         const updatedWs = await workspaces.update(wsId, { settings: newSettings });
                         setWs(updatedWs);
                       } catch (err) { toast({ message: String(err), variant: "error" }); }
                     }}
                   />
                </div>
              )}
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
              <h3 style={{ fontSize: 14, margin: "0 0 16px", display: "flex", alignItems: "center", gap: 8 }}><Clock size={18} /> {t('ws_settings.edge_decay_status')}</h3>
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
              <h3 style={{ fontSize: 14, margin: "0 0 16px", display: "flex", alignItems: "center", gap: 8 }}><ShieldAlert size={18} /> {t('ws_settings.health_report')}</h3>
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
              <h3 style={{ fontSize: 14, margin: "0 0 12px", color: "var(--color-error)", display: "flex", alignItems: "center", gap: 8 }}>
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
                  toast({ message: zh ? `工作區「${ws.name}」已刪除` : `Workspace "${ws.name}" deleted`, variant: "success" });
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
            <h3 style={{ fontSize: 14, margin: "0 0 16px", display: "flex", alignItems: "center", gap: 8 }}><ExternalLink size={18} style={{ color: "var(--color-primary)" }} /> {t('ws_settings.add_assoc_title')}</h3>
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
                        <div style={{ fontWeight: 600 }}>{result.name}</div>
                        <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{result.language} / {result.visibility}</div>
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
              <div key={association.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 10 }}>
                <div>
                  <div style={{ fontWeight: 600 }}>{association.target_name}</div>
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
        <AIReviewerSettings wsId={wsId} ws={ws} isOwner={isOwner} zh={zh} loadData={loadData} />
      ) : tab === "apikeys" ? (
        <APIKeysSettings wsId={wsId} />
      ) : tab === "connectors" ? (
        <ConnectorSettings wsId={wsId} zh={zh} />
      ) : (
        <>
          {renderAccessTabs}

          {accessTab === "members" && (
            <section>
              <h3 style={{ fontSize: 14, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}><Users size={18} style={{ color: "var(--color-primary)" }} /> {t('ws_settings.ws_members')}</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {members.map((member) => (
                  <div key={member.user_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 10 }}>
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
                <h3 style={{ fontSize: 14, margin: "0 0 16px", display: "flex", alignItems: "center", gap: 8 }}><Link2 size={18} style={{ color: "var(--color-primary)" }} /> {t('ws_settings.create_invite_link')}</h3>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: 10 }}>
                  <div>
                    <label className="form-label">{zh ? "角色" : "Role"}</label>
                    <select className="mt-input" value={inviteRole} onChange={(e) => setInviteRole(e.target.value)}>
                      <option value="viewer">Viewer</option>
                      <option value="editor">Editor</option>
                    </select>
                  </div>
                  <div>
                    <label className="form-label">{zh ? "有效期限" : "Expires in"}</label>
                    <select className="mt-input" value={inviteDays} onChange={(e) => setInviteDays(Number(e.target.value))}>
                      <option value={3}>{zh ? "3 天" : "3 days"}</option>
                      <option value={7}>{zh ? "7 天" : "7 days"}</option>
                      <option value={30}>{zh ? "30 天" : "30 days"}</option>
                    </select>
                  </div>
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
              <h3 style={{ fontSize: 14, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}><UserPlus size={18} style={{ color: "var(--color-primary)" }} /> {t('ws_settings.join_requests')}</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {joinRequests.map((req) => (
                  <div key={req.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 10 }}>
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
