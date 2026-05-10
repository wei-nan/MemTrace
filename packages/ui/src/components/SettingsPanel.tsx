import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Moon, Sun, LogOut } from 'lucide-react';
import { auth } from '../api';
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
    // ai.listKeys().then(setKeys).catch(() => {});
    // users.apiKeys.list().then(setPersonalKeys).catch(() => {});
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
