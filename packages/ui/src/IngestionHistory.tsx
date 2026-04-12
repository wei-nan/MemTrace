import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Loader2, CheckCircle2, XCircle, Clock, ExternalLink } from 'lucide-react';
import { ingest, type IngestionLog } from './api';

export default function IngestionHistory({ wsId, onGoToReview, refreshKey }: { 
    wsId: string, 
    onGoToReview: () => void,
    refreshKey: number 
}) {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
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
    // Auto-refresh when processing
    const hasProcessing = logs.some(l => l.status === 'processing');
    if (hasProcessing) {
        const timer = setTimeout(loadLogs, 3000);
        return () => clearTimeout(timer);
    }
  }, [wsId, refreshKey, logs.some(l => l.status === 'processing')]);

  if (logs.length === 0 && !loading) return null;

  return (
    <div style={{ marginTop: 40, textAlign: 'left' }}>
      <h3 style={{ fontSize: 16, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
        <Clock size={16} />
        {zh ? '最近匯入紀錄' : 'Recent Ingestions'}
      </h3>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {logs.map(log => (
          <div key={log.id} style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-default)',
            borderRadius: 12,
            padding: '12px 16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 16
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1, minWidth: 0 }}>
              <div style={{ color: log.status === 'processing' ? 'var(--color-primary)' : 
                                  log.status === 'completed' ? 'var(--color-success)' : 
                                  'var(--color-error)' }}>
                {log.status === 'processing' && <Loader2 size={18} className="animate-spin" />}
                {log.status === 'completed' && <CheckCircle2 size={18} />}
                {log.status === 'failed' && <XCircle size={18} />}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {log.filename}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                    {log.status === 'processing' ? (zh ? 'AI 正在分析並提取知識點...' : 'AI is analyzing and extracting nodes...') :
                     log.status === 'completed' ? (zh ? '已產出建議節點，等待審核' : 'Suggestions generated, pending review') :
                     log.error_msg || (zh ? '解析失敗' : 'Analysis failed')}
                </div>
              </div>
            </div>

            {log.status === 'completed' && (
                <button 
                  className="btn-secondary" 
                  onClick={onGoToReview}
                  style={{ padding: '6px 12px', fontSize: 12, display: 'flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap' }}
                >
                    {zh ? '前往審核' : 'Review'}
                    <ExternalLink size={12} />
                </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
