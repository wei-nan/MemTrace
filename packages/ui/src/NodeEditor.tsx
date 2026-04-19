import { useEffect, useMemo, useState } from "react";
import MDEditor from "@uiw/react-md-editor";
import ReactMarkdown from "react-markdown";
import { Calendar, Edit3, History, Link as LinkIcon, Save, Shield, Trash2, User, X } from "lucide-react";
import { edges as edgesApi, nodes as nodesApi, type DiffSummary, type Edge, type Node, type NodeCreatePayload, type NodeRevisionMeta } from "./api";
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

const CONTENT_TYPES = ["factual", "procedural", "preference", "context"];
const VISIBILITIES = ["private", "team", "public"];
const RELATIONS = ["depends_on", "extends", "related_to", "contradicts"];

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
  const isCreate = node === null;
  const isViewerLocked = Boolean(node && !node.body_zh && !node.body_en);
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
    setSelectedRevisionDiff(null);
    if (node?.id) {
      edgesApi.list(wsId, node.id).then(setNodeEdges).catch(() => {});
      nodesApi.revisions(wsId, node.id).then(setRevisions).catch(() => setRevisions([]));
      nodesApi.traverse(node.id).catch(() => {});
    } else {
      setNodeEdges([]);
      setRevisions([]);
    }
  }, [wsId, node, isCreate]);

  const payload = useMemo(() => buildPayload({ titleZh, titleEn, contentType, format, bodyZh, bodyEn, tags, visibility }), [titleZh, titleEn, contentType, format, bodyZh, bodyEn, tags, visibility]);
  const relatedNodes = allNodes.filter((candidate) => candidate.id !== node?.id && candidate.title_en.toLowerCase().includes(linkTarget.toLowerCase()));

  const submitSave = async () => {
    if (!payload.title_zh || !payload.title_en) {
      setError("Both Chinese and English titles are required.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const saved = node ? await nodesApi.update(wsId, node.id, payload) : await nodesApi.create(wsId, payload);
      if ("detail" in saved && !isNodeResponse(saved)) {
        toast({ message: saved.detail ?? "Submitted for review", variant: "success" });
        onClose();
        return;
      }
      if (!isNodeResponse(saved)) {
        throw new Error("Unexpected save response.");
      }
      onSaved(saved);
      setIsEditing(false);
      toast({ message: "Memory saved", variant: "success" });
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
      title: "Delete Memory",
      message: `Delete "${node.title_en}"? Editors will submit a review request instead of deleting immediately.`,
      variant: "danger",
      confirmLabel: "Delete",
    });
    if (!ok) return;
    try {
      await nodesApi.delete(wsId, node.id);
      toast({ message: "Delete request submitted", variant: "success" });
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
      toast({ message: result.detail ?? result.message ?? "Restore submitted", variant: "success" });
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ padding: "18px 22px", borderBottom: "1px solid var(--border-default)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <div style={{ fontSize: 18, fontWeight: 700 }}>{isCreate ? "New Memory" : isEditing ? "Edit Memory" : "Memory Details"}</div>
          {!isCreate && (
            <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
              <button className={`tag ${tab === "details" ? "tag-active" : ""}`} onClick={() => setTab("details")}>Details</button>
              <button className={`tag ${tab === "history" ? "tag-active" : ""}`} onClick={() => setTab("history")}>
                <History size={12} /> History
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
                    <div style={{ fontWeight: 600 }}>Revision {revision.revision_no}</div>
                    <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
                      {revision.proposer_type} · {revision.proposer_id || "unknown"} · {new Date(revision.created_at).toLocaleString()}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button className="btn-secondary" onClick={() => handleShowRevisionDiff(revision.revision_no)}>Compare</button>
                    <button className="btn-primary" onClick={() => handleRestoreRevision(revision.revision_no)}>Restore</button>
                  </div>
                </div>
              </div>
            ))}
            {selectedRevisionDiff && (
              <div style={{ marginTop: 8 }}>
                <DiffPreviewModal diff={selectedRevisionDiff} title="Revision Diff" onCancel={() => setSelectedRevisionDiff(null)} onConfirm={() => setSelectedRevisionDiff(null)} confirmLabel="Close" />
              </div>
            )}
          </div>
        ) : isEditing ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div>
              <label className="form-label">Titles</label>
              <div style={{ display: "grid", gap: 8 }}>
                <input className="mt-input" value={titleEn} onChange={(e) => setTitleEn(e.target.value)} placeholder="English title" />
                <input className="mt-input" value={titleZh} onChange={(e) => setTitleZh(e.target.value)} placeholder="Chinese title" />
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
              <div>
                <label className="form-label">Type</label>
                <select className="mt-input" value={contentType} onChange={(e) => setContentType(e.target.value)}>
                  {CONTENT_TYPES.map((item) => <option key={item}>{item}</option>)}
                </select>
              </div>
              <div>
                <label className="form-label">Format</label>
                <select className="mt-input" value={format} onChange={(e) => setFormat(e.target.value as "plain" | "markdown")}>
                  <option value="markdown">markdown</option>
                  <option value="plain">plain</option>
                </select>
              </div>
              <div>
                <label className="form-label">Visibility</label>
                <select className="mt-input" value={visibility} onChange={(e) => setVisibility(e.target.value)}>
                  {VISIBILITIES.map((item) => <option key={item}>{item}</option>)}
                </select>
              </div>
            </div>

            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <label className="form-label" style={{ margin: 0 }}>Content</label>
                <div style={{ display: "flex", gap: 8 }}>
                  <button className={`tag ${displayLang === "en" ? "tag-active" : ""}`} onClick={() => setDisplayLang("en")}>EN</button>
                  <button className={`tag ${displayLang === "zh" ? "tag-active" : ""}`} onClick={() => setDisplayLang("zh")}>ZH</button>
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
              <label className="form-label">Tags</label>
              <input className="mt-input" value={tags} onChange={(e) => setTags(e.target.value)} placeholder="comma separated" />
            </div>

            {error && <div style={{ color: "var(--color-error)", fontSize: 13 }}>{error}</div>}

            <div style={{ display: "flex", gap: 10 }}>
              <button className="btn-primary" style={{ flex: 1 }} onClick={handleSaveClick} disabled={saving}>
                <Save size={16} /> {saving ? "Saving..." : "Save"}
              </button>
              {!isCreate && <button className="btn-danger" onClick={handleDelete}><Trash2 size={16} /></button>}
            </div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            <div>
              <h1 style={{ margin: 0, fontSize: 26 }}>{displayLang === "zh" ? node?.title_zh : node?.title_en}</h1>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12 }}>
                <span className="tag"><Shield size={12} /> {node?.content_type}</span>
                <span className="tag"><Calendar size={12} /> {node?.created_at.split("T")[0]}</span>
                <span className="tag"><User size={12} /> trust {(node?.trust_score ?? 0).toFixed(2)}</span>
                {node?.tags.map((tag) => <span key={tag} className="tag">#{tag}</span>)}
              </div>
            </div>

            <div style={{ display: "flex", gap: 8 }}>
              <button className={`tag ${displayLang === "en" ? "tag-active" : ""}`} onClick={() => setDisplayLang("en")}>English</button>
              <button className={`tag ${displayLang === "zh" ? "tag-active" : ""}`} onClick={() => setDisplayLang("zh")}>Chinese</button>
            </div>

            <div className="markdown-body" style={{ background: "var(--bg-surface)", padding: 18, borderRadius: 12, border: "1px solid var(--border-default)" }}>
              {isViewerLocked ? (
                <div style={{ color: "var(--text-muted)" }}>This memory is visible, but body content is restricted for viewers.</div>
              ) : (
                <ReactMarkdown>{displayLang === "zh" ? node?.body_zh || "" : node?.body_en || ""}</ReactMarkdown>
              )}
            </div>

            <div>
              <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                <LinkIcon size={16} /> Associations
              </div>
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
                        cursor: otherNode ? "pointer" : "default",
                      }}
                    >
                      <span>{otherNode ? `${otherNode.title_en} (${edge.relation})` : `${otherId} (${edge.relation})`}</span>
                    </button>
                  );
                })}
                {!nodeEdges.length && <div style={{ color: "var(--text-muted)", fontSize: 13 }}>No associations yet.</div>}
              </div>

              {!isViewerLocked && node && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr auto auto", gap: 8, marginTop: 12 }}>
                  <input className="mt-input" value={linkTarget} onChange={(e) => setLinkTarget(e.target.value)} list="memtrace-node-list" placeholder="Search node title or paste node id" />
                  <datalist id="memtrace-node-list">
                    {relatedNodes.slice(0, 20).map((candidate) => <option key={candidate.id} value={candidate.title_en}>{candidate.title_zh}</option>)}
                    {relatedNodes.slice(0, 20).map((candidate) => <option key={`${candidate.id}-id`} value={candidate.id}>{candidate.title_en}</option>)}
                  </datalist>
                  <select className="mt-input" value={linkRelation} onChange={(e) => setLinkRelation(e.target.value)}>
                    {RELATIONS.map((relation) => <option key={relation}>{relation}</option>)}
                  </select>
                  <button className="btn-secondary" onClick={handleAddEdge}>Link</button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {pendingDiff && (
        <DiffPreviewModal
          diff={pendingDiff}
          title={node ? "Confirm Changes" : "Confirm New Memory"}
          onCancel={() => setPendingDiff(null)}
          onConfirm={submitSave}
          confirmLabel={node ? "Apply Changes" : "Create Memory"}
        />
      )}
    </div>
  );
}
