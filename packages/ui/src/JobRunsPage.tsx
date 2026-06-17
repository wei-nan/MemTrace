import { useEffect, useState, type ReactNode, type CSSProperties } from 'react';
import { Activity, CheckCircle2, XCircle, SkipForward, Clock, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { workspaces, type JobRun } from './api';

const STATUS_COLOR: Record<string, string> = {
  success: '#22c55e',
  failed: 'var(--color-error)',
  running: '#f59e0b',
  skipped: 'var(--text-muted)',
};

function MetricCard({ icon, label, value, warn }: { icon: ReactNode; label: string; value: string; warn?: boolean }) {
  return (
    <div style={{
      background: warn ? 'color-mix(in srgb, var(--color-warning) 10%, var(--bg-surface))' : 'var(--bg-surface)',
      border: `1px solid ${warn ? 'var(--color-warning)' : 'var(--border-default)'}`,
      borderRadius: 10, padding: 18,
      display: 'flex', flexDirection: 'column', gap: 10, minHeight: 100,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-muted)', fontSize: 13 }}>
        {icon}<span>{label}</span>
      </div>
      <div style={{ fontSize: 28, fontWeight: 700 }}>{value}</div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const { t } = useTranslation();
  const color = STATUS_COLOR[status] ?? 'var(--text-muted)';
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 600,
      color, border: `1px solid ${color}`,
      background: `color-mix(in srgb, ${color} 12%, var(--bg-surface))`,
      flexShrink: 0,
    }}>
      {status === 'running' && <RefreshCw size={10} className="animate-spin" />}
      {t(`jobRuns.${status}`, status)}
    </span>
  );
}

function formatDuration(ms: number | null) {
  if (ms == null) return '—';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
}

function formatRelative(ts: string) {
  const diff = Date.now() - new Date(ts).getTime();
  if (diff < 60000) return '< 1 min ago';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return new Date(ts).toLocaleDateString();
}

function RunRow({ run }: { run: JobRun }) {
  const [expanded, setExpanded] = useState(false);
  const hasSummary = run.summary && Object.keys(run.summary).length > 0;

  return (
    <div style={{ border: '1px solid var(--border-default)', borderRadius: 8, background: 'var(--bg-surface)', marginBottom: 6, overflow: 'hidden' }}>
      <div
        style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', cursor: hasSummary || run.error ? 'pointer' : 'default' }}
        onClick={() => (hasSummary || run.error) && setExpanded(e => !e)}
      >
        <StatusBadge status={run.status} />
        <span style={{ flex: 1, fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {run.job_name}
        </span>
        <span style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
          <Clock size={11} /> {formatDuration(run.duration_ms)}
        </span>
        <span style={{ fontSize: 12, color: 'var(--text-muted)', flexShrink: 0, minWidth: 72, textAlign: 'right' }}>
          {formatRelative(run.started_at)}
        </span>
        {(hasSummary || run.error) && (
          <span style={{ color: 'var(--text-muted)', marginLeft: 2 }}>
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </span>
        )}
      </div>
      {expanded && (hasSummary || run.error) && (
        <div style={{ borderTop: '1px solid var(--border-subtle)', padding: '10px 14px', background: 'var(--bg-elevated)' }}>
          {run.error && (
            <div style={{ color: 'var(--color-error)', fontSize: 12, marginBottom: hasSummary ? 8 : 0 }}>{run.error}</div>
          )}
          {hasSummary && (
            <pre style={{ margin: 0, fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: 'inherit' }}>
              {JSON.stringify(run.summary, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

const KNOWN_JOBS = [
  'deduper', 'tag_normalizer', 'edge_auditor', 'embedding_consistency',
  'trust_calibrator', 'coverage_gap_detector', 'source_decay_monitor',
  'conductor_dispatch', 'edge_decay',
];

const selectStyle: CSSProperties = {
  padding: '6px 10px', borderRadius: 6, fontSize: 13,
  background: 'var(--bg-elevated)', border: '1px solid var(--border-default)',
  color: 'var(--text-primary)',
};

export default function JobRunsPage({ wsId }: { wsId: string }) {
  const { t } = useTranslation();
  const [runs, setRuns] = useState<JobRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterJob, setFilterJob] = useState('');
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    workspaces.jobRuns(wsId, {
      status: filterStatus || undefined,
      job_name: filterJob || undefined,
      limit: 100,
    }).then(res => {
      if (active) setRuns(res.runs);
    }).catch(e => {
      if (active) setError(e.message);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [wsId, filterStatus, filterJob, tick]);

  const successCount = runs.filter(r => r.status === 'success').length;
  const failedCount = runs.filter(r => r.status === 'failed').length;
  const skippedCount = runs.filter(r => r.status === 'skipped').length;

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>{t('jobRuns.title')}</h2>
        <p style={{ margin: '4px 0 0', color: 'var(--text-muted)', fontSize: 13 }}>{t('jobRuns.subtitle')}</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 28 }}>
        <MetricCard icon={<Activity size={16} />} label={t('jobRuns.total')} value={String(runs.length)} />
        <MetricCard icon={<CheckCircle2 size={16} />} label={t('jobRuns.success')} value={String(successCount)} />
        <MetricCard icon={<XCircle size={16} />} label={t('jobRuns.failed')} value={String(failedCount)} warn={failedCount > 0} />
        <MetricCard icon={<SkipForward size={16} />} label={t('jobRuns.skipped')} value={String(skippedCount)} />
      </div>

      <div style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap' }}>
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} style={selectStyle}>
          <option value="">{t('jobRuns.filter_status')}: {t('jobRuns.all')}</option>
          <option value="success">{t('jobRuns.success')}</option>
          <option value="failed">{t('jobRuns.failed')}</option>
          <option value="skipped">{t('jobRuns.skipped')}</option>
          <option value="running">{t('jobRuns.running')}</option>
        </select>
        <select value={filterJob} onChange={e => setFilterJob(e.target.value)} style={selectStyle}>
          <option value="">{t('jobRuns.filter_job')}: {t('jobRuns.all')}</option>
          {KNOWN_JOBS.map(n => <option key={n} value={n}>{n}</option>)}
        </select>
        <button
          onClick={() => setTick(n => n + 1)}
          style={{ ...selectStyle, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}
        >
          <RefreshCw size={13} /> {t('jobRuns.refresh')}
        </button>
      </div>

      {loading ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 14, padding: 32, textAlign: 'center' }}>
          <RefreshCw size={18} className="animate-spin" style={{ display: 'block', margin: '0 auto 10px' }} />
          {t('jobRuns.loading')}
        </div>
      ) : error ? (
        <div style={{ color: 'var(--color-error)', padding: 16, background: 'var(--bg-surface)', borderRadius: 8, border: '1px solid var(--color-error)' }}>
          {error}
        </div>
      ) : runs.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 14, padding: 32, textAlign: 'center' }}>
          {t('jobRuns.no_data')}
        </div>
      ) : (
        runs.map(run => <RunRow key={run.id} run={run} />)
      )}
    </div>
  );
}
