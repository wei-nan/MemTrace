import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Loader2, CheckCircle2, XCircle, Clock, ExternalLink, ServerCrash } from 'lucide-react';
import { ingest, type IngestionLog } from './api';

// ── Progress bar ────────────────────────────────────────────────────────────

function ChunkProgress({ done, total }: { done: number; total: number }) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>
        <span>{done} / {total}</span>
        <span>{pct}%</span>
      </div>
      <div style={{ height: 4, borderRadius: 99, background: 'var(--border-default)', overflow: 'hidden' }}>
        <div
          style={{
            height: '100%',
            width: `${pct}%`,
            background: 'var(--color-primary)',
            borderRadius: 99,
            transition: 'width 0.4s ease',
          }}
        />
      </div>
    </div>
  );
}

// ── Server-side notice (shown once) ─────────────────────────────────────────

function ServerSideNotice({ t }: { t: any }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: 10,
      padding: '10px 14px', borderRadius: 10,
      background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)',
      fontSize: 12, color: 'var(--text-secondary)', marginBottom: 12,
    }}>
      <ServerCrash size={14} style={{ marginTop: 1, flexShrink: 0, color: 'var(--color-primary)' }} />
      <span>
        {t('ingest.server_notice')}
      </span>
    </div>
  );
}

// ── Single log row ──────────────────────────────────────────────────────────

function LogRow({ log, t, onGoToReview }: { log: IngestionLog; t: any; onGoToReview: () => void }) {
  const isMultiChunk = (log.chunks_total ?? 1) > 1;

  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: `1px solid ${log.status === 'failed' ? 'var(--color-error)' : 'var(--border-default)'}`,
      borderRadius: 12,
      padding: '12px 16px',
    }}>
      {/* ── Top row: icon + info + action ── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1, minWidth: 0 }}>

          {/* Status icon */}
          <div style={{ flexShrink: 0, color:
            log.status === 'processing' ? 'var(--color-primary)' :
            log.status === 'completed'  ? 'var(--color-success)' :
            'var(--color-error)'
          }}>
            {log.status === 'processing' && <Loader2 size={18} className="animate-spin" />}
            {log.status === 'completed'  && <CheckCircle2 size={18} />}
            {log.status === 'failed'     && <XCircle size={18} />}
          </div>

          <div style={{ flex: 1, minWidth: 0 }}>
            {/* Filename */}
            <div style={{ fontSize: 13, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {log.filename}
            </div>

            {/* Status label */}
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
              {log.status === 'processing' && (
                isMultiChunk
                  ? t('ingest.processing_chunks')
                  : t('ingest.processing_single')
              )}
              {log.status === 'completed' && t('ingest.completed')}
              {log.status === 'failed'    && (log.error_msg || t('ingest.failed'))}
            </div>

            {/* Progress bar — only when multi-chunk & still processing */}
            {log.status === 'processing' && isMultiChunk && (
              <ChunkProgress done={log.chunks_done ?? 0} total={log.chunks_total!} />
            )}
          </div>
        </div>

        {/* Action */}
        {log.status === 'completed' && (
          <button
            className="btn-secondary"
            onClick={onGoToReview}
            style={{ padding: '6px 12px', fontSize: 12, display: 'flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap', flexShrink: 0 }}
          >
            {t('ingest.review_btn')}
            <ExternalLink size={12} />
          </button>
        )}
      </div>
    </div>
  );
}

// ── Main component ──────────────────────────────────────────────────────────

export default function IngestionHistory({
  wsId,
  onGoToReview,
  refreshKey,
}: {
  wsId: string;
  onGoToReview: () => void;
  refreshKey: number;
}) {
  const { t } = useTranslation();
  const [logs, setLogs] = useState<IngestionLog[]>([]);
  const [loading, setLoading] = useState(false);

  const loadLogs = async () => {
    try {
      setLoading(true);
      const data = await ingest.getLogs(wsId);
      setLogs(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wsId, refreshKey]);

  // Auto-poll while any job is still processing
  useEffect(() => {
    const hasProcessing = logs.some(l => l.status === 'processing');
    if (!hasProcessing) return;
    const timer = setTimeout(loadLogs, 3000);
    return () => clearTimeout(timer);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [logs]);

  if (logs.length === 0 && !loading) return null;

  const hasProcessing = logs.some(l => l.status === 'processing');

  return (
    <div style={{ marginTop: 40, textAlign: 'left' }}>
      <h3 style={{ fontSize: 16, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
        <Clock size={16} />
        {t('ingest.recent')}
      </h3>

      {hasProcessing && <ServerSideNotice t={t} />}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {logs.map(log => (
          <LogRow key={log.id} log={log} t={t} onGoToReview={onGoToReview} />
        ))}
      </div>
    </div>
  );
}
