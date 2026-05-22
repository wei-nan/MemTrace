import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Moon, Sun, LogOut, Key, Plus, RotateCcw, Trash2, Copy,
  ChevronRight, Cpu, HardDrive, ShieldCheck, Languages,
} from 'lucide-react';
import { auth, users } from '../api';
import type { PersonalApiKey, PersonalApiKeyCreateResponse } from '../api/workspaces';
import { useModal } from './ModalContext';
import BackupSettings from './BackupSettings';
import AiProviderSettings from './AiProviderSettings';

// ── Shared card layout helpers ────────────────────────────────────────────────

const CARD: React.CSSProperties = {
  border: '1px solid var(--border-default)',
  borderRadius: 10,
  overflow: 'hidden',
};

const CARD_HD: React.CSSProperties = {
  padding: '14px 20px',
  borderBottom: '1px solid var(--border-subtle)',
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  background: 'var(--bg-surface)',
};

const CARD_BODY: React.CSSProperties = {
  padding: 20,
  display: 'flex',
  flexDirection: 'column',
  gap: 16,
};

function CardHeader({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description?: string;
}) {
  return (
    <div style={CARD_HD}>
      <span style={{ color: 'var(--color-primary)', display: 'flex', alignItems: 'center' }}>{icon}</span>
      <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>{title}</h3>
      {description && (
        <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 'auto' }}>{description}</span>
      )}
    </div>
  );
}

// ── Preference toggle card (theme / language) ─────────────────────────────────

