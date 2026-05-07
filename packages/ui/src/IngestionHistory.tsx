import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Loader2, CheckCircle2, XCircle, Clock, ExternalLink, ServerCrash, Compass, ChevronDown, ChevronRight, Ban } from 'lucide-react';
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

function LogRow({ log, t, onGoToReview, nested = false }: { log: IngestionLog; t: any; onGoToReview: () => void; nested?: boolean }) {
  const isMultiChunk = (log.chunks_total ?? 1) > 1;
  const zh = t.language === 'zh-TW';

  return (
    <div style={{
      background: nested ? 'transparent' : 'var(--bg-surface)',
      border: nested ? 'none' : `1px solid ${log.status === 'failed' ? 'var(--color-error)' : 'var(--border-default)'}`,
      borderBottom: nested ? '1px solid var(--border-subtle)' : undefined,
      borderRadius: nested ? 0 : 12,
      padding: nested ? '8px 0' : '12px 16px',
    }}>
      {/* ── Top row: icon + info + action ── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1, minWidth: 0 }}>

          {/* Status icon */}
          <div style={{ flexShrink: 0, color:
            (log.status === 'processing' || log.status === 'cancelling') ? 'var(--color-primary)' :
            log.status === 'completed'  ? 'var(--color-success)' :
            log.status === 'cancelled'   ? 'var(--text-muted)' :
            'var(--color-error)'
          }}>
            {(log.status === 'processing' || log.status === 'cancelling') && <Loader2 size={18} className="animate-spin" />}
            {log.status === 'completed'  && <CheckCircle2 size={18} />}
            {log.status === 'failed'     && <XCircle size={18} />}
            {log.status === 'cancelled'  && <Ban size={18} />}
            {log.status === 'pending'    && <Clock size={18} />}
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
              {log.status === 'cancelling' && (zh ? '正在取消...' : 'Cancelling...')}
              {log.status === 'cancelled' && (zh ? '已取消' : 'Cancelled')}
              {log.status === 'pending' && (zh ? '佇列中' : 'In Queue')}
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
        <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
          {log.status === 'completed' && log.source_document_id && (
            <button
              className="btn-secondary"
              onClick={() => {
                if ((window as any).mt_trigger_explore) {
                  (window as any).mt_trigger_explore(log.source_document_id);
                }
              }}
              style={{ padding: '4px 10px', fontSize: 11, display: 'flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap' }}
            >
              <Compass size={11} />
              {t('ingest.explore_btn', { defaultValue: 'Explore' })}
            </button>
          )}
          {log.status === 'completed' && (
            <button
              className="btn-secondary"
              onClick={onGoToReview}
              style={{ padding: '4px 10px', fontSize: 11, display: 'flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap' }}
            >
              {t('ingest.review_btn')}
              <ExternalLink size={11} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Batch Group component ───────────────────────────────────────────────────

function BatchGroup({ batchId, logs, t, onGoToReview }: { batchId: string; logs: IngestionLog[]; t: any; onGoToReview: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const zh = t.language === 'zh-TW';
  const doneCount = logs.filter(l => l.status === 'completed').length;
  const totalCount = logs.length;
  const isProcessing = logs.some(l => l.status === 'processing' || l.status === 'cancelling' || l.status === 'pending');
  const hasFailed = logs.some(l => l.status === 'failed');

  return (
    <div style={{ 
      background: 'var(--bg-surface)', 
      border: `1px solid ${hasFailed ? 'var(--color-error)' : 'var(--border-default)'}`, 
      borderRadius: 12, overflow: 'hidden' 
    }}>
      <div 
        onClick={() => setExpanded(!expanded)}
        style={{ 
          padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', 
          cursor: 'pointer', background: isProcessing ? 'var(--color-primary-subtle)' : 'transparent' 
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ color: 
            isProcessing ? 'var(--color-primary)' : 
            hasFailed ? 'var(--color-error)' : 'var(--color-success)' 
          }}>
            {isProcessing ? <Loader2 size={18} className="animate-spin" /> : 
             hasFailed ? <XCircle size={18} /> : <CheckCircle2 size={18} />}
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700 }}>
              {zh ? '多檔案批次攝入' : 'Batch Ingestion'} ({doneCount}/{totalCount})
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>ID: {batchId.substring(0, 12)}...</div>
          </div>
        </div>
        {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      </div>
      
      {expanded && (
        <div style={{ padding: '0 16px 8px 46px', display: 'flex', flexDirection: 'column' }}>
          {logs.sort((a,b) => (a.queue_position || 0) - (b.queue_position || 0)).map(log => (
            <LogRow key={log.id} log={log} t={t} onGoToReview={onGoToReview} nested />
          ))}
        </div>
      )}
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
    const hasProcessing = logs.some(l => l.status === 'processing' || l.status === 'cancelling' || l.status === 'pending');
    if (!hasProcessing) return;
    const timer = setTimeout(loadLogs, 3000);
    return () => clearTimeout(timer);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [logs]);

  if (logs.length === 0 && !loading) return null;

  // Group logs by batch_id
  const batchGroups: Record<string, IngestionLog[]> = {};
  const individuals: IngestionLog[] = [];

  logs.forEach(log => {
    if (log.batch_id) {
      if (!batchGroups[log.batch_id]) batchGroups[log.batch_id] = [];
      batchGroups[log.batch_id].push(log);
    } else {
      individuals.push(log);
    }
  });

  const hasProcessingGlobal = logs.some(l => l.status === 'processing');

  return (
    <div style={{ marginTop: 40, textAlign: 'left' }}>
      <h3 style={{ fontSize: 16, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8, fontWeight: 700 }}>
        <Clock size={16} />
        {t('ingest.recent')}
      </h3>

      {hasProcessingGlobal && <ServerSideNotice t={t} />}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {/* Batches first */}
        {Object.entries(batchGroups).map(([bid, group]) => (
          <BatchGroup key={bid} batchId={bid} logs={group} t={t} onGoToReview={onGoToReview} />
        ))}
        {/* Then individuals */}
        {individuals.map(log => (
          <LogRow key={log.id} log={log} t={t} onGoToReview={onGoToReview} />
        ))}
      </div>
    </div>
  );
}
