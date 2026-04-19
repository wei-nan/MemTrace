import { useEffect, useMemo, useState } from "react";
import { Bot, Check, Clock, Filter, RefreshCw, User, X } from "lucide-react";
import { review, type ReviewItem } from "./api";
import { useModal } from "./components/ModalContext";

function DiffSummaryBlock({ item }: { item: ReviewItem }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 12 }}>
      {Object.entries(item.diff_summary.fields).map(([field, entry]) => (
        <div key={field} style={{ background: "var(--bg-base)", border: "1px solid var(--border-default)", borderRadius: 10, padding: 10 }}>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>{field}</div>
          {entry.type === "scalar" && <div style={{ fontSize: 13 }}>{String(entry.before ?? "empty")} → {String(entry.after ?? "empty")}</div>}
          {entry.type === "set" && (
            <div style={{ fontSize: 13 }}>
              <div>Added: {entry.added?.length ? entry.added.join(", ") : "none"}</div>
              <div>Removed: {entry.removed?.length ? entry.removed.join(", ") : "none"}</div>
            </div>
          )}
          {entry.type === "text" && (
            <pre style={{ margin: 0, fontSize: 12, whiteSpace: "pre-wrap" }}>
              {entry.line_diff?.slice(0, 12).map((line) => `${line.op === "add" ? "+" : line.op === "remove" ? "-" : " "} ${line.text}`).join("\n")}
            </pre>
          )}
        </div>
      ))}
    </div>
  );
}

function ReviewCard({
  item,
  canReview,
  onAccept,
  onReject,
}: {
  item: ReviewItem;
  canReview: boolean;
  onAccept: (id: string) => void;
  onReject: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const proposerLabel = item.proposer_type === "ai" ? item.proposer_id?.replace(/^ai:/, "") ?? "AI" : item.proposer_id ?? "User";

  return (
    <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 16, padding: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
            <span className="tag tag-active">{item.change_type}</span>
            <span className="tag">{item.proposer_type === "ai" ? <Bot size={12} /> : <User size={12} />} {proposerLabel}</span>
            {item.ai_review && <span className="tag">{item.ai_review.decision} · {(item.ai_review.confidence * 100).toFixed(0)}%</span>}
          </div>
          <div style={{ fontSize: 18, fontWeight: 700 }}>{String(item.node_data.title_en ?? item.node_data.title_zh ?? "Untitled change")}</div>
          <div style={{ color: "var(--text-muted)", fontSize: 13, marginTop: 4 }}>
            {item.source_info || "Review proposal"} · {new Date(item.created_at).toLocaleString()}
          </div>
          {item.ai_review?.reasoning && (
            <blockquote style={{ margin: "10px 0 0", padding: "10px 12px", borderLeft: "3px solid var(--color-primary)", background: "var(--bg-base)", color: "var(--text-secondary)" }}>
              {item.ai_review.reasoning}
            </blockquote>
          )}
        </div>
      </div>

      <div style={{ display: "flex", gap: 10, marginTop: 12, flexWrap: "wrap" }}>
        <button className="btn-secondary" onClick={() => setExpanded((prev) => !prev)}>{expanded ? "Hide Diff" : "Show Diff"}</button>
        {canReview && <button className="btn-primary" onClick={() => onAccept(item.id)}><Check size={16} /> Accept</button>}
        {canReview && <button className="btn-secondary" onClick={() => onReject(item.id)}><X size={16} /> Reject</button>}
      </div>

      {expanded && <DiffSummaryBlock item={item} />}
    </div>
  );
}

export default function ReviewQueue({ wsId, onClose }: { wsId: string; onClose: () => void }) {
  const { confirm, toast } = useModal();
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [changeType, setChangeType] = useState<"all" | "create" | "update" | "delete">("all");
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
    () => items.filter((item) => (changeType === "all" || item.change_type === changeType) && (proposerType === "all" || item.proposer_type === proposerType)),
    [items, changeType, proposerType],
  );
  const canReviewAny = filteredItems.some((item) => item.can_review);

  const handleAccept = async (id: string) => {
    try {
      await review.accept(id);
      setItems((prev) => prev.filter((item) => item.id !== id));
      toast({ message: "Review accepted", variant: "success" });
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    }
  };

  const handleReject = async (id: string) => {
    const ok = await confirm({ title: "Reject change", message: "Reject this pending change?", variant: "danger", confirmLabel: "Reject" });
    if (!ok) return;
    try {
      await review.reject(id);
      setItems((prev) => prev.filter((item) => item.id !== id));
      toast({ message: "Review rejected", variant: "success" });
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    }
  };

  const handleAcceptAll = async () => {
    const ok = await confirm({ title: "Accept all", message: `Accept all ${filteredItems.length} visible review items?`, variant: "warning", confirmLabel: "Accept All" });
    if (!ok) return;
    try {
      await review.acceptAll(wsId);
      await loadItems();
      toast({ message: "All pending reviews processed", variant: "success" });
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
      <div style={{ padding: "24px 32px", borderBottom: "1px solid var(--border-default)", background: "var(--bg-surface)", display: "flex", justifyContent: "space-between", gap: 16, alignItems: "center" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Clock size={20} />
            <h2 style={{ margin: 0 }}>Review Queue</h2>
            <span className="tag tag-active">{filteredItems.length}</span>
          </div>
          <div style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 6 }}>Change diff, proposer tracking, and hybrid review signals in one place.</div>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
          {canReviewAny && <button className="btn-secondary" onClick={handleRunAIPrescreen}><Bot size={16} /> AI Prescreen</button>}
          {canReviewAny && <button className="btn-primary" onClick={handleAcceptAll}><Check size={16} /> Accept All</button>}
          <button className="btn-secondary" onClick={loadItems}><RefreshCw size={16} /> Refresh</button>
          <button className="btn-secondary" onClick={onClose}>Back to Graph</button>
        </div>
      </div>

      <div style={{ padding: "16px 32px", borderBottom: "1px solid var(--border-subtle)", display: "flex", gap: 10, alignItems: "center", background: "var(--bg-surface)" }}>
        <Filter size={16} />
        <select className="mt-input" style={{ width: 150 }} value={changeType} onChange={(e) => setChangeType(e.target.value as typeof changeType)}>
          <option value="all">All changes</option>
          <option value="create">Create</option>
          <option value="update">Update</option>
          <option value="delete">Delete</option>
        </select>
        <select className="mt-input" style={{ width: 150 }} value={proposerType} onChange={(e) => setProposerType(e.target.value as typeof proposerType)}>
          <option value="all">All proposers</option>
          <option value="human">Human</option>
          <option value="ai">AI</option>
        </select>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: 24 }}>
        {loading ? (
          <div style={{ color: "var(--text-muted)" }}>Loading review queue...</div>
        ) : filteredItems.length === 0 ? (
          <div style={{ color: "var(--text-muted)" }}>No pending review items match the current filters.</div>
        ) : (
          <div style={{ display: "grid", gap: 16 }}>
            {filteredItems.map((item) => (
              <ReviewCard key={item.id} item={item} canReview={item.can_review} onAccept={handleAccept} onReject={handleReject} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
