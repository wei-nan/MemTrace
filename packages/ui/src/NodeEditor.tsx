import { useEffect, useMemo, useState } from "react";
import MDEditor from "@uiw/react-md-editor";
import ReactMarkdown from "react-markdown";
import { useTranslation } from "react-i18next";
import { Archive, Bot, Calendar, CheckCircle2, Copy, Edit3, History, Link as LinkIcon, RotateCcw, Save, Shield, Trash2, TriangleAlert, User, X } from "lucide-react";
import { ai as aiApi, edges as edgesApi, nodes as nodesApi, review as reviewApi, workspaces as workspacesApi, type DiffSummary, type Edge, type Node, type NodeCreatePayload, type NodeRevisionMeta, type ReviewItem } from "./api";
import DiffPreviewModal from "./components/DiffPreviewModal";
import { useModal } from "./components/ModalContext";

interface Props {
  wsId: string;
  node?: Node | null;
  onSaved: (node: Node) => void;
  onClose: () => void;
  onSelectNode?: (node: Node) => void;
  sourceNodeId?: string;
}

const CONTENT_TYPES = ["factual", "procedural", "preference", "context", "inquiry"];
const VISIBILITIES = ["private", "team", "public"];
const RELATIONS = ["depends_on", "extends", "related_to", "contradicts", "answered_by", "similar_to", "queried_via_mcp"];

function isNodeResponse(value: unknown): value is Node {
  return Boolean(value && typeof value === "object" && "id" in value && "workspace_id" in value);
}

function buildPayload(state: {
  titleZh: string;
  titleEn: string;
  contentType: string;
  format: "plain" | "markdown";
  bodyZh: string;
  bodyEn: string;
  tags: string;
  visibility: string;
}): NodeCreatePayload {
  return {
    title_zh: state.titleZh.trim(),
    title_en: state.titleEn.trim(),
    content_type: state.contentType,
    content_format: state.format,
    body_zh: state.bodyZh.trim(),
    body_en: state.bodyEn.trim(),
    tags: state.tags.split(",").map((t) => t.trim()).filter(Boolean),
    visibility: state.visibility,
  };
}

function buildDiff(before: Partial<NodeCreatePayload> | null, after: NodeCreatePayload, changeType: "create" | "update"): DiffSummary {
  const fields: DiffSummary["fields"] = {};
  const changedFields: string[] = [];
  const source = before ?? {};

  for (const key of Object.keys(after) as (keyof NodeCreatePayload)[]) {
    const prev = source[key];
    const next = after[key];
    if (key === "tags") {
      const prevTags = Array.isArray(prev) ? prev : [];
      const nextTags = Array.isArray(next) ? next : [];
      const added = nextTags.filter((tag) => !prevTags.includes(tag));
      const removed = prevTags.filter((tag) => !nextTags.includes(tag));
      if (changeType === "create" || added.length || removed.length) {
        fields[key] = { type: "set", added: nextTags.filter((tag) => !prevTags.includes(tag)), removed };
        changedFields.push(key);
      }
      continue;
    }
    if (key === "body_zh" || key === "body_en") {
      const beforeText = String(prev ?? "");
      const afterText = String(next ?? "");
      if (changeType === "create" || beforeText !== afterText) {
        fields[key] = {
          type: "text",
          before: beforeText,
          after: afterText,
          line_diff: afterText.split("\n").map((line) => ({ op: changeType === "create" ? "add" : "keep", text: line })),
        };
        changedFields.push(key);
      }
      continue;
    }
    if (changeType === "create" || prev !== next) {
      fields[key] = { type: "scalar", before: prev ?? null, after: next };
      changedFields.push(key);
    }
  }

  return { change_type: changeType, changed_fields: changedFields, field_count: changedFields.length, fields };
}

