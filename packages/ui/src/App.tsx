import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Network, PlusCircle, Settings,
  Globe, LogOut, ChevronDown,
  ChevronLeft, ChevronRight, X, Key, Trash2,
  Inbox, Users, Mail, Moon, Sun, Brain
} from 'lucide-react';
import './index.css';
import AiChatPanel from './components/AiChatPanel';
import AuthPage from './AuthPage';
import GraphContainer from './GraphContainer';
import NodeEditor from './NodeEditor';
import ReviewQueue from './ReviewQueue';
import IngestButton from './IngestButton';
import IngestionHistory from './IngestionHistory';
import OnboardingWizard from './OnboardingWizard';
import WorkspaceSettings from './WorkspaceSettings';
import { auth, workspaces, ai, type Workspace, type Node as ApiNode, type AIKey, type Onboarding } from './api';
import { useModal } from './components/ModalContext';
import { ErrorBoundary } from './components/ErrorBoundary';

type User = { id: string; display_name: string; email: string; email_verified: boolean };
type View = 'graph' | 'settings' | 'review' | 'ws_settings' | 'ingest';

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
        background: 'var(--bg-overlay)', display: 'flex',
        alignItems: 'center', justifyContent: 'center',
      }}
      onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div style={{
        background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
        borderRadius: 16, padding: 32, width: 480, maxWidth: '90vw',
        boxShadow: 'var(--shadow-lg)',
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
              placeholder={zh ? '例：我的知識庫' : 'e.g. My Knowledge Base'}
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
                    border: `2px solid ${kbType === card.value ? 'var(--color-primary)' : 'var(--border-default)'}`,
                    background: kbType === card.value ? 'var(--color-primary-subtle)' : 'var(--bg-surface)',
                    transition: 'all 0.15s',
                  }}
                >
                  <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>{card.label}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.5 }}>{card.desc}</div>
                </div>
              ))}
            </div>
          </div>

          {error && <div style={{ color: 'var(--color-error)', fontSize: 13 }}>{error}</div>}

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

