import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Network, PlusCircle, Search, Settings,
  BrainCircuit, Globe, Layers, LogOut, ChevronDown,
  ChevronLeft, ChevronRight, X, Key, Coins, Trash2,
} from 'lucide-react';
import './index.css';
import AuthPage from './AuthPage';
import GraphView from './GraphView';
import GraphView3D from './GraphView3D';
import NodeEditor from './NodeEditor';
import ReviewQueue from './ReviewQueue';
import IngestButton from './IngestButton';
import OnboardingWizard from './OnboardingWizard';
import WorkspaceSettings from './WorkspaceSettings';
import { Inbox, Users, Mail } from 'lucide-react';
import { auth, workspaces, ai, type Workspace, type Node as ApiNode, type AIKey, type CreditStatus, type Onboarding } from './api';

type User = { id: string; display_name: string; email: string; email_verified: boolean };
type View = 'graph' | 'graph3d' | 'settings' | 'review' | 'ws_settings';

// ── CreateWorkspaceModal ───────────────────────────────────────────────────────

function CreateWorkspaceModal({
  onCreated,
  onClose,
}: {
  onCreated: (ws: Workspace) => void;
  onClose: () => void;
}) {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const [nameZh, setNameZh] = useState('');
  const [nameEn, setNameEn] = useState('');
  const [kbType, setKbType] = useState<'evergreen' | 'ephemeral'>('evergreen');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (!nameZh.trim() || !nameEn.trim()) {
      setError(zh ? '請填寫中英文名稱' : 'Both names are required');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const ws = await workspaces.create({
        name_zh: nameZh.trim(),
        name_en: nameEn.trim(),
        visibility: 'private',
        kb_type: kbType,
      });
      onCreated(ws);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const typeCards: { value: 'evergreen' | 'ephemeral'; label: string; desc: string }[] = [
    {
      value: 'evergreen',
      label: zh ? '長效型 (Evergreen)' : 'Evergreen',
      desc: zh
        ? '規格書、參考資料。記憶不會因時間淡化，低參考率者才會封存。'
        : 'Specs, references. Nodes never decay by time — only archived by low traversal.',
    },
    {
      value: 'ephemeral',
      label: zh ? '短效型 (Ephemeral)' : 'Ephemeral',
      desc: zh
        ? '任務日誌、排障記錄。記憶隨時間與使用頻率衰減，過時內容自動封存。'
        : 'Task logs, troubleshooting. Nodes decay over time and usage; stale content is archived.',
    },
  ];

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 200,
        background: 'rgba(0,0,0,0.7)', display: 'flex',
        alignItems: 'center', justifyContent: 'center',
      }}
      onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div style={{
        background: '#1a1d24', border: '1px solid var(--border-color)',
        borderRadius: 16, padding: 32, width: 480, maxWidth: '90vw',
        boxShadow: '0 24px 64px rgba(0,0,0,0.6)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <h2 style={{ fontSize: 18 }}>{zh ? '建立工作區' : 'Create Workspace'}</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
            <X size={18} />
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
              {zh ? '中文名稱' : 'Chinese Name'}
            </label>
            <input
              className="mt-input"
              placeholder={zh ? '例：MemTrace 規格書' : 'e.g. MemTrace Spec'}
              value={nameZh}
              onChange={e => setNameZh(e.target.value)}
            />
          </div>
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
              {zh ? '英文名稱' : 'English Name'}
            </label>
            <input
              className="mt-input"
              placeholder="e.g. MemTrace Spec"
              value={nameEn}
              onChange={e => setNameEn(e.target.value)}
            />
          </div>

          <div>
            <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 8 }}>
              {zh ? '知識庫類型（建立後不可更改）' : 'KB Type (cannot be changed after creation)'}
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              {typeCards.map(card => (
                <div
                  key={card.value}
                  onClick={() => setKbType(card.value)}
                  style={{
                    padding: '12px 14px', borderRadius: 10, cursor: 'pointer',
                    border: `2px solid ${kbType === card.value ? 'var(--accent-color)' : 'var(--border-color)'}`,
                    background: kbType === card.value ? 'rgba(99,102,241,0.12)' : 'var(--bg-secondary)',
                    transition: 'all 0.15s',
                  }}
                >
                  <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>{card.label}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.5 }}>{card.desc}</div>
                </div>
              ))}
            </div>
          </div>

          {error && <div style={{ color: 'var(--error-color)', fontSize: 13 }}>{error}</div>}

          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 8 }}>
            <button className="btn-secondary" onClick={onClose} disabled={loading}>
              {zh ? '取消' : 'Cancel'}
            </button>
            <button className="btn-primary" onClick={handleSubmit} disabled={loading}>
              {loading ? (zh ? '建立中…' : 'Creating…') : (zh ? '建立' : 'Create')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── SettingsPanel ──────────────────────────────────────────────────────────────

function SettingsPanel() {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';

  const [keys, setKeys] = useState<AIKey[]>([]);
  const [credits, setCredits] = useState<CreditStatus | null>(null);
  const [provider, setProvider] = useState<'openai' | 'anthropic'>('openai');
  const [apiKey, setApiKey] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const loadData = () => {
    ai.listKeys().then(setKeys).catch(() => {});
    ai.getCredits().then(setCredits).catch(() => {});
  };

  useEffect(() => { loadData(); }, []);

  const handleSaveKey = async () => {
    if (apiKey.length < 10) {
      setError(zh ? 'API Key 太短' : 'API key too short');
      return;
    }
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      await ai.createKey({ provider, api_key: apiKey });
      setApiKey('');
      setSuccess(zh ? '已儲存' : 'Saved');
      loadData();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteKey = async (p: string) => {
    if (!confirm(zh ? `確定要刪除 ${p} 的 API Key？` : `Delete ${p} API key?`)) return;
    try {
      await ai.deleteKey(p);
      loadData();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const providers = [
    { value: 'openai', label: 'OpenAI' },
    { value: 'anthropic', label: 'Anthropic (Claude)' },
  ] as const;

  return (
    <div style={{ padding: 40, maxWidth: 600, margin: '0 auto' }}>
      <h2 style={{ fontSize: 22, marginBottom: 32 }}>{zh ? '設定' : 'Settings'}</h2>

      {/* Free Credits */}
      <section style={{ marginBottom: 40 }}>
        <h3 style={{ fontSize: 15, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Coins size={16} style={{ color: 'var(--accent-color)' }} />
          {zh ? '免費 AI 額度' : 'Free AI Credits'}
        </h3>
        {credits ? (
          <div style={{
            background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
            borderRadius: 12, padding: 20,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
              <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                {zh ? '本月已用' : 'Used this month'}
              </span>
              <span style={{ fontSize: 13 }}>
                {credits.free_used.toLocaleString()} / {credits.free_limit.toLocaleString()} tokens
              </span>
            </div>
            <div style={{ height: 6, background: 'var(--border-color)', borderRadius: 3, overflow: 'hidden' }}>
              <div style={{
                height: '100%', borderRadius: 3,
                background: 'linear-gradient(90deg, var(--gradient-start), var(--gradient-end))',
                width: `${Math.min(100, (credits.free_used / credits.free_limit) * 100)}%`,
                transition: 'width 0.4s',
              }} />
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
              {credits.free_remaining.toLocaleString()} {zh ? 'tokens 剩餘' : 'tokens remaining'}
            </div>
          </div>
        ) : (
          <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>
            {zh ? '載入中…' : 'Loading…'}
          </div>
        )}
      </section>

      {/* API Keys */}
      <section style={{ marginBottom: 40 }}>
        <h3 style={{ fontSize: 15, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Key size={16} style={{ color: 'var(--accent-color)' }} />
          {zh ? '個人 API Key' : 'Personal API Keys'}
        </h3>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
          {zh
            ? '提供自己的 API Key 可超越免費額度限制，Key 使用 AES-256 加密儲存。'
            : 'Add your own key to bypass the free tier limit. Keys are stored AES-256 encrypted.'}
        </p>

        {/* Existing keys */}
        {keys.length > 0 && (
          <div style={{ marginBottom: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
            {keys.map(k => (
              <div key={k.id} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
                borderRadius: 8, padding: '10px 14px',
              }}>
                <div>
                  <span style={{ fontSize: 13, fontWeight: 500 }}>{k.provider}</span>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 10 }}>
                    ····{k.key_hint}
                  </span>
                </div>
                <button
                  onClick={() => handleDeleteKey(k.provider)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex', alignItems: 'center' }}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Add key form */}
        <div style={{
          background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
          borderRadius: 12, padding: 20, display: 'flex', flexDirection: 'column', gap: 12,
        }}>
          <div style={{ display: 'flex', gap: 10 }}>
            {providers.map(p => (
              <button
                key={p.value}
                onClick={() => setProvider(p.value)}
                style={{
                  padding: '6px 14px', borderRadius: 20, fontSize: 12, cursor: 'pointer',
                  border: `1px solid ${provider === p.value ? 'var(--accent-color)' : 'var(--border-color)'}`,
                  background: provider === p.value ? 'rgba(99,102,241,0.18)' : 'transparent',
                  color: provider === p.value ? 'var(--accent-color)' : 'var(--text-muted)',
                }}
              >
                {p.label}
              </button>
            ))}
          </div>
          <input
            className="mt-input"
            type="password"
            placeholder={provider === 'openai' ? 'sk-...' : 'sk-ant-...'}
            value={apiKey}
            onChange={e => setApiKey(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleSaveKey(); }}
          />
          {error && <div style={{ color: 'var(--error-color)', fontSize: 12 }}>{error}</div>}
          {success && <div style={{ color: '#4ade80', fontSize: 12 }}>{success}</div>}
          <button className="btn-primary" onClick={handleSaveKey} disabled={saving} style={{ alignSelf: 'flex-start' }}>
            {saving ? (zh ? '儲存中…' : 'Saving…') : (zh ? '儲存 API Key' : 'Save API Key')}
          </button>
        </div>
      </section>
    </div>
  );
}

// ── App ────────────────────────────────────────────────────────────────────────

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
  const [authenticated, setAuthenticated] = useState<boolean>(!!localStorage.getItem('mt_token'));
  const [user, setUser] = useState<User | null>(null);
  const [onboarding, setOnboarding] = useState<Onboarding | null>(null);

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
  const [showCreateWs, setShowCreateWs] = useState(false);
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

  const handleWsCreated = (ws: Workspace) => {
    setWsList(prev => [ws, ...prev]);
    setSelectedWs(ws);
    setShowCreateWs(false);
  };

  // ── Navigation ────────────────────────────────────────────────────────────
  const [currentView, setCurrentView] = useState<View>('graph');

  // ── Side Panel (Node Details) ──────────────────────────────────────────────
  // undefined  = panel closed
  // null       = create new node
  // ApiNode    = edit existing node
  const [editingNode, setEditingNode] = useState<ApiNode | null | undefined>(undefined);
  const [sourceNodeId, setSourceNodeId] = useState<string | undefined>(undefined);
  const [graphVersion, setGraphVersion] = useState(0);

  const handleNodeSaved = (saved: ApiNode) => {
    setEditingNode(saved);
    setGraphVersion(v => v + 1);
  };

  // ── Render ────────────────────────────────────────────────────────────────
  if (!authenticated) {
    return <AuthPage onAuthenticated={() => setAuthenticated(true)} />;
  }

  const zh = i18n.language === 'zh-TW';

  return (
    <div className="app-container">
      {/* ── Onboarding Wizard ─────────────────────────────────────────── */}
      {onboarding && !onboarding.completed && (
        <OnboardingWizard 
          state={onboarding} 
          onUpdate={handleUpdateOnboarding}
          onComplete={() => handleUpdateOnboarding({ completed: true })}
        />
      )}

      {/* ── Create Workspace Modal ──────────────────────────────────────── */}
      {showCreateWs && (
        <CreateWorkspaceModal
          onCreated={handleWsCreated}
          onClose={() => setShowCreateWs(false)}
        />
      )}

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
                {selectedWs ? (zh ? selectedWs.name_zh : selectedWs.name_en) : (zh ? '選擇工作區…' : 'Select workspace…')}
              </span>
              <ChevronDown size={14} />
            </button>
            {wsMenuOpen && (
              <div style={{
                position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 50,
                background: '#1a1d24', border: '1px solid var(--border-color)',
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
                    {zh ? ws.name_zh : ws.name_en}
                    <span style={{ fontSize: 10, opacity: 0.6, marginLeft: 6 }}>{ws.kb_type}</span>
                  </div>
                ))}
                {/* New workspace button */}
                <div
                  onClick={() => { setWsMenuOpen(false); setShowCreateWs(true); }}
                  style={{
                    padding: '9px 14px', cursor: 'pointer', fontSize: 13,
                    borderTop: '1px solid var(--border-color)',
                    color: 'var(--accent-color)',
                    display: 'flex', alignItems: 'center', gap: 6,
                  }}
                >
                  <PlusCircle size={13} />
                  {zh ? '新增工作區…' : 'New workspace…'}
                </div>
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

          {!sidebarCollapsed && selectedWs && currentView !== 'settings' && (
            <div className="nav-item" style={{ marginTop: 8, color: 'var(--accent-color)' }} onClick={() => setEditingNode(null)}>
              <PlusCircle size={18} />
              <span className="nav-text">{zh ? '新增節點' : 'New Node'}</span>
            </div>
          )}

          {!sidebarCollapsed && selectedWs && (
            <div className={`nav-item ${currentView === 'review' ? 'active' : ''}`} style={{ marginTop: 4 }} onClick={() => setCurrentView('review')}>
              <Inbox size={18} />
              <span className="nav-text">{zh ? '審核佇列' : 'Review Queue'}</span>
            </div>
          )}
          {!sidebarCollapsed && selectedWs && (
            <div className={`nav-item ${currentView === 'ws_settings' ? 'active' : ''}`} style={{ marginTop: 4 }} onClick={() => setCurrentView('ws_settings')}>
              <Users size={18} />
              <span className="nav-text">{zh ? '成員管理' : 'Workspace Members'}</span>
            </div>
          )}
        </nav>

        {!sidebarCollapsed && selectedWs && (
          <div style={{ padding: '4px 0 16px' }}>
            <IngestButton wsId={selectedWs.id} onStarted={() => setCurrentView('review')} />
          </div>
        )}

        <div style={{ marginTop: 'auto' }}>
          {!sidebarCollapsed && user && !user.email_verified && (
            <div style={{
              margin: '0 12px 12px', padding: '10px 12px', borderRadius: 8,
              background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)',
              display: 'flex', flexDirection: 'column', gap: 6
            }}>
              <div style={{ fontSize: 11, color: '#f59e0b', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}>
                <Mail size={12} /> {zh ? '信箱未驗證' : 'Email Unverified'}
              </div>
              <button 
                onClick={() => auth.resendVerification().then(() => alert(zh ? '已送出' : 'Sent!'))}
                style={{ background: 'none', border: 'none', color: 'var(--accent-color)', fontSize: 10, cursor: 'pointer', textAlign: 'left', padding: 0 }}
              >
                {zh ? '重新發送驗證信' : 'Resend verification'}
              </button>
            </div>
          )}

          <div className="nav-item" onClick={switchLanguage}>
            <Globe size={18} />
            {!sidebarCollapsed && <span className="nav-text">{zh ? 'Switch to English' : '切換至中文'}</span>}
          </div>

          {!sidebarCollapsed && user && (
            <div style={{ padding: '10px 16px', fontSize: 12, color: 'var(--text-muted)', borderTop: '1px solid var(--panel-border)' }}>
              {user.display_name}
            </div>
          )}

          <div className={`nav-item ${currentView === 'settings' ? 'active' : ''}`} onClick={() => setCurrentView('settings')}>
            <Settings size={18} />
            {!sidebarCollapsed && <span className="nav-text">{t('sidebar.settings')}</span>}
          </div>
          <div className="nav-item" onClick={handleLogout}>
            <LogOut size={18} />
            {!sidebarCollapsed && <span className="nav-text">{zh ? '登出' : 'Sign Out'}</span>}
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
        {currentView === 'settings' && <SettingsPanel />}
        {currentView === 'review' && selectedWs && (
          <ReviewQueue wsId={selectedWs.id} onClose={() => setCurrentView('graph')} />
        )}
        {currentView === 'ws_settings' && selectedWs && (
          <div style={{ padding: 40, maxWidth: 800, margin: '0 auto' }}>
             <h2 style={{ fontSize: 22, marginBottom: 32 }}>{zh ? '工作區設定' : 'Workspace Settings'}</h2>
             <WorkspaceSettings wsId={selectedWs.id} />
          </div>
        )}
      </main>

      {/* ── Integrated Side Panel ────────────────────────────────────────── */}
      <aside className={`side-panel ${editingNode === undefined || currentView === 'settings' ? 'hidden' : ''}`}>
        {editingNode !== undefined && selectedWs && currentView !== 'settings' && (
          <NodeEditor
            wsId={selectedWs.id}
            node={editingNode}
            onSaved={handleNodeSaved}
            onClose={() => { setEditingNode(undefined); setSourceNodeId(undefined); }}
            onSelectNode={n => {
              setSourceNodeId(editingNode?.id ?? undefined);
              setEditingNode(n);
            }}
            sourceNodeId={sourceNodeId}
          />
        )}
      </aside>
    </div>
  );
}
