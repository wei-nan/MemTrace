import type { DiffSummary } from "../api";

function renderScalar(value: unknown) {
  if (value === null || value === undefined || value === "") return <em style={{ opacity: 0.6 }}>empty</em>;
  if (Array.isArray(value)) return value.join(", ");
  return String(value);
}

export default function DiffPreviewModal({
  diff,
  title,
  onCancel,
  onConfirm,
  confirmLabel = "Confirm",
}: {
  diff: DiffSummary;
  title: string;
  onCancel: () => void;
  onConfirm: () => void;
  confirmLabel?: string;
}) {
  return (
    <div
      style={{ position: "fixed", inset: 0, background: "var(--bg-overlay)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 5000 }}
      onMouseDown={(e) => e.target === e.currentTarget && onCancel()}
    >
      <div style={{ width: "min(880px, 94vw)", maxHeight: "88vh", overflow: "auto", background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 16, padding: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
          <div>
            <h3 style={{ margin: 0 }}>{title}</h3>
            <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
              {diff.change_type} · {diff.field_count} changed fields
            </div>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {Object.entries(diff.fields).map(([field, entry]) => (
            <div key={field} style={{ border: "1px solid var(--border-default)", borderRadius: 12, padding: 14, background: "var(--bg-base)" }}>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>{field}</div>
              {entry.type === "scalar" && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, fontSize: 13 }}>
                  <div><div style={{ opacity: 0.6, marginBottom: 4 }}>Before</div>{renderScalar(entry.before)}</div>
                  <div><div style={{ opacity: 0.6, marginBottom: 4 }}>After</div>{renderScalar(entry.after)}</div>
                </div>
              )}
              {entry.type === "set" && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, fontSize: 13 }}>
                  <div>
                    <div style={{ opacity: 0.6, marginBottom: 4 }}>Added</div>
                    <div>{entry.added?.length ? entry.added.map((tag) => `#${tag}`).join(", ") : <em style={{ opacity: 0.6 }}>none</em>}</div>
                  </div>
                  <div>
                    <div style={{ opacity: 0.6, marginBottom: 4 }}>Removed</div>
                    <div>{entry.removed?.length ? entry.removed.map((tag) => `#${tag}`).join(", ") : <em style={{ opacity: 0.6 }}>none</em>}</div>
                  </div>
                </div>
              )}
              {entry.type === "text" && (
                <pre style={{ margin: 0, fontSize: 12, overflowX: "auto", whiteSpace: "pre-wrap", lineHeight: 1.5 }}>
                  {entry.line_diff?.map((line, index) => (
                    <div
                      key={`${field}-${index}`}
                      style={{
                        color:
                          line.op === "add"
                            ? "var(--color-success)"
                            : line.op === "remove"
                              ? "var(--color-error)"
                              : "var(--text-secondary)",
                      }}
                    >
                      {line.op === "add" ? "+" : line.op === "remove" ? "-" : " "} {line.text || " "}
                    </div>
                  ))}
                </pre>
              )}
            </div>
          ))}
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, marginTop: 20 }}>
          <button className="btn-secondary" onClick={onCancel}>Cancel</button>
          <button className="btn-primary" onClick={onConfirm}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}

