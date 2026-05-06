import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Network, Brain, Lock } from 'lucide-react';
import GraphView from './GraphView';
import { api } from './api';

export default function PublicWorkspaceView() {
  const { wsId } = useParams<{ wsId: string }>();
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [wsName, setWsName] = useState('');

  useEffect(() => {
    async function load() {
      if (!wsId) return;
      try {
        setLoading(true);
        // Phase 4.6: Public access uses a specific endpoint or allows anonymous on standard one
        const data = await api.kb.getGraph(wsId);
        setNodes(data.nodes || []);
        setEdges(data.edges || []);
        
        // Fetch public metadata
        const ws = await api.kb.getPublicInfo(wsId);
        setWsName(ws.name_zh || ws.name_en || 'Public Workspace');
      } catch (err: any) {
        console.error('Failed to load public workspace:', err);
        setError(err.message || 'Unable to load workspace. It may not be public.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [wsId]);

  if (loading) {
    return (
      <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-surface)' }}>
        <div className="animate-pulse" style={{ textAlign: 'center' }}>
          <Brain size={48} color="var(--color-primary)" style={{ marginBottom: 16 }} />
          <p style={{ color: 'var(--text-muted)' }}>載入公開知識庫...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-surface)' }}>
        <div style={{ textAlign: 'center', maxWidth: 400, padding: 40 }} className="glass-panel">
          <Lock size={48} color="var(--color-error)" style={{ marginBottom: 16 }} />
          <h2 style={{ marginBottom: 8 }}>存取受限</h2>
          <p style={{ color: 'var(--text-muted)', marginBottom: 24 }}>{error}</p>
          <Link to="/auth" className="btn-primary">返回登入</Link>
        </div>
      </div>
    );
  }

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg-surface)' }}>
      <header style={{ padding: '16px 40px', borderBottom: '1px solid var(--border-default)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ background: 'var(--color-primary-subtle)', padding: 8, borderRadius: 8 }}>
            <Network size={20} color="var(--color-primary)" />
          </div>
          <div>
            <h1 style={{ fontSize: 18, margin: 0 }}>{wsName}</h1>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>公開唯讀視圖</p>
          </div>
        </div>
        <Link to="/auth" className="btn-secondary" style={{ fontSize: 13 }}>
          登入以編輯
        </Link>
      </header>
      
      <main style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        <GraphView 
          apiNodes={nodes} 
          apiEdges={edges} 
          relationColors={{
            depends_on: 'var(--color-primary)',
            extends: 'var(--node-secondary)',
            related_to: 'var(--text-muted)',
            contradicts: 'var(--color-error)',
          }}
          isPreview={true}
        />
        
        {/* Bottom stats overlay */}
        <div style={{ 
          position: 'absolute', bottom: 24, left: 24, 
          padding: '8px 16px', borderRadius: 20, 
          background: 'rgba(255,255,255,0.8)', backdropFilter: 'blur(8px)',
          border: '1px solid var(--border-default)', fontSize: 12, color: 'var(--text-muted)',
          display: 'flex', gap: 16
        }}>
          <span>節點: {nodes.length}</span>
          <span>連結: {edges.length}</span>
        </div>
      </main>
    </div>
  );
}