export default function NodeEditor({ wsId, node, onSaved, onClose, onSelectNode, sourceNodeId }: Props) {
  const { confirm, toast } = useModal();
  const { t } = useTranslation();
  const isCreate = node === null;
  const isViewerLocked = Boolean(node?.content_stripped);
  const [tab, setTab] = useState<"details" | "history">("details");
  const [isEditing, setIsEditing] = useState(isCreate);
  const [titleZh, setTitleZh] = useState(node?.title_zh ?? "");
  const [titleEn, setTitleEn] = useState(node?.title_en ?? "");
  const [contentType, setContentType] = useState(node?.content_type ?? "factual");
  const [format, setFormat] = useState<"plain" | "markdown">((node?.content_format as "plain" | "markdown") ?? "markdown");
  const [bodyZh, setBodyZh] = useState(node?.body_zh ?? "");
  const [bodyEn, setBodyEn] = useState(node?.body_en ?? "");
  const [tags, setTags] = useState((node?.tags ?? []).join(", "));
  const [visibility, setVisibility] = useState(node?.visibility ?? "private");
  const [displayLang, setDisplayLang] = useState<"zh" | "en">("en");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [pendingDiff, setPendingDiff] = useState<DiffSummary | null>(null);
  const [allNodes, setAllNodes] = useState<Node[]>([]);
  const [nodeEdges, setNodeEdges] = useState<Edge[]>([]);
  const [linkTarget, setLinkTarget] = useState("");
  const [linkRelation, setLinkRelation] = useState("related_to");
  const [revisions, setRevisions] = useState<NodeRevisionMeta[]>([]);
  const [selectedRevisionDiff, setSelectedRevisionDiff] = useState<DiffSummary | null>(null);
  const [validityConfirmedAt, setValidityConfirmedAt] = useState<string | null>(node?.validity_confirmed_at ?? null);
  const [validityConfirmedBy, setValidityConfirmedBy] = useState<string | null>(node?.validity_confirmed_by ?? null);
  const [confirmingValidity, setConfirmingValidity] = useState(false);
  const [archiving, setArchiving] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [suggestedReviewItems, setSuggestedReviewItems] = useState<ReviewItem[]>([]);
  const [isVoting, setIsVoting] = useState(false);
  const [voteAccuracy, setVoteAccuracy] = useState(5);
  const [voteUtility, setVoteUtility] = useState(5);
  const [submittingVote, setSubmittingVote] = useState(false);
  const isArchived = node?.status === 'archived';

  useEffect(() => {
    nodesApi.list(wsId).then(setAllNodes).catch(() => {});
  }, [wsId]);

  useEffect(() => {
    setTab("details");
    setIsEditing(isCreate);
    setTitleZh(node?.title_zh ?? "");
    setTitleEn(node?.title_en ?? "");
    setContentType(node?.content_type ?? "factual");
    setFormat((node?.content_format as "plain" | "markdown") ?? "markdown");
    setBodyZh(node?.body_zh ?? "");
    setBodyEn(node?.body_en ?? "");
    setTags((node?.tags ?? []).join(", "));
    setVisibility(node?.visibility ?? "private");
    setValidityConfirmedAt(node?.validity_confirmed_at ?? null);
    setValidityConfirmedBy(node?.validity_confirmed_by ?? null);
    setSelectedRevisionDiff(null);
    if (node?.id) {
      edgesApi.list(wsId, node.id).then(setNodeEdges).catch(() => {});
      nodesApi.revisions(wsId, node.id).then(setRevisions).catch(() => setRevisions([]));
      nodesApi.traverse(node.id).catch(() => {});
    } else {
      setNodeEdges([]);
      setRevisions([]);
    }
    // Fetch suggested edges from review queue
    if (node?.id) {
      reviewApi.list(wsId).then(items => {
        const suggested = items.filter(item => 
          item.change_type === "create_edge" && 
          item.status === "pending" &&
          (item.node_data?.from_id === node.id || item.node_data?.to_id === node.id)
        );
        setSuggestedReviewItems(suggested);
      }).catch(() => {});
    }
    setIsVoting(false);
    setVoteAccuracy(5);
    setVoteUtility(5);
  }, [wsId, node, isCreate]);

  const payload = useMemo(() => buildPayload({ titleZh, titleEn, contentType, format, bodyZh, bodyEn, tags, visibility }), [titleZh, titleEn, contentType, format, bodyZh, bodyEn, tags, visibility]);
  const relatedNodes = allNodes.filter((candidate) => candidate.id !== node?.id && candidate.title_en.toLowerCase().includes(linkTarget.toLowerCase()));
  const trustDimensions = node ? [
    { key: "accuracy", label: t("node.dim_accuracy"), value: node.dim_accuracy, help: "AI 擷取初始較低，人工建立通常較高。" },
    { key: "freshness", label: t("node.dim_freshness"), value: node.dim_freshness, help: "內容更新後會重置，之後再隨時間衰減。" },
    { key: "utility", label: t("node.dim_utility"), value: node.dim_utility, help: "會隨節點被走訪與使用而累積。" },
    { key: "author_rep", label: t("node.dim_author_rep"), value: node.dim_author_rep, help: "反映作者歷史內容品質。" },
  ] : [];

  const handleConfirmValidity = async () => {
    if (!node) return;
    setConfirmingValidity(true);
    try {
      const result = await nodesApi.confirmValidity(wsId, node.id);
      setValidityConfirmedAt(result.confirmed_at);
      setValidityConfirmedBy(result.confirmed_by);
      onSaved({ ...node, validity_confirmed_at: result.confirmed_at, validity_confirmed_by: result.confirmed_by });
      toast({ message: t("node.validity_confirmed"), variant: "success" });
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    } finally {
      setConfirmingValidity(false);
    }
  };

  const handleArchive = async () => {
    if (!node) return;
    const ok = await confirm({
      title: isArchived ? t('node.restore_title') : t('node.archive_title'),
      message: isArchived
        ? t('node.restore_confirm', { title: node.title_en })
        : t('node.archive_confirm', { title: node.title_en }),
      variant: isArchived ? 'info' : 'danger',
      confirmLabel: isArchived ? t('node.restore_btn') : t('node.archive_btn'),
    });
    if (!ok) return;
    setArchiving(true);
    try {
      if (isArchived) {
        await nodesApi.restore(wsId, node.id);
        onSaved({ ...node, status: 'active', archived_at: null });
        toast({ message: t('node.node_restored'), variant: 'success' });
      } else {
        await nodesApi.archive(wsId, node.id);
        onSaved({ ...node, status: 'archived', archived_at: new Date().toISOString() });
        toast({ message: t('node.node_archived'), variant: 'success' });
        onClose();
      }
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: 'error' });
    } finally {
      setArchiving(false);
    }
  };

  const handleAIComplete = async () => {
    if (!titleEn && !titleZh) {
      toast({ message: "Please provide a title first", variant: "warning" });
      return;
    }
    setCompleting(true);
    try {
      const prompt = `Based on the title "${titleEn || titleZh}", please generate a concise knowledge node content (around 100-200 words) in both English and Chinese. 
      Format the output as a JSON object: {"body_en": "...", "body_zh": "..."}.
      Do not include any other text or markdown fences.`;
      
      const res = await aiApi.chat({ workspace_id: wsId, message: prompt });
      const data = JSON.parse(res.answer.replace(/```json|```/g, "").trim());
      if (data.body_en) setBodyEn(data.body_en);
      if (data.body_zh) setBodyZh(data.body_zh);
      toast({ message: "Content generated", variant: "success" });
    } catch (e) {
      toast({ message: "AI completion failed: " + String(e), variant: "error" });
    } finally {
      setCompleting(false);
    }
  };

  const handleAcceptReview = async (id: string) => {
    try {
      await reviewApi.accept(id);
      setSuggestedReviewItems(prev => prev.filter(item => item.id !== id));
      toast({ message: "Edge accepted", variant: "success" });
      // Refresh edges
      if (node?.id) edgesApi.list(wsId, node.id).then(setNodeEdges).catch(() => {});
    } catch (e) {
      toast({ message: String(e), variant: "error" });
    }
  };

  const handleRejectReview = async (id: string) => {
    try {
      await reviewApi.reject(id);
      setSuggestedReviewItems(prev => prev.filter(item => item.id !== id));
      toast({ message: "Edge rejected", variant: "success" });
    } catch (e) {
      toast({ message: String(e), variant: "error" });
    }
  };

  const handleVoteTrust = async () => {
    if (!node) return;
    setSubmittingVote(true);
    try {
      const res = await nodesApi.voteTrust(wsId, node.id, { accuracy: voteAccuracy, utility: voteUtility });
      onSaved({ ...node, trust_score: res.trust_score, dim_accuracy: voteAccuracy / 5, dim_utility: voteUtility / 5 });
      setIsVoting(false);
      toast({ message: t("node.vote_submitted"), variant: "success" });
    } catch (e) {
      toast({ message: String(e), variant: "error" });
    } finally {
      setSubmittingVote(false);
    }
  };

  const submitSave = async () => {
    if (!payload.title_zh || !payload.title_en) {
      setError(t("node.titles_required"));
      return;
    }
    setSaving(true);
    setError("");
    try {
      const saved = node ? await nodesApi.update(wsId, node.id, payload) : await nodesApi.create(wsId, payload);
      if ("detail" in saved && !isNodeResponse(saved)) {
        toast({ message: saved.detail ?? t("node.submitted_review"), variant: "success" });
        onClose();
        return;
      }
      if (!isNodeResponse(saved)) {
        throw new Error("Unexpected save response.");
      }
      onSaved(saved);
      setIsEditing(false);
      toast({ message: t("node.memory_saved"), variant: "success" });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
      setPendingDiff(null);
    }
  };

  const handleSaveClick = () => {
    const diff = buildDiff(node ? {
      title_zh: node.title_zh,
      title_en: node.title_en,
      content_type: node.content_type,
      content_format: node.content_format,
      body_zh: node.body_zh,
      body_en: node.body_en,
      tags: node.tags,
      visibility: node.visibility,
    } : null, payload, node ? "update" : "create");
    setPendingDiff(diff);
  };

  const handleDelete = async () => {
    if (!node) return;
    const ok = await confirm({
      title: t("node.delete_title"),
      message: t("node.delete_confirm", { title: node.title_en }),
      variant: "danger",
      confirmLabel: t("node.delete_btn"),
    });
    if (!ok) return;
    try {
      await nodesApi.delete(wsId, node.id);
      toast({ message: t("node.delete_submitted"), variant: "success" });
      onClose();
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    }
  };

  const handleAddEdge = async () => {
    if (!node) return;
    const target = allNodes.find((candidate) => candidate.id === linkTarget || candidate.title_en === linkTarget || candidate.title_zh === linkTarget);
    if (!target) return;
    try {
      const edge = await edgesApi.create(wsId, { from_id: node.id, to_id: target.id, relation: linkRelation, weight: 1, half_life_days: 30 });
      setNodeEdges((prev) => [...prev, edge]);
      setLinkTarget("");
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    }
  };

  const handleShowRevisionDiff = async (revisionNo: number) => {
    if (!node) return;
    try {
      const diff = await nodesApi.diffRevisions(wsId, node.id, revisionNo, revisions[0]?.revision_no ?? revisionNo);
      setSelectedRevisionDiff(diff);
      setTab("history");
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    }
  };

  const handleRestoreRevision = async (revisionNo: number) => {
    if (!node) return;
    try {
      const result = await nodesApi.restoreRevision(wsId, node.id, revisionNo);
      toast({ message: result.detail ?? result.message ?? t("node.restore_submitted"), variant: "success" });
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ padding: "18px 22px", borderBottom: "1px solid var(--border-default)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <div style={{ fontSize: 18, fontWeight: 700 }}>{isCreate ? t("node.title_new") : isEditing ? t("node.title_edit") : t("node.title_detail")}</div>
          {!isCreate && (
            <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
              <button className={`tag ${tab === "details" ? "tag-active" : ""}`} onClick={() => setTab("details")}>{t("node.tab_details")}</button>
              <button className={`tag ${tab === "history" ? "tag-active" : ""}`} onClick={() => setTab("history")}>
                <History size={12} /> {t("node.tab_history")}
              </button>
            </div>
          )}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {!isCreate && !isEditing && !isViewerLocked && <button className="nav-item" style={{ padding: 6, margin: 0 }} onClick={() => setIsEditing(true)}><Edit3 size={18} /></button>}
          <button className="nav-item" style={{ padding: 6, margin: 0 }} onClick={onClose}><X size={18} /></button>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: 22 }}>
        {tab === "history" && node ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {revisions.map((revision) => (
              <div key={revision.id} style={{ border: "1px solid var(--border-default)", borderRadius: 12, padding: 14, background: "var(--bg-surface)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
                  <div>
                    <div style={{ fontWeight: 600 }}>{t("node.revision_no")} {revision.revision_no}</div>
                    <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
                      {revision.proposer_type} · {revision.proposer_id || "unknown"} · {new Date(revision.created_at).toLocaleString()}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button className="btn-secondary" onClick={() => handleShowRevisionDiff(revision.revision_no)}>{t("node.compare")}</button>
                    <button className="btn-primary" onClick={() => handleRestoreRevision(revision.revision_no)}>{t("node.restore")}</button>
                  </div>
                </div>
              </div>
            ))}
            {selectedRevisionDiff && (
              <div style={{ marginTop: 8 }}>
                <DiffPreviewModal diff={selectedRevisionDiff} title={t("node.revision_diff")} onCancel={() => setSelectedRevisionDiff(null)} onConfirm={() => setSelectedRevisionDiff(null)} confirmLabel={t("node.close")} />
              </div>
            )}
          </div>
        ) : isEditing ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div>
              <label className="form-label">{t("node.titles")}</label>
              <div style={{ display: "grid", gap: 8 }}>
                <input className="mt-input" value={titleEn} onChange={(e) => setTitleEn(e.target.value)} placeholder={t("node.en_title_ph")} />
                <input className="mt-input" value={titleZh} onChange={(e) => setTitleZh(e.target.value)} placeholder={t("node.zh_title_ph")} />
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
              <div>
                <label className="form-label">{t("node.type_label")}</label>
                <select className="mt-input" value={contentType} onChange={(e) => setContentType(e.target.value)}>
                  {CONTENT_TYPES.map((item) => <option key={item} value={item}>{t(`content_type.${item}`, { defaultValue: item })}</option>)}
                </select>
              </div>
              <div>
                <label className="form-label">{t("node.format_label")}</label>
                <select className="mt-input" value={format} onChange={(e) => setFormat(e.target.value as "plain" | "markdown")}>
                  <option value="markdown">markdown</option>
                  <option value="plain">plain</option>
                </select>
              </div>
              <div>
                <label className="form-label">{t("node.visibility_label")}</label>
                <select className="mt-input" value={visibility} onChange={(e) => setVisibility(e.target.value)}>
                  {VISIBILITIES.map((item) => <option key={item} value={item}>{t(`form.vis_${item}`, { defaultValue: item })}</option>)}
                </select>
              </div>
            </div>

            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <label className="form-label" style={{ margin: 0 }}>{t("node.content")}</label>
                <div style={{ display: "flex", gap: 8 }}>
                  <button 
                    className="tag" 
                    onClick={handleAIComplete} 
                    disabled={completing}
                    style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}
                  >
                    <Bot size={12} /> {completing ? "..." : t('node.ai_complete')}
                  </button>
                  <button className={`tag ${displayLang === "en" ? "tag-active" : ""}`} onClick={() => setDisplayLang("en")}>{t("node.lang_en")}</button>
                  <button className={`tag ${displayLang === "zh" ? "tag-active" : ""}`} onClick={() => setDisplayLang("zh")}>{t("node.lang_zh")}</button>
                </div>
              </div>
              <div data-color-mode="dark">
                <MDEditor
                  value={displayLang === "zh" ? bodyZh : bodyEn}
                  onChange={(value) => displayLang === "zh" ? setBodyZh(value ?? "") : setBodyEn(value ?? "")}
                  height={280}
                  preview="edit"
                />
              </div>
            </div>

            <div>
              <label className="form-label">{t("node.tags_label")}</label>
              <input className="mt-input" value={tags} onChange={(e) => setTags(e.target.value)} placeholder={t("node.tags_ph")} />
            </div>

            {error && <div style={{ color: "var(--color-error)", fontSize: 13 }}>{error}</div>}

            <div style={{ display: "flex", gap: 10 }}>
              <button className="btn-primary" style={{ flex: 1 }} onClick={handleSaveClick} disabled={saving}>
                <Save size={16} /> {saving ? t("node.saving") : t("node.save")}
              </button>
              {!isCreate && <button className="btn-danger" onClick={handleDelete}><Trash2 size={16} /></button>}
            </div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            <div>
              <h1 style={{ margin: 0, fontSize: 26 }}>{displayLang === "zh" ? node?.title_zh : node?.title_en}</h1>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12 }}>
                <span className="tag"><Shield size={12} /> {t(`content_type.${node?.content_type}`, { defaultValue: node?.content_type })}</span>
                {node?.content_type === 'inquiry' && node?.ask_count > 0 && (
                  <span className="tag" style={{ background: 'rgba(148, 163, 184, 0.1)', color: '#64748b' }}>
                    <Bot size={12} /> ASK: {node.ask_count}
                  </span>
                )}
                <span className="tag"><Calendar size={12} /> {node?.created_at.split("T")[0]}</span>
                <span className="tag"><User size={12} /> {t("node.trust_score")} {(node?.trust_score ?? 0).toFixed(2)}</span>
                {node?.tags.map((tag) => <span key={tag} className="tag">#{tag}</span>)}
              </div>
            </div>

            {node && (
              <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 12, padding: 16, display: "flex", flexDirection: "column", gap: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
                  <div>
                    <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 8 }}>
                      <CheckCircle2 size={16} /> {t("node.validity")}
                    </div>
                    <div style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 4 }}>
                      {validityConfirmedAt
                        ? t('node.validity_last_confirmed', { date: new Date(validityConfirmedAt).toLocaleDateString(), user: validityConfirmedBy })
                        : t('node.validity_unconfirmed')}
                    </div>
                  </div>
                  {!isViewerLocked && (
                    <button className="btn-secondary" onClick={handleConfirmValidity} disabled={confirmingValidity}>
                      {confirmingValidity ? t("node.confirming") : t("node.confirm_validity")}
                    </button>
                  )}
                </div>
                {!validityConfirmedAt && (
                  <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-muted)", fontSize: 12 }}>
                    <TriangleAlert size={14} /> {t('node.validity_suggest_label')}
                  </div>
                )}
              </div>
            )}

            <div style={{ display: "flex", gap: 8 }}>
              <button className={`tag ${displayLang === "en" ? "tag-active" : ""}`} onClick={() => setDisplayLang("en")}>{t("node.lang_en")}</button>
              <button className={`tag ${displayLang === "zh" ? "tag-active" : ""}`} onClick={() => setDisplayLang("zh")}>{t("node.lang_zh")}</button>
            </div>

            <div className="markdown-body" style={{ background: "var(--bg-surface)", padding: 18, borderRadius: 12, border: "1px solid var(--border-default)" }}>
              {isViewerLocked ? (
                <div style={{ color: "var(--text-muted)" }}>{t('node.private_locked')}</div>
              ) : (
                <ReactMarkdown>{displayLang === "zh" ? node?.body_zh || "" : node?.body_en || ""}</ReactMarkdown>
              )}
            </div>

            {node && (
              <div style={{ background: "var(--bg-surface)", padding: 18, borderRadius: 12, border: "1px solid var(--border-default)", display: "flex", flexDirection: "column", gap: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ fontWeight: 600 }}>{t("node.trust_dimensions")}</div>
                  {!isViewerLocked && (
                    <button 
                      className="btn-secondary" 
                      style={{ padding: "4px 10px", fontSize: 12 }} 
                      onClick={() => setIsVoting(!isVoting)}
                    >
                      {isVoting ? t("node.cancel_vote") : t("node.vote_trust")}
                    </button>
                  )}
                </div>

                {isVoting ? (
                  <div style={{ padding: "10px 0", borderTop: "1px solid var(--border-subtle)", marginTop: 4, display: "flex", flexDirection: "column", gap: 14 }}>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 120px", gap: 12, alignItems: "center" }}>
                      <span style={{ fontSize: 13 }}>{t("node.accuracy")} (1-5)</span>
                      <input 
                        type="range" min="1" max="5" step="1" 
                        value={voteAccuracy} 
                        onChange={(e) => setVoteAccuracy(parseInt(e.target.value))} 
                        style={{ accentColor: "var(--color-primary)" }}
                      />
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 120px", gap: 12, alignItems: "center" }}>
                      <span style={{ fontSize: 13 }}>{t("node.utility")} (1-5)</span>
                      <input 
                        type="range" min="1" max="5" step="1" 
                        value={voteUtility} 
                        onChange={(e) => setVoteUtility(parseInt(e.target.value))} 
                        style={{ accentColor: "var(--color-primary)" }}
                      />
                    </div>
                    <button 
                      className="btn-primary" 
                      onClick={handleVoteTrust} 
                      disabled={submittingVote}
                      style={{ marginTop: 4 }}
                    >
                      {submittingVote ? t("node.saving") : t("node.submit_vote")}
                    </button>
                  </div>
                ) : (
                  <>
                    {trustDimensions.map((item) => (
                      <div key={item.key} style={{ display: "grid", gridTemplateColumns: "120px 1fr 56px", gap: 12, alignItems: "center" }} title={item.help}>
                        <div style={{ fontSize: 13 }}>{item.label}</div>
                        <div style={{ height: 10, borderRadius: 999, background: "var(--border-subtle)", overflow: "hidden" }}>
                          <div style={{ width: `${Math.max(0, Math.min(1, item.value)) * 100}%`, height: "100%", background: "linear-gradient(90deg, var(--color-primary), #34d399)" }} />
                        </div>
                        <div style={{ fontSize: 12, color: "var(--text-muted)", textAlign: "right" }}>{item.value.toFixed(2)}</div>
                      </div>
                    ))}
                  </>
                )}
              </div>
            )}

            {/* inquiry 節點：answered_by 答案列表 */}
            {node?.content_type === 'inquiry' && nodeEdges.some(e => e.relation === 'answered_by') && (
              <div>
                <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                  <Bot size={16} /> {displayLang === 'zh' ? '答案節點' : 'Answers'}
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {nodeEdges.filter(e => e.relation === 'answered_by').map(edge => {
                    const answerNode = allNodes.find(n => n.id === edge.to_id);
                    return (
                      <button
                        key={edge.id}
                        onClick={() => answerNode && onSelectNode?.(answerNode)}
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          padding: "10px 12px",
                          borderRadius: 10,
                          border: "1px solid var(--border-default)",
                          background: "var(--bg-surface)",
                          cursor: answerNode ? "pointer" : "default",
                        }}
                      >
                        <span>{answerNode ? (displayLang === 'zh' ? answerNode.title_zh : answerNode.title_en) : edge.to_id}</span>
                        <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
                          trust: {(answerNode?.trust_score ?? 0).toFixed(2)}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            <div>
              <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                <LinkIcon size={16} /> {t("node.associations")}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {nodeEdges.filter(e => e.relation !== 'queried_via_mcp').map((edge) => {
                  const otherId = edge.from_id === node?.id ? edge.to_id : edge.from_id;
                  const otherNode = allNodes.find((candidate) => candidate.id === otherId);
                  return (
                    <button
                      key={edge.id}
                      onClick={() => otherNode && onSelectNode?.(otherNode)}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        padding: "10px 12px",
                        borderRadius: 10,
                        border: `1px solid ${otherId === sourceNodeId ? "var(--color-primary)" : "var(--border-default)"}`,
                        background: otherId === sourceNodeId ? "var(--color-primary-subtle)" : "var(--bg-surface)",
                        cursor: otherNode ? "pointer" : "default",
                      }}
                    >
                      <span>{otherNode ? `${otherNode.title_en} (${t(`relation.${edge.relation}`, { defaultValue: edge.relation })})` : `${otherId} (${t(`relation.${edge.relation}`, { defaultValue: edge.relation })})`}</span>
                    </button>
                  );
                })}
                {nodeEdges.some(e => e.relation === 'queried_via_mcp') && (
                  <div style={{ 
                    marginTop: 4, 
                    padding: "8px 12px", 
                    background: "var(--bg-app)", 
                    borderRadius: 10, 
                    border: "1px solid var(--border-subtle)",
                    fontSize: 13,
                    color: "var(--text-muted)",
                    display: "flex",
                    justifyContent: "space-between"
                  }}>
                    <span>{t('node.queried_via_mcp_label', { defaultValue: 'System Query (MCP)' })}</span>
                    <span style={{ fontWeight: 600, color: "var(--color-primary)" }}>
                      {nodeEdges.find(e => e.relation === 'queried_via_mcp')?.metadata?.count ?? 0} {t('node.times', { defaultValue: 'hits' })}
                    </span>
                  </div>
                )}
                {nodeEdges.filter(e => e.relation !== 'queried_via_mcp').length === 0 && <div style={{ color: "var(--text-muted)", fontSize: 13 }}>{t("node.no_associations")}</div>}
              </div>

              {/* AI Suggested Edges */}
              {suggestedReviewItems.length > 0 && (
                <div style={{ marginTop: 12, background: "rgba(124, 58, 237, 0.05)", border: "1px dashed var(--color-primary)", borderRadius: 12, padding: 14 }}>
                  <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 8, marginBottom: 10, color: "var(--color-primary)" }}>
                    <Bot size={16} /> {t('node.suggested_by_ai')}
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {suggestedReviewItems.map(item => {
                      const otherId = item.node_data.from_id === node?.id ? item.node_data.to_id : item.node_data.from_id;
                      const otherNode = allNodes.find(n => n.id === otherId);
                      return (
                        <div key={item.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, background: "var(--bg-surface)", padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border-subtle)" }}>
                          <span style={{ fontSize: 13 }}>{otherNode ? otherNode.title_en : otherId} ({item.node_data.relation})</span>
                          <div style={{ display: "flex", gap: 6 }}>
                            <button className="btn-primary" style={{ padding: "4px 8px", fontSize: 11 }} onClick={() => handleAcceptReview(item.id)}>{t('node.accept')}</button>
                            <button className="btn-secondary" style={{ padding: "4px 8px", fontSize: 11 }} onClick={() => handleRejectReview(item.id)}>{t('node.skip')}</button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {!isViewerLocked && node && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr auto auto", gap: 8, marginTop: 12 }}>
                  <input className="mt-input" value={linkTarget} onChange={(e) => setLinkTarget(e.target.value)} list="memtrace-node-list" placeholder={t("node.search_node_ph")} />
                  <datalist id="memtrace-node-list">
                    {relatedNodes.slice(0, 20).map((candidate) => <option key={candidate.id} value={candidate.title_en}>{candidate.title_zh}</option>)}
                    {relatedNodes.slice(0, 20).map((candidate) => <option key={`${candidate.id}-id`} value={candidate.id}>{candidate.title_en}</option>)}
                  </datalist>
                  <select className="mt-input" value={linkRelation} onChange={(e) => setLinkRelation(e.target.value)}>
                    {RELATIONS.map((relation) => <option key={relation}>{relation}</option>)}
                  </select>
                  <button className="btn-secondary" onClick={handleAddEdge}>{t("node.link")}</button>
                </div>
              )}
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              {!isViewerLocked && node && (
                <button
                  className={isArchived ? "btn-secondary" : "btn-secondary"}
                  style={{ color: isArchived ? 'var(--color-primary)' : 'var(--text-muted)' }}
                  onClick={handleArchive}
                  disabled={archiving}
                  title={isArchived ? t('node.restore_title') : t('node.archive_title')}
                >
                  {isArchived ? <RotateCcw size={16} /> : <Archive size={16} />}
                </button>
              )}
              {!isViewerLocked && node && (
                <button
                  className="btn-secondary"
                  style={{ flex: 1 }}
                  onClick={async () => {
                    const wsList = await workspacesApi.list();
                    const available = wsList.filter((w: any) => w.id !== wsId);
                    if (available.length === 0) {
                      toast({ message: t("node.no_other_ws"), variant: "warning" });
                      return;
                    }
                    const targetId = await confirm({
                      title: t("node.copy_to_workspace"),
                      message: t("node.copy_to_workspace"),
                      confirmLabel: t("node.copy"),
                      customElement: (
                        <select className="mt-input" id="copy-target-ws">
                          {available.map((w: any) => <option key={w.id} value={w.id}>{w.name_en} ({w.name_zh})</option>)}
                        </select>
                      )
                    });
                    if (!targetId) return;
                    const select = document.getElementById("copy-target-ws") as HTMLSelectElement;
                    const selectedWsId = select.value;
                    try {
                      await nodesApi.create(selectedWsId, {
                        ...payload,
                        copied_from_node: node.id,
                        copied_from_ws: wsId
                      });
                      toast({ message: t("node.copied_success"), variant: "success" });
                    } catch (e) {
                      toast({ message: String(e), variant: "error" });
                    }
                  }}
                >
                  <Copy size={16} /> {t("node.copy_to_workspace")}
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {pendingDiff && (
        <DiffPreviewModal
          diff={pendingDiff}
          title={node ? t("node.confirm_changes") : t("node.confirm_new")}
          onCancel={() => setPendingDiff(null)}
          onConfirm={submitSave}
          confirmLabel={node ? t("node.apply_changes") : t("node.create_memory")}
        />
      )}
    </div>
  );
}
