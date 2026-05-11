import { useState, useEffect, useRef, lazy, Suspense } from 'react';
import { useTranslation } from 'react-i18next';
import { Brain, RefreshCw } from 'lucide-react';
import './index.css';
import { auth, workspaces, refreshAccessToken, isTokenStale, type Workspace, type Node as ApiNode, type Onboarding, type WorkspaceCloneJob } from './api';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import AppRouter from './AppRouter';

// Extracted Components
const OnboardingWizard = lazy(() => import('./OnboardingWizard'));
const CreateWorkspaceModal = lazy(() => import('./components/CreateWorkspaceModal'));
const ForkWorkspaceModal = lazy(() => import('./components/ForkWorkspaceModal'));
const NodeEditor = lazy(() => import('./NodeEditor'));
const AiChatPanel = lazy(() => import('./components/AiChatPanel'));

type User = { id: string; display_name: string; email: string; email_verified: boolean };
type View = 'graph' | 'analytics' | 'node_health' | 'settings' | 'review' | 'ws_settings' | 'ingest';

export default function App() {
  const { i18n } = useTranslation();

  // ── Theme & Language ──────────────────────────────────────────────────
  const [theme, setTheme] = useState(() => localStorage.getItem('mt_theme') || 'dark');
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => {
      const next = prev === 'dark' ? 'light' : 'dark';
      localStorage.setItem('mt_theme', next);
      return next;
    });
  };

  const switchLanguage = (next: string) => {
    i18n.changeLanguage(next);
    localStorage.setItem('mt_lang', next);
  };

  useEffect(() => {
    const saved = localStorage.getItem('mt_lang');
    if (saved) i18n.changeLanguage(saved);
  }, [i18n]);

  // ── Sidebar ───────────────────────────────────────────────────────────────
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => localStorage.getItem('mt_sidebar_collapsed') === 'true');
  const toggleSidebar = () => {
    setSidebarCollapsed(prev => {
      const next = !prev;
      localStorage.setItem('mt_sidebar_collapsed', String(next));
      return next;
    });
  };

  // ── Auth ──────────────────────────────────────────────────────────────────
  const [authenticated, setAuthenticated] = useState<boolean>(false);
  const [authChecking, setAuthChecking] = useState<boolean>(true);
  const [user, setUser] = useState<User | null>(null);
  const [onboarding, setOnboarding] = useState<Onboarding | null>(null);

  // Validate token before any data loads — prevents race condition where
  // workspaces.list() fires with an expired token and gets public-only data (200, not 401).
  useEffect(() => {
    const init = async () => {
      const stored = localStorage.getItem('mt_token');
      if (!stored) { setAuthChecking(false); return; }

      if (isTokenStale(stored)) {
        // Token expired or expiring soon — refresh before setting authenticated
        const refreshed = await refreshAccessToken();
        if (!refreshed) {
          localStorage.removeItem('mt_token');
          setAuthChecking(false);
          return;
        }
      }

      // Token is valid — now safe to set authenticated and load data
      setAuthenticated(true);
      setAuthChecking(false);
    };
    init();
  }, []);

  useEffect(() => {
    if (authenticated) {
      auth.me()
        .then(u => setUser(u))
        .catch(() => { localStorage.removeItem('mt_token'); setAuthenticated(false); });

      auth.getOnboarding()
        .then(o => setOnboarding(o))
        .catch(() => {});
    }
  }, [authenticated]);

  useEffect(() => {
    const onExpired = () => {
      localStorage.removeItem('mt_token');
      setAuthenticated(false);
      setUser(null);
      setSelectedWs(null);
      setWsList([]);
    };
    window.addEventListener('mt:session-expired', onExpired);
    return () => window.removeEventListener('mt:session-expired', onExpired);
  }, []);

  const handleUpdateOnboarding = async (data: Partial<Onboarding>) => {
    if (!onboarding) return;
    try {
      const updated = await auth.updateOnboarding(data);
      setOnboarding(updated);
    } catch (e) {}
  };

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
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [showCreateWs, setShowCreateWs] = useState(false);
  const [showForkWs, setShowForkWs] = useState<Workspace | null>(null);
  const wsMenuRef = useRef<HTMLDivElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);

  const canWrite = !!(selectedWs && selectedWs.my_role && ['admin', 'editor', 'owner'].includes(selectedWs.my_role));

  useEffect(() => {
    const onDeleted = (e: any) => {
      const deletedId = e.detail?.wsId;
      if (!deletedId) return;
      setWsList(prev => prev.filter(w => w.id !== deletedId));
      if (selectedWs?.id === deletedId) {
        setSelectedWs(null);
        setCurrentView('graph');
      }
    };
    window.addEventListener('workspace-deleted', onDeleted);
    return () => window.removeEventListener('workspace-deleted', onDeleted);
  }, [selectedWs]);

  useEffect(() => {
    if (!authenticated) return;
    workspaces.list().then(list => {
      setWsList(list);
      if (list.length > 0 && !selectedWs) setSelectedWs(list[0]);
    }).catch(() => {});
  }, [authenticated]);

  const [cloneJob, setCloneJob] = useState<WorkspaceCloneJob | null>(null);
  const [cancellingJob, setCancellingJob] = useState(false);

  useEffect(() => {
    if (!selectedWs) {
      setCloneJob(null);
      return;
    }
    let timer: any;
    const poll = async () => {
      try {
        const job = await workspaces.getCloneStatus(selectedWs.id);
        setCloneJob(job);
        if (job && ['pending', 'running', 'cancelling'].includes(job.status)) {
          timer = setTimeout(poll, 3000);
        } else {
          setCancellingJob(false);
        }
      } catch {
        setCloneJob(null);
      }
    };
    poll();
    return () => clearTimeout(timer);
  }, [selectedWs?.id]);

  useEffect(() => {
    if (selectedWs) {
      const name = i18n.language === 'zh-TW' ? selectedWs.name_zh : selectedWs.name_en;
      document.title = `${name} - MemTrace`;
    } else {
      document.title = 'MemTrace';
    }
  }, [selectedWs, i18n.language]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wsMenuRef.current && !wsMenuRef.current.contains(e.target as Node)) {
        setWsMenuOpen(false);
      }
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // ── Navigation & View State ──────────────────────────────────────────────
  const [currentView, setCurrentView] = useState<View>('graph');
  const [editingNode, setEditingNode] = useState<ApiNode | null | undefined>(undefined);
  const [sourceNodeId, setSourceNodeId] = useState<string | undefined>(undefined);
  const [graphVersion, setGraphVersion] = useState(0);
  const [showChat, setShowChat] = useState(false);
  const [showMcpStatus, setShowMcpStatus] = useState(false);
  const [pageSubtitle, setPageSubtitle] = useState('');

  useEffect(() => {
    const handler = (e: any) => {
      if (e.detail?.subtitle !== undefined) setPageSubtitle(e.detail.subtitle);
    };
    window.addEventListener('mt:update-header', handler);
    return () => window.removeEventListener('mt:update-header', handler);
  }, []);

  if (authChecking) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: 'var(--bg-base)' }}>
        <RefreshCw size={24} className="animate-spin" style={{ color: 'var(--text-muted)' }} />
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* ── Modals & Wizard ────────────────────────────────────────── */}
      <Suspense fallback={null}>
        {onboarding && !onboarding.completed && (
          <OnboardingWizard
            user={user}
            state={onboarding}
            onUpdate={handleUpdateOnboarding}
            onComplete={async () => {
              await handleUpdateOnboarding({ completed: true });
              const list = await workspaces.list();
              setWsList(list);
              if (list.length > 0 && !selectedWs) {
                setSelectedWs(list[0]);
                setCurrentView('ingest');
              }
            }}
            onOpenSpecKb={() => {
              const specKb = wsList.find(ws => ws.id === 'ws_spec0001');
              if (specKb) setSelectedWs(specKb);
            }}
          />
        )}
        {showCreateWs && (
          <CreateWorkspaceModal
            onCreated={(ws) => {
              setWsList(prev => [ws, ...prev]);
              setSelectedWs(ws);
              setShowCreateWs(false);
              setCurrentView('ingest');
            }}
            onClose={() => setShowCreateWs(false)}
          />
        )}
        {showForkWs && (
          <ForkWorkspaceModal
            sourceWs={showForkWs}
            onForked={(job, targetWs) => {
              setShowForkWs(null);
              setWsList(prev => [targetWs, ...prev]);
              setSelectedWs(targetWs);
              setCloneJob(job);
            }}
            onClose={() => setShowForkWs(null)}
          />
        )}
      </Suspense>

      {/* ── Layout ──────────────────────────────────────────────────────── */}
      {authenticated && (
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={toggleSidebar}
          selectedWs={selectedWs}
          onSelectWs={setSelectedWs}
          wsList={wsList}
          wsMenuOpen={wsMenuOpen}
          onSetWsMenuOpen={setWsMenuOpen}
          wsMenuRef={wsMenuRef}
          currentView={currentView}
          onSetView={setCurrentView}
          user={user}
          cloneJob={cloneJob}
          cancellingJob={cancellingJob}
          onSetCancellingJob={setCancellingJob}
          onShowCreateWs={() => setShowCreateWs(true)}
          onShowForkWs={setShowForkWs}
          canWrite={canWrite}
        />
      )}

      <main className="view-port">
        <div className="workspace-content">
          {authenticated && (
            <Header
              currentView={currentView}
              pageSubtitle={pageSubtitle}
              user={user}
              userMenuOpen={userMenuOpen}
              onSetUserMenuOpen={setUserMenuOpen}
              userMenuRef={userMenuRef}
              onSetView={setCurrentView}
              onLogout={handleLogout}
              showMcpStatus={showMcpStatus}
              onSetShowMcpStatus={setShowMcpStatus}
            />
          )}

          <AppRouter
            authenticated={authenticated}
            setAuthenticated={setAuthenticated}
            user={user}
            selectedWs={selectedWs}
            currentView={currentView}
            setCurrentView={setCurrentView}
            graphVersion={graphVersion}
            setEditingNode={setEditingNode}
            theme={theme}
            toggleTheme={toggleTheme}
            language={i18n.language}
            switchLanguage={switchLanguage}
          />
        </div>
      </main>

      {/* ── Panels ──────────────────────────────────────────────────────── */}
      <aside className={`side-panel ${editingNode === undefined || currentView === 'settings' ? 'hidden' : ''}`}>
        <Suspense fallback={<div className="loading-overlay"><RefreshCw className="animate-spin" /></div>}>
          {editingNode !== undefined && selectedWs && currentView !== 'settings' && (
            <NodeEditor
              wsId={selectedWs.id}
              node={editingNode}
              onSaved={(saved: ApiNode) => {
                setEditingNode(saved);
                setGraphVersion(v => v + 1);
              }}
              onClose={() => { setEditingNode(undefined); setSourceNodeId(undefined); }}
              onSelectNode={n => {
                setSourceNodeId(editingNode?.id ?? undefined);
                setEditingNode(n);
              }}
              sourceNodeId={sourceNodeId}
            />
          )}
        </Suspense>
      </aside>

      {selectedWs && currentView === 'graph' && (
        <button
          onClick={() => setShowChat(true)}
          className={`ai-fab ${showChat ? 'hidden' : ''}`}
          style={{ right: editingNode !== undefined ? 482 : 32 }}
        >
          <Brain size={24} />
        </button>
      )}

      <aside className={`side-panel ${(!showChat || currentView !== 'graph') ? 'hidden' : ''}`} style={{ zIndex: 90 }}>
        <div style={{ width: '100%', height: '100%', overflow: 'hidden', position: 'relative', borderLeft: (showChat && currentView === 'graph') ? '1px solid var(--border-default)' : 'none' }}>
          <div style={{ width: 450, height: '100%' }}>
            <Suspense fallback={<div className="loading-overlay"><RefreshCw className="animate-spin" /></div>}>
              {selectedWs && <AiChatPanel wsId={selectedWs.id} zh={i18n.language === 'zh-TW'} />}
            </Suspense>
          </div>
        </div>
      </aside>
    </div>
  );
}
