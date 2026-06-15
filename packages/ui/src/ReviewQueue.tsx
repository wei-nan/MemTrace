import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { Bot, Check, GitMerge, Layers, Loader2, RefreshCw, User, X, FileText, TriangleAlert } from "lucide-react";
import { review, nodes as nodesApi, kb, type ReviewItem } from "./api";
import { useTranslation } from "react-i18next";
import { useModal } from "./components/ModalContext";
import { Button, Card } from "./components/ui";

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
        <Card key={field} padding="sm" style={{ border: "1px solid var(--border-default)" }}>
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
        </Card>
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
      .then(n => setBody(n.body || ""))
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
  onApplySplit,
  zh,
}: {
  wsId: string;
  item: ReviewItem;
  canReview: boolean;
  onAccept: (id: string) => void;
  onReject: (id: string) => void;
  onApplySplit: (item: ReviewItem) => void;
  zh: boolean;
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
    <Card variant="surface" padding="md" style={{ border: "1px solid var(--border-default)", borderRadius: 10 }}>
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
          <div style={{ fontSize: 15, fontWeight: 600 }}>{String(item.node_data.title ?? "Untitled change")}</div>
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
          {item.source_info?.startsWith("feature_complete:") && (
            <div style={{ marginTop: 12, padding: 12, background: "rgba(34, 197, 94, 0.05)", border: "1px solid rgba(34, 197, 94, 0.2)", borderRadius: 10 }}>
              <div style={{ color: "#16a34a", fontSize: 13, fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
                <GitMerge size={14} /> {zh ? "功能完成 — 需整合驗收" : "Feature Complete — Integration Check Required"}
              </div>
              {!!item.proposer_meta?.subtask_count && (
                <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 6 }}>
                  {zh ? `所有 ${String(item.proposer_meta.subtask_count)} 個子任務已完成` : `All ${String(item.proposer_meta.subtask_count)} subtask(s) completed`}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div style={{ display: "flex", gap: 10, marginTop: 12, flexWrap: "wrap" }}>
        {item.change_type !== "split_suggestion" && (
          <Button variant="secondary" onClick={() => setExpanded((prev) => !prev)}>{expanded ? t('review.hideDiff') : t('review.showDiff')}</Button>
        )}
        {item.change_type === "split_suggestion" && (
          <Button variant="secondary" onClick={() => setExpanded((prev) => !prev)}>
            {expanded ? (zh ? "隱藏建議" : "Hide Suggestions") : (zh ? "查看拆分建議" : "View Split Suggestions")}
          </Button>
        )}
        {hasSource && (
          <Button
            variant="secondary"
            onClick={handleViewSource}
            leftIcon={<FileText size={14} />}
          >
            {t('review.viewSource')}
          </Button>
        )}
        {canReview && item.change_type !== "split_suggestion" && (
          <Button variant="primary" onClick={() => onAccept(item.id)} leftIcon={<Check size={16} />}>
            {t('review.accept')}
          </Button>
        )}
        {canReview && item.change_type === "split_suggestion" && (
          <Button variant="primary" onClick={() => onApplySplit(item)} leftIcon={<Check size={16} />}>
            {zh ? "執行拆分" : "Apply Split"}
          </Button>
        )}
        {canReview && (
          <Button variant="secondary" onClick={() => onReject(item.id)} leftIcon={<X size={16} />}>
            {t('review.reject')}
          </Button>
        )}
      </div>

      {expanded && item.change_type === "split_suggestion" && (
        <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 10 }}>
          {((item.proposer_meta?.split_suggestion as any[]) || []).map((p, i) => (
            <Card key={i} padding="sm" style={{ border: "1px solid var(--border-default)" }}>
               <div style={{ fontWeight: 600, fontSize: 13 }}>{p.title}</div>
               <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>{p.body}</div>
            </Card>
          ))}
        </div>
      )}
      {expanded && item.change_type !== "split_suggestion" && <DiffSummaryBlock item={item} />}
    </Card>
  );
}

export default function ReviewQueue({ wsId, onClose }: { wsId: string; onClose: () => void }) {
  const { t } = useTranslation();
  const { confirm, toast } = useModal();
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [prescreening, setPrescreening] = useState(false);
  const [bulkActing, setBulkActing] = useState(false);
  const [changeType, setChangeType] = useState<"all" | "create" | "update" | "delete" | "gap" | "conflicted">("all");
  const [proposerType, setProposerType] = useState<"all" | "human" | "ai">("all");
  const [grouped, setGrouped] = useState(false);

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

  const groupedItems = useMemo(() => {
    if (!grouped) return null;
    const groups: Record<string, ReviewItem[]> = {};
    for (const item of filteredItems) {
      const key = item.source_info?.split(":")[0] ?? "other";
      if (!groups[key]) groups[key] = [];
      groups[key].push(item);
    }
    return groups;
  }, [filteredItems, grouped]);

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
    setBulkActing(true);
    try {
      await review.acceptAll(wsId);
      setItems([]);
      await loadItems();
      toast({ message: "All pending reviews processed", variant: "success" });
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    } finally {
      setBulkActing(false);
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
    setBulkActing(true);
    try {
      await review.rejectAll(wsId);
      setItems([]);
      await loadItems();
      toast({ message: zh ? "所有待審核項目已拒絕" : "All pending items rejected", variant: "success" });
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    } finally {
      setBulkActing(false);
    }
  };

  const handleRunAIPrescreen = async () => {
    setPrescreening(true);
    try {
      const result = await review.aiPrescreen(wsId);
      await loadItems();
      toast({ message: `AI prescreen processed ${result.processed_count} items`, variant: "success" });
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    } finally {
      setPrescreening(false);
    }
  };

  const handleAcceptGroup = async (groupItems: ReviewItem[]) => {
    const ids = groupItems.map((i) => i.id);
    const ok = await confirm({ title: zh ? "接受此群組" : "Accept Group", message: zh ? `確定接受這 ${ids.length} 個提案？` : `Accept these ${ids.length} proposals?`, variant: "warning", confirmLabel: zh ? "接受" : "Accept" });
    if (!ok) return;
    try {
      await review.acceptBatch(wsId, ids);
      setItems((prev) => prev.filter((i) => !ids.includes(i.id)));
      toast({ message: zh ? `已接受 ${ids.length} 項` : `${ids.length} items accepted`, variant: "success" });
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    }
  };

  const handleRejectGroup = async (groupItems: ReviewItem[]) => {
    const ids = groupItems.map((i) => i.id);
    const ok = await confirm({ title: zh ? "拒絕此群組" : "Reject Group", message: zh ? `確定拒絕這 ${ids.length} 個提案？此操作無法復原。` : `Reject these ${ids.length} proposals? This cannot be undone.`, variant: "danger", confirmLabel: zh ? "拒絕" : "Reject" });
    if (!ok) return;
    try {
      await review.rejectBatch(wsId, ids);
      setItems((prev) => prev.filter((i) => !ids.includes(i.id)));
      toast({ message: zh ? `已拒絕 ${ids.length} 項` : `${ids.length} items rejected`, variant: "success" });
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    }
  };

  const handleApplySplit = async (item: ReviewItem) => {
    const ok = await confirm({ 
      title: zh ? "執行拆分" : "Apply Split", 
      message: zh ? "這將會把原始記憶存檔並建立多個原子化的新記憶。確定執行？" : "This will archive the original memory and create multiple atomic new memories. Proceed?", 
      variant: "warning",
      confirmLabel: zh ? "執行" : "Apply"
    });
    if (!ok) return;
    try {
      // PROPOSALS can be in proposer_meta.split_suggestion
      const proposals = (item.proposer_meta?.split_suggestion as any[]) || [];
      await kb.applySplit(wsId, item.id, { proposals });
      setItems((prev) => prev.filter((i) => i.id !== item.id));
      toast({ message: zh ? "拆分執行成功" : "Split applied successfully", variant: "success" });
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    }
  };
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "var(--bg-base)" }}>
      {createPortal(
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
          {canReviewAny && (
            <Button variant="secondary" onClick={handleRunAIPrescreen} disabled={prescreening || bulkActing} leftIcon={prescreening ? <Loader2 size={16} className="animate-spin" /> : <Bot size={16} />}>
              {prescreening ? (zh ? '分析中…' : 'Analyzing…') : t('review.aiPrescreen')}
            </Button>
          )}
          {canReviewAny && (
            <Button variant="secondary" onClick={handleRejectAll} disabled={prescreening || bulkActing} leftIcon={bulkActing ? <Loader2 size={16} className="animate-spin" /> : <X size={16} />}>
              {zh ? '全部拒絕' : 'Reject All'}
            </Button>
          )}
          {canReviewAny && (
            <Button variant="primary" onClick={handleAcceptAll} disabled={prescreening || bulkActing} leftIcon={bulkActing ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}>
              {bulkActing ? (zh ? '處理中…' : 'Processing…') : t('review.acceptAll')}
            </Button>
          )}
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
            <Button
              key={value}
              variant={changeType === value ? "primary" : "secondary"}
              onClick={() => setChangeType(value)}
              style={{ height: 32, padding: "0 12px" }}
            >
              {label}
            </Button>
          ))}
        </div>
        <div style={{ width: 1, height: 20, background: "var(--border-subtle)", margin: "0 4px" }} />
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <User size={14} style={{ color: "var(--text-muted)" }} />
          <select 
            className="mt-input" 
            style={{ width: 140, height: 32, fontSize: 13, padding: "0 10px", background: "var(--bg-surface)" }} 
            value={proposerType} 
            onChange={(e) => setProposerType(e.target.value as typeof proposerType)}
          >
            <option value="all">{t('review.allProposers')}</option>
            <option value="human">{t('review.human')}</option>
            <option value="ai">{t('review.ai')}</option>
          </select>
        </div>

        <div style={{ flex: 1 }} />

        <div style={{ display: "flex", gap: 8 }}>
          <Button variant={grouped ? "primary" : "secondary"} onClick={() => setGrouped((v) => !v)} leftIcon={<Layers size={14} />}>
            {zh ? "分群" : "Group"}
          </Button>
          <Button variant="secondary" onClick={loadItems} leftIcon={<RefreshCw size={14} />}>
            {t('review.refresh')}
          </Button>
          <Button variant="secondary" onClick={onClose}>
            {t('review.backToGraph')}
          </Button>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: 24 }}>
        {loading ? (
          <div style={{ color: "var(--text-muted)" }}>{t('review.loading')}</div>
        ) : filteredItems.length === 0 ? (
          <div style={{ color: "var(--text-muted)" }}>{t('review.noData')}</div>
        ) : grouped && groupedItems ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            {Object.entries(groupedItems).map(([groupKey, groupItems]) => {
              const canReviewGroup = groupItems.some((i) => i.can_review);
              const isFeatureComplete = groupKey === "feature_complete";
              return (
                <div key={groupKey}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12, padding: "8px 14px", background: isFeatureComplete ? "rgba(34,197,94,0.06)" : "var(--bg-surface)", borderRadius: 8, border: `1px solid ${isFeatureComplete ? "rgba(34,197,94,0.3)" : "var(--border-subtle)"}` }}>
                    <span style={{ fontWeight: 600, fontSize: 14, color: isFeatureComplete ? "#16a34a" : "var(--text-primary)", flex: 1, display: "flex", alignItems: "center", gap: 6 }}>
                      {isFeatureComplete && <GitMerge size={14} />}
                      {groupKey}
                      <span style={{ fontWeight: 400, color: "var(--text-muted)", fontSize: 13 }}>({groupItems.length})</span>
                    </span>
                    {canReviewGroup && (
                      <>
                        <Button variant="primary" onClick={() => handleAcceptGroup(groupItems)} leftIcon={<Check size={13} />} style={{ height: 28, padding: "0 10px", fontSize: 12 }}>
                          {zh ? "全部接受" : "Accept Group"}
                        </Button>
                        <Button variant="secondary" onClick={() => handleRejectGroup(groupItems)} leftIcon={<X size={13} />} style={{ height: 28, padding: "0 10px", fontSize: 12 }}>
                          {zh ? "全部拒絕" : "Reject Group"}
                        </Button>
                      </>
                    )}
                  </div>
                  <div style={{ display: "grid", gap: 12 }}>
                    {groupItems.map((item) => (
                      <ReviewCard key={item.id} wsId={wsId} item={item} canReview={item.can_review} onAccept={handleAccept} onReject={handleReject} onApplySplit={handleApplySplit} zh={zh} />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{ display: "grid", gap: 16 }}>
            {filteredItems.map((item) => (
              <ReviewCard key={item.id} wsId={wsId} item={item} canReview={item.can_review} onAccept={handleAccept} onReject={handleReject} onApplySplit={handleApplySplit} zh={zh} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
