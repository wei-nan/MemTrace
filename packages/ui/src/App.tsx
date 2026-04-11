import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Network, PlusCircle, Search, Settings,
  BrainCircuit, Globe, Layers, LogOut, ChevronDown,
  ChevronLeft, ChevronRight, PanelRightClose, PanelLeft,
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

  // ── Language ──────────────────────────────────────────────────────────────
  const switchLanguage = () => {
    const next = i18n.language === 'zh-TW' ? 'en' : 'zh-TW';
    i18n.changeLanguage(next);
    localStorage.setItem('mt_lang', next);
  };

  useEffect(() => {
    const saved = localStorage.getItem('mt_lang');
    if (saved) i18n.changeLanguage(saved);
  }, []);

  // ── Sidebar Collapse ──────────────────────────────────────────────────────
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => localStorage.getItem('mt_sidebar_collapsed') === 'true');
  const toggleSidebar = () => {
    setSidebarCollapsed(prev => {
      const next = !prev;
      localStorage.setItem('mt_sidebar_collapsed', String(next));
      return next;
    });
  };

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

  // ── Side Panel (Node Details) ──────────────────────────────────────────────
  // undefined  = panel closed
  // null       = create new node
  // ApiNode    = edit existing node
  const [editingNode, setEditingNode] = useState<ApiNode | null | undefined>(undefined);
  const [graphVersion, setGraphVersion] = useState(0);

  const handleNodeSaved = (saved: ApiNode) => {
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
      <aside className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
        <button className="sidebar-toggle" onClick={toggleSidebar}>
          {sidebarCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>

        <div className="brand" style={{ justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div className="brand-icon"><BrainCircuit size={20} /></div>
            {!sidebarCollapsed && <div className="brand-text">MemTrace</div>}
          </div>
        </div>

        {/* Workspace selector */}
        {!sidebarCollapsed && (
          <div ref={wsMenuRef} style={{ position: 'relative', padding: '0 0 12px' }}>
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
                position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 50,
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
              </div>
            )}
          </div>
        )}

        <nav style={{ flex: 1 }}>
          <div className={`nav-item ${currentView === 'graph' ? 'active' : ''}`} onClick={() => setCurrentView('graph')}>
            <Network size={18} />
            {!sidebarCollapsed && <span className="nav-text">2D {t('sidebar.graph')}</span>}
          </div>
          <div className={`nav-item ${currentView === 'graph3d' ? 'active' : ''}`} onClick={() => setCurrentView('graph3d')}>
            <Layers size={18} />
            {!sidebarCollapsed && <span className="nav-text">3D {t('sidebar.graph')}</span>}
          </div>
          <div className="nav-item">
            <Search size={18} />
            {!sidebarCollapsed && <span className="nav-text">{t('sidebar.explore')}</span>}
          </div>

          {!sidebarCollapsed && selectedWs && (
            <div className="nav-item" style={{ marginTop: 8, color: 'var(--accent-color)' }} onClick={() => setEditingNode(null)}>
              <PlusCircle size={18} />
              <span className="nav-text">New Node</span>
            </div>
          )}
        </nav>

        <div style={{ marginTop: 'auto' }}>
          <div className="nav-item" onClick={switchLanguage}>
            <Globe size={18} />
            {!sidebarCollapsed && <span className="nav-text">{i18n.language === 'zh-TW' ? 'Switch to English' : '切換至中文'}</span>}
          </div>
          
          {!sidebarCollapsed && user && (
            <div style={{ padding: '10px 16px', fontSize: 12, color: 'var(--text-muted)', borderTop: '1px solid var(--panel-border)' }} className="user-info">
              {user.display_name}
            </div>
          )}
          
          <div className="nav-item" onClick={handleLogout}>
            <LogOut size={18} />
            {!sidebarCollapsed && <span className="nav-text">Sign Out</span>}
          </div>
          <div className="nav-item">
            <Settings size={18} />
            {!sidebarCollapsed && <span className="nav-text">{t('sidebar.settings')}</span>}
          </div>
        </div>
      </aside>

      {/* ── Main Viewport ────────────────────────────────────────────────── */}
      <main className="view-port">
        {currentView === 'graph' && (
          <GraphView
            wsId={selectedWs?.id}
            reloadKey={graphVersion}
            onEditNode={node => setEditingNode(node)}
            onNewNode={() => setEditingNode(null)}
          />
        )}
        {currentView === 'graph3d' && (
          <GraphView3D
            wsId={selectedWs?.id}
            reloadKey={graphVersion}
            onEditNode={node => setEditingNode(node)}
          />
        )}
      </main>

      {/* ── Integrated Side Panel ────────────────────────────────────────── */}
      <aside className={`side-panel ${editingNode === undefined ? 'hidden' : ''}`}>
        {editingNode !== undefined && selectedWs && (
          <NodeEditor
            wsId={selectedWs.id}
            node={editingNode}
            onSaved={handleNodeSaved}
            onClose={() => setEditingNode(undefined)}
          />
        )}
      </aside>
    </div>
  );
}
