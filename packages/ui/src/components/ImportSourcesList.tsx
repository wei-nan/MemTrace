import { useState, useEffect } from 'react';
import { Database, ShieldCheck, ShieldAlert, ChevronDown, ChevronUp, Clock, FileText } from 'lucide-react';
import { authHeaders } from '../api';

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

export default function ImportSourcesList({ wsId }: { wsId: string }) {
  const [sources, setSources] = useState<ImportSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [audits, setAudits] = useState<Record<string, AuditResult>>({});
  const [expanded, setExpanded] = useState<string | null>(null);

  const fetchSources = async () => {
    try {
      const resp = await fetch(`http://localhost:8000/api/v1/workspaces/${wsId}/sources`, {
        headers: authHeaders()
      });
      if (resp.ok) {
        const data = await resp.json();
        setSources(data);
      }
    } catch (e) {
      console.error('Failed to fetch sources', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSources();
  }, [wsId]);

  const handleAudit = async (sourceId: string) => {
    try {
      const resp = await fetch(`http://localhost:8000/api/v1/workspaces/${wsId}/audit/${sourceId}`, {
        headers: authHeaders()
      });
      if (resp.ok) {
        const result = await resp.json();
        setAudits(prev => ({ ...prev, [sourceId]: result }));
        setExpanded(sourceId);
      }
    } catch (e) {
      console.error('Audit failed', e);
    }
  };

  const handleRetry = async (sourceId: string, missingHeadings: string[]) => {
    if (!missingHeadings.length) return;
    
    try {
      const resp = await fetch(`http://localhost:8000/api/v1/workspaces/${wsId}/audit/${sourceId}/retry`, {
        method: 'POST',
        headers: {
          ...authHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ headings: missingHeadings })
      });
      
      if (resp.ok) {
        const result = await resp.json();
        alert(`已啟動補缺任務 (Job ID: ${result.job_id})，請至進度清單查看。`);
      }
    } catch (e) {
      console.error('Retry failed', e);
    }
  };

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
                  {audit ? (
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
                  ) : (
                    <button 
                      className="btn-secondary" 
                      style={{ padding: '6px 12px', fontSize: 12 }}
                      onClick={() => handleAudit(src.id)}
                    >
                      執行完整性稽核
                    </button>
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
                        <button 
                          className="btn-primary" 
                          style={{ padding: '4px 10px', fontSize: 11 }}
                          onClick={() => handleRetry(src.id, audit.missing)}
                        >
                          一鍵補缺 (Retry Missing)
                        </button>
                      )}
                    </h4>
                    {audit.missing.length > 0 ? (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                        {audit.missing.map((h, i) => (
                          <div key={i} style={{ 
                            padding: '4px 10px', borderRadius: 6, 
                            background: 'white', border: '1px solid var(--border-subtle)',
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
    </div>
  );
}
