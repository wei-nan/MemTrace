import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Network, X, ShieldCheck, Activity, Clock, ChevronRight } from 'lucide-react';
import { system } from '../api';

export default function McpStatusPanel({ onClose }: { onClose: () => void }) {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetch = () => {
      system.getMcpStatus()
        .then(s => setStatus(s))
        .catch(() => setStatus(null))
        .finally(() => setLoading(false));
    };
    fetch();
    const timer = setInterval(fetch, 10000); // refresh every 10s
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="side-panel mcp-status-panel" style={{ width: 400, position: 'fixed', right: 0, top: 0, height: '100vh', zIndex: 2000, display: 'flex', flexDirection: 'column', borderLeft: '1px solid var(--border-default)' }}>
      <div style={{ padding: '24px 24px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ padding: 8, background: 'var(--color-primary-subtle)', borderRadius: 8, color: 'var(--color-primary)' }}>
            <Network size={20} />
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: 16 }}>{zh ? 'MCP 實時狀態' : 'MCP Live Status'}</h3>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
              Model Context Protocol Gateway
            </div>
          </div>
        </div>
        <button className="btn-ghost" onClick={onClose} style={{ padding: 8 }}><X size={18} /></button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
        {loading && !status ? (
          <div className="flex-center" style={{ height: 100 }}>
            <div className="animate-spin-slow"><Activity size={24} color="var(--text-muted)" /></div>
          </div>
        ) : status ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* Global Stats */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div style={{ background: 'var(--bg-elevated)', padding: 16, borderRadius: 12, border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase' }}>{zh ? '當前總連線' : 'Total Sessions'}</div>
                <div style={{ fontSize: 24, fontWeight: 700 }}>{status.active_sessions_total}</div>
              </div>
              <div style={{ background: 'var(--bg-elevated)', padding: 16, borderRadius: 12, border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase' }}>{zh ? '伺服器版本' : 'Server Ver'}</div>
                <div style={{ fontSize: 24, fontWeight: 700 }}>{status.server_info?.version}</div>
              </div>
            </div>

            {/* My Sessions */}
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
                <ShieldCheck size={14} color="var(--color-primary)" />
                {zh ? '我的活躍連線' : 'My Active Sessions'}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {status.user_sessions.length === 0 ? (
                  <div style={{ padding: '20px', textAlign: 'center', background: 'var(--bg-elevated)', borderRadius: 12, border: '1px dashed var(--border-default)', fontSize: 12, color: 'var(--text-muted)' }}>
                    {zh ? '尚無活躍的 MCP 連線' : 'No active MCP sessions'}
                  </div>
                ) : status.user_sessions.map((s: any) => (
                  <div key={s.session_id} style={{ background: 'var(--bg-elevated)', padding: 12, borderRadius: 10, border: '1px solid var(--border-subtle)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                      <div style={{ fontSize: 12, fontWeight: 600, fontFamily: 'monospace' }}>{s.session_id.slice(0, 8)}...</div>
                      <div style={{ fontSize: 10, padding: '2px 6px', background: 'var(--color-success-subtle)', color: 'var(--color-success)', borderRadius: 4 }}>ACTIVE</div>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Clock size={10} />
                        {new Date(s.created_at * 1000).toLocaleTimeString()}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'right' }}>
                        {zh ? '最後活動: ' : 'Last: '}
                        {Math.floor(Date.now() / 1000 - s.last_accessed)}s ago
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* MCP Download Link */}
            <div style={{ marginTop: 'auto', background: 'var(--color-primary-subtle)', padding: 16, borderRadius: 12, border: '1px solid var(--color-primary)' }}>
              <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--color-primary)', marginBottom: 4 }}>
                {zh ? '整合至 Claude Code?' : 'Integrate with Claude Code?'}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: 12 }}>
                {zh ? '在本地執行 claude mcp add memtrace-remote 並填入你的 SSE URL 以存取圖譜。' : 'Run claude mcp add memtrace-remote locally and use your SSE URL to access the graph.'}
              </div>
              <a 
                href="/mcp/download/memtrace-mcp.zip" 
                className="btn-primary" 
                style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, fontSize: 12, padding: '8px 0' }}
              >
                {zh ? '下載 MCP 套件' : 'Download MCP Package'} <ChevronRight size={14} />
              </a>
            </div>
          </div>
        ) : (
          <div className="error-text">
            {zh ? '無法取得 MCP 狀態。請檢查連線或 API Key。' : 'Failed to fetch MCP status. Check connection or API Key.'}
          </div>
        )}
      </div>
    </div>
  );
}
