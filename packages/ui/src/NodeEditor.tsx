import { useEffect, useMemo, useState } from "react";
import MDEditor from "@uiw/react-md-editor";
import ReactMarkdown from "react-markdown";
import { useTranslation } from "react-i18next";
import { Archive, Bot, Calendar, Compass, Copy, Edit3, ExternalLink, FileUp, History, Link as LinkIcon, Paperclip, RotateCcw, Save, Shield, Trash2, X } from "lucide-react";
import { ai as aiApi, documents as documentsApi, edges as edgesApi, nodes as nodesApi, review as reviewApi, workspaces as workspacesApi, type DiffSummary, type Edge, type Node, type NodeCreatePayload, type NodeRevisionMeta, type NodeSource, type ReviewItem } from "./api";
import DiffPreviewModal from "./components/DiffPreviewModal";
import { useModal } from "./components/ModalContext";
import { Button, Input, Card } from "./components/ui";

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
const RELATIONS = ["depends_on", "extends", "related_to", "contradicts", "answered_by", "similar_to"];

function isNodeResponse(value: unknown): value is Node {
  return Boolean(value && typeof value === "object" && "id" in value && "workspace_id" in value);
}

function buildPayload(state: {
  title: string;
  contentType: string;
  format: "plain" | "markdown";
  body: string;
  tags: string;
  visibility: string;
  resolutionStatus: 'open' | 'resolved' | 'superseded';
}): NodeCreatePayload {
  return {
    title: state.title.trim(),
    content_type: state.contentType,
    content_format: state.format,
    body: state.body.trim(),
    tags: state.tags.split(",").map((t) => t.trim()).filter(Boolean),
    visibility: state.visibility,
    resolution_status: state.resolutionStatus,
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
    if (key === "body") {
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
  const [title, setTitle] = useState(node?.title ?? "");
  const [contentType, setContentType] = useState(node?.content_type ?? "factual");
  const [format, setFormat] = useState<"plain" | "markdown">((node?.content_format as "plain" | "markdown") ?? "markdown");
  const [body, setBody] = useState(node?.body ?? "");
  const [tags, setTags] = useState((node?.tags ?? []).join(", "));
  const [visibility, setVisibility] = useState(node?.visibility ?? "private");
  const [resolutionStatus, setResolutionStatus] = useState<'open' | 'resolved' | 'superseded'>(node?.resolution_status ?? "open");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [pendingDiff, setPendingDiff] = useState<DiffSummary | null>(null);
  const [allNodes, setAllNodes] = useState<Node[]>([]);
  const [nodeEdges, setNodeEdges] = useState<Edge[]>([]);
  const [linkTarget, setLinkTarget] = useState("");
  const [linkRelation, setLinkRelation] = useState("related_to");
  const [revisions, setRevisions] = useState<NodeRevisionMeta[]>([]);
  const [selectedRevisionDiff, setSelectedRevisionDiff] = useState<DiffSummary | null>(null);

  const [archiving, setArchiving] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [suggestedReviewItems, setSuggestedReviewItems] = useState<ReviewItem[]>([]);
  const [nodeSources, setNodeSources] = useState<NodeSource[]>([]);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [urlInput, setUrlInput] = useState('');
  const [linkingUrl, setLinkingUrl] = useState(false);
  const isArchived = node?.status === 'archived';

  useEffect(() => {
    nodesApi.list(wsId).then(setAllNodes).catch(() => {});
  }, [wsId]);

  useEffect(() => {
    setTab("details");
    setIsEditing(isCreate);
    setTitle(node?.title ?? "");
    setContentType(node?.content_type ?? "factual");
    setFormat((node?.content_format as "plain" | "markdown") ?? "markdown");
    setBody(node?.body ?? "");
    setTags((node?.tags ?? []).join(", "));
    setVisibility(node?.visibility ?? "private");
    setResolutionStatus(node?.resolution_status ?? "open");

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
    setNodeSources([]);
    setUrlInput('');
    if (node?.id) {
      documentsApi.getNodeSources(wsId, node.id).then(setNodeSources).catch(() => {});
    }
  }, [wsId, node, isCreate]);

  const payload = useMemo(() => buildPayload({ title, contentType, format, body, tags, visibility, resolutionStatus }), [title, contentType, format, body, tags, visibility, resolutionStatus]);
  const relatedNodes = allNodes.filter((candidate) => candidate.id !== node?.id && candidate.title.toLowerCase().includes(linkTarget.toLowerCase()));


  const handleArchive = async () => {
    if (!node) return;
    const ok = await confirm({
      title: isArchived ? t('node.restore_title') : t('node.archive_title'),
      message: isArchived
        ? t('node.restore_confirm', { title: node.title })
        : t('node.archive_confirm', { title: node.title }),
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
    if (!title) {
      toast({ message: "Please provide a title first", variant: "warning" });
      return;
    }
    setCompleting(true);
    try {
      const prompt = `Based on the title "${title}", please generate a concise knowledge node content (around 100-200 words). 
      Format the output as a JSON object: {"body": "..."}.
      Do not include any other text or markdown fences.`;
      
      const res = await aiApi.chat({ workspace_id: wsId, message: prompt });
      const data = JSON.parse(res.answer.replace(/```json|```/g, "").trim());
      if (data.body) setBody(data.body);
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


  const submitSave = async () => {
    if (!payload.title) {
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
      title: node.title,
      content_type: node.content_type,
      content_format: node.content_format,
      body: node.body,
      tags: node.tags,
      visibility: node.visibility,
      resolution_status: node.resolution_status,
    } : null, payload, node ? "update" : "create");
    setPendingDiff(diff);
  };

  const handleDelete = async () => {
    if (!node) return;
    const ok = await confirm({
      title: t("node.delete_title"),
      message: t("node.delete_confirm", { title: node.title }),
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
    const target = allNodes.find((candidate) => candidate.id === linkTarget || candidate.title === linkTarget);
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
      <div style={{ padding: "18px 24px", borderBottom: "1px solid var(--border-default)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <div style={{ fontSize: 15, fontWeight: 600 }}>{isCreate ? t("node.title_new") : isEditing ? t("node.title_edit") : t("node.title_detail")}</div>
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
          {!isCreate && !isEditing && !isViewerLocked && (
            <Button variant="ghost" size="sm" onClick={() => setIsEditing(true)}>
              <Edit3 size={18} />
            </Button>
          )}
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X size={18} />
          </Button>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: "auto", overflowX: "hidden", padding: "20px 24px", minWidth: 0 }}>
        {tab === "history" && node ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {revisions.map((revision) => (
              <Card key={revision.id} padding="sm" style={{ border: "1px solid var(--border-default)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
                  <div>
                    <div style={{ fontWeight: 600 }}>{t("node.revision_no")} {revision.revision_no}</div>
                    <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
                      {revision.proposer_type} · {revision.proposer_id || "unknown"} · {new Date(revision.created_at).toLocaleString()}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <Button variant="secondary" onClick={() => handleShowRevisionDiff(revision.revision_no)}>{t("node.compare")}</Button>
                    <Button variant="primary" onClick={() => handleRestoreRevision(revision.revision_no)}>{t("node.restore")}</Button>
                  </div>
                </div>
              </Card>
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
              <label className="form-label">{t("node.title")}</label>
              <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder={t("node.title_ph", { defaultValue: "Enter title" })} />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
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
              <div>
                <label className="form-label">{t("node.resolution_status", { defaultValue: "Status" })}</label>
                <select className="mt-input" value={resolutionStatus} onChange={(e) => setResolutionStatus(e.target.value as any)}>
                  <option value="open">Open</option>
                  <option value="resolved">Resolved</option>
                  <option value="superseded">Superseded</option>
                </select>
              </div>
            </div>

            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <label className="form-label" style={{ margin: 0 }}>{t("node.content")}</label>
                <button 
                  className="tag" 
                  onClick={handleAIComplete} 
                  disabled={completing}
                  style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}
                >
                  <Bot size={12} /> {completing ? "..." : t('node.ai_complete')}
                </button>
              </div>
              <div data-color-mode="dark">
                <MDEditor
                  value={body}
                  onChange={(value) => setBody(value ?? "")}
                  height={280}
                  preview="edit"
                />
              </div>
            </div>

            <div>
              <label className="form-label">{t("node.tags_label")}</label>
              <Input value={tags} onChange={(e) => setTags(e.target.value)} placeholder={t("node.tags_ph")} />
            </div>

            {error && <div style={{ color: "var(--color-error)", fontSize: 13 }}>{error}</div>}

            <div style={{ display: "flex", gap: 10 }}>
              <Button variant="primary" style={{ flex: 1 }} onClick={handleSaveClick} loading={saving} leftIcon={<Save size={16} />}>
                {saving ? t("node.saving") : t("node.save")}
              </Button>
              {!isCreate && (
                <Button variant="danger" onClick={handleDelete}>
                  <Trash2 size={16} />
                </Button>
              )}
            </div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            <div>
              <h1 style={{ margin: 0, fontSize: 19, lineHeight: 1.4 }}>{node?.title}</h1>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12 }}>
                <span className="tag"><Shield size={12} /> {t(`content_type.${node?.content_type}`, { defaultValue: node?.content_type })}</span>
                {node?.resolution_status && node.resolution_status !== 'open' && (
                  <span className="tag" style={{
                    background: node.resolution_status === 'resolved' ? 'rgba(34, 197, 94, 0.1)' : 'rgba(148, 163, 184, 0.1)',
                    color: node.resolution_status === 'resolved' ? '#16a34a' : '#475569',
                    border: node.resolution_status === 'resolved' ? '1px solid rgba(34, 197, 94, 0.2)' : '1px solid rgba(148, 163, 184, 0.2)',
                    fontWeight: 'bold',
                  }}>
                    {node.resolution_status.toUpperCase()}
                  </span>
                )}
                {node?.content_type === 'inquiry' && node?.ask_count > 0 && (
                  <span className="tag" style={{ background: 'rgba(148, 163, 184, 0.1)', color: '#64748b' }}>
                    <Bot size={12} /> ASK: {node.ask_count}
                  </span>
                )}
                <span className="tag"><Calendar size={12} /> {node?.created_at.split("T")[0]}</span>
                {node?.tags.map((tag) => <span key={tag} className="tag">#{tag}</span>)}
              </div>
            </div>


            <div className="markdown-body" style={{ background: "var(--bg-surface)", padding: 18, borderRadius: 10, border: "1px solid var(--border-default)", wordBreak: "break-word", overflowWrap: "anywhere", overflowX: "auto", minWidth: 0 }}>
              {isViewerLocked ? (
                <div style={{ color: "var(--text-muted)" }}>{t('node.private_locked')}</div>
              ) : (
                <ReactMarkdown>{node?.body || ""}</ReactMarkdown>
              )}
            </div>


            {/* inquiry 節點：answered_by 答案列表 */}
            {node?.content_type === 'inquiry' && nodeEdges.some(e => e.relation === 'answered_by') && (
              <div>
                <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                  <Bot size={16} /> {t("node.answers", { defaultValue: "Answers" })}
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
                        <span>{answerNode ? answerNode.title : edge.to_id}</span>
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
              
              {node && !isViewerLocked && (
                <Button
                  variant="primary"
                  style={{ width: '100%', marginBottom: 16, height: 36 }}
                  onClick={() => {
                    if (node?.id && (window as any).mt_trigger_explore) {
                      (window as any).mt_trigger_explore(node.id);
                      onClose();
                    }
                  }}
                  leftIcon={<Compass size={18} />}
                >
                  {t("node.explore_in_graph", { defaultValue: "Explore in Graph" })}
                </Button>
              )}
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {nodeEdges.map((edge) => {
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
                        color: "var(--text-primary)",
                        cursor: otherNode ? "pointer" : "default",
                      }}
                    >
                      <span>{otherNode ? `${otherNode.title} (${t(`relation.${edge.relation}`, { defaultValue: edge.relation })})` : `${otherId} (${t(`relation.${edge.relation}`, { defaultValue: edge.relation })})`}</span>
                    </button>
                  );
                })}
                {nodeEdges.length === 0 && <div style={{ color: "var(--text-muted)", fontSize: 13 }}>{t("node.no_associations")}</div>}
              </div>

              {/* AI Suggested Edges */}
              {suggestedReviewItems.length > 0 && (
                <div style={{ marginTop: 12, background: "rgba(124, 58, 237, 0.05)", border: "1px dashed var(--color-primary)", borderRadius: 10, padding: 14 }}>
                  <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 8, marginBottom: 10, color: "var(--color-primary)" }}>
                    <Bot size={16} /> {t('node.suggested_by_ai')}
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {suggestedReviewItems.map(item => {
                      const otherId = item.node_data.from_id === node?.id ? item.node_data.to_id : item.node_data.from_id;
                      const otherNode = allNodes.find(n => n.id === otherId);
                      return (
                        <div key={item.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, background: "var(--bg-surface)", padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border-subtle)" }}>
                          <span style={{ fontSize: 13 }}>{otherNode ? otherNode.title : otherId} ({item.node_data.relation})</span>
                          <div style={{ display: "flex", gap: 6 }}>
                            <Button variant="primary" size="sm" onClick={() => handleAcceptReview(item.id)}>{t('node.accept')}</Button>
                            <Button variant="secondary" size="sm" onClick={() => handleRejectReview(item.id)}>{t('node.skip')}</Button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {!isViewerLocked && node && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr auto auto", gap: 8, marginTop: 12 }}>
                  <Input value={linkTarget} onChange={(e) => setLinkTarget(e.target.value)} list="memtrace-node-list" placeholder={t("node.search_node_ph")} />
                  <datalist id="memtrace-node-list">
                    {relatedNodes.slice(0, 20).map((candidate) => <option key={candidate.id} value={candidate.title}>{candidate.title}</option>)}
                    {relatedNodes.slice(0, 20).map((candidate) => <option key={`${candidate.id}-id`} value={candidate.id}>{candidate.title}</option>)}
                  </datalist>
                  <select className="mt-input" value={linkRelation} onChange={(e) => setLinkRelation(e.target.value)}>
                    {RELATIONS.map((relation) => <option key={relation}>{relation}</option>)}
                  </select>
                  <Button variant="secondary" onClick={handleAddEdge}>{t("node.link")}</Button>
                </div>
              )}
            </div>
            {/* ── 原始資料附件 ─────────────────────────────────── */}
            {node && (
              <div>
                <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                  <Paperclip size={16} /> {t("node.attachments", { defaultValue: "原始資料" })}
                </div>

                {/* Existing sources */}
                {nodeSources.filter(s => s.evidence_type !== 'agent_attached').length > 0 && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 10 }}>
                    <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-muted)", marginBottom: 4 }}>
                      📎 {t("node.human_upload", { defaultValue: "人類上傳文件" })}
                    </div>
                    {nodeSources.filter(s => s.evidence_type !== 'agent_attached').map(src => (
                      <div key={src.id} style={{
                        display: "flex", alignItems: "center", gap: 8,
                        padding: "8px 10px", borderRadius: 8,
                        border: "1px solid var(--border-default)",
                        background: "var(--bg-surface)", fontSize: 13,
                      }}>
                        {src.source_url && !src.size_bytes ? (
                          <ExternalLink size={13} style={{ color: "var(--color-primary)", flexShrink: 0 }} />
                        ) : (
                          <FileUp size={13} style={{ color: "var(--text-muted)", flexShrink: 0 }} />
                        )}
                        <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {src.title || src.filename}
                        </span>
                        {src.size_bytes > 0 && (
                          <span style={{ fontSize: 11, color: "var(--text-muted)", flexShrink: 0 }}>
                            {(src.size_bytes / 1024 / 1024).toFixed(1)} MB
                          </span>
                        )}
                        <a
                          href={src.source_url && !src.size_bytes ? src.source_url : documentsApi.contentUrl(wsId, src.id)}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ color: "var(--color-primary)", fontSize: 11, flexShrink: 0 }}
                        >
                          {src.source_url && !src.size_bytes ? t("node.open_link", { defaultValue: "開啟" }) : t("node.download", { defaultValue: "下載" })}
                        </a>
                        {!isViewerLocked && (
                          <button
                            title={t("node.detach_doc", { defaultValue: "移除關聯" })}
                            style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", padding: 2, flexShrink: 0, display: "flex", alignItems: "center" }}
                            onClick={async () => {
                              if (!node?.id) return;
                              try {
                                await documentsApi.detachFromNode(wsId, node.id, src.id);
                                setNodeSources(prev => prev.filter(s => s.id !== src.id));
                              } catch (err: any) {
                                toast({ message: err.message ?? "Failed to detach", variant: "error" });
                              }
                            }}
                          >
                            <X size={13} />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Agent Evidence */}
                {nodeSources.filter(s => s.evidence_type === 'agent_attached').length > 0 && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 10 }}>
                    <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-muted)", marginBottom: 4 }}>
                      🤖 {t("node.agent_references", { defaultValue: "Agent 參考資料" })}
                    </div>
                    {nodeSources.filter(s => s.evidence_type === 'agent_attached').map(src => (
                      <div key={src.id} style={{
                        display: "flex", alignItems: "center", gap: 8,
                        padding: "8px 10px", borderRadius: 8,
                        border: "1px solid var(--border-default)",
                        background: "var(--bg-surface)", fontSize: 13,
                      }}>
                        <Bot size={13} style={{ color: "var(--color-primary)", flexShrink: 0 }} />
                        <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {src.title || src.filename}
                        </span>
                        {src.source_url && (
                          <a href={src.source_url} target="_blank" rel="noopener noreferrer" style={{ color: "var(--color-primary)", fontSize: 11, flexShrink: 0 }}>
                            {t("node.open_link", { defaultValue: "開啟" })}
                          </a>
                        )}
                        {!isViewerLocked && (
                          <button
                            title={t("node.detach_doc", { defaultValue: "移除關聯" })}
                            style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", padding: 2, flexShrink: 0, display: "flex", alignItems: "center" }}
                            onClick={async () => {
                              if (!node?.id) return;
                              try {
                                await documentsApi.detachFromNode(wsId, node.id, src.id);
                                setNodeSources(prev => prev.filter(s => s.id !== src.id));
                              } catch (err: any) {
                                toast({ message: err.message ?? "Failed to detach", variant: "error" });
                              }
                            }}
                          >
                            <X size={13} />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Upload file */}
                {!isViewerLocked && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    <label style={{
                      display: "flex", alignItems: "center", gap: 8,
                      padding: "8px 12px", borderRadius: 8, cursor: uploadingFile ? "default" : "pointer",
                      border: "1px dashed var(--border-default)", fontSize: 13,
                      color: "var(--text-muted)", background: "var(--bg-surface)",
                      opacity: uploadingFile ? 0.6 : 1,
                    }}>
                      <FileUp size={14} />
                      {uploadingFile ? t("node.uploading", { defaultValue: "上傳中…" }) : t("node.upload_file", { defaultValue: "附加檔案（最大 30 MB）" })}
                      <input
                        type="file"
                        style={{ display: "none" }}
                        disabled={uploadingFile}
                        onChange={async (e) => {
                          const file = e.target.files?.[0];
                          if (!file || !node?.id) return;
                          setUploadingFile(true);
                          try {
                            const doc = await documentsApi.upload(wsId, file);
                            await documentsApi.attachToNode(wsId, node.id, [doc.id]);
                            const sources = await documentsApi.getNodeSources(wsId, node.id);
                            setNodeSources(sources);
                          } catch (err: any) {
                            toast({ message: err.message ?? "Upload failed", variant: "error" });
                          } finally {
                            setUploadingFile(false);
                            e.target.value = "";
                          }
                        }}
                      />
                    </label>

                    {/* Attach URL */}
                    <div style={{ display: "flex", gap: 6 }}>
                      <Input
                        value={urlInput}
                        onChange={e => setUrlInput(e.target.value)}
                        placeholder={t("node.url_placeholder", { defaultValue: "https://… 外部連結" })}
                        style={{ flex: 1, fontSize: 13 }}
                      />
                      <Button
                        variant="secondary"
                        disabled={!urlInput.startsWith("http") || linkingUrl}
                        loading={linkingUrl}
                        onClick={async () => {
                          if (!node?.id) return;
                          setLinkingUrl(true);
                          try {
                            await documentsApi.linkUrl(wsId, urlInput, { nodeId: node.id });
                            const sources = await documentsApi.getNodeSources(wsId, node.id);
                            setNodeSources(sources);
                            setUrlInput('');
                          } catch (err: any) {
                            toast({ message: err.message ?? "Failed to attach URL", variant: "error" });
                          } finally {
                            setLinkingUrl(false);
                          }
                        }}
                      >
                        {t("node.attach_url", { defaultValue: "附加" })}
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            )}

            <div style={{ display: "flex", gap: 10 }}>
              {!isViewerLocked && node && (
                <Button
                  variant="secondary"
                  onClick={handleArchive}
                  loading={archiving}
                  title={isArchived ? t('node.restore_title') : t('node.archive_title')}
                  style={{ color: isArchived ? 'var(--color-primary)' : 'var(--text-muted)' }}
                  leftIcon={isArchived ? <RotateCcw size={16} /> : <Archive size={16} />}
                />
              )}
              {!isViewerLocked && node && (
                <Button
                  variant="secondary"
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
                          {available.map((w: any) => <option key={w.id} value={w.id}>{w.name}</option>)}
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
                  leftIcon={<Copy size={16} />}
                >
                  {t("node.copy_to_workspace")}
                </Button>
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
