import { useState, useEffect, type CSSProperties } from 'react';
import { useTranslation } from 'react-i18next';
import { RefreshCw, CheckCircle2, Activity, Database, Zap } from 'lucide-react';
import { system } from './api';
import type {
  SystemSchedulerHeartbeat,
  SystemJobRun,
  SystemMcpLog,
  SystemAiUsage,
} from './api/system';

// ─── helpers ─────────────────────────────────────────────────────────────────

function fmtDate(s: string | null): string {
  if (!s) return '—';
  const d = new Date(s);
  return d.toLocaleString();
}

function fmtDuration(ms: number | null): string {
  if (ms == null) return '—';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

function fmtTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return String(n);
}

const STATUS_COLOR: Record<string, string> = {
  success: '#22c55e',
  running: '#f59e0b',
  failed: 'var(--color-error)',
  skipped: 'var(--text-muted)',
  unknown: 'var(--text-muted)',
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span style={{
      display: 'inline-block',
      padding: '2px 8px',
      borderRadius: 12,
      fontSize: 11,
      fontWeight: 600,
      background: STATUS_COLOR[status] ? `${STATUS_COLOR[status]}22` : 'transparent',
      color: STATUS_COLOR[status] ?? 'var(--text-muted)',
      border: `1px solid ${STATUS_COLOR[status] ?? 'var(--border-default)'}44`,
    }}>
      {status}
    </span>
  );
}

const tdStyle: CSSProperties = {
  padding: '8px 12px',
  borderBottom: '1px solid var(--border-subtle)',
  fontSize: 12,
  verticalAlign: 'middle',
};

const thStyle: CSSProperties = {
  ...tdStyle,
  fontWeight: 600,
  color: 'var(--text-muted)',
  background: 'var(--bg-elevated)',
  position: 'sticky',
  top: 0,
};

// ─── Tab 1: Scheduler Heartbeats ─────────────────────────────────────────────

