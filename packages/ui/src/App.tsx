import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Network, PlusCircle, Search, Settings,
  BrainCircuit, Globe, Layers, LogOut, ChevronDown,
} from 'lucide-react';
import './index.css';
import AuthPage from './AuthPage';
import GraphView from './GraphView';
import GraphView3D from './GraphView3D';
import NodeEditor from './NodeEditor';
import { auth, workspaces, type Workspace, type Node as ApiNode } from './api';

type View = 'graph' | 'graph3d';

export default function App() {
  const { t, i18n } = useTranslation();

  // ── Auth ──────────────────────────────────────────────────────────────────
  const [authenticated, setAuthenticated] = useState(() => !!localStorage.getItem('mt_token'));
  const [user, setUser] = useState<{ display_name: string; email: string } | null>(null);

  useEffect(() => {
    if (authenticated) {
      auth.me()
        .then(u => setUser(u))
        .catch(() => { localStorage.removeItem('mt_token'); setAuthenticated(false); });
    }
  }, [authenticated]);

  const handleLogout = async () => {
    await auth.logout().catch(() => {});
    localStorage.removeItem('mt_token');
    setAuthenticated(false);
    setUser(null);
    setSelectedWs(null);
    setWsList([]);
  };

  // ── Workspaces ────────────────────────────────────────────────────────────
  const [wsList, setWsList] = useState<Workspace[]>([]);
  const [selectedWs, setSelectedWs] = useState<Workspace | null>(null);
  const [wsMenuOpen, setWsMenuOpen] = useState(false);
  const wsMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!authenticated) return;
    workspaces.list().then(list => {
      setWsList(list);
      if (list.length > 0 && !selectedWs) setSelectedWs(list[0]);
    }).catch(() => {});
  }, [authenticated]);

  // close ws dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wsMenuRef.current && !wsMenuRef.current.contains(e.target as Node)) {
        setWsMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // ── Navigation ────────────────────────────────────────────────────────────
  const [currentView, setCurrentView] = useState<View>('graph');

  // ── Node Editor ───────────────────────────────────────────────────────────
  // undefined  = panel closed
  // null       = create new node
  // ApiNode    = edit existing node
  const [editingNode, setEditingNode] = useState<ApiNode | null | undefined>(undefined);
  const [graphVersion, setGraphVersion] = useState(0);

  const handleNodeSaved = (saved: ApiNode) => {
    // Keep modal open so the edge panel appears; reload graph in background
    setEditingNode(saved);
    setGraphVersion(v => v + 1);
  };

  // ── Render ────────────────────────────────────────────────────────────────
  if (!authenticated) {
    return <AuthPage onAuthenticated={() => setAuthenticated(true)} />;
  }

  return (
    <div className="app-container">
      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <aside className="sidebar">
        <div className="brand" style={{ justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div className="brand-icon"><BrainCircuit size={20} /></div>
            <div className="brand-text">MemTrace</div>
          </div>
          <button
            className="btn-secondary"
            style={{ padding: '6px 10px', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem' }}
            onClick={() => i18n.changeLanguage(i18n.language === 'zh-TW' ? 'en' : 'zh-TW')}
          >
            <Globe size={14} />
            {i18n.language === 'zh-TW' ? 'EN' : '中文'}
          </button>
        </div>

        {/* Workspace selector */}
        <div ref={wsMenuRef} style={{ position: 'relative', padding: '0 16px 12px' }}>
          <button
            onClick={() => setWsMenuOpen(o => !o)}
            style={{
              width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '8px 12px', background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)', borderRadius: 8, cursor: 'pointer',
              color: 'var(--text-primary)', fontSize: 13,
            }}
          >
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {selectedWs ? (i18n.language === 'zh-TW' ? selectedWs.name_zh : selectedWs.name_en) : 'Select workspace…'}
            </span>
            <ChevronDown size={14} />
          </button>
          {wsMenuOpen && (
            <div style={{
              position: 'absolute', top: '100%', left: 16, right: 16, zIndex: 50,
              background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
              borderRadius: 8, overflow: 'hidden', boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
            }}>
              {wsList.map(ws => (
                <div
                  key={ws.id}
                  onClick={() => { setSelectedWs(ws); setWsMenuOpen(false); }}
                  style={{
                    padding: '9px 14px', cursor: 'pointer', fontSize: 13,
                    background: selectedWs?.id === ws.id ? 'var(--accent-color)' : 'transparent',
                    color: selectedWs?.id === ws.id ? '#fff' : 'var(--text-primary)',
                  }}
                >
                  {i18n.language === 'zh-TW' ? ws.name_zh : ws.name_en}
                </div>
              ))}
              {wsList.length === 0 && (
                <div style={{ padding: '9px 14px', fontSize: 13, color: 'var(--text-muted)' }}>
                  No workspaces yet
                </div>
              )}
            </div>
          )}
        </div>

        <nav>
          <div
            className={`nav-item ${currentView === 'graph' ? 'active' : ''}`}
            onClick={() => setCurrentView('graph')}
          >
            <Network size={18} />
            2D {t('sidebar.graph')}
          </div>
          <div
            className={`nav-item ${currentView === 'graph3d' ? 'active' : ''}`}
            onClick={() => setCurrentView('graph3d')}
          >
            <Layers size={18} />
            3D {t('sidebar.graph')}
          </div>
          <div className="nav-item">
            <Search size={18} />
            {t('sidebar.explore')}
          </div>

          {selectedWs && (
            <div
              className="nav-item"
              style={{ marginTop: 8, color: 'var(--accent-color)' }}
              onClick={() => setEditingNode(null)}
            >
              <PlusCircle size={18} />
              New Node
            </div>
          )}
        </nav>

        <div style={{ marginTop: 'auto' }}>
          {user && (
            <div style={{ padding: '10px 16px', fontSize: 12, color: 'var(--text-muted)', borderTop: '1px solid var(--border-color)' }}>
              {user.display_name}
            </div>
          )}
          <div className="nav-item" onClick={handleLogout}>
            <LogOut size={18} />
            Sign Out
          </div>
          <div className="nav-item">
            <Settings size={18} />
            {t('sidebar.settings')}
          </div>
        </div>
      </aside>

      {/* ── Main content ─────────────────────────────────────────────────── */}
      {currentView === 'graph' && (
        <GraphView
          wsId={selectedWs?.id}
          reloadKey={graphVersion}
          onEditNode={node => setEditingNode(node)}
          onNewNode={() => setEditingNode(null)}
        />
      )}
      {currentView === 'graph3d' && <GraphView3D />}

      {/* ── NodeEditor overlay ───────────────────────────────────────────── */}
      {editingNode !== undefined && selectedWs && (
        <div
          style={{
            position: 'fixed', inset: 0, zIndex: 100,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)',
          }}
          onClick={e => { if (e.target === e.currentTarget) setEditingNode(undefined); }}
        >
          <NodeEditor
            wsId={selectedWs.id}
            node={editingNode}
            onSaved={handleNodeSaved}
            onClose={() => setEditingNode(undefined)}
          />
        </div>
      )}
    </div>
  );
}
