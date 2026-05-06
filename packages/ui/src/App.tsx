import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Network, PlusCircle, Settings,
  Globe, LogOut, ChevronDown,
  ChevronLeft, ChevronRight, X, Key, Trash2, AlertTriangle, RefreshCw,
  Inbox, Users, FileUp, Mail, Moon, Sun, Brain, BarChart3, HardDrive,
  GitFork, XCircle,
} from 'lucide-react';
import './index.css';
import AiChatPanel from './components/AiChatPanel';
import AuthPage from './AuthPage';
import GraphContainer from './GraphContainer';
import NodeEditor from './NodeEditor';
import ReviewQueue from './ReviewQueue';
import IngestPage from './IngestPage';
import McpStatusPanel from './components/McpStatusPanel';
import OnboardingWizard from './OnboardingWizard';
import WorkspaceSettings from './WorkspaceSettings';
import AnalyticsDashboard from './AnalyticsDashboard';
import NodeHealthManager from './NodeHealthManager';
import ResetPasswordPage from './ResetPasswordPage';
import { Routes, Route, Navigate, Link } from 'react-router-dom';
import { auth, workspaces, ai, users, system, type Workspace, type Node as ApiNode, type AIKey, type Onboarding, type PersonalApiKey, type BackupConfig, type WorkspaceCloneJob } from './api';
import { useModal } from './components/ModalContext';
import { ErrorBoundary } from './components/ErrorBoundary';

// Phase 4.6 Pages
import PublicWorkspaceView from './PublicWorkspaceView';
import MagicLinkVerifyPage from './MagicLinkVerifyPage';
import JoinInvitationPage from './JoinInvitationPage';

type User = { id: string; display_name: string; email: string; email_verified: boolean };
type View = 'graph' | 'analytics' | 'node_health' | 'settings' | 'review' | 'ws_settings' | 'ingest';

// ── CreateWorkspaceModal ───────────────────────────────────────────────────────

// Known embedding models per provider (used when dynamic listing is unavailable)
const KNOWN_EMBED_MODELS: Record<string, { id: string; dim: number }[]> = {
  openai: [
    { id: 'text-embedding-3-small', dim: 1536 },
    { id: 'text-embedding-3-large', dim: 3072 },
    { id: 'text-embedding-ada-002', dim: 1536 },
  ],
  gemini: [
    { id: 'text-embedding-004', dim: 768 },
  ],
  anthropic: [],  // no embedding API
};

