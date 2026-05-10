import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ai } from '../api';
import { useModal } from './ModalContext';

export default function AiProviderSettings({ zh, onSaved }: { zh: boolean, onSaved: () => void }) {
  const { t } = useTranslation();
  const { toast } = useModal();
  const [provider, setProvider] = useState<'openai' | 'anthropic' | 'gemini' | 'ollama'>('openai');
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [authMode, setAuthMode] = useState<'none' | 'bearer'>('none');
  const [authToken, setAuthToken] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSaveKey = async () => {
    setSaving(true);
    setError('');
    try {
      if (provider === 'ollama') {
        await ai.upsertKey({ provider: 'ollama', base_url: baseUrl, auth_mode: authMode, auth_token: authToken });
      } else {
        await ai.upsertKey({ provider, api_key: apiKey });
      }
      setApiKey('');
      onSaved();
      toast({ message: zh ? '設定已儲存' : 'Settings saved', variant: 'success' });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card" style={{ padding: 24 }}>
      <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
        {['openai', 'anthropic', 'gemini', 'ollama'].map((p: any) => (
          <button
            key={p}
            className={provider === p ? 'btn-primary' : 'btn-secondary'}
            onClick={() => { setProvider(p); setError(''); }}
            style={{ flex: 1, textTransform: 'capitalize' }}
          >
            {p}
          </button>
        ))}
      </div>

      {provider === 'ollama' ? (
         <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
           <input className="mt-input" placeholder="Base URL (e.g. http://localhost:11434)" value={baseUrl} onChange={e => setBaseUrl(e.target.value)} />
           <select className="mt-input" value={authMode} onChange={e => setAuthMode(e.target.value as any)}>
             <option value="none">No Auth</option>
             <option value="bearer">Bearer Token</option>
           </select>
           {authMode === 'bearer' && <input className="mt-input" type="password" placeholder="Token" value={authToken} onChange={e => setAuthToken(e.target.value)} />}
         </div>
      ) : (
         <input className="mt-input" type="password" placeholder={`${provider.toUpperCase()} API Key`} value={apiKey} onChange={e => setApiKey(e.target.value)} />
      )}

      {error && <div style={{ color: 'var(--color-error)', marginTop: 12, fontSize: 13 }}>{error}</div>}
      <button className="btn-primary" onClick={handleSaveKey} disabled={saving} style={{ marginTop: 20, width: '100%' }}>
        {saving ? t('common.saving') : t('common.save')}
      </button>
    </div>
  );
}
