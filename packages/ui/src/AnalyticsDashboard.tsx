import { useEffect, useMemo, useState, type ReactNode } from "react";
import { AlertTriangle, BarChart3, Network, Route, ShieldCheck } from "lucide-react";
import { workspaces, type TokenEfficiency, type WorkspaceAnalytics } from "./api";
import { useTranslation } from "react-i18next";

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function TinyLineChart({ points }: { points: Array<{ date: string; count: number }> }) {
  const { t } = useTranslation();
  const { polyline, max } = useMemo(() => {
    if (!points.length) return { polyline: "", max: 0 };
    const maxCount = Math.max(...points.map((point) => point.count), 1);
    const coords = points.map((point, index) => {
      const x = (index / Math.max(points.length - 1, 1)) * 100;
      const y = 100 - (point.count / maxCount) * 100;
      return `${x},${y}`;
    });
    return { polyline: coords.join(" "), max: maxCount };
  }, [points]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" style={{ width: "100%", height: 180, overflow: "visible" }}>
        <defs>
          <linearGradient id="analyticsLine" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0%" stopColor="var(--color-primary)" />
            <stop offset="100%" stopColor="#34d399" />
          </linearGradient>
        </defs>
        <polyline
          fill="none"
          stroke="url(#analyticsLine)"
          strokeWidth="2.5"
          vectorEffect="non-scaling-stroke"
          points={polyline}
        />
      </svg>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--text-muted)" }}>
        <span>{points[0]?.date ?? ""}</span>
        <span>{t('analytics.peak')} {max}</span>
        <span>{points[points.length - 1]?.date ?? ""}</span>
      </div>
    </div>
  );
}

