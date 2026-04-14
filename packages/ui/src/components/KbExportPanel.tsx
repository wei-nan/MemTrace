import { useState, useEffect } from 'react';
import { Download, CheckCircle, Clock, AlertCircle, Loader2 } from 'lucide-react';
import { workspaces, type KBExport } from '../api';

export default function KbExportPanel({ wsId, zh }: { wsId: string; zh: boolean }) {
  const [exports, setExports] = useState<KBExport[]>([]);
  const [exporting, setExporting] = useState(false);
  const [includeMarkdown, setIncludeMarkdown] = useState(true);

  const loadExports = async () => {
    try {
      const data = await workspaces.listExports(wsId);
      setExports(data);
    } catch (e) {}
  };

  useEffect(() => {
    loadExports();
    const timer = setInterval(loadExports, 5000);
    return () => clearInterval(timer);
  }, [wsId]);

  const handleStartExport = async () => {
    setExporting(true);
    try {
      await workspaces.createExport(wsId, { include_markdown: includeMarkdown });
      loadExports();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <section style={{ background: 'var(--bg-surface)', padding: 20, borderRadius: 12, border: '1px solid var(--border-default)' }}>
        <h4 style={{ fontSize: 15, fontWeight: 600, marginBottom: 12 }}>
          {zh ? '新任務：匯出知識庫' : 'New Task: Export Knowledge Base'}
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontSize: 14 }}>
            <input 
              type="checkbox" 
              checked={includeMarkdown} 
              onChange={e => setIncludeMarkdown(e.target.checked)}
              style={{ width: 16, height: 16 }}
            />
            {zh ? '包含 Markdown 格式文件 (獨立打包)' : 'Include Markdown files (Individually zipped)'}
          </label>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', background: 'var(--bg-app)', padding: 10, borderRadius: 6 }}>
            {zh 
              ? '匯出檔 (.memtrace) 將包含所有節點資料、關聯資訊及其對應的 Markdown 文件。此格式可用於備份或匯入其他 MemTrace 實例。'
              : 'The export file (.memtrace) includes all node data, edge relations, and markdown files. This format is suitable for backups or transfers.'}
          </div>
          <button 
            className="btn-primary" 
            onClick={handleStartExport} 
            disabled={exporting}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, height: 40 }}
          >
            {exporting ? <Loader2 className="animate-spin" size={18} /> : <Download size={18} />}
            {zh ? '開始匯出' : 'Start Export'}
          </button>
        </div>
      </section>

      <section>
        <h4 style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Clock size={14} />
          {zh ? '最近的匯出紀錄' : 'Recent Exports'}
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {exports.length === 0 && (
            <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
              {zh ? '尚無紀錄' : 'No exports yet'}
            </div>
          )}
          {exports.map(exp => (
            <div 
              key={exp.id} 
              style={{ 
                display: 'flex', justifyContent: 'space-between', alignItems: 'center', 
                padding: '12px 16px', background: 'var(--bg-surface)', 
                border: '1px solid var(--border-subtle)', borderRadius: 10 
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ 
                  width: 36, height: 36, borderRadius: 18, 
                  background: exp.status === 'completed' ? 'var(--success-bg)' : 'var(--bg-app)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>
                  {exp.status === 'completed' && <CheckCircle size={18} style={{ color: 'var(--success-color)' }} />}
                  {exp.status === 'processing' && <Loader2 size={18} className="animate-spin" />}
                  {exp.status === 'pending' && <Clock size={18} />}
                  {exp.status === 'failed' && <AlertCircle size={18} style={{ color: 'var(--error-color)' }} />}
                </div>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 500 }}>
                    {exp.id} 
                    <span style={{ marginLeft: 8, fontSize: 11, fontWeight: 400, opacity: 0.6 }}>
                      {new Date(exp.created_at).toLocaleString()}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                    Status: {exp.status}
                  </div>
                </div>
              </div>

              {exp.status === 'completed' && (
                <a 
                  href={`http://localhost:8000/api/v1/workspaces/${wsId}/exports/${exp.id}/download`} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="btn-secondary"
                  style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px', fontSize: 13 }}
                >
                  <Download size={14} />
                  {zh ? '下載' : 'Download'}
                </a>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
