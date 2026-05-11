import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Moon, Sun, LogOut, Key, Plus, RotateCcw, Trash2, Copy } from 'lucide-react';
import { auth, users } from '../api';
import type { PersonalApiKey, PersonalApiKeyCreateResponse } from '../api/workspaces';
import { useModal } from './ModalContext';
import BackupSettings from './BackupSettings';
import AiProviderSettings from './AiProviderSettings';

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

  // Account-level API Keys
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

  const loadData = () => {
    loadApiKeys();
  };

  useEffect(() => { loadData(); }, []);

  // loadData called from AiProviderSettings onSaved


  return (
    <div className="settings-panel" style={{ padding: 40, maxWidth: 800, margin: '0 auto' }}>
      <header style={{ marginBottom: 40, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: 24, marginBottom: 8 }}>{t('nav.settings')}</h1>
          <p style={{ color: 'var(--text-muted)' }}>{user?.email}</p>
        </div>
        <button className="btn-secondary" onClick={() => auth.logout()} style={{ color: 'var(--color-error)' }}>
          <LogOut size={16} />
          {t('nav.logout')}
        </button>
      </header>

      {/* Appearance */}
      <section style={{ marginBottom: 40 }}>
        <h3 style={{ fontSize: 15, marginBottom: 16 }}>{zh ? '個人偏好' : 'Preferences'}</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div className="card" onClick={toggleTheme} style={{ cursor: 'pointer', padding: 20, display: 'flex', alignItems: 'center', gap: 12 }}>
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            <div>
              <div style={{ fontSize: 14, fontWeight: 600 }}>{zh ? '外觀主題' : 'Theme'}</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{theme === 'dark' ? (zh ? '深色模式' : 'Dark Mode') : (zh ? '淺色模式' : 'Light Mode')}</div>
            </div>
          </div>
          <div className="card" onClick={() => switchLanguage(language === 'zh-TW' ? 'en' : 'zh-TW')} style={{ cursor: 'pointer', padding: 20, display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ fontSize: 18, fontWeight: 700 }}>文</div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600 }}>{zh ? '語言' : 'Language'}</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{zh ? '繁體中文' : 'English'}</div>
            </div>
          </div>
        </div>
      </section>

      {/* AI Providers */}
      <section style={{ marginBottom: 40 }}>
        <h3 style={{ fontSize: 15, marginBottom: 16 }}>{zh ? 'AI 模型供應商' : 'AI Providers'}</h3>
        <AiProviderSettings zh={zh} onSaved={loadData} />
      </section>

      {/* Backup */}
      <BackupSettings zh={zh} />

      {/* Account-level API Keys */}
      <section style={{ marginBottom: 40 }}>
        <h3 style={{ fontSize: 15, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Key size={15} />
          {zh ? 'MCP / API 金鑰' : 'MCP / API Keys'}
        </h3>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
          {zh
            ? '金鑰繼承你在每個知識庫的角色權限，可直接用於 MCP 工具或 API 呼叫。'
            : 'Keys inherit your role in each knowledge base. Use them with MCP tools or direct API calls.'}
        </p>

        {/* One-time key reveal */}
        {newKeySecret && (
          <div className="card" style={{ padding: 16, marginBottom: 16, borderColor: 'var(--color-primary)', background: 'var(--bg-subtle)' }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, color: 'var(--color-primary)' }}>
              {zh ? '請立即複製金鑰，關閉後無法再次查看。' : 'Copy your key now — it won\'t be shown again.'}
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <code style={{ flex: 1, fontSize: 12, wordBreak: 'break-all', padding: '8px 12px', background: 'var(--bg-code)', borderRadius: 6 }}>
                {newKeySecret.key}
              </code>
              <button className="btn-secondary" style={{ flexShrink: 0 }} onClick={() => handleCopy(newKeySecret.key)}>
                <Copy size={14} />
              </button>
            </div>
            <button style={{ marginTop: 8, fontSize: 12, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }}
              onClick={() => setNewKeySecret(null)}>
              {zh ? '我已保存，關閉' : 'I\'ve saved it, close'}
            </button>
          </div>
        )}

        {/* Existing keys */}
        {apiKeys.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
            {apiKeys.map(k => (
              <div key={k.id} className="card" style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 600 }}>{k.name}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                    {k.prefix}… &nbsp;·&nbsp; {zh ? '建立於' : 'Created'} {new Date(k.created_at).toLocaleDateString()}
                    {k.last_used_at && <> &nbsp;·&nbsp; {zh ? '最後使用' : 'Last used'} {new Date(k.last_used_at).toLocaleDateString()}</>}
                  </div>
                </div>
                <button className="btn-ghost" title={zh ? '輪替' : 'Rotate'} onClick={() => handleRotateKey(k.id)} style={{ padding: '4px 8px' }}>
                  <RotateCcw size={14} />
                </button>
                <button className="btn-ghost" title={zh ? '撤銷' : 'Revoke'} onClick={() => handleRevokeKey(k.id)} style={{ padding: '4px 8px', color: 'var(--color-error)' }}>
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Create new key */}
        <div style={{ display: 'flex', gap: 8 }}>
          <input className="mt-input" style={{ flex: 1 }}
            placeholder={zh ? '金鑰名稱（例：My MCP Agent）' : 'Key name (e.g. My MCP Agent)'}
            value={newKeyName} onChange={e => setNewKeyName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleCreateKey()}
          />
          <button className="btn-primary" onClick={handleCreateKey} disabled={keyCreating || !newKeyName.trim()} style={{ flexShrink: 0 }}>
            <Plus size={14} />
            {keyCreating ? (zh ? '建立中…' : 'Creating…') : (zh ? '建立' : 'Create')}
          </button>
        </div>
      </section>

      {/* Password */}
      <section style={{ marginBottom: 40 }}>
        <h3 style={{ fontSize: 15, marginBottom: 16 }}>{zh ? '帳號安全性' : 'Security'}</h3>
        <div className="card" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 14 }}>
          <input className="mt-input" type="password" placeholder={zh ? '新密碼' : 'New Password'} value={pwd} onChange={e => setPwd(e.target.value)} />
          <input className="mt-input" type="password" placeholder={zh ? '確認新密碼' : 'Confirm New Password'} value={confirmPwd} onChange={e => setConfirmPwd(e.target.value)} />
          {pwdError && <div style={{ color: 'var(--color-error)', fontSize: 13 }}>{pwdError}</div>}
          <button className="btn-secondary" onClick={handleUpdatePassword} disabled={pwdSaving}>
            {pwdSaving ? t('common.saving') : zh ? '更新密碼' : 'Update Password'}
          </button>
        </div>
      </section>
    </div>
  );
}
