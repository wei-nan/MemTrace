import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { Bot, Check, RefreshCw, User, X, FileText, TriangleAlert } from "lucide-react";
import { review, nodes as nodesApi, type ReviewItem } from "./api";
import { useTranslation } from "react-i18next";
import { useModal } from "./components/ModalContext";

function TagChip({ label, variant }: { label: string; variant: "add" | "remove" | "neutral" }) {
  const colors = {
    add: { bg: "rgba(34,197,94,0.12)", border: "rgba(34,197,94,0.4)", text: "#16a34a" },
    remove: { bg: "rgba(239,68,68,0.12)", border: "rgba(239,68,68,0.4)", text: "#dc2626" },
    neutral: { bg: "var(--bg-base)", border: "var(--border-default)", text: "var(--text-secondary)" },
  }[variant];
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 3,
      padding: "2px 8px", borderRadius: 99, fontSize: 12, fontWeight: 500,
      background: colors.bg, border: `1px solid ${colors.border}`, color: colors.text,
    }}>
      {variant === "add" && <span>+</span>}
      {variant === "remove" && <span>−</span>}
      {label}
    </span>
  );
}

function DiffSummaryBlock({ item }: { item: ReviewItem }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 12 }}>
      {Object.entries(item.diff_summary.fields).map(([field, entry]) => (
        <div key={field} style={{ background: "var(--bg-base)", border: "1px solid var(--border-default)", borderRadius: 10, padding: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 13, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>{field}</div>

          {entry.type === "scalar" && (() => {
            const isEmpty = entry.before === null || entry.before === undefined || entry.before === "";
            return isEmpty ? (
              <div style={{ fontSize: 13, padding: "6px 10px", background: "rgba(34,197,94,0.08)", borderRadius: 6, borderLeft: "3px solid #22c55e", color: "var(--text-primary)" }}>
                {String(entry.after ?? "")}
              </div>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: 13 }}>
                <div style={{ padding: "6px 10px", background: "rgba(239,68,68,0.08)", borderRadius: 6, borderLeft: "3px solid #ef4444", color: "var(--text-secondary)", textDecoration: "line-through" }}>
                  {String(entry.before)}
                </div>
                <div style={{ padding: "6px 10px", background: "rgba(34,197,94,0.08)", borderRadius: 6, borderLeft: "3px solid #22c55e", color: "var(--text-primary)" }}>
                  {String(entry.after ?? "")}
                </div>
              </div>
            );
          })()}

          {entry.type === "set" && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {entry.added?.map((tag) => <TagChip key={`+${tag}`} label={tag} variant="add" />)}
              {entry.removed?.map((tag) => <TagChip key={`-${tag}`} label={tag} variant="remove" />)}
              {!entry.added?.length && !entry.removed?.length && <span style={{ fontSize: 13, color: "var(--text-muted)" }}>—</span>}
            </div>
          )}

          {entry.type === "text" && (
            <div style={{ fontSize: 12, lineHeight: 1.6, fontFamily: "monospace", borderRadius: 6, overflow: "hidden" }}>
              {entry.line_diff?.slice(0, 16).map((line, i) => (
                <div key={i} style={{
                  padding: "1px 10px",
                  background: line.op === "add" ? "rgba(34,197,94,0.1)" : line.op === "remove" ? "rgba(239,68,68,0.1)" : "transparent",
                  color: line.op === "add" ? "#16a34a" : line.op === "remove" ? "#dc2626" : "var(--text-secondary)",
                  whiteSpace: "pre-wrap", wordBreak: "break-word",
                }}>
                  <span style={{ userSelect: "none", marginRight: 8, opacity: 0.7 }}>
                    {line.op === "add" ? "+" : line.op === "remove" ? "−" : " "}
                  </span>
                  {line.text || " "}
                </div>
              ))}
              {(entry.line_diff?.length ?? 0) > 16 && (
                <div style={{ padding: "2px 10px", color: "var(--text-muted)", fontSize: 11 }}>
                  … {(entry.line_diff?.length ?? 0) - 16} more lines
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function SourceDocumentModal({
  wsId,
  nodeId,
  paragraphIndex,
  segment,
}: {
  wsId: string;
  nodeId?: string;
  paragraphIndex?: number;
  segment?: string;
}) {
  const [body, setBody] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!nodeId) {
      setBody(segment ?? null);
      return;
    }
    setLoading(true);
    nodesApi.get(wsId, nodeId)
      .then(n => setBody(n.body_zh || n.body_en || ""))
      .catch(() => setBody(segment ?? "Failed to load source document"))
      .finally(() => setLoading(false));
  }, [wsId, nodeId, segment]);

  useEffect(() => {
    if (body && paragraphIndex !== undefined) {
      const el = document.getElementById(`src-para-${paragraphIndex}`);
      el?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [body, paragraphIndex]);

  if (loading) {
    return <div style={{ color: "var(--text-muted)", padding: 20 }}>載入原始文件中… / Loading source document…</div>;
  }

  if (!body) return null;

  // Split body into paragraphs and highlight the target one
  const paragraphs = body.split(/\n\n+/);
  return (
    <div style={{ maxHeight: 480, overflowY: "auto", fontSize: 13, lineHeight: 1.7 }}>
      {paragraphs.map((para, idx) => {
        const isHighlighted = paragraphIndex !== undefined && idx === paragraphIndex;
        return (
          <div
            key={idx}
            id={`src-para-${idx}`}
            style={{
              padding: "8px 12px", marginBottom: 6, borderRadius: 6,
              background: isHighlighted ? "var(--color-primary-subtle)" : "transparent",
              border: isHighlighted ? "1px solid var(--color-primary)" : "1px solid transparent",
              whiteSpace: "pre-wrap",
            }}
          >
            {para}
          </div>
        );
      })}
    </div>
  );
}

function ReviewCard({
  wsId,
  item,
  canReview,
  onAccept,
  onReject,
}: {
  wsId: string;
  item: ReviewItem;
  canReview: boolean;
  onAccept: (id: string) => void;
  onReject: (id: string) => void;
}) {
  const { t } = useTranslation();
  const { alert } = useModal();
  const [expanded, setExpanded] = useState(false);
  const proposerLabel = item.proposer_type === "ai" ? item.proposer_id?.replace(/^ai:/, "") ?? "AI" : item.proposer_id ?? "User";

  const sourceDocNodeId = item.proposer_meta?.source_document_node_id as string | undefined;
  const sourceParagraphIndex = item.proposer_meta?.source_paragraph_index as number | undefined;
  const sourceSegment = item.proposer_meta?.source_segment as string | undefined;
  const hasSource = !!(sourceDocNodeId || sourceSegment);

  const handleViewSource = () => {
    alert({
      title: "查看原始段落 / Source Paragraph",
      message: (
        <SourceDocumentModal
          wsId={wsId}
          nodeId={sourceDocNodeId}
          paragraphIndex={sourceParagraphIndex}
          segment={sourceSegment}
        />
      ),
    });
  };

  return (
    <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 16, padding: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
            <span className="tag tag-active">{item.change_type}</span>
            <span className="tag" style={{
              background: item.proposer_type === "ai" ? "var(--ai-ollama-subtle)" : "var(--color-primary-subtle)",
              color: item.proposer_type === "ai" ? "var(--ai-ollama)" : "var(--color-primary)",
              borderColor: item.proposer_type === "ai" ? "var(--ai-ollama)" : "var(--color-primary)",
            }}>
              {item.proposer_type === "ai" ? <Bot size={12} /> : <User size={12} />} {proposerLabel}
            </span>
            {item.ai_review && <span className="tag">{item.ai_review.decision} · {(item.ai_review.confidence * 100).toFixed(0)}%</span>}
          </div>
          <div style={{ fontSize: 18, fontWeight: 700 }}>{String(item.node_data.title_en ?? item.node_data.title_zh ?? "Untitled change")}</div>
          <div style={{ color: "var(--text-muted)", fontSize: 13, marginTop: 4 }}>
            {item.source_info || "Review proposal"} · {new Date(item.created_at).toLocaleString()}
          </div>
          {!!item.proposer_meta?.conflict_reason && (
            <div style={{ marginTop: 12, padding: 12, background: "rgba(239, 68, 68, 0.05)", border: "1px solid rgba(239, 68, 68, 0.2)", borderRadius: 10 }}>
              <div style={{ color: "#dc2626", fontSize: 13, fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
                <TriangleAlert size={14} /> {t('review.conflict_detected', { defaultValue: 'Conflict Detected' })}
              </div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 6, lineHeight: 1.5 }}>
                {String(item.proposer_meta.conflict_reason)}
              </div>
            </div>
          )}
        </div>
      </div>

      <div style={{ display: "flex", gap: 10, marginTop: 12, flexWrap: "wrap" }}>
        <button className="btn-secondary" onClick={() => setExpanded((prev) => !prev)}>{expanded ? t('review.hideDiff') : t('review.showDiff')}</button>
        {hasSource && (
          <button
            className="btn-secondary"
            onClick={handleViewSource}
            style={{ display: "flex", alignItems: "center", gap: 6 }}
          >
            <FileText size={14} />
            {t('review.viewSource')}
          </button>
        )}
        {canReview && <button className="btn-primary" onClick={() => onAccept(item.id)}><Check size={16} /> {t('review.accept')}</button>}
        {canReview && <button className="btn-secondary" onClick={() => onReject(item.id)}><X size={16} /> {t('review.reject')}</button>}
      </div>

      {expanded && <DiffSummaryBlock item={item} />}
    </div>
  );
}

export default function ReviewQueue({ wsId, onClose }: { wsId: string; onClose: () => void }) {
  const { t } = useTranslation();
  const { confirm, toast } = useModal();
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [changeType, setChangeType] = useState<"all" | "create" | "update" | "delete" | "gap" | "conflicted">("all");
  const [proposerType, setProposerType] = useState<"all" | "human" | "ai">("all");

  const loadItems = async () => {
    setLoading(true);
    try {
      setItems(await review.list(wsId));
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadItems();
  }, [wsId]);

  const filteredItems = useMemo(
    () => items.filter((item) => {
      const matchType = changeType === "all" 
        || (changeType === "gap" ? item.node_data?.status === "gap" : 
            changeType === "conflicted" ? item.node_data?.status === "conflicted" :
            item.change_type === changeType);
      const matchProposer = proposerType === "all" || item.proposer_type === proposerType;
      return matchType && matchProposer;
    }),
    [items, changeType, proposerType],
  );
  const canReviewAny = filteredItems.some((item) => item.can_review);

  const { i18n } = useTranslation();
  const zh = i18n.language.startsWith('zh');

  const handleAccept = async (id: string) => {
    try {
      await review.accept(id);
      setItems((prev) => prev.filter((item) => item.id !== id));
      toast({ message: t('review.acceptSuccess'), variant: "success" });
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    }
  };

  const handleReject = async (id: string) => {
    const ok = await confirm({ title: t('review.reject'), message: t('review.rejectConfirm'), variant: "danger", confirmLabel: t('review.reject') });
    if (!ok) return;
    try {
      await review.reject(id);
      setItems((prev) => prev.filter((item) => item.id !== id));
      toast({ message: t('review.rejectSuccess'), variant: "success" });
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    }
  };

  const handleAcceptAll = async () => {
    const ok = await confirm({ title: t('review.acceptAll'), message: t('review.acceptAllConfirm'), variant: "warning", confirmLabel: t('review.acceptAll') });
    if (!ok) return;
    try {
      await review.acceptAll(wsId);
      await loadItems();
      toast({ message: "All pending reviews processed", variant: "success" });
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    }
  };

  const handleRejectAll = async () => {
    const ok = await confirm({ 
      title: zh ? "全部拒絕" : "Reject All", 
      message: zh ? "您確定要拒絕所有待審核的記憶嗎？此操作無法復原。" : "Are you sure you want to reject all pending review items? This action cannot be undone.", 
      variant: "danger", 
      confirmLabel: zh ? "全部拒絕" : "Reject All" 
    });
    if (!ok) return;
    try {
      await review.rejectAll(wsId);
      await loadItems();
      toast({ message: zh ? "所有待審核項目已拒絕" : "All pending items rejected", variant: "success" });
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    }
  };

  const handleRunAIPrescreen = async () => {
    try {
      const result = await review.aiPrescreen(wsId);
      await loadItems();
      toast({ message: `AI prescreen processed ${result.processed_count} items`, variant: "success" });
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "var(--bg-base)" }}>
      {createPortal(
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
          {canReviewAny && <button className="btn-secondary" style={{ height: 38 }} onClick={handleRunAIPrescreen}><Bot size={16} /> {t('review.aiPrescreen')}</button>}
          {canReviewAny && <button className="btn-secondary" style={{ height: 38 }} onClick={handleRejectAll}><X size={16} /> {zh ? '全部拒絕' : 'Reject All'}</button>}
          {canReviewAny && <button className="btn-primary" style={{ height: 38 }} onClick={handleAcceptAll}><Check size={16} /> {t('review.acceptAll')}</button>}
        </div>,
        document.getElementById('header-actions')!
      )}

      <div style={{ padding: "16px 32px", borderBottom: "1px solid var(--border-subtle)", display: "flex", gap: 12, alignItems: "center", background: "var(--bg-surface)", flexWrap: "wrap" }}>
        <div style={{ display: "flex", gap: 6 }}>
          {([
            ["all", t('review.allChanges')],
            ["create", t('review.create')],
            ["update", t('review.update')],
            ["delete", t('review.delete')],
            ["gap", t('review.gap')],
            ["conflicted", t('review.conflicted')],
          ] as Array<[typeof changeType, string]>).map(([value, label]) => (
            <button
              key={value}
              className={`tag ${changeType === value ? "tag-active" : ""}`}
              onClick={() => setChangeType(value)}
              style={{ cursor: "pointer", height: 38, border: "none" }}
            >
              {label}
            </button>
          ))}
        </div>
        <div style={{ width: 1, height: 20, background: "var(--border-subtle)", margin: "0 4px" }} />
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <User size={14} style={{ color: "var(--text-muted)" }} />
          <select className="mt-input" style={{ width: 140, height: 38, fontSize: 13 }} value={proposerType} onChange={(e) => setProposerType(e.target.value as typeof proposerType)}>
            <option value="all">{t('review.allProposers')}</option>
            <option value="human">{t('review.human')}</option>
            <option value="ai">{t('review.ai')}</option>
          </select>
        </div>

        <div style={{ flex: 1 }} />

        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn-secondary" style={{ height: 38, padding: "0 16px", fontSize: 13, display: "flex", alignItems: "center", gap: 6 }} onClick={loadItems}>
            <RefreshCw size={14} /> {t('review.refresh')}
          </button>
          <button className="btn-secondary" style={{ height: 38, padding: "0 16px", fontSize: 13 }} onClick={onClose}>
            {t('review.backToGraph')}
          </button>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: 24 }}>
        {loading ? (
          <div style={{ color: "var(--text-muted)" }}>{t('review.loading')}</div>
        ) : filteredItems.length === 0 ? (
          <div style={{ color: "var(--text-muted)" }}>{t('review.noData')}</div>
        ) : (
          <div style={{ display: "grid", gap: 16 }}>
            {filteredItems.map((item) => (
              <ReviewCard key={item.id} wsId={wsId} item={item} canReview={item.can_review} onAccept={handleAccept} onReject={handleReject} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