function PrefCard({
  icon,
  title,
  value,
  onClick,
}: {
  icon: React.ReactNode;
  title: string;
  value: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '12px 14px',
        border: '1px solid var(--border-default)',
        borderRadius: 8,
        cursor: 'pointer',
        background: 'var(--bg-surface)',
        color: 'var(--text-primary)',
        textAlign: 'left',
        transition: 'border-color 0.15s, background 0.15s',
        width: '100%',
      }}
      className="pref-card-btn"
    >
      <div style={{
        width: 36, height: 36, borderRadius: 8, flexShrink: 0,
        background: 'var(--color-primary-subtle)', color: 'var(--color-primary)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        {icon}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 600 }}>{title}</div>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{value}</div>
      </div>
      <ChevronRight size={14} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
    </button>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function SettingsPanel({
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
  const { t } = useTranslation();
  const zh = language === 'zh-TW';
  const { toast } = useModal();

  const [pwd, setPwd] = useState('');
  const [confirmPwd, setConfirmPwd] = useState('');
  const [pwdSaving, setPwdSaving] = useState(false);
  const [pwdError, setPwdError] = useState('');

  const [apiKeys, setApiKeys] = useState<PersonalApiKey[]>([]);
  const [newKeyName, setNewKeyName] = useState('');
  const [keyCreating, setKeyCreating] = useState(false);
  const [newKeySecret, setNewKeySecret] = useState<PersonalApiKeyCreateResponse | null>(null);

  const loadApiKeys = () => {
    users.apiKeys.list().then(setApiKeys).catch(() => {});
  };

  const handleCreateKey = async () => {
    const name = newKeyName.trim();
    if (!name) return;
    setKeyCreating(true);
    try {
      const created = await users.apiKeys.create({ name });
      setNewKeySecret(created);
      setNewKeyName('');
      loadApiKeys();
    } catch (e: any) {
      toast({ message: e.message || (zh ? '建立失敗' : 'Failed to create key'), variant: 'error' });
    } finally {
      setKeyCreating(false);
    }
  };

  const handleRotateKey = async (id: string) => {
    try {
      const rotated = await users.apiKeys.rotate(id);
      setNewKeySecret(rotated);
      loadApiKeys();
    } catch (e: any) {
      toast({ message: e.message || (zh ? '輪替失敗' : 'Failed to rotate key'), variant: 'error' });
    }
  };

  const handleRevokeKey = async (id: string) => {
    if (!confirm(zh ? '確定要撤銷此金鑰？此操作無法復原。' : 'Revoke this key? This cannot be undone.')) return;
    try {
      await users.apiKeys.revoke(id);
      loadApiKeys();
    } catch (e: any) {
      toast({ message: e.message || (zh ? '撤銷失敗' : 'Failed to revoke key'), variant: 'error' });
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    toast({ message: zh ? '已複製' : 'Copied', variant: 'success' });
  };

  const handleUpdatePassword = async () => {
    if (pwd.length < 8) {
      setPwdError(zh ? '密碼長度需至少 8 個字元' : 'Password must be at least 8 characters');
      return;
    }
    if (pwd !== confirmPwd) {
      setPwdError(zh ? '兩次輸入的密碼不一致' : 'Passwords do not match');
      return;
    }
    setPwdSaving(true);
    setPwdError('');
    try {
      await auth.updatePassword(pwd);
      setPwd('');
      setConfirmPwd('');
      toast({ message: zh ? '密碼已更新' : 'Password updated', variant: 'success' });
    } catch (e: any) {
      setPwdError(e.message);
    } finally {
      setPwdSaving(false);
    }
  };

  useEffect(() => { loadApiKeys(); }, []);

  return (
    <div className="settings-panel" style={{ padding: '32px 40px', maxWidth: 800, margin: '0 auto' }}>

      {/* ── Page header ──────────────────────────────────────────────────── */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
        marginBottom: 28, paddingBottom: 20, borderBottom: '1px solid var(--border-subtle)',
      }}>
        <div>
          <h1 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 4px' }}>
            {t('nav.settings')}
          </h1>
          <p style={{ margin: 0, fontSize: 12, color: 'var(--text-muted)' }}>
            {user?.email}
          </p>
        </div>
        <button
          className="btn-secondary"
          onClick={() => auth.logout()}
          style={{ color: 'var(--color-error)', borderColor: 'var(--color-error-subtle)', flexShrink: 0 }}
        >
          <LogOut size={14} />
          {t('nav.logout')}
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* ── Preferences ──────────────────────────────────────────────── */}
        <div style={CARD}>
          <CardHeader
            icon={<Sun size={15} />}
            title={zh ? '個人偏好' : 'Preferences'}
            description={zh ? '外觀與顯示語言' : 'Appearance & language'}
          />
          <div style={{ ...CARD_BODY }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <PrefCard
                icon={theme === 'dark' ? <Moon size={16} /> : <Sun size={16} />}
                title={zh ? '外觀主題' : 'Theme'}
                value={theme === 'dark' ? (zh ? '深色模式' : 'Dark Mode') : (zh ? '淺色模式' : 'Light Mode')}
                onClick={toggleTheme}
              />
              <PrefCard
                icon={<Languages size={16} />}
                title={zh ? '語言' : 'Language'}
                value={zh ? '繁體中文' : 'English'}
                onClick={() => switchLanguage(language === 'zh-TW' ? 'en' : 'zh-TW')}
              />
            </div>
          </div>
        </div>

        {/* ── AI Providers ─────────────────────────────────────────────── */}
        <div style={CARD}>
          <CardHeader
            icon={<Cpu size={15} />}
            title={zh ? 'AI 模型供應商' : 'AI Providers'}
            description={zh ? '金鑰僅儲存於本機' : 'Keys stored locally only'}
          />
          <div style={CARD_BODY}>
            <AiProviderSettings zh={zh} onSaved={loadApiKeys} />
          </div>
        </div>

        {/* ── Backup ───────────────────────────────────────────────────── */}
        <div style={CARD}>
          <CardHeader
            icon={<HardDrive size={15} />}
            title={zh ? '資料備份' : 'Data Backup'}
            description={zh ? '本機快照 · 不含 API 金鑰' : 'Local snapshots · no API keys'}
          />
          <div style={CARD_BODY}>
            <BackupSettings zh={zh} />
          </div>
        </div>

        {/* ── MCP / API Keys ───────────────────────────────────────────── */}
        <div style={CARD}>
          <CardHeader
            icon={<Key size={15} />}
            title={zh ? 'MCP / API 金鑰' : 'MCP / API Keys'}
            description={apiKeys.length > 0 ? `${apiKeys.length} ${zh ? '把作用中' : 'active'}` : undefined}
          />
          <div style={CARD_BODY}>
            <p style={{ margin: 0, fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.6 }}>
              {zh
                ? '金鑰繼承你在每個知識庫的角色權限，可直接用於 MCP 工具或 API 呼叫。'
                : 'Keys inherit your role in each knowledge base. Use them with MCP tools or direct API calls.'}
            </p>

            {/* One-time key reveal */}
            {newKeySecret && (
              <div style={{
                padding: 14, borderRadius: 8,
                border: '1px solid var(--color-primary)',
                background: 'var(--color-primary-subtle)',
              }}>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: 'var(--color-primary)' }}>
                  {zh ? '請立即複製金鑰，關閉後無法再次查看。' : "Copy your key now — it won't be shown again."}
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <code style={{
                    flex: 1, fontSize: 11, wordBreak: 'break-all',
                    padding: '7px 10px', background: 'var(--bg-code)', borderRadius: 6,
                    fontFamily: 'monospace',
                  }}>
                    {newKeySecret.key}
                  </code>
                  <button className="btn-secondary" style={{ flexShrink: 0 }} onClick={() => handleCopy(newKeySecret.key)}>
                    <Copy size={13} />
                  </button>
                </div>
                <button
                  style={{ marginTop: 8, fontSize: 11, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                  onClick={() => setNewKeySecret(null)}
                >
                  {zh ? '我已保存，關閉' : "I've saved it, close"}
                </button>
              </div>
            )}

            {/* Key list */}
            {apiKeys.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {apiKeys.map(k => (
                  <div
                    key={k.id}
                    style={{
                      display: 'grid', gridTemplateColumns: '1fr auto auto',
                      gap: 12, alignItems: 'center',
                      padding: '10px 12px', borderRadius: 8,
                      background: 'var(--bg-surface)',
                    }}
                  >
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{k.name}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2, fontFamily: 'monospace' }}>
                        {k.prefix}… &nbsp;·&nbsp; {zh ? '建立於' : 'Created'} {new Date(k.created_at).toLocaleDateString()}
                        {k.last_used_at && <> &nbsp;·&nbsp; {zh ? '最後使用' : 'Last'} {new Date(k.last_used_at).toLocaleDateString()}</>}
                      </div>
                    </div>
                    <button className="btn-ghost" title={zh ? '輪替' : 'Rotate'} onClick={() => handleRotateKey(k.id)} style={{ padding: '4px 6px' }}>
                      <RotateCcw size={13} />
                    </button>
                    <button className="btn-ghost" title={zh ? '撤銷' : 'Revoke'} onClick={() => handleRevokeKey(k.id)} style={{ padding: '4px 6px', color: 'var(--color-error)' }}>
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Create new key — separated by top border */}
            <div style={{
              display: 'grid', gridTemplateColumns: '1fr auto',
              gap: 8, paddingTop: 14,
              borderTop: '1px solid var(--border-subtle)',
              marginTop: 2,
            }}>
              <input
                className="mt-input"
                placeholder={zh ? '金鑰名稱（例：My MCP Agent）' : 'Key name (e.g. My MCP Agent)'}
                value={newKeyName}
                onChange={e => setNewKeyName(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleCreateKey()}
              />
              <button
                className="btn-primary"
                onClick={handleCreateKey}
                disabled={keyCreating || !newKeyName.trim()}
                style={{ flexShrink: 0, whiteSpace: 'nowrap' }}
              >
                <Plus size={13} />
                {keyCreating ? (zh ? '建立中…' : 'Creating…') : (zh ? '建立' : 'Create')}
              </button>
            </div>
          </div>
        </div>

        {/* ── Security ─────────────────────────────────────────────────── */}
        <div style={CARD}>
          <CardHeader
            icon={<ShieldCheck size={15} />}
            title={zh ? '帳號安全性' : 'Security'}
            description={zh ? '更新密碼後將登出所有裝置' : 'Updating password signs out all devices'}
          />
          <div style={CARD_BODY}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <input
                className="mt-input"
                type="password"
                placeholder={zh ? '新密碼' : 'New Password'}
                value={pwd}
                onChange={e => setPwd(e.target.value)}
              />
              <input
                className="mt-input"
                type="password"
                placeholder={zh ? '確認新密碼' : 'Confirm New Password'}
                value={confirmPwd}
                onChange={e => setConfirmPwd(e.target.value)}
              />
            </div>
            {pwdError && <div style={{ color: 'var(--color-error)', fontSize: 12 }}>{pwdError}</div>}
            <button className="btn-secondary" onClick={handleUpdatePassword} disabled={pwdSaving} style={{ alignSelf: 'flex-start' }}>
              {pwdSaving ? t('common.saving') : (zh ? '更新密碼' : 'Update Password')}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
