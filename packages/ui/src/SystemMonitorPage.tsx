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
  whiteSpace: 'nowrap',
};

const thRight: CSSProperties = { ...thStyle, textAlign: 'right' };

// ─── Tab 1: Scheduler Heartbeats ─────────────────────────────────────────────

function CategoryBadge({ meta, zh }: { meta: JobMeta | undefined; zh: boolean }) {
  if (!meta) return <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>—</span>;
  return (
    <span style={{
      display: 'inline-block', padding: '1px 7px', borderRadius: 10,
      fontSize: 10, fontWeight: 700,
      background: `${meta.color}22`, color: meta.color,
      border: `1px solid ${meta.color}44`,
    }}>
      {zh ? meta.categoryZh : meta.category}
    </span>
  );
}

function HeartbeatsTab({ zh }: { zh: boolean }) {
  const [data, setData] = useState<SystemSchedulerHeartbeat[]>([]);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    setLoading(true);
    system.monitorHeartbeats().then(r => { setData(r.heartbeats); setLoading(false); });
  }, [tick]);

  if (loading) return <Spinner />;

  // Merge heartbeat data with full known-jobs list
  const hbMap = new Map(data.map(hb => [hb.job_name, hb]));
  const rows = KNOWN_JOBS.map(name => ({ name, hb: hbMap.get(name) ?? null, meta: JOB_META[name] }));

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
        <button className="btn-secondary" style={{ display: 'flex', gap: 6, alignItems: 'center', fontSize: 12 }}
          onClick={() => setTick(t => t + 1)}>
          <RefreshCw size={12} /> {zh ? '重新整理' : 'Refresh'}
        </button>
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse', tableLayout: 'fixed' }}>
        <colgroup>
          <col style={{ width: 180 }} />
          <col style={{ width: 72 }} />
          <col style={{ width: 48 }} />
          <col style={{ width: 90 }} />
          <col style={{ width: 155 }} />
          <col style={{ width: 155 }} />
          <col style={{ width: 65 }} />
          <col style={{ width: 58 }} />
          <col style={{ width: 58 }} />
          <col />
        </colgroup>
        <thead>
          <tr>
            <th style={thStyle}>{zh ? '作業名稱' : 'Job'}</th>
            <th style={thStyle}>{zh ? '分類' : 'Category'}</th>
            <th style={thRight}>{zh ? '間隔' : 'Interval'}</th>
            <th style={thStyle}>Status</th>
            <th style={thStyle}>{zh ? '上次執行' : 'Last Run'}</th>
            <th style={thStyle}>{zh ? '上次成功' : 'Last Success'}</th>
            <th style={thRight}>{zh ? '耗時' : 'Duration'}</th>
            <th style={thRight}>{zh ? '執行' : 'Runs'}</th>
            <th style={thRight}>{zh ? '失敗' : 'Fails'}</th>
            <th style={thStyle}>{zh ? '錯誤' : 'Error'}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ name, hb, meta }) => (
            <tr key={name} style={{ opacity: hb ? 1 : 0.6 }}>
              <td style={{ ...tdStyle, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                <code style={{ fontSize: 11 }}>{name}</code>
              </td>
              <td style={tdStyle}><CategoryBadge meta={meta} zh={zh} /></td>
              <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--text-muted)', fontSize: 11 }}>
                {meta?.interval ?? '—'}
              </td>
              <td style={tdStyle}>
                {hb
                  ? <StatusBadge status={hb.status} />
                  : <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                      {meta?.observable === false ? (zh ? '不追蹤' : 'untracked') : (zh ? '等待中' : 'pending')}
                    </span>
                }
              </td>
              <td style={{ ...tdStyle, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{fmtDate(hb?.last_run_at ?? null)}</td>
              <td style={{ ...tdStyle, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{fmtDate(hb?.last_success_at ?? null)}</td>
              <td style={{ ...tdStyle, textAlign: 'right' }}>{fmtDuration(hb?.duration_ms ?? null)}</td>
              <td style={{ ...tdStyle, textAlign: 'right' }}>{hb?.run_count ?? '—'}</td>
              <td style={{ ...tdStyle, textAlign: 'right', color: (hb?.failure_count ?? 0) > 0 ? 'var(--color-error)' : undefined }}>
                {hb?.failure_count ?? '—'}
              </td>
              <td style={{ ...tdStyle, color: 'var(--color-error)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {hb?.last_error ?? ''}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Job metadata (shared by Heartbeats + JobRuns tabs) ──────────────────────

const KNOWN_JOBS = [
  'ai_review_for_item',
  'ai_review_prescreen',
  'audit_reviewers',
  'audit_writer',
  'backup',
  'cleanup',
  'conductor_dispatch',
  'decay',
  'deletion_notify',
  'embedding_consistency',
  'ephemeral_decay',
  'kb_health',
  'path_reinforcement',
  'process_node_events',
  'retry_embeddings',
  'review_sla',
  'safety_review_queue',
  'safety_sweep',
  'stale_ingest',
];

interface JobMeta { categoryZh: string; category: string; color: string; interval: string; observable: boolean; }
const JOB_META: Record<string, JobMeta> = {
  process_node_events: { categoryZh: '知識庫', category: 'KB',     color: '#3b82f6', interval: '10s',  observable: true  },
  audit_writer:        { categoryZh: '系統',   category: 'System', color: '#64748b', interval: '5s',   observable: true  },
  safety_review_queue: { categoryZh: 'AI',     category: 'AI',     color: '#a855f7', interval: '30s',  observable: true  },
  retry_embeddings:    { categoryZh: '知識庫', category: 'KB',     color: '#3b82f6', interval: '1m',   observable: true  },
  stale_ingest:        { categoryZh: '知識庫', category: 'KB',     color: '#3b82f6', interval: '5m',   observable: true  },
  ephemeral_decay:     { categoryZh: '知識庫', category: 'KB',     color: '#3b82f6', interval: '1h',   observable: true  },
  backup:              { categoryZh: '系統',   category: 'System', color: '#64748b', interval: '1h',   observable: true  },
  decay:               { categoryZh: '知識庫', category: 'KB',     color: '#3b82f6', interval: '24h',  observable: true  },
  cleanup:             { categoryZh: '系統',   category: 'System', color: '#64748b', interval: '24h',  observable: true  },
  deletion_notify:     { categoryZh: '系統',   category: 'System', color: '#64748b', interval: '24h',  observable: true  },
  path_reinforcement:  { categoryZh: '知識庫', category: 'KB',     color: '#3b82f6', interval: '24h',  observable: true  },
  audit_reviewers:     { categoryZh: 'AI',     category: 'AI',     color: '#a855f7', interval: '24h',  observable: false },
  safety_sweep:        { categoryZh: 'AI',     category: 'AI',     color: '#a855f7', interval: '24h',  observable: false },
  conductor_dispatch:  { categoryZh: '系統',   category: 'System', color: '#64748b', interval: '—',    observable: true  },
};

function JobRunsTab({ zh }: { zh: boolean }) {
  const [data, setData] = useState<SystemJobRun[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState('');
  const [filterJob, setFilterJob] = useState('');
  const [filterReviewer, setFilterReviewer] = useState('');
  const [offset, setOffset] = useState(0);
  const [tick, setTick] = useState(0);
  const limit = 100;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    system.monitorJobRuns({
      job_name: filterJob || undefined,
      status: filterStatus || undefined,
      reviewer: filterReviewer.trim() || undefined,
      limit,
      offset,
    }).then(r => {
      if (!cancelled) { setData(r.runs); setTotal(r.total); setLoading(false); }
    });
    return () => { cancelled = true; };
  }, [filterStatus, filterJob, filterReviewer, offset, tick]);

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
        <input
          className="mt-input"
          style={{ fontSize: 12, width: 180 }}
          value={filterReviewer}
          onChange={e => { setFilterReviewer(e.target.value); setOffset(0); }}
          placeholder="Reviewer"
        />
        <div style={{ flex: 1 }} />
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{total} {zh ? '筆' : 'rows'}</span>
        <button className="btn-secondary" style={{ display: 'flex', gap: 6, alignItems: 'center', fontSize: 12 }}
          onClick={() => setTick(t => t + 1)}>
          <RefreshCw size={12} /> {zh ? '重新整理' : 'Refresh'}
        </button>
      </div>

      {loading ? <Spinner /> : (
        <table style={{ width: '100%', borderCollapse: 'collapse', tableLayout: 'fixed' }}>
          <colgroup>
            <col style={{ width: 190 }} />
            <col style={{ width: 140 }} />
            <col style={{ width: 130 }} />
            <col style={{ width: 90 }} />
            <col style={{ width: 90 }} />
            <col style={{ width: 165 }} />
            <col style={{ width: 72 }} />
            <col style={{ width: 60 }} />
            <col />
          </colgroup>
          <thead>
            <tr>
              <th style={thStyle}>{zh ? '作業' : 'Job'}</th>
              <th style={thStyle}>{zh ? 'AI 機制' : 'AI Mechanism'}</th>
              <th style={thStyle}>{zh ? '工作區' : 'Workspace'}</th>
              <th style={thStyle}>Status</th>
              <th style={thStyle}>{zh ? '觸發' : 'Trigger'}</th>
              <th style={thStyle}>{zh ? '開始時間' : 'Started'}</th>
              <th style={thRight}>{zh ? '耗時' : 'Duration'}</th>
              <th style={thRight}>{zh ? '處理' : 'Items'}</th>
              <th style={thStyle}>{zh ? '錯誤' : 'Error'}</th>
            </tr>
          </thead>
          <tbody>
            {data.map(r => {
              const s = (r.summary ?? {}) as Record<string, any>;
              let aiLabel = '—';
              if (r.job_name === 'safety_review_queue') {
                if (s.ai_provider && s.ai_model) aiLabel = `${s.ai_provider} / ${s.ai_model}`;
                else if (s.ai_provider === 'unavailable') aiLabel = zh ? '無可用模型' : 'unavailable';
                else aiLabel = 'LLM';
              } else if (r.job_name === 'audit_reviewers') {
                aiLabel = zh ? '向量相似度' : 'Vector similarity';
              } else if (r.job_name === 'safety_sweep') {
                aiLabel = zh ? '規則式' : 'Rule-based';
              }
              return (
                <tr key={r.id}>
                  <td style={{ ...tdStyle, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    <code style={{ fontSize: 11 }}>{r.job_name}</code>
                  </td>
                  <td style={{ ...tdStyle, fontSize: 11, color: aiLabel === '—' ? 'var(--text-muted)' : 'var(--text-secondary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {aiLabel}
                  </td>
                  <td style={{ ...tdStyle, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {r.workspace_name ?? r.workspace_id ?? '—'}
                  </td>
                  <td style={tdStyle}><StatusBadge status={r.status} /></td>
                  <td style={{ ...tdStyle, color: 'var(--text-muted)' }}>{r.trigger}</td>
                  <td style={{ ...tdStyle, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{fmtDate(r.started_at)}</td>
                  <td style={{ ...tdStyle, textAlign: 'right' }}>{fmtDuration(r.duration_ms)}</td>
                  <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--text-muted)' }}>
                    {r.processed_count != null && r.processed_count > 0 ? r.processed_count : '—'}
                  </td>
                  <td style={{ ...tdStyle, color: 'var(--color-error)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {r.error ?? ''}
                  </td>
                </tr>
              );
            })}
            {data.length === 0 && (
              <tr><td colSpan={9} style={{ ...tdStyle, textAlign: 'center', color: 'var(--text-muted)', padding: 32 }}>
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
        <table style={{ width: '100%', borderCollapse: 'collapse', tableLayout: 'fixed' }}>
          <colgroup>
            <col style={{ width: 160 }} />
            <col style={{ width: 150 }} />
            <col />
            <col style={{ width: 65 }} />
            <col style={{ width: 90 }} />
            <col style={{ width: 90 }} />
            <col style={{ width: 165 }} />
          </colgroup>
          <thead>
            <tr>
              <th style={thStyle}>{zh ? '工具' : 'Tool'}</th>
              <th style={thStyle}>{zh ? '工作區' : 'Workspace'}</th>
              <th style={thStyle}>{zh ? '查詢' : 'Query'}</th>
              <th style={thRight}>{zh ? '節點數' : 'Nodes'}</th>
              <th style={thRight}>{zh ? '估算 Token' : 'Est. Tokens'}</th>
              <th style={thStyle}>{zh ? '供應商' : 'Provider'}</th>
              <th style={thStyle}>{zh ? '時間' : 'Time'}</th>
            </tr>
          </thead>
          <tbody>
            {data.map(log => (
              <tr key={log.id}>
                <td style={{ ...tdStyle, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  <code style={{ fontSize: 11 }}>{log.tool_name}</code>
                </td>
                <td style={{ ...tdStyle, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {log.workspace_name ?? log.workspace_id}
                </td>
                <td style={{ ...tdStyle, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-muted)' }}>
                  {log.query_text ?? '—'}
                </td>
                <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--text-muted)' }}>
                  {log.result_node_count > 0 ? log.result_node_count : '—'}
                </td>
                <td style={{ ...tdStyle, textAlign: 'right' }}>
                  {log.estimated_tokens > 0 ? fmtTokens(log.estimated_tokens) : '—'}
                </td>
                <td style={{ ...tdStyle, color: 'var(--text-muted)' }}>{log.provider ?? '—'}</td>
                <td style={{ ...tdStyle, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{fmtDate(log.created_at)}</td>
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