function CreateWorkspaceModal({
  onCreated,
  onClose,
}: {
  onCreated: (ws: Workspace) => void;
  onClose: () => void;
}) {
  const { t, i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const [nameZh, setNameZh] = useState('');
  const [nameEn, setNameEn] = useState('');
  const [kbType, setKbType] = useState<'evergreen' | 'ephemeral'>('evergreen');
  const [visibility, setVisibility] = useState<'private' | 'restricted' | 'conditional_public' | 'public'>('private');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [embedModels, setEmbedModels] = useState<{ id: string; dim: number }[]>([]);
  const [selectedEmbedModel, setSelectedEmbedModel] = useState<string>('');

  useEffect(() => {
    // 1. Resolve which provider / model would be used automatically
    ai.getResolvedModel('embedding').then(async resolved => {
      const provider = resolved.provider?.toLowerCase() ?? '';
      const autoModel = resolved.model ?? '';

      // 2. Build model list based on provider
      if (provider === 'ollama') {
        try {
          const all = await ai.listModels('ollama');
          const embedOnly = all.filter(m => m.model_type === 'embedding');
          const list = embedOnly.map(m => ({ id: m.id, dim: m.embedding_dim ?? 768 }));
          setEmbedModels(list.length ? list : [{ id: autoModel, dim: 768 }]);
        } catch {
          setEmbedModels([{ id: autoModel, dim: 768 }]);
        }
      } else {
        const knownList = KNOWN_EMBED_MODELS[provider] ?? [{ id: autoModel, dim: 1536 }];
        setEmbedModels(knownList.length ? knownList : [{ id: autoModel, dim: 1536 }]);
      }

      // 3. Default selection = auto-resolved model
      setSelectedEmbedModel(autoModel);
    }).catch(() => {
      // No AI provider configured; use safe default
      setEmbedModels([{ id: 'text-embedding-3-small', dim: 1536 }]);
      setSelectedEmbedModel('text-embedding-3-small');
    });
  }, []);

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
        visibility,
        kb_type: kbType,
        embedding_model: selectedEmbedModel || undefined,
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

          {/* Visibility toggle */}
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 8 }}>
              {zh ? '可見度' : 'Visibility'}
            </label>
            <select
              className="mt-input"
              value={visibility}
              onChange={e => setVisibility(e.target.value as any)}
              style={{ width: '100%' }}
            >
              <option value="private">{t('ws_settings.vis_private')}</option>
              <option value="restricted">{t('ws_settings.vis_restricted')}</option>
              <option value="conditional_public">{t('ws_settings.vis_conditional_public')}</option>
              <option value="public">{t('ws_settings.vis_public')}</option>
            </select>
            {visibility === 'public' && (
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
                {zh ? '任何人（包含未登入用戶）均可瀏覽此知識庫。' : 'Anyone, including unauthenticated users, can browse this workspace.'}
              </div>
            )}
          </div>

          {/* P4.1-E: Embedding model selector */}
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
              <Brain size={12} />
              {zh ? '向量模型（建立後鎖定）' : 'Embedding Model (locked after creation)'}
            </label>
            {embedModels.length > 1 ? (
              <select
                className="mt-input"
                value={selectedEmbedModel}
                onChange={e => setSelectedEmbedModel(e.target.value)}
                style={{ width: '100%' }}
              >
                {embedModels.map(m => (
                  <option key={m.id} value={m.id}>
                    {m.id} ({m.dim}d)
                  </option>
                ))}
              </select>
            ) : (
              <div style={{ background: 'var(--bg-elevated)', padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border-subtle)', fontSize: 12 }}>
                {selectedEmbedModel ? `${selectedEmbedModel} (${embedModels[0]?.dim ?? '?'}d)` : (zh ? '載入中…' : 'Loading…')}
              </div>
            )}
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

// ── ForkWorkspaceModal ─────────────────────────────────────────────────────────

function ForkWorkspaceModal({
  sourceWs,
  onForked,
  onClose,
}: {
  sourceWs: Workspace;
  onForked: (job: WorkspaceCloneJob, targetWs: Workspace) => void;
  onClose: () => void;
}) {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const { toast } = useModal();
  const [nameZh, setNameZh] = useState(`${sourceWs.name_zh} (Fork)`);
  const [nameEn, setNameEn] = useState(`${sourceWs.name_en} (Fork)`);
  const [embedModels, setEmbedModels] = useState<{ id: string; dim: number }[]>([]);
  const [selectedEmbedModel, setSelectedEmbedModel] = useState<string>(sourceWs.embedding_model);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    // Build embed model list: auto-resolve + inherit from source
    ai.getResolvedModel('embedding').then(async resolved => {
      const provider = resolved.provider?.toLowerCase() ?? '';
      if (provider === 'ollama') {
        try {
          const all = await ai.listModels('ollama');
          const list = all
            .filter(m => m.model_type === 'embedding')
            .map(m => ({ id: m.id, dim: m.embedding_dim ?? 768 }));
          // Ensure source model is in the list (even if not installed locally)
          if (!list.find(m => m.id === sourceWs.embedding_model)) {
            list.unshift({ id: sourceWs.embedding_model, dim: sourceWs.embedding_dim });
          }
          setEmbedModels(list.length ? list : [{ id: sourceWs.embedding_model, dim: sourceWs.embedding_dim }]);
        } catch {
          setEmbedModels([{ id: sourceWs.embedding_model, dim: sourceWs.embedding_dim }]);
        }
      } else {
        const knownList = KNOWN_EMBED_MODELS[provider] ?? [];
        const combined = [...knownList];
        if (!combined.find(m => m.id === sourceWs.embedding_model)) {
          combined.unshift({ id: sourceWs.embedding_model, dim: sourceWs.embedding_dim });
        }
        setEmbedModels(combined.length ? combined : [{ id: sourceWs.embedding_model, dim: sourceWs.embedding_dim }]);
      }
    }).catch(() => {
      setEmbedModels([{ id: sourceWs.embedding_model, dim: sourceWs.embedding_dim }]);
    });
  }, [sourceWs.embedding_model, sourceWs.embedding_dim]);

  const handleFork = async () => {
    if (!nameZh.trim() || !nameEn.trim()) {
      setError(zh ? '請填寫中英文名稱' : 'Both names are required');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const job = await workspaces.fork(sourceWs.id, {
        name_zh: nameZh.trim(),
        name_en: nameEn.trim(),
        embedding_model: selectedEmbedModel || undefined,
      });
      // Fetch the newly created target workspace to pass to the parent
      const allWs = await workspaces.list();
      const targetWs = allWs.find(w => w.id === job.target_ws_id) ?? null;
      toast({ message: zh ? `🍴 Fork 已啟動，正在背景搬移節點…` : `🍴 Fork started — migrating nodes in background…`, variant: 'info' });
      if (targetWs) onForked(job, targetWs);
      else onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

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
        borderRadius: 16, padding: 32, width: 500, maxWidth: '90vw',
        boxShadow: 'var(--shadow-lg)',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <GitFork size={20} color="var(--color-primary)" />
            <h2 style={{ fontSize: 18 }}>{zh ? 'Fork 知識庫' : 'Fork Knowledge Base'}</h2>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
            <X size={18} />
          </button>
        </div>

        {/* Source info */}
        <div style={{ background: 'var(--bg-elevated)', padding: '8px 14px', borderRadius: 8, marginBottom: 20, border: '1px solid var(--border-subtle)', fontSize: 12, color: 'var(--text-muted)' }}>
          {zh ? '來源：' : 'Source: '}
          <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
            {zh ? sourceWs.name_zh : sourceWs.name_en}
          </span>
          {' '}
          <span style={{ opacity: 0.6 }}>· {sourceWs.embedding_model} ({sourceWs.embedding_dim}d)</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Names */}
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
              {zh ? '新名稱（中文）' : 'New Name (Chinese)'}
            </label>
            <input className="mt-input" value={nameZh} onChange={e => setNameZh(e.target.value)} />
          </div>
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
              {zh ? '新名稱（英文）' : 'New Name (English)'}
            </label>
            <input className="mt-input" value={nameEn} onChange={e => setNameEn(e.target.value)} />
          </div>

          {/* Embedding model */}
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
              <Brain size={12} />
              {zh ? '向量模型（建立後鎖定）' : 'Embedding Model (locked after creation)'}
            </label>
            {embedModels.length > 1 ? (
              <select
                className="mt-input"
                value={selectedEmbedModel}
                onChange={e => setSelectedEmbedModel(e.target.value)}
                style={{ width: '100%' }}
              >
                {embedModels.map(m => (
                  <option key={m.id} value={m.id}>
                    {m.id} ({m.dim}d)
                    {m.id === sourceWs.embedding_model ? (zh ? ' ← 與來源相同' : ' ← same as source') : ''}
                  </option>
                ))}
              </select>
            ) : (
              <div style={{ background: 'var(--bg-elevated)', padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border-subtle)', fontSize: 12 }}>
                {selectedEmbedModel} ({sourceWs.embedding_dim}d)
              </div>
            )}
            {selectedEmbedModel !== sourceWs.embedding_model && (
              <div style={{ fontSize: 11, color: 'var(--color-warning, #D97706)', marginTop: 4 }}>
                ⚠ {zh ? '選擇了不同的向量模型，Fork 後將重新計算所有節點的向量。' : 'Different model selected — all node embeddings will be recomputed.'}
              </div>
            )}
          </div>

          {/* Info notice */}
          <div style={{ background: 'var(--bg-elevated)', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--border-subtle)', fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.6 }}>
            ℹ {zh
              ? 'Fork 後將在背景搬移所有節點。搬移完成前語意搜尋不可用，但節點可正常瀏覽與編輯。可隨時取消。'
              : 'Nodes will be migrated in the background. Semantic search is unavailable until migration completes, but nodes can be browsed and edited. You can cancel at any time.'}
          </div>

          {error && <div style={{ color: 'var(--color-error)', fontSize: 13 }}>{error}</div>}

          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 8 }}>
            <button className="btn-secondary" onClick={onClose} disabled={loading}>
              {zh ? '取消' : 'Cancel'}
            </button>
            <button className="btn-primary" onClick={handleFork} disabled={loading || !nameZh.trim() || !nameEn.trim()}>
              {loading
                ? (zh ? 'Fork 中…' : 'Forking…')
                : (
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <GitFork size={14} />
                    {zh ? '開始 Fork' : 'Start Fork'}
                  </span>
                )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── BackupSettings ─────────────────────────────────────────────────────────────

const SCHEDULE_OPTIONS = [
  { value: 1,   labelZh: '每小時',    labelEn: 'Hourly' },
  { value: 6,   labelZh: '每 6 小時', labelEn: 'Every 6 hours' },
  { value: 12,  labelZh: '每 12 小時',labelEn: 'Every 12 hours' },
  { value: 24,  labelZh: '每天',      labelEn: 'Daily' },
  { value: 168, labelZh: '每週',      labelEn: 'Weekly' },
];

function BackupSettings({ zh }: { zh: boolean }) {
  const { toast } = useModal();
  const [cfg, setCfg] = useState<BackupConfig | null>(null);
  const [enabled, setEnabled] = useState(false);
  const [path, setPath] = useState('/backups');
  const [intervalHours, setIntervalHours] = useState(24);
  const [keepCount, setKeepCount] = useState(7);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);

  const load = async () => {
    try {
      const c = await system.getBackupConfig();
      setCfg(c);
      setEnabled(c.enabled);
      setPath(c.path);
      setIntervalHours(c.interval_hours);
      setKeepCount(c.keep_count);
    } catch { /* system_config table may not exist yet on older installs */ }
  };

  useEffect(() => { load(); }, []);

  const save = async () => {
    setSaving(true);
    try {
      await system.updateBackupConfig({ enabled, path, interval_hours: intervalHours, keep_count: keepCount });
      toast({ message: zh ? '備份設定已儲存' : 'Backup settings saved', variant: 'success' });
      await load();
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const runNow = async () => {
    setRunning(true);
    try {
      await system.runBackup();
      toast({ message: zh ? '備份已啟動，稍後查看狀態' : 'Backup started — check status shortly', variant: 'success' });
      setTimeout(load, 4000);
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: 'error' });
    } finally {
      setRunning(false);
    }
  };

  const statusColor = cfg?.last_backup_status === 'ok'
    ? 'var(--color-success)'
    : cfg?.last_backup_status
      ? 'var(--color-error)'
      : 'var(--text-muted)';

  return (
    <section style={{ marginBottom: 40 }}>
      <h3 style={{ fontSize: 15, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
        <HardDrive size={16} style={{ color: 'var(--color-primary)' }} />
        {zh ? '資料備份' : 'Data Backup'}
      </h3>
      <div style={{
        background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
        borderRadius: 12, padding: 20, display: 'flex', flexDirection: 'column', gap: 16,
      }}>
        <label style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 14 }}>{zh ? '啟用自動備份' : 'Enable automatic backup'}</span>
          <input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} />
        </label>

        <div>
          <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
            {zh ? '備份路徑（伺服器本機絕對路徑）' : 'Backup path (absolute path on server)'}
          </label>
          <input className="mt-input" value={path} onChange={e => setPath(e.target.value)} placeholder="/backups" />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 12 }}>
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
              {zh ? '備份週期' : 'Backup interval'}
            </label>
            <select
              className="mt-input"
              value={intervalHours}
              onChange={e => setIntervalHours(Number(e.target.value))}
            >
              {SCHEDULE_OPTIONS.map(o => (
                <option key={o.value} value={o.value}>{zh ? o.labelZh : o.labelEn}</option>
              ))}
            </select>
          </div>
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
              {zh ? '保留數量' : 'Keep last N'}
            </label>
            <input
              className="mt-input"
              type="number" min={1} max={30} value={keepCount}
              onChange={e => setKeepCount(Math.max(1, Number(e.target.value)))}
              style={{ width: 72 }}
            />
          </div>
        </div>

        {cfg?.last_backup_at && (
          <div style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span>
              {zh ? '上次備份：' : 'Last backup: '}
              {new Date(cfg.last_backup_at).toLocaleString()}
              <span style={{ marginLeft: 8, color: statusColor, fontWeight: 600 }}>
                {cfg.last_backup_status === 'ok'
                  ? (zh ? '成功' : 'OK')
                  : cfg.last_backup_status}
              </span>
            </span>
            {cfg.last_backup_file && (
              <span style={{ fontFamily: 'monospace', fontSize: 11 }}>{cfg.last_backup_file}</span>
            )}
          </div>
        )}

        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn-primary" onClick={save} disabled={saving}>
            {saving ? (zh ? '儲存中…' : 'Saving…') : (zh ? '儲存設定' : 'Save Settings')}
          </button>
          <button className="btn-secondary" onClick={runNow} disabled={running}>
            {running ? (zh ? '備份中…' : 'Running…') : (zh ? '立即備份' : 'Backup Now')}
          </button>
        </div>
      </div>
    </section>
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
  switchLanguage: (lang: string) => void;
}) {
  const { t, i18n } = useTranslation();
  const zh = language === 'zh-TW';
  const { confirm, toast } = useModal();

  const [keys, setKeys] = useState<AIKey[]>([]);
  const [personalKeys, setPersonalKeys] = useState<PersonalApiKey[]>([]);
  const [personalKeyName, setPersonalKeyName] = useState('');
  const [personalKeySaving, setPersonalKeySaving] = useState(false);
  const [personalKeyError, setPersonalKeyError] = useState('');
  const [newKey, setNewKey] = useState('');
  const [provider, setProvider] = useState<'openai' | 'anthropic' | 'gemini' | 'ollama'>('openai');
  const [apiKey, setApiKey] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [authMode, setAuthMode] = useState<'none' | 'bearer'>('none');
  const [authToken, setAuthToken] = useState('');
  const [testing, setTesting] = useState(false);
  const [ollamaModels, setOllamaModels] = useState<import('./api').ModelInfo[]>([]);
  const [fetchingModels, setFetchingModels] = useState(false);
  const [modelFetchSource, setModelFetchSource] = useState<'server' | 'fallback' | null>(null);
  const [defaultChatModel, setDefaultChatModel] = useState('');
  const [defaultEmbeddingModel, setDefaultEmbeddingModel] = useState('');

  // Derived lists from fetched models
  const chatModels = ollamaModels.filter(m => m.model_type !== 'embedding');
  const embeddingModels = ollamaModels.filter(m => m.model_type === 'embedding');
  const selectedEmbedDim = embeddingModels.find(m => m.id === defaultEmbeddingModel)?.embedding_dim ?? null;

  const loadData = () => {
    ai.listKeys().then(setKeys).catch(() => {});
    users.apiKeys.list().then(setPersonalKeys).catch(() => {});
  };

  const fetchOllamaModels = async (silent = false) => {
    if (!baseUrl) {
      if (!silent) setError(zh ? '請先輸入 Base URL' : 'Please enter Base URL first');
      return;
    }
    setError('');
    setFetchingModels(true);
    setModelFetchSource(null);
    try {
      const ms = await ai.listModelsProxy('ollama', { base_url: baseUrl, auth_mode: authMode, auth_token: authToken });
      setOllamaModels(ms);
      // If backend appended fallback embedding models, all chat models are from server.
      // If ALL models have no unique id outside known list AND none are marked needs_install = false,
      // it's a pure fallback. Simplest heuristic: if any model lacks needs_install flag and isn't
      // in the static known list, it came from the server.
      const knownFallbackIds = new Set(['llama3','mistral','mixtral','phi3','phi4','gemma2','qwen2.5','deepseek-r1','nomic-embed-text','mxbai-embed-large','all-minilm','bge-m3','llama3:8b','llama3:70b','llama3.2']);
      const chatFromServer = ms.filter((m: any) => m.model_type !== 'embedding');
      const looksLiveFetch = chatFromServer.some((m: any) => !knownFallbackIds.has(m.id));
      setModelFetchSource(looksLiveFetch ? 'server' : 'fallback');
      if (!silent) toast({ message: zh ? '已取得模型列表' : 'Models fetched', variant: 'success' });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setFetchingModels(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const handleCreatePersonalKey = async () => {
    if (!personalKeyName.trim()) {
      setPersonalKeyError(zh ? '請輸入名稱' : 'Name required');
      return;
    }
    setPersonalKeySaving(true);
    setPersonalKeyError('');
    setNewKey('');
    try {
      const res = await users.apiKeys.create({ name: personalKeyName, scopes: ['*'] });
      setNewKey(res.key);
      setPersonalKeyName('');
      loadData();
    } catch (e: any) {
      setPersonalKeyError(e.message);
    } finally {
      setPersonalKeySaving(false);
    }
  };

  const handleRevokePersonalKey = async (id: string, name: string) => {
    const ok = await confirm({
      title: zh ? '刪除 API Key' : 'Delete API Key',
      message: zh ? `確定要刪除 ${name} 嗎？此操作無法還原。` : `Delete ${name}? This cannot be undone.`,
      variant: 'danger',
      confirmLabel: zh ? '刪除' : 'Delete',
    });
    if (!ok) return;
    try {
      await users.apiKeys.revoke(id);
      loadData();
      toast({ message: zh ? '已刪除' : 'Deleted', variant: 'success' });
    } catch (e: any) {
      toast({ message: e.message, variant: 'error' });
    }
  };

  const handleSaveKey = async () => {
    if (provider !== 'ollama' && apiKey.length < 10) {
      setError(zh ? 'API Key 太短' : 'API key too short');
      return;
    }
    if (provider === 'ollama') {
      if (!baseUrl) {
        setError(zh ? '請輸入 Base URL' : 'Base URL required');
        return;
      }
      if (!defaultChatModel) {
        setError(zh ? '請選擇預設對話模型' : 'Please select a default chat model');
        return;
      }
      if (!defaultEmbeddingModel) {
        setError(zh ? '請選擇預設向量模型' : 'Please select a default embedding model');
        return;
      }
    }
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      await ai.createKey({
        provider,
        api_key: apiKey,
        base_url: provider === 'ollama' ? baseUrl : undefined,
        auth_mode: provider === 'ollama' ? authMode : undefined,
        auth_token: provider === 'ollama' ? authToken : undefined,
        default_chat_model: provider === 'ollama' ? defaultChatModel : undefined,
        default_embedding_model: provider === 'ollama' ? defaultEmbeddingModel : undefined,
      });
      setApiKey('');
      setSuccess(zh ? '已儲存' : 'Saved');
      loadData();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setError('');
    setSuccess('');
    try {
      await ai.testConnection({
        provider,
        api_key: apiKey,
        base_url: baseUrl,
        auth_mode: authMode,
        auth_token: authToken,
        // For Ollama, pass the selected chat model so the test doesn't use the
        // hardcoded default "llama3" which may not be installed on the server.
        model: provider === 'ollama' ? (defaultChatModel || undefined) : undefined,
      });
      setSuccess(zh ? '連線測試成功' : 'Connection test successful');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setTesting(false);
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
    { value: 'ollama', label: 'Ollama' },
  ] as const;

  return (
    <div style={{ padding: 40, maxWidth: 600, margin: '0 auto' }}>
      <h2 style={{ fontSize: 22, marginBottom: 32 }}>{t('sidebar.settings')}</h2>

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
            <span style={{ fontSize: 14 }}>{t('ws_settings.language')}</span>
            <select
              className="mt-input"
              style={{ width: 140, padding: '4px 10px' }}
              value={i18n.language}
              onChange={(e) => switchLanguage(e.target.value)}
            >
              <option value="zh-TW">繁體中文</option>
              <option value="en">English</option>
            </select>
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

      {/* MemTrace API Keys */}
      <section style={{ marginBottom: 40 }}>
        <h3 style={{ fontSize: 15, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Key size={16} style={{ color: 'var(--color-primary)' }} />
          {zh ? '開發者 API Key' : 'Developer API Keys'}
        </h3>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
          {zh
            ? '請使用此 API Key 搭配 MCP Server 或其他外部工具整合 MemTrace。'
            : 'Use these API keys with MCP Server or other external tools to integrate MemTrace.'}
        </p>

        {personalKeys.length > 0 && (
          <div style={{ marginBottom: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
            {personalKeys.map(k => (
              <div key={k.id} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
                borderRadius: 8, padding: '10px 14px',
              }}>
                <div>
                  <span style={{ fontSize: 13, fontWeight: 500 }}>{k.name}</span>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 10 }}>
                    {k.prefix}••••••••••••
                  </span>
                </div>
                <button
                  onClick={() => handleRevokePersonalKey(k.id, k.name)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
                  title={zh ? '刪除' : 'Delete'}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        )}

        {newKey && (
          <div style={{ background: 'var(--color-success-subtle)', border: '1px solid var(--color-success)', borderRadius: 8, padding: 16, marginBottom: 16 }}>
            <p style={{ fontSize: 13, color: 'var(--color-success)', margin: '0 0 8px', fontWeight: 600 }}>
              {zh ? '金鑰已建立！請立即複製並妥善保存：' : 'Key created! Please copy and store it safely now:'}
            </p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <input readOnly value={newKey} className="mt-input" style={{ flex: 1, fontFamily: 'monospace' }} />
              <button 
                className="btn-primary" 
                onClick={() => { navigator.clipboard.writeText(newKey); toast({ message: zh ? '已複製' : 'Copied', variant: 'success' }); }}
              >
                {zh ? '複製' : 'Copy'}
              </button>
            </div>
            <p style={{ fontSize: 11, color: 'var(--text-secondary)', margin: '8px 0 0' }}>
              {zh ? '基於安全考量，離開此畫面後將無法再次查看此金鑰。' : 'For security reasons, you will not be able to see this key again after leaving.'}
            </p>
          </div>
        )}

        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <input
            className="mt-input"
            style={{ width: 240 }}
            placeholder={zh ? '金鑰名稱 (例: MCP Server)' : 'Key Name (e.g. MCP Server)'}
            value={personalKeyName}
            onChange={e => setPersonalKeyName(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleCreatePersonalKey(); }}
          />
          <button className="btn-secondary" onClick={handleCreatePersonalKey} disabled={personalKeySaving}>
            <PlusCircle size={14} style={{ marginRight: 6 }} />
            {personalKeySaving ? (zh ? '建立中…' : 'Creating…') : (zh ? '建立新金鑰' : 'Create New Key')}
          </button>
          {personalKeyError && <span style={{ color: 'var(--color-error)', fontSize: 12 }}>{personalKeyError}</span>}
        </div>
      </section>

      <BackupSettings zh={zh} />

      {/* AI Provider Keys */}
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
            {providers.map(p => {
              const isActive = provider === p.value;
              const brandColor = `var(--ai-${p.value})`;
              const brandBg = `var(--ai-${p.value}-subtle)`;
              return (
                <button
                  key={p.value}
                  onClick={() => {
                    setProvider(p.value);
                    const existing = keys.find(k => k.provider === p.value);
                    if (existing) {
                      const savedUrl = existing.base_url || '';
                      setBaseUrl(savedUrl);
                      setAuthMode((existing.auth_mode as any) || 'none');
                      setAuthToken(existing.auth_token || '');
                      setDefaultChatModel(existing.default_chat_model || '');
                      setDefaultEmbeddingModel(existing.default_embedding_model || '');
                      // Auto-fetch models when switching to a configured Ollama provider
                      if (p.value === 'ollama' && savedUrl) {
                        setTimeout(() => fetchOllamaModels(true), 0);
                      }
                    } else {
                      setBaseUrl('');
                      setAuthMode('none');
                      setAuthToken('');
                      setDefaultChatModel('');
                      setDefaultEmbeddingModel('');
                      setOllamaModels([]);
                    }
                    setError('');
                    setSuccess('');
                  }}
                  style={{
                    padding: '6px 14px', borderRadius: 20, fontSize: 12, cursor: 'pointer',
                    border: `1px solid ${isActive ? brandColor : 'var(--border-default)'}`,
                    background: isActive ? brandBg : 'transparent',
                    color: isActive ? brandColor : 'var(--text-muted)',
                    transition: 'all 0.2s',
                    fontWeight: isActive ? 600 : 400,
                  }}
                >
                  {p.label}
                </button>
              );
            })}
          </div>
          {provider === 'ollama' ? (
            <>
              {/* ── Step 1: Connection ── */}
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>Base URL</label>
                <input
                  className="mt-input"
                  placeholder="http://localhost:11434"
                  value={baseUrl}
                  onChange={e => { setBaseUrl(e.target.value); setModelFetchSource(null); }}
                />
              </div>
              <div style={{ display: 'flex', gap: 12 }}>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>{zh ? '認證模式' : 'Auth Mode'}</label>
                  <select className="mt-input" value={authMode} onChange={e => setAuthMode(e.target.value as any)}>
                    <option value="none">{zh ? '無認證（本機）' : 'None (local)'}</option>
                    <option value="bearer">Bearer Token</option>
                  </select>
                </div>
                {authMode === 'bearer' && (
                  <div style={{ flex: 2 }}>
                    <label style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>Token</label>
                    <input
                      className="mt-input"
                      type="password"
                      placeholder="token..."
                      value={authToken}
                      onChange={e => setAuthToken(e.target.value)}
                    />
                  </div>
                )}
              </div>

              {/* ── Step 2: Fetch & pick models ── */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                <button
                  className="btn-secondary"
                  onClick={() => fetchOllamaModels(false)}
                  disabled={fetchingModels || !baseUrl}
                  style={{ whiteSpace: 'nowrap' }}
                >
                  {fetchingModels
                    ? (zh ? '取得中…' : 'Fetching…')
                    : (zh ? '取得模型列表' : 'Fetch Models')}
                </button>
                {modelFetchSource === 'server' && (() => {
                  const serverChatCount = chatModels.length;
                  const needsInstallEmbeds = embeddingModels.filter(m => m.needs_install);
                  const liveEmbedCount = embeddingModels.length - needsInstallEmbeds.length;
                  return (
                    <span style={{ fontSize: 11, color: 'var(--color-success)' }}>
                      ✓ {zh
                        ? `${serverChatCount} 個對話模型${liveEmbedCount > 0 ? `・${liveEmbedCount} 個向量模型` : ''}`
                        : `${serverChatCount} chat model${serverChatCount !== 1 ? 's' : ''}${liveEmbedCount > 0 ? ` · ${liveEmbedCount} embedding` : ''}`}
                      {needsInstallEmbeds.length > 0 && (
                        <span style={{ color: 'var(--color-warning, #f59e0b)', marginLeft: 6 }}>
                          · {zh ? `向量模型需另行安裝` : `embedding models need install`}
                        </span>
                      )}
                    </span>
                  );
                })()}
                {modelFetchSource === 'fallback' && (
                  <span style={{ fontSize: 11, color: 'var(--color-warning, #f59e0b)' }}>
                    ⚠ {zh ? '伺服器未回應，顯示預設清單' : 'Server unavailable — showing default list'}
                  </span>
                )}
              </div>

              {/* Chat model selector */}
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>
                  {zh ? '預設對話模型' : 'Default Chat Model'}
                  {!defaultChatModel && ollamaModels.length > 0 && (
                    <span style={{ color: 'var(--color-error)', marginLeft: 6 }}>*</span>
                  )}
                </label>
                <select
                  className="mt-input"
                  value={defaultChatModel}
                  onChange={e => setDefaultChatModel(e.target.value)}
                  disabled={ollamaModels.length === 0}
                >
                  <option value="">{ollamaModels.length === 0 ? (zh ? '請先取得模型列表' : 'Fetch models first') : (zh ? '-- 選擇對話模型 --' : '-- Select chat model --')}</option>
                  {chatModels.map(m => <option key={m.id} value={m.id}>{m.display_name}</option>)}
                  {/* Preserve previously saved value even if not in current list */}
                  {defaultChatModel && !chatModels.find(m => m.id === defaultChatModel) && (
                    <option value={defaultChatModel}>{defaultChatModel}</option>
                  )}
                </select>
              </div>

              {/* Embedding model selector */}
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>
                  {zh ? '預設向量模型' : 'Default Embedding Model'}
                  {!defaultEmbeddingModel && ollamaModels.length > 0 && (
                    <span style={{ color: 'var(--color-error)', marginLeft: 6 }}>*</span>
                  )}
                </label>
                <select
                  className="mt-input"
                  value={defaultEmbeddingModel}
                  onChange={e => setDefaultEmbeddingModel(e.target.value)}
                  disabled={ollamaModels.length === 0}
                >
                  <option value="">{ollamaModels.length === 0 ? (zh ? '請先取得模型列表' : 'Fetch models first') : (zh ? '-- 選擇向量模型 --' : '-- Select embedding model --')}</option>
                  {embeddingModels.map(m => (
                    <option key={m.id} value={m.id}>
                      {/* needs_install models already include "(需安裝)" in display_name from backend */}
                      {m.needs_install
                        ? m.display_name
                        : `${m.display_name}${m.embedding_dim ? ` (${m.embedding_dim}d)` : ''}`}
                    </option>
                  ))}
                  {defaultEmbeddingModel && !embeddingModels.find(m => m.id === defaultEmbeddingModel) && (
                    <option value={defaultEmbeddingModel}>{defaultEmbeddingModel}</option>
                  )}
                </select>
                {selectedEmbedDim && (
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                    {zh ? `向量維度：${selectedEmbedDim}（工作區建立後鎖定）` : `Embedding dim: ${selectedEmbedDim} — locked after workspace creation`}
                  </div>
                )}
              </div>
            </>
          ) : (
            <input
              className="mt-input"
              type="password"
              placeholder={provider === 'openai' ? 'sk-...' : provider === 'anthropic' ? 'sk-ant-...' : 'AIza...'}
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleSaveKey(); }}
            />
          )}
          {error && <div style={{ color: 'var(--color-error)', fontSize: 12 }}>{error}</div>}
          {success && <div style={{ color: 'var(--color-success)', fontSize: 12 }}>{success}</div>}
          <div style={{ display: 'flex', gap: 10 }}>
            <button className="btn-primary" onClick={handleSaveKey} disabled={saving}>
              {saving ? (zh ? '儲存中…' : 'Saving…') : (zh ? '儲存 API Key' : 'Save API Key')}
            </button>
            <button className="btn-secondary" onClick={handleTestConnection} disabled={testing}>
              {testing ? (zh ? '測試中…' : 'Testing…') : (zh ? '測試連線' : 'Test Connection')}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

// ── App ────────────────────────────────────────────────────────────────────────

export default function App() {
  const { t, i18n } = useTranslation();

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
  const switchLanguage = (next: string) => {
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
  const [showMcpStatus, setShowMcpStatus] = useState(false);

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

  // Listen for silent-refresh failures from api.ts — force re-login
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
  const [showForkWs, setShowForkWs] = useState<Workspace | null>(null); // P4.1-F: source workspace to fork
  const wsMenuRef = useRef<HTMLDivElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);

  // True when the current user has write access to the selected workspace
  const canWrite = !!(selectedWs && selectedWs.my_role && ['admin', 'editor', 'owner'].includes(selectedWs.my_role));

  useEffect(() => {
    const onDeleted = (e: any) => {
      const deletedId = e.detail?.wsId;
      if (!deletedId) return;
      setWsList(prev => prev.filter(w => w.id !== deletedId));
      setSelectedWs(prev => {
        if (prev?.id === deletedId) return null;
        return prev;
      });
      if (selectedWs?.id === deletedId) {
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
        // Keep polling while in a transient state
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

  // ── Dynamic Title ─────────────────────────────────────────────────────────
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

  const handleWsCreated = (ws: Workspace) => {
    setWsList(prev => [ws, ...prev]);
    setSelectedWs(ws);
    setShowCreateWs(false);
    setCurrentView('ingest');
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
  const [showChat, setShowChat] = useState(false);

  const handleNodeSaved = (saved: ApiNode) => {
    setEditingNode(saved);
    setGraphVersion(v => v + 1);
  };

  // ── Render ────────────────────────────────────────────────────────────────
  const zh = i18n.language === 'zh-TW';

  return (
    <Routes>
      <Route path="/public/:wsId" element={<PublicWorkspaceView />} />
      <Route path="/verify" element={<MagicLinkVerifyPage />} />
      <Route path="/invite/:token" element={<JoinInvitationPage />} />
      <Route path="/auth" element={
        authenticated ? <Navigate to="/" /> : <AuthPage onAuthenticated={() => setAuthenticated(true)} />
      } />
      <Route path="/reset-password" element={
        <ResetPasswordPage 
          token={new URLSearchParams(window.location.search).get('token') || ''} 
          onSuccess={() => window.location.href = '/'} 
        />
      } />
      <Route path="/" element={
        !authenticated ? <Navigate to="/auth" /> : (
          <div className="app-container">
      {/* ── Onboarding Wizard ─────────────────────────────────────────── */}
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
            if (specKb) {
              setSelectedWs(specKb);
            } else {
              workspaces.list().then(list => {
                setWsList(list);
                const found = list.find(ws => ws.id === 'ws_spec0001');
                if (found) setSelectedWs(found);
              }).catch(() => {});
            }
          }}
        />
      )}

      {/* ── Create Workspace Modal ──────────────────────────────────────── */}
      {showCreateWs && (
        <CreateWorkspaceModal
          onCreated={handleWsCreated}
          onClose={() => setShowCreateWs(false)}
        />
      )}

      {/* ── Fork Workspace Modal (P4.1-F) ────────────────────────────────── */}
      {showForkWs && (
        <ForkWorkspaceModal
          sourceWs={showForkWs}
          onForked={(job, targetWs) => {
            setShowForkWs(null);
            // Add the new forked workspace to the list and navigate to it
            setWsList(prev => [targetWs, ...prev]);
            setSelectedWs(targetWs);
            setCloneJob(job);
          }}
          onClose={() => setShowForkWs(null)}
        />
      )}

      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <aside className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
        <button className="sidebar-toggle" onClick={toggleSidebar}>
          {sidebarCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>

        <div className="brand" style={{ justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
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
                {/* Pinned: MemTrace Public Spec */}
                {wsList.find(ws => ws.id === 'ws_spec0001') && (
                  <div
                    onClick={() => { 
                      const spec = wsList.find(ws => ws.id === 'ws_spec0001');
                      if (spec) {
                        setSelectedWs(spec);
                        setCurrentView('graph');
                        setWsMenuOpen(false);
                      }
                    }}
                    style={{
                      padding: '12px 14px', cursor: 'pointer', fontSize: 13,
                      background: selectedWs?.id === 'ws_spec0001' ? 'var(--color-primary-subtle)' : 'var(--bg-elevated)',
                      borderBottom: '1px solid var(--border-default)',
                      display: 'flex', alignItems: 'center', gap: 10,
                    }}
                  >
                    <div style={{
                      width: 28, height: 28, borderRadius: 6,
                      background: 'var(--color-primary)', display: 'flex',
                      alignItems: 'center', justifyContent: 'center', color: 'white',
                    }}>
                      <Brain size={16} />
                    </div>
                    <div>
                      <div style={{ fontWeight: 600, color: 'var(--color-primary)' }}>
                        {zh ? 'MemTrace 公開規格書' : 'MemTrace Public Spec'}
                      </div>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                        {zh ? '核心文件與設計規範' : 'Core docs & design specs'}
                      </div>
                    </div>
                  </div>
                )}

                {/* My workspaces */}
                {wsList.filter(ws => ws.visibility !== 'public' && ws.visibility !== 'conditional_public').map(ws => (
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
                {/* Public / example workspaces */}
                {wsList.some(ws => ws.visibility === 'public' || ws.visibility === 'conditional_public') && (
                  <>
                    <div style={{ padding: '6px 14px 4px', fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: 'var(--text-muted)', borderTop: '1px solid var(--border-subtle)', textTransform: 'uppercase' }}>
                      {zh ? '公開知識庫' : 'Public'}
                    </div>
                    {wsList.filter(ws => ws.visibility === 'public' || ws.visibility === 'conditional_public').map(ws => (
                      <div
                        key={ws.id}
                        style={{
                          padding: '7px 14px', cursor: 'pointer', fontSize: 13,
                          background: selectedWs?.id === ws.id ? 'var(--color-primary-subtle)' : 'transparent',
                          color: selectedWs?.id === ws.id ? 'var(--color-primary)' : 'var(--text-primary)',
                          transition: 'all 0.15s',
                          display: 'flex', alignItems: 'center', gap: 6,
                        }}
                        onClick={() => { setSelectedWs(ws); setWsMenuOpen(false); }}
                      >
                        <Globe size={11} style={{ opacity: 0.5, flexShrink: 0 }} />
                        <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {zh ? ws.name_zh : ws.name_en}
                        </span>
                        <span style={{ fontSize: 10, opacity: 0.6 }}>{ws.kb_type}</span>
                        {/* P4.1-F: Fork button — only for public workspaces not owned by current user */}
                        {user && ws.owner_id !== user.id && (
                          <button
                            title={zh ? 'Fork 此知識庫' : 'Fork this KB'}
                            onClick={e => {
                              e.stopPropagation();
                              setWsMenuOpen(false);
                              setShowForkWs(ws);
                            }}
                            style={{
                              padding: '2px 6px', borderRadius: 6, fontSize: 10,
                              border: '1px solid var(--border-default)',
                              background: 'transparent', cursor: 'pointer',
                              color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 3,
                              flexShrink: 0,
                            }}
                          >
                            <GitFork size={10} />
                            Fork
                          </button>
                        )}
                      </div>
                    ))}
                  </>
                )}
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

        {/* P4.1-C/F: Clone / Fork progress panel */}
        {!sidebarCollapsed && cloneJob && ['pending', 'running', 'cancelling', 'cancelled', 'failed'].includes(cloneJob.status) && (
          <div style={{ padding: '0 12px 16px' }}>
            <div style={{
              padding: '10px 12px',
              background: cloneJob.status === 'failed' ? 'var(--color-error-subtle)'
                        : cloneJob.status === 'cancelled' ? 'var(--bg-elevated)'
                        : 'var(--bg-elevated)',
              borderRadius: 10,
              border: `1px solid ${
                cloneJob.status === 'failed' ? 'var(--color-error)' : 'var(--border-default)'
              }`,
            }}>
              {/* Status row */}
              <div style={{
                fontSize: 11,
                color: cloneJob.status === 'failed' ? 'var(--color-error)' : 'var(--text-muted)',
                marginBottom: 6,
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  {cloneJob.status === 'failed' && <AlertTriangle size={12} />}
                  {cloneJob.status === 'cancelled' && <XCircle size={12} />}
                  {['pending', 'running', 'cancelling'].includes(cloneJob.status) && (
                    <RefreshCw size={12} className="animate-spin-slow" />
                  )}
                  {cloneJob.status === 'failed'
                    ? (zh ? `${cloneJob.is_fork ? 'Fork' : '複製'}失敗` : `${cloneJob.is_fork ? 'Fork' : 'Clone'} Failed`)
                    : cloneJob.status === 'cancelled'
                    ? (zh ? '已取消' : 'Cancelled')
                    : cloneJob.status === 'cancelling'
                    ? (zh ? '取消中…' : 'Cancelling…')
                    : zh
                    ? `${cloneJob.is_fork ? 'Fork' : '複製'}進行中…`
                    : `${cloneJob.is_fork ? 'Fork' : 'Clone'} in progress…`}
                </span>
                {['pending', 'running'].includes(cloneJob.status) && cloneJob.total_nodes > 0 && (
                  <span>{cloneJob.processed_nodes} / {cloneJob.total_nodes}</span>
                )}
              </div>

              {/* Progress bar */}
              {['pending', 'running'].includes(cloneJob.status) && (
                <div style={{ height: 4, background: 'var(--border-default)', borderRadius: 2, overflow: 'hidden', marginBottom: 8 }}>
                  <div style={{
                    height: '100%',
                    background: 'var(--color-primary)',
                    width: `${Math.max(5, (cloneJob.processed_nodes / (cloneJob.total_nodes || 1)) * 100)}%`,
                    transition: 'width 0.3s',
                  }} />
                </div>
              )}

              {/* Error message */}
              {cloneJob.status === 'failed' && (
                <div style={{ fontSize: 10, color: 'var(--color-error)', opacity: 0.8 }}>{cloneJob.error_msg}</div>
              )}

              {/* Cancel button (only for active jobs) */}
              {['pending', 'running'].includes(cloneJob.status) && (
                <button
                  onClick={async () => {
                    if (cancellingJob) return;
                    setCancellingJob(true);
                    try {
                      await workspaces.cancelCloneJob(cloneJob.id);
                    } catch {
                      setCancellingJob(false);
                    }
                  }}
                  disabled={cancellingJob}
                  style={{
                    marginTop: 4,
                    fontSize: 11, padding: '2px 8px', borderRadius: 6,
                    border: '1px solid var(--border-default)',
                    background: 'transparent', cursor: cancellingJob ? 'default' : 'pointer',
                    color: 'var(--text-muted)',
                  }}
                >
                  {cancellingJob ? (zh ? '取消中…' : 'Cancelling…') : (zh ? '取消' : 'Cancel')}
                </button>
              )}
            </div>
          </div>
        )}

        <nav style={{ flex: 1 }}>
          <div className={`nav-item ${currentView === 'graph' ? 'active' : ''}`} onClick={() => setCurrentView('graph')}>
            <Network size={18} />
            {!sidebarCollapsed && <span className="nav-text">{t('sidebar.graph')}</span>}
          </div>

          {selectedWs && canWrite && currentView !== 'settings' && (
            <div
              className="nav-item"
              style={{ marginTop: 8, color: 'var(--color-primary)' }}
              title={sidebarCollapsed ? t('sidebar.write') : undefined}
              onClick={() => { setCurrentView('graph'); setEditingNode(null); }}
            >
              <PlusCircle size={18} />
              {!sidebarCollapsed && <span className="nav-text">{t('sidebar.write')}</span>}
            </div>
          )}

          {selectedWs && (
            <div
              className={`nav-item ${currentView === 'analytics' ? 'active' : ''}`}
              style={{ marginTop: 4 }}
              title={sidebarCollapsed ? t('sidebar.analytics') : undefined}
              onClick={() => setCurrentView('analytics')}
            >
              <BarChart3 size={18} />
              {!sidebarCollapsed && <span className="nav-text">{t('sidebar.analytics')}</span>}
            </div>
          )}
          {selectedWs && canWrite && (
            <div
              className={`nav-item ${currentView === 'review' ? 'active' : ''}`}
              style={{ marginTop: 4 }}
              title={sidebarCollapsed ? t('sidebar.review') : undefined}
              onClick={() => setCurrentView('review')}
            >
              <Inbox size={18} />
              {!sidebarCollapsed && <span className="nav-text">{t('sidebar.review')}</span>}
            </div>
          )}
          {selectedWs && canWrite && (
            <div
              className={`nav-item ${currentView === 'ws_settings' ? 'active' : ''}`}
              style={{ marginTop: 4 }}
              title={sidebarCollapsed ? t('sidebar.ws_settings') : undefined}
              onClick={() => setCurrentView('ws_settings')}
            >
              <Users size={18} />
              {!sidebarCollapsed && <span className="nav-text">{t('sidebar.ws_settings')}</span>}
            </div>
          )}
          {selectedWs && canWrite && (
            <div
              className={`nav-item ${currentView === 'ingest' ? 'active' : ''}`}
              style={{ marginTop: 4 }}
              title={sidebarCollapsed ? t('sidebar.ingest') : undefined}
              onClick={() => setCurrentView('ingest')}
            >
              <FileUp size={18} />
              {!sidebarCollapsed && <span className="nav-text">{t('sidebar.ingest')}</span>}
            </div>
          )}
        </nav>

        {/* Relocated to top-right corner */}
      </aside>

      {/* ── Main Viewport ────────────────────────────────────────────────── */}
      <main className="view-port">
        {/* Global Top-Right Account Menu (Fixed position) */}
        {user && (
          <div 
            ref={userMenuRef}
            style={{ 
              position: 'absolute', top: 22, right: 40, zIndex: 1200,
              display: 'flex', gap: 12, alignItems: 'center'
            }}
          >
            {/* User Profile Dropdown */}
            <div style={{ position: 'relative' }}>
              <div 
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                style={{ 
                  background: 'transparent', border: 'none',
                  borderRadius: 8, padding: '0 4px', height: 38, display: 'flex', alignItems: 'center', gap: 10,
                  cursor: 'pointer', boxShadow: 'none', transition: 'all 0.2s',
                  userSelect: 'none'
                }}
                className="user-menu-trigger"
              >
                <div style={{ 
                  width: 28, height: 28, borderRadius: '50%', background: 'var(--color-primary-subtle)',
                  color: 'var(--color-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 14, fontWeight: 700
                }}>
                  {user.display_name?.[0]?.toUpperCase()}
                </div>
                <span style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>{user.display_name}</span>
              </div>

              {userMenuOpen && (
                <div style={{ 
                  position: 'absolute', top: 'calc(100% + 8px)', right: 0, 
                  width: 200, background: 'var(--bg-elevated)', border: '1px solid var(--border-default)',
                  borderRadius: 12, boxShadow: 'var(--shadow-lg)', overflow: 'hidden',
                  animation: 'fade-in-down 0.2s ease-out', zIndex: 1100
                }}>
                  <div 
                    className="nav-item" 
                    onClick={() => { setCurrentView('settings'); setUserMenuOpen(false); }}
                    style={{ borderRadius: 0, padding: '12px 16px', margin: 0, border: 'none' }}
                  >
                    <Settings size={16} />
                    <span className="nav-text" style={{ fontSize: 13, whiteSpace: 'nowrap' }}>{zh ? '個人設定' : 'Personal Settings'}</span>
                  </div>
                  <div 
                    className="nav-item" 
                    onClick={() => { setShowMcpStatus(!showMcpStatus); setUserMenuOpen(false); }}
                    style={{ borderRadius: 0, padding: '12px 16px', margin: 0, border: 'none' }}
                  >
                    <Network size={16} />
                    <span className="nav-text" style={{ fontSize: 13, whiteSpace: 'nowrap' }}>MCP Status</span>
                  </div>
                  <div style={{ borderTop: '1px solid var(--border-subtle)' }} />
                  <div 
                    className="nav-item logout-item" 
                    onClick={() => { handleLogout(); setUserMenuOpen(false); }}
                    style={{ borderRadius: 0, padding: '12px 16px', margin: 0, border: 'none' }}
                  >
                    <LogOut size={16} />
                    <span className="nav-text" style={{ fontSize: 13, whiteSpace: 'nowrap' }}>{zh ? '登出' : 'Logout'}</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
        <ErrorBoundary>
        {currentView === 'graph' && (
          <GraphContainer
            wsId={selectedWs?.id}
            userId={user?.id}
            reloadKey={graphVersion}
            onEditNode={node => setEditingNode(node)}
            onNewNode={() => setEditingNode(null)}
            onSwitchView={setCurrentView}
            user={user}
            onLogout={handleLogout}
            showMcpStatus={showMcpStatus}
            setShowMcpStatus={setShowMcpStatus}
          />
        )}
        {currentView === 'analytics' && selectedWs && (
          <div style={{ flex: 1, overflowY: 'auto', padding: 40 }}>
            <div style={{ maxWidth: 1100, margin: '0 auto' }}>
              <h2 style={{ fontSize: 22, marginBottom: 24 }}>{t('analytics.title')}</h2>
              <AnalyticsDashboard wsId={selectedWs.id} onOpenHealthManager={() => setCurrentView('node_health')} />
            </div>
          </div>
        )}
        {currentView === 'node_health' && selectedWs && (
          <div style={{ flex: 1, overflowY: 'auto', padding: 40 }}>
            <div style={{ maxWidth: 1100, margin: '0 auto' }}>
              <h2 style={{ fontSize: 22, marginBottom: 24 }}>{t('sidebar.health')}</h2>
              <NodeHealthManager wsId={selectedWs.id} onEditNode={(node) => setEditingNode(node)} />
            </div>
          </div>
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
                <WorkspaceSettings wsId={selectedWs.id} userId={user?.id} />
             </div>
          </div>
        )}
        {currentView === 'ingest' && selectedWs && (
          <IngestPage 
            wsId={selectedWs.id} 
            onGoToReview={() => setCurrentView('review')} 
          />
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
          onClick={() => setShowChat(true)}
          className={`ai-fab ${showChat ? 'hidden' : ''}`}
          title={zh ? '開啟 AI 助手' : 'Open AI Assistant'}
          style={{
            // Shift left when the node editor panel is open so the FAB doesn't
            // sit on top of the editor; otherwise stay at the viewport edge.
            right: editingNode !== undefined ? 482 : 32,
          }}
        >
          <Brain size={24} />
        </button>
      )}

      {/* ── Chat Side Panel ──────────────────────────────────────────────── */}
      <aside 
        className={`side-panel ${(!showChat || currentView !== 'graph') ? 'hidden' : ''}`} 
        style={{ zIndex: 90, overflow: 'visible' }}
      >
         {/* Content Wrapper for Clipping */}
         <div style={{ width: '100%', height: '100%', overflow: 'hidden', position: 'relative', borderLeft: (showChat && currentView === 'graph') ? '1px solid var(--border-default)' : 'none' }}>
            <div style={{ width: 450, height: '100%' }}>
               {selectedWs && <AiChatPanel wsId={selectedWs.id} zh={zh} />}
            </div>
         </div>

         {/* Close Handle — only when panel is open; FAB handles opening when closed */}
         {selectedWs && currentView === 'graph' && showChat && (
           <div
             className="panel-handle"
             onClick={() => setShowChat(false)}
             style={{ background: 'var(--bg-surface)' }}
             title={zh ? '收合 AI 助手' : 'Collapse AI Assistant'}
           >
             <ChevronRight size={14} />
           </div>
         )}
      </aside>

      {/* MCP Status Panel (P4.5-4A-3) */}
      {showMcpStatus && (
        <McpStatusPanel onClose={() => setShowMcpStatus(false)} />
      )}
    </div>
        )
      } />
    </Routes>
  );
}
