import { useState, useEffect, useCallback } from 'react';
import { Database, ShieldCheck, ShieldAlert, ChevronDown, ChevronUp, Clock, FileText, Loader2 } from 'lucide-react';
import { ingest } from '../api';
import { ToastContainer, type ToastItem } from './Toast';

interface ImportSource {
  id: string;
  filename: string;
  doc_type: string;
  created_at: string;
  coverage?: number;
}

interface AuditResult {
  source_id: string;
  coverage: number;
  total_headings: number;
  missing: string[];
}

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

export default function ImportSourcesList({ wsId }: { wsId: string }) {
  const [sources, setSources] = useState<ImportSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [audits, setAudits] = useState<Record<string, AuditResult>>({});
  const [expanded, setExpanded] = useState<string | null>(null);

  const [loadingAudits, setLoadingAudits] = useState<Record<string, boolean>>({});
  const [retryingSources, setRetryingSources] = useState<Record<string, boolean>>({});
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [activeRetries, setActiveRetries] = useState<Record<string, {
    jobId: string;
    status: string;
    done: number;
    total: number;
  }>>({});

  const showToast = useCallback((message: string, variant: 'success' | 'error' | 'warning' | 'info' = 'info') => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts(prev => [...prev, { id, message, variant }]);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const fetchSources = useCallback(async () => {
    try {
      const data = await ingest.listSources(wsId);
      setSources(data);
    } catch (e) {
      console.error('Failed to fetch sources', e);
    } finally {
      setLoading(false);
    }
  }, [wsId]);

  useEffect(() => {
    fetchSources();
  }, [wsId, fetchSources]);

  const handleAudit = useCallback(async (sourceId: string, silent = false) => {
    setLoadingAudits(prev => ({ ...prev, [sourceId]: true }));
    try {
      const result = await ingest.auditSource(wsId, sourceId);
      setAudits(prev => ({ ...prev, [sourceId]: result }));
      setExpanded(sourceId);
      if (!silent) {
        showToast('完整性稽核執行成功', 'success');
      }
    } catch (e) {
      console.error('Audit failed', e);
      showToast(`稽核失敗: ${(e as Error)?.message || '未知錯誤'}`, 'error');
    } finally {
      setLoadingAudits(prev => ({ ...prev, [sourceId]: false }));
    }
  }, [wsId, showToast]);

  const handleRetry = useCallback(async (sourceId: string, missingHeadings: string[]) => {
    if (!missingHeadings.length) return;
    
    setRetryingSources(prev => ({ ...prev, [sourceId]: true }));
    try {
      const result = await ingest.retryAudit(wsId, sourceId, missingHeadings);
      showToast(`已啟動補缺任務，正在進行後端排程...`, 'info');
      setActiveRetries(prev => ({
        ...prev,
        [sourceId]: {
          jobId: result.job_id,
          status: 'pending',
          done: 0,
          total: missingHeadings.length
        }
      }));
    } catch (e) {
      console.error('Retry failed', e);
      showToast(`啟動補缺任務失敗: ${(e as Error)?.message || '未知錯誤'}`, 'error');
    } finally {
      setRetryingSources(prev => ({ ...prev, [sourceId]: false }));
    }
  }, [wsId, showToast]);

  useEffect(() => {
    const activeJobs = Object.values(activeRetries).filter(
      r => r.status === 'pending' || r.status === 'processing'
    );
    if (activeJobs.length === 0) return;

    let active = true;
    const poll = async () => {
      try {
        const logs = await ingest.getLogs(wsId);
        if (!active) return;
        
        setActiveRetries(prev => {
          const next = { ...prev };
          let changed = false;
          
          for (const [sourceId, retry] of Object.entries(prev)) {
            if (retry.status === 'completed' || retry.status === 'failed' || retry.status === 'cancelled') {
              continue;
            }
            const log = logs.find(l => l.id === retry.jobId);
            if (log) {
              const updated = {
                ...retry,
                status: log.status,
                done: log.chunks_done ?? 0,
                total: log.chunks_total ?? retry.total
              };
              if (
                updated.status !== retry.status ||
                updated.done !== retry.done ||
                updated.total !== retry.total
              ) {
                next[sourceId] = updated;
                changed = true;
                
                if (log.status === 'completed') {
                  showToast(`檔案補缺完成！正在更新稽核結果...`, 'success');
                  handleAudit(sourceId, true);
                } else if (log.status === 'failed') {
                  showToast(`補缺任務失敗: ${log.error_msg || '未知錯誤'}`, 'error');
                } else if (log.status === 'cancelled') {
                  showToast(`補缺任務已取消`, 'warning');
                }
              }
            }
          }
          return changed ? next : prev;
        });
      } catch (e) {
        console.error('Failed to poll retry progress', e);
      }
    };

    const interval = setInterval(poll, 2000);
    poll();
    
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [activeRetries, wsId, showToast, handleAudit]);

  if (loading) return <div style={{ padding: 20, textAlign: 'center' }}>Loading sources...</div>;

  return (
    <div style={{ marginTop: 40 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
        <Database size={20} className="color-primary" />
        <h3 style={{ fontSize: 18, fontWeight: 700 }}>匯入源檔案管理 (Source Audit)</h3>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {sources.length === 0 && (
          <div style={{ padding: 40, textAlign: 'center', background: 'var(--bg-surface)', borderRadius: 12, color: 'var(--text-muted)' }}>
            尚未有任何匯入紀錄。
          </div>
        )}
        
        {sources.map(src => {
          const audit = audits[src.id];
          const isExpanded = expanded === src.id;
          const activeRetry = activeRetries[src.id];

          return (
            <div 
              key={src.id}
              className="glass-panel"
              style={{ padding: 0, overflow: 'hidden', border: '1px solid var(--border-subtle)' }}
            >
              <div style={{ padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  <div style={{ 
                    width: 40, height: 40, borderRadius: 10, 
                    background: 'var(--bg-elevated)', display: 'flex', 
                    alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' 
                  }}>
                    <FileText size={20} />
                  </div>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{src.filename}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4, marginTop: 4 }}>
                      <Clock size={12} />
                      {new Date(src.created_at).toLocaleString()}
                      <span style={{ margin: '0 4px' }}>•</span>
                      <span style={{ 
                        padding: '2px 6px', borderRadius: 4, 
                        background: 'var(--bg-elevated)', fontSize: 10, fontWeight: 700,
                        textTransform: 'uppercase'
                      }}>
                        {src.doc_type}
                      </span>
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  {activeRetry && (activeRetry.status === 'pending' || activeRetry.status === 'processing') ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--color-primary)' }}>
                      <Loader2 size={14} className="animate-spin" />
                      <span>
                        {activeRetry.status === 'pending' ? '等待補缺...' : `補缺中: ${activeRetry.done}/${activeRetry.total}`}
                      </span>
                    </div>
                  ) : (
                    <>
                      {audit && (
                        <div style={{ 
                          display: 'flex', alignItems: 'center', gap: 8, 
                          padding: '4px 12px', borderRadius: 20,
                          background: audit.coverage >= 0.9 ? 'rgba(34, 197, 94, 0.1)' : 'rgba(234, 179, 8, 0.1)',
                          color: audit.coverage >= 0.9 ? '#16a34a' : '#ca8a04',
                          fontSize: 12, fontWeight: 700
                        }}>
                          {audit.coverage >= 0.9 ? <ShieldCheck size={14} /> : <ShieldAlert size={14} />}
                          覆蓋率: {Math.round(audit.coverage * 100)}%
                        </div>
                      )}

                      <button 
                        className="btn-secondary" 
                        style={{ padding: '6px 12px', fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}
                        onClick={() => handleAudit(src.id)}
                        disabled={loadingAudits[src.id]}
                      >
                        {loadingAudits[src.id] && <Loader2 size={12} className="animate-spin" />}
                        {audit ? '重新稽核' : '執行完整性稽核'}
                      </button>
                    </>
                  )}
                  
                  {audit && (
                    <button 
                      style={{ padding: 4, background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
                      onClick={() => setExpanded(isExpanded ? null : src.id)}
                    >
                      {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                    </button>
                  )}
                </div>
              </div>

              {isExpanded && audit && (
                <div style={{ padding: '0 20px 20px', borderTop: '1px solid var(--border-subtle)', background: 'var(--bg-surface)' }}>
                  <div style={{ paddingTop: 16 }}>
                    <h4 style={{ fontSize: 12, fontWeight: 700, marginBottom: 12, color: 'var(--text-secondary)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      遺漏的章節標題 ({audit.missing.length})
                      {audit.missing.length > 0 && (
                        activeRetry && (activeRetry.status === 'pending' || activeRetry.status === 'processing') ? (
                          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>任務執行中...</span>
                        ) : (
                          <button 
                            className="btn-primary" 
                            style={{ padding: '4px 10px', fontSize: 11, display: 'flex', alignItems: 'center', gap: 6 }}
                            onClick={() => handleRetry(src.id, audit.missing)}
                            disabled={retryingSources[src.id]}
                          >
                            {retryingSources[src.id] && <Loader2 size={11} className="animate-spin" />}
                            一鍵補缺 (Retry Missing)
                          </button>
                        )
                      )}
                    </h4>

                    {activeRetry && (activeRetry.status === 'pending' || activeRetry.status === 'processing') && (
                      <div style={{ marginBottom: 16, padding: '10px 14px', background: 'var(--bg-elevated)', borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
                        <ChunkProgress done={activeRetry.done} total={activeRetry.total} />
                      </div>
                    )}

                    {audit.missing.length > 0 ? (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                        {audit.missing.map((h, i) => (
                          <div key={i} style={{
                            padding: '4px 10px', borderRadius: 6,
                            background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)',
                            fontSize: 12, color: 'var(--text-primary)'
                          }}>
                            {h}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div style={{ fontSize: 13, color: '#16a34a', display: 'flex', alignItems: 'center', gap: 6 }}>
                        <ShieldCheck size={16} />
                        完美覆蓋！所有標題均已轉換為知識節點。
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