function SettingsPanel({
  user,
  theme,
  toggleTheme,
  language,
  switchLanguage,
}: {
  user: any;
  theme: string;
  toggleTheme: () => void;
  language: string;
  switchLanguage: () => void;
}) {
  useTranslation();
  const zh = language === 'zh-TW';
  const { confirm, toast } = useModal();

  const [keys, setKeys] = useState<AIKey[]>([]);
  const [provider, setProvider] = useState<'openai' | 'anthropic' | 'gemini'>('openai');
  const [apiKey, setApiKey] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const loadData = () => {
    ai.listKeys().then(setKeys).catch(() => {});
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
    const ok = await confirm({
      title: zh ? '刪除 API Key' : 'Delete API Key',
      message: zh ? `確定要刪除 ${p} 的 API Key？` : `Delete ${p} API key?`,
      variant: 'danger',
      confirmLabel: zh ? '刪除' : 'Delete',
    });
    if (!ok) return;
    try {
      await ai.deleteKey(p);
      loadData();
      toast({ message: zh ? 'API Key 已刪除' : 'API key deleted', variant: 'success' });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const providers = [
    { value: 'openai', label: 'OpenAI' },
    { value: 'anthropic', label: 'Anthropic (Claude)' },
    { value: 'gemini', label: 'Google Gemini' },
  ] as const;

  return (
    <div style={{ padding: 40, maxWidth: 600, margin: '0 auto' }}>
      <h2 style={{ fontSize: 22, marginBottom: 32 }}>{zh ? '系統設定' : 'Settings'}</h2>

      {/* Preferences Section */}
      <section style={{ marginBottom: 40 }}>
        <h3 style={{ fontSize: 15, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Settings size={16} style={{ color: 'var(--color-primary)' }} />
          {zh ? '偏好設定' : 'Preferences'}
        </h3>
        <div style={{
          background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
          borderRadius: 12, padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 16
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 14 }}>{zh ? '外觀模式' : 'Theme Mode'}</span>
            <button className="btn-secondary" onClick={toggleTheme} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 16px' }}>
              {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
              {theme === 'dark' ? (zh ? '亮色模式' : 'Light Mode') : (zh ? '暗色模式' : 'Dark Mode')}
            </button>
          </div>
          <div style={{ borderTop: '1px solid var(--border-subtle)' }} />
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 14 }}>{zh ? '語言' : 'Language'}</span>
            <button className="btn-secondary" onClick={switchLanguage} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 16px' }}>
              <Globe size={14} />
              {zh ? 'Switch to English' : '切換至中文'}
            </button>
          </div>
        </div>
      </section>

      {/* Account Status / Email Verification */}
      {!user?.email_verified && (
        <section style={{ marginBottom: 40 }}>
          <h3 style={{ fontSize: 15, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Mail size={16} style={{ color: 'var(--color-warning)' }} />
            {zh ? '帳號安全' : 'Account Security'}
          </h3>
          <div style={{
            background: 'var(--color-warning-subtle)', border: '1px solid var(--color-warning)',
            borderRadius: 12, padding: '20px', display: 'flex', flexDirection: 'column', gap: 12
          }}>
            <div style={{ fontSize: 14, color: 'var(--color-warning)', fontWeight: 600 }}>
              {zh ? '電子信箱尚未驗證' : 'Email Address Not Verified'}
            </div>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: 0 }}>
              {zh ? '請驗證您的信箱以啟用完整功能，包括跨裝置同步與協作工具。' : 'Please verify your email to enable full features including sync and collaboration.'}
            </p>
            <button
              className="btn-primary"
              style={{ alignSelf: 'flex-start', background: 'var(--color-warning)', borderColor: 'var(--color-warning)', color: 'white' }}
              onClick={async () => {
                try {
                  await auth.resendVerification();
                  toast({ message: zh ? '驗證信已送出' : 'Verification email sent', variant: 'success' });
                } catch (e: any) {
                  toast({ message: e.message, variant: 'error' });
                }
              }}
            >
              {zh ? '立即發送驗證信' : 'Resend Verification Email'}
            </button>
          </div>
        </section>
      )}

      {/* API Keys */}
      <section style={{ marginBottom: 40 }}>
        <h3 style={{ fontSize: 15, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Key size={16} style={{ color: 'var(--color-primary)' }} />
          {zh ? '個人 API Key' : 'Personal API Keys'}
        </h3>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
          {zh
            ? '請提供自己的 AI Provider API Key 以啟用節點提取、語意搜尋與 AI 助手功能。'
            : 'Please provide your own AI provider API key to enable extraction, semantic search, and AI assistant.'}
        </p>

        {/* Existing keys */}
        {keys.length > 0 && (
          <div style={{ marginBottom: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
            {keys.map(k => (
              <div key={k.id} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
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
          background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
          borderRadius: 12, padding: 20, display: 'flex', flexDirection: 'column', gap: 12,
        }}>
          <div style={{ display: 'flex', gap: 10 }}>
            {providers.map(p => (
              <button
                key={p.value}
                onClick={() => setProvider(p.value)}
                style={{
                  padding: '6px 14px', borderRadius: 20, fontSize: 12, cursor: 'pointer',
                  border: `1px solid ${provider === p.value ? 'var(--color-primary)' : 'var(--border-default)'}`,
                  background: provider === p.value ? 'var(--color-primary-subtle)' : 'transparent',
                  color: provider === p.value ? 'var(--color-primary)' : 'var(--text-muted)',
                }}
              >
                {p.label}
              </button>
            ))}
          </div>
          <input
            className="mt-input"
            type="password"
            placeholder={provider === 'openai' ? 'sk-...' : provider === 'anthropic' ? 'sk-ant-...' : 'AIza...'}
            value={apiKey}
            onChange={e => setApiKey(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleSaveKey(); }}
          />
          {error && <div style={{ color: 'var(--color-error)', fontSize: 12 }}>{error}</div>}
          {success && <div style={{ color: 'var(--color-success)', fontSize: 12 }}>{success}</div>}
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
  const { i18n } = useTranslation();
  const { toast } = useModal();

  // ── Theme Management ───────────────────────────────────────────────────
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
  const [ingestRefreshKey, setIngestRefreshKey] = useState(0);
  const [showChat, setShowChat] = useState(false);

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
          user={user}
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
            <div className="brand-icon">
              <img src="/favicon.svg" alt="logo" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
            </div>
            {!sidebarCollapsed && <div className="brand-text">MemTrace</div>}
          </div>
        </div>

        {/* Workspace selector */}
        {!sidebarCollapsed && (
          <div ref={wsMenuRef} style={{ position: 'relative', padding: '0 0 12px' }}>
            <button
              onClick={() => setWsMenuOpen(o => !o)}
              className="search-bar"
              style={{
                width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '8px 12px', background: 'var(--bg-elevated)',
                border: '1px solid var(--border-default)', borderRadius: 8, cursor: 'pointer',
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
                background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
                borderRadius: 8, overflow: 'hidden', boxShadow: 'var(--shadow-lg)',
              }}>
                {wsList.map(ws => (
                  <div
                    key={ws.id}
                    onClick={() => { setSelectedWs(ws); setWsMenuOpen(false); }}
                    style={{
                      padding: '9px 14px', cursor: 'pointer', fontSize: 13,
                      background: selectedWs?.id === ws.id ? 'var(--color-primary-subtle)' : 'transparent',
                      color: selectedWs?.id === ws.id ? 'var(--color-primary)' : 'var(--text-primary)',
                      transition: 'all 0.15s'
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
                    borderTop: '1px solid var(--border-default)',
                    color: 'var(--color-primary)',
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
            {!sidebarCollapsed && <span className="nav-text">{zh ? '知識庫圖譜' : 'Knowledge Graph'}</span>}
          </div>

          {!sidebarCollapsed && selectedWs && currentView !== 'settings' && (
            <div className="nav-item" style={{ marginTop: 8, color: 'var(--color-primary)' }} onClick={() => { setCurrentView('graph'); setEditingNode(null); }}>
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
          {!sidebarCollapsed && selectedWs && (
            <div className={`nav-item ${currentView === 'ingest' ? 'active' : ''}`} style={{ marginTop: 4 }} onClick={() => setCurrentView('ingest')}>
              <Mail size={18} />
              <span className="nav-text">{zh ? '匯入文件' : 'Ingest File'}</span>
            </div>
          )}
        </nav>

        <div style={{ marginTop: 'auto' }}>
          {!sidebarCollapsed && user && (
            <div style={{ padding: '10px 16px', fontSize: 12, color: 'var(--text-muted)', borderTop: '1px solid var(--border-default)' }}>
              {user.display_name}
            </div>
          )}

          <div className={`nav-item ${currentView === 'settings' ? 'active' : ''}`} onClick={() => setCurrentView('settings')}>
            <Settings size={18} />
            {!sidebarCollapsed && <span className="nav-text">{zh ? '系統設定' : 'Settings'}</span>}
          </div>
          <div className="nav-item" onClick={handleLogout}>
            <LogOut size={18} />
            {!sidebarCollapsed && <span className="nav-text">{zh ? '登出' : 'Logout'}</span>}
          </div>
        </div>
      </aside>

      {/* ── Main Viewport ────────────────────────────────────────────────── */}
      <main className="view-port">
        <ErrorBoundary>
        {currentView === 'graph' && (
          <GraphContainer
            wsId={selectedWs?.id}
            reloadKey={graphVersion}
            onEditNode={node => setEditingNode(node)}
            onNewNode={() => setEditingNode(null)}
          />
        )}
        {currentView === 'settings' && (
          <div style={{ flex: 1, overflowY: 'auto' }}>
            <SettingsPanel 
              user={user}
              theme={theme} 
              toggleTheme={toggleTheme} 
              language={i18n.language} 
              switchLanguage={switchLanguage} 
            />
          </div>
        )}
        {currentView === 'review' && selectedWs && (
          <ReviewQueue wsId={selectedWs.id} onClose={() => setCurrentView('graph')} />
        )}
        {currentView === 'ws_settings' && selectedWs && (
          <div style={{ flex: 1, overflowY: 'auto', padding: 40 }}>
             <div style={{ maxWidth: 800, margin: '0 auto' }}>
                <h2 style={{ fontSize: 22, marginBottom: 32 }}>{zh ? '工作區設定' : 'Workspace Settings'}</h2>
                <WorkspaceSettings wsId={selectedWs.id} />
             </div>
          </div>
        )}
        {currentView === 'ingest' && selectedWs && (
          <div style={{ flex: 1, overflowY: 'auto', padding: 40 }}>
            <div style={{ maxWidth: 600, margin: '0 auto', textAlign: 'center' }}>
               <h2 style={{ fontSize: 22, marginBottom: 12 }}>{zh ? '匯入現有文件' : 'Ingest Existing File'}</h2>
               <p style={{ color: 'var(--text-muted)', marginBottom: 32 }}>
                 {zh ? '上傳 .md 或 .txt 檔案，讓 AI 幫您拆解成知識節點。' : 'Upload .md or .txt files; AI will break them into knowledge nodes.'}
               </p>
               <IngestButton 
                  wsId={selectedWs.id} 
                  onStarted={() => {
                      setIngestRefreshKey(prev => prev + 1);
                      toast({ message: zh ? '開始上傳...' : 'Starting upload...', variant: 'success' });
                  }} 
               />
               
               <IngestionHistory 
                 wsId={selectedWs.id} 
                 refreshKey={ingestRefreshKey}
                 onGoToReview={() => setCurrentView('review')}
               />

               <div style={{ marginTop: 60, padding: 24, background: 'var(--bg-elevated)', borderRadius: 16, textAlign: 'left', border: '1px solid var(--border-subtle)' }}>
                 <h4 style={{ fontSize: 14, marginBottom: 12, fontWeight: 700 }}>{zh ? '匯入說明' : 'Ingestion Tips'}</h4>
                 <ul style={{ fontSize: 13, color: 'var(--text-secondary)', paddingLeft: 20, lineHeight: 1.8, margin: 0 }}>
                   <li>{zh ? '支援格式：Markdown (.md) 與純文字 (.txt)' : 'Supported formats: Markdown (.md) and Plain Text (.txt)'}</li>
                   <li>{zh ? 'AI 會自動辨識標題、節點類型與關聯' : 'AI automatically identifies titles, types, and relations'}</li>
                   <li>{zh ? '擷取結果將進入「審核佇列」，確認後才正式存入圖譜' : 'Extractions go to the Review Queue for your final confirmation'}</li>
                   <li>{zh ? '您可以隨時離開此頁面，處理進度將在背景持續進行' : 'You can leave this page; processing continues in the background'}</li>
                 </ul>
               </div>
            </div>
          </div>
        )}
        </ErrorBoundary>
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

      {/* ── AI Chat Toggle Button ─────────────────────────────────────────── */}
      {selectedWs && currentView === 'graph' && (
        <button 
          onClick={() => setShowChat(!showChat)}
          style={{ 
            position: 'fixed', bottom: 32, right: editingNode === undefined ? 32 : 512,
            width: 56, height: 56, borderRadius: 28, 
            background: showChat ? 'var(--text-primary)' : 'var(--color-primary)',
            color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: 'var(--shadow-lg)', border: 'none', cursor: 'pointer', zIndex: 100,
            transition: 'all 0.3s ease'
          }}
        >
          {showChat ? <X size={24} /> : <Brain size={24} />}
        </button>
      )}

      {/* ── Chat Side Panel ──────────────────────────────────────────────── */}
      <aside className={`side-panel ${!showChat || currentView !== 'graph' ? 'hidden' : ''}`} style={{ zIndex: 90 }}>
         {selectedWs && <AiChatPanel wsId={selectedWs.id} zh={zh} />}
      </aside>
    </div>
  );
}