function MetricCard({ icon, label, value, tone = "default" }: { icon: ReactNode; label: string; value: string; tone?: "default" | "warning" }) {
  return (
    <div style={{
      background: tone === "warning" ? "color-mix(in srgb, var(--color-warning) 10%, var(--bg-surface))" : "var(--bg-surface)",
      border: `1px solid ${tone === "warning" ? "var(--color-warning)" : "var(--border-default)"}`,
      borderRadius: 16,
      padding: 18,
      display: "flex",
      flexDirection: "column",
      gap: 10,
      minHeight: 120,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-muted)", fontSize: 13 }}>
        {icon}
        <span>{label}</span>
      </div>
      <div style={{ fontSize: 28, fontWeight: 700 }}>{value}</div>
    </div>
  );
}

export default function AnalyticsDashboard({ wsId, onOpenHealthManager }: { wsId: string; onOpenHealthManager?: () => void }) {
  const { t } = useTranslation();
  const [data, setData] = useState<WorkspaceAnalytics | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [tokenEfficiency, setTokenEfficiency] = useState<TokenEfficiency | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    workspaces.analytics(wsId)
      .then((result) => {
        if (!active) return;
        setData(result);
      })
      .catch((e) => {
        if (!active) return;
        setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    workspaces.tokenEfficiency(wsId).then(setTokenEfficiency).catch(() => {});
    return () => {
      active = false;
    };
  }, [wsId]);

  const warningText = useMemo(() => {
    if (!data) return "";
    if (data.kb_type === "evergreen" && data.orphan_node_count > 0) {
      return `${data.orphan_node_count} ${t('analytics.warningOrphan')}`;
    }
    const neverTraversedRatio = data.kb_type_metrics.never_traversed_ratio ?? 0;
    if (data.kb_type !== "evergreen" && neverTraversedRatio > 0.3) {
      return t('analytics.warningTraversed');
    }
    return "";
  }, [data, t]);

  if (loading) {
    return <div style={{ color: "var(--text-muted)" }}>{t('analytics.loading')}</div>;
  }

  if (error) {
    return <div style={{ color: "var(--color-error)" }}>{error}</div>;
  }

  if (!data) {
    return <div style={{ color: "var(--text-muted)" }}>{t('analytics.noData')}</div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {warningText && (
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "14px 16px",
          borderRadius: 14,
          border: "1px solid var(--color-warning)",
          background: "color-mix(in srgb, var(--color-warning) 10%, var(--bg-surface))",
          color: "var(--text-primary)",
        }}>
          <AlertTriangle size={18} />
          <span>{warningText}</span>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 14 }}>
        <MetricCard icon={<Network size={16} />} label={t('analytics.totalNodes')} value={String(data.total_nodes)} />
        <MetricCard icon={<Route size={16} />} label={t('analytics.activeEdges')} value={String(data.active_edges)} />
        <MetricCard icon={<AlertTriangle size={16} />} label={t('analytics.orphanNodes')} value={String(data.orphan_node_count)} tone={data.orphan_node_count > 0 ? "warning" : "default"} />
        <MetricCard icon={<ShieldCheck size={16} />} label={t('analytics.avgTrustScore')} value={formatPercent(data.avg_trust_score)} />
      </div>

      {onOpenHealthManager && (
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <button className="btn-secondary" onClick={onOpenHealthManager}>{t('analytics.manageHealth')}</button>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 0.9fr", gap: 16 }}>
        <section style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 16, padding: 18 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12, fontWeight: 600 }}>
            <BarChart3 size={17} /> {t('analytics.traversalTrend')}
          </div>
          <TinyLineChart points={data.traversal_trend} />
          <div style={{ marginTop: 12, fontSize: 13, color: "var(--text-muted)" }}>
            {t('analytics.monthlyTraversals')}: {data.monthly_traversal_count}
          </div>
        </section>

        <section style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 16, padding: 18, display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ fontWeight: 600 }}>{t('analytics.topNodes')}</div>
          {data.top_nodes.map((node) => (
            <div key={node.id} style={{ display: "flex", justifyContent: "space-between", gap: 12, fontSize: 13 }}>
              <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{node.title || node.id}</div>
              <div style={{ color: "var(--text-muted)" }}>{node.traversal_count}</div>
            </div>
          ))}
          {!data.top_nodes.length && <div style={{ color: "var(--text-muted)", fontSize: 13 }}>{t('analytics.noData')}</div>}
        </section>
      </div>

      <section style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 16, padding: 18 }}>
        <div style={{ fontWeight: 600, marginBottom: 12 }}>{t('analytics.kbTypeMetrics')}</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
          {Object.entries(data.kb_type_metrics).map(([key, value]) => (
            <div key={key} style={{ border: "1px solid var(--border-subtle)", borderRadius: 12, padding: 14 }}>
              <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8 }}>{t(`analytics.metrics.${key}`, { defaultValue: key })}</div>
              <div style={{ fontSize: 20, fontWeight: 700 }}>
                {key.includes("ratio") ? formatPercent(value) : Number(value).toFixed(key.includes("avg_days") ? 1 : 2).replace(".00", "")}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 16, padding: 18 }}>
        <div style={{ fontWeight: 600, marginBottom: 12 }}>{t('analytics.tokenEfficiency')}</div>
        {!tokenEfficiency || tokenEfficiency.monthly_query_count === 0 ? (
          <div style={{ color: "var(--text-muted)", fontSize: 13 }}>{t('analytics.noMcpData')}</div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 12 }}>
            <div style={{ border: "1px solid var(--border-subtle)", borderRadius: 12, padding: 14 }}>
              <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8 }}>{t('analytics.avgTokensPerQuery')}</div>
              <div style={{ fontSize: 20, fontWeight: 700 }}>{tokenEfficiency.avg_tokens_per_query}</div>
            </div>
            <div style={{ border: "1px solid var(--border-subtle)", borderRadius: 12, padding: 14 }}>
              <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8 }}>{t('analytics.fullDocTokens')}</div>
              <div style={{ fontSize: 20, fontWeight: 700 }}>{tokenEfficiency.estimated_full_doc_tokens}</div>
            </div>
            <div style={{ border: "1px solid var(--border-subtle)", borderRadius: 12, padding: 14 }}>
              <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8 }}>{t('analytics.savingsRatio')}</div>
              <div style={{ fontSize: 20, fontWeight: 700 }}>{formatPercent(tokenEfficiency.savings_ratio)}</div>
            </div>
            <div style={{ border: "1px solid var(--border-subtle)", borderRadius: 12, padding: 14 }}>
              <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8 }}>{t('analytics.monthlyMcpQueries')}</div>
              <div style={{ fontSize: 20, fontWeight: 700 }}>{tokenEfficiency.monthly_query_count}</div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