function HeartbeatsTab({ zh }: { zh: boolean }) {
  const [data, setData] = useState<SystemSchedulerHeartbeat[]>([]);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    setLoading(true);
    system.monitorHeartbeats().then(r => { setData(r.heartbeats); setLoading(false); });
  }, [tick]);

  if (loading) return <Spinner />;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
        <button className="btn-secondary" style={{ display: 'flex', gap: 6, alignItems: 'center', fontSize: 12 }}
          onClick={() => setTick(t => t + 1)}>
          <RefreshCw size={12} /> {zh ? '重新整理' : 'Refresh'}
        </button>
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            {[
              zh ? '作業名稱' : 'Job', 'Status',
              zh ? '上次執行' : 'Last Run',
              zh ? '上次成功' : 'Last Success',
              zh ? '耗時' : 'Duration',
              zh ? '執行次數' : 'Runs',
              zh ? '失敗次數' : 'Fails',
              zh ? '錯誤' : 'Error',
            ].map(h => <th key={h} style={thStyle}>{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {data.map(hb => (
            <tr key={hb.job_name}>
              <td style={tdStyle}><code style={{ fontSize: 11 }}>{hb.job_name}</code></td>
              <td style={tdStyle}><StatusBadge status={hb.status} /></td>
              <td style={{ ...tdStyle, color: 'var(--text-muted)' }}>{fmtDate(hb.last_run_at)}</td>
              <td style={{ ...tdStyle, color: 'var(--text-muted)' }}>{fmtDate(hb.last_success_at)}</td>
              <td style={tdStyle}>{fmtDuration(hb.duration_ms)}</td>
              <td style={{ ...tdStyle, textAlign: 'right' }}>{hb.run_count}</td>
              <td style={{ ...tdStyle, textAlign: 'right', color: hb.failure_count > 0 ? 'var(--color-error)' : undefined }}>
                {hb.failure_count}
              </td>
              <td style={{ ...tdStyle, color: 'var(--color-error)', maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {hb.last_error ?? ''}
              </td>
            </tr>
          ))}
          {data.length === 0 && (
            <tr><td colSpan={8} style={{ ...tdStyle, textAlign: 'center', color: 'var(--text-muted)', padding: 32 }}>
              {zh ? '尚無紀錄' : 'No data'}
            </td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

// ─── Tab 2: Job Runs (global) ─────────────────────────────────────────────────

const KNOWN_JOBS = ['decay', 'embedding_consistency', 'kb_health', 'review_sla', 'conductor', 'backup'];

function JobRunsTab({ zh }: { zh: boolean }) {
  const [data, setData] = useState<SystemJobRun[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState('');
  const [filterJob, setFilterJob] = useState('');
  const [offset, setOffset] = useState(0);
  const [tick, setTick] = useState(0);
  const limit = 100;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    system.monitorJobRuns({
      job_name: filterJob || undefined,
      status: filterStatus || undefined,
      limit,
      offset,
    }).then(r => {
      if (!cancelled) { setData(r.runs); setTotal(r.total); setLoading(false); }
    });
    return () => { cancelled = true; };
  }, [filterStatus, filterJob, offset, tick]);

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <select className="mt-input" style={{ fontSize: 12 }}
          value={filterStatus} onChange={e => { setFilterStatus(e.target.value); setOffset(0); }}>
          <option value="">{zh ? '全部狀態' : 'All statuses'}</option>
          {['running', 'success', 'failed', 'skipped'].map(s =>
            <option key={s} value={s}>{s}</option>)}
        </select>
        <select className="mt-input" style={{ fontSize: 12 }}
          value={filterJob} onChange={e => { setFilterJob(e.target.value); setOffset(0); }}>
          <option value="">{zh ? '全部作業' : 'All jobs'}</option>
          {KNOWN_JOBS.map(j => <option key={j} value={j}>{j}</option>)}
        </select>
        <div style={{ flex: 1 }} />
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{total} {zh ? '筆' : 'rows'}</span>
        <button className="btn-secondary" style={{ display: 'flex', gap: 6, alignItems: 'center', fontSize: 12 }}
          onClick={() => setTick(t => t + 1)}>
          <RefreshCw size={12} /> {zh ? '重新整理' : 'Refresh'}
        </button>
      </div>

      {loading ? <Spinner /> : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {[
                zh ? '作業' : 'Job',
                zh ? '工作區' : 'Workspace',
                'Status',
                zh ? '觸發' : 'Trigger',
                zh ? '開始時間' : 'Started',
                zh ? '耗時' : 'Duration',
                zh ? '處理' : 'Processed',
                zh ? '錯誤' : 'Error',
              ].map(h => <th key={h} style={thStyle}>{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {data.map(r => (
              <tr key={r.id}>
                <td style={tdStyle}><code style={{ fontSize: 11 }}>{r.job_name}</code></td>
                <td style={{ ...tdStyle, color: 'var(--text-muted)', maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {r.workspace_name ?? r.workspace_id ?? '—'}
                </td>
                <td style={tdStyle}><StatusBadge status={r.status} /></td>
                <td style={{ ...tdStyle, color: 'var(--text-muted)' }}>{r.trigger}</td>
                <td style={{ ...tdStyle, color: 'var(--text-muted)' }}>{fmtDate(r.started_at)}</td>
                <td style={tdStyle}>{fmtDuration(r.duration_ms)}</td>
                <td style={{ ...tdStyle, textAlign: 'right' }}>{r.processed_count ?? '—'}</td>
                <td style={{ ...tdStyle, color: 'var(--color-error)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {r.error ?? ''}
                </td>
              </tr>
            ))}
            {data.length === 0 && (
              <tr><td colSpan={8} style={{ ...tdStyle, textAlign: 'center', color: 'var(--text-muted)', padding: 32 }}>
                {zh ? '尚無紀錄' : 'No data'}
              </td></tr>
            )}
          </tbody>
        </table>
      )}

      {total > limit && (
        <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 12 }}>
          <button className="btn-secondary" style={{ fontSize: 12 }} disabled={offset === 0}
            onClick={() => setOffset(o => Math.max(0, o - limit))}>
            {zh ? '上一頁' : 'Prev'}
          </button>
          <span style={{ fontSize: 12, color: 'var(--text-muted)', alignSelf: 'center' }}>
            {offset + 1}–{Math.min(offset + limit, total)} / {total}
          </span>
          <button className="btn-secondary" style={{ fontSize: 12 }} disabled={offset + limit >= total}
            onClick={() => setOffset(o => o + limit)}>
            {zh ? '下一頁' : 'Next'}
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Tab 3: MCP Query Logs ────────────────────────────────────────────────────

function McpLogsTab({ zh }: { zh: boolean }) {
  const [data, setData] = useState<SystemMcpLog[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [offset, setOffset] = useState(0);
  const [tick, setTick] = useState(0);
  const limit = 100;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    system.monitorMcpLogs({ limit, offset }).then(r => {
      if (!cancelled) { setData(r.logs); setTotal(r.total); setLoading(false); }
    });
    return () => { cancelled = true; };
  }, [offset, tick]);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginBottom: 12, alignItems: 'center' }}>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{total} {zh ? '筆' : 'rows'}</span>
        <button className="btn-secondary" style={{ display: 'flex', gap: 6, alignItems: 'center', fontSize: 12 }}
          onClick={() => setTick(t => t + 1)}>
          <RefreshCw size={12} /> {zh ? '重新整理' : 'Refresh'}
        </button>
      </div>

      {loading ? <Spinner /> : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {[
                zh ? '工具' : 'Tool',
                zh ? '工作區' : 'Workspace',
                zh ? '查詢' : 'Query',
                zh ? '節點數' : 'Nodes',
                zh ? '估算 Token' : 'Est. Tokens',
                zh ? '供應商' : 'Provider',
                zh ? '時間' : 'Time',
              ].map(h => <th key={h} style={thStyle}>{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {data.map(log => (
              <tr key={log.id}>
                <td style={tdStyle}><code style={{ fontSize: 11 }}>{log.tool_name}</code></td>
                <td style={{ ...tdStyle, color: 'var(--text-muted)', maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {log.workspace_name ?? log.workspace_id}
                </td>
                <td style={{ ...tdStyle, maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-muted)' }}>
                  {log.query_text ?? '—'}
                </td>
                <td style={{ ...tdStyle, textAlign: 'right' }}>{log.result_node_count}</td>
                <td style={{ ...tdStyle, textAlign: 'right' }}>{fmtTokens(log.estimated_tokens)}</td>
                <td style={{ ...tdStyle, color: 'var(--text-muted)' }}>{log.provider ?? '—'}</td>
                <td style={{ ...tdStyle, color: 'var(--text-muted)' }}>{fmtDate(log.created_at)}</td>
              </tr>
            ))}
            {data.length === 0 && (
              <tr><td colSpan={7} style={{ ...tdStyle, textAlign: 'center', color: 'var(--text-muted)', padding: 32 }}>
                {zh ? '尚無紀錄' : 'No data'}
              </td></tr>
            )}
          </tbody>
        </table>
      )}

      {total > limit && (
        <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 12 }}>
          <button className="btn-secondary" style={{ fontSize: 12 }} disabled={offset === 0}
            onClick={() => setOffset(o => Math.max(0, o - limit))}>
            {zh ? '上一頁' : 'Prev'}
          </button>
          <span style={{ fontSize: 12, color: 'var(--text-muted)', alignSelf: 'center' }}>
            {offset + 1}–{Math.min(offset + limit, total)} / {total}
          </span>
          <button className="btn-secondary" style={{ fontSize: 12 }} disabled={offset + limit >= total}
            onClick={() => setOffset(o => o + limit)}>
            {zh ? '下一頁' : 'Next'}
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Tab 4: AI Usage Summary ──────────────────────────────────────────────────

function AiUsageTab({ zh }: { zh: boolean }) {
  const [data, setData] = useState<SystemAiUsage[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    system.monitorAiUsage().then(r => { setData(r.usage); setLoading(false); });
  }, []);

  // Group by month for summary row
  const byMonth: Record<string, number> = {};
  for (const row of data) {
    byMonth[row.year_month] = (byMonth[row.year_month] ?? 0) + row.token_count;
  }
  const months = Object.keys(byMonth).sort().reverse().slice(0, 6);

  if (loading) return <Spinner />;

  return (
    <div>
      {/* Monthly totals */}
      {months.length > 0 && (
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 24 }}>
          {months.map(m => (
            <div key={m} style={{
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-default)',
              borderRadius: 8,
              padding: '10px 16px',
              minWidth: 120,
            }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>{m}</div>
              <div style={{ fontSize: 18, fontWeight: 700 }}>{fmtTokens(byMonth[m])}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>tokens</div>
            </div>
          ))}
        </div>
      )}

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            {[
              zh ? '月份' : 'Month',
              zh ? '工作區' : 'Workspace',
              zh ? 'Token 數' : 'Tokens',
              zh ? '最後更新' : 'Last Updated',
            ].map(h => <th key={h} style={thStyle}>{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i}>
              <td style={tdStyle}>{row.year_month}</td>
              <td style={{ ...tdStyle, color: 'var(--text-muted)' }}>
                {row.workspace_name ?? row.workspace_id}
              </td>
              <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 600 }}>
                {fmtTokens(row.token_count)}
              </td>
              <td style={{ ...tdStyle, color: 'var(--text-muted)' }}>{fmtDate(row.last_updated)}</td>
            </tr>
          ))}
          {data.length === 0 && (
            <tr><td colSpan={4} style={{ ...tdStyle, textAlign: 'center', color: 'var(--text-muted)', padding: 32 }}>
              {zh ? '尚無用量紀錄' : 'No usage data'}
            </td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

// ─── Shared ───────────────────────────────────────────────────────────────────

function Spinner() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
      <RefreshCw size={20} className="animate-spin" color="var(--text-muted)" />
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

type Tab = 'scheduler' | 'job_runs' | 'mcp_logs' | 'ai_usage';

const TABS: { id: Tab; zh: string; en: string; icon: typeof Activity }[] = [
  { id: 'scheduler', zh: '排程器', en: 'Scheduler', icon: CheckCircle2 },
  { id: 'job_runs',  zh: '作業紀錄', en: 'Job Runs', icon: Activity },
  { id: 'mcp_logs', zh: 'MCP 查詢', en: 'MCP Queries', icon: Zap },
  { id: 'ai_usage', zh: '用量統計', en: 'AI Usage', icon: Database },
];

export default function SystemMonitorPage() {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const [tab, setTab] = useState<Tab>('scheduler');

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '32px 24px' }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <Activity size={20} />
          <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>
            {zh ? '系統監控' : 'System Monitor'}
          </h2>
        </div>
        <p style={{ margin: 0, fontSize: 13, color: 'var(--text-muted)' }}>
          {zh
            ? '跨工作區的 AI 作業、MCP 查詢與用量統計（系統管理員限定）'
            : 'Cross-workspace AI job runs, MCP queries and usage stats — admin only'}
        </p>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '1px solid var(--border-default)', paddingBottom: 0 }}>
        {TABS.map(t => {
          const Icon = t.icon;
          const active = tab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '8px 14px',
                border: 'none',
                borderBottom: active ? '2px solid var(--color-primary)' : '2px solid transparent',
                background: 'transparent',
                cursor: 'pointer',
                fontSize: 13,
                fontWeight: active ? 600 : 400,
                color: active ? 'var(--color-primary)' : 'var(--text-muted)',
                marginBottom: -1,
              }}
            >
              <Icon size={14} />
              {zh ? t.zh : t.en}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <div style={{ overflowX: 'auto' }}>
        {tab === 'scheduler' && <HeartbeatsTab zh={zh} />}
        {tab === 'job_runs'  && <JobRunsTab zh={zh} />}
        {tab === 'mcp_logs'  && <McpLogsTab zh={zh} />}
        {tab === 'ai_usage'  && <AiUsageTab zh={zh} />}
      </div>
    </div>
  );
}
