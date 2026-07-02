import { useState, useEffect } from 'react';
import { voice } from '../api';
import type { VoiceKey } from '../api';
import { useModal } from './ModalContext';

const STT_PROVIDERS = ['gcp', 'openai', 'azure', 'deepgram'] as const;
const TTS_PROVIDERS = ['gcp', 'openai', 'azure', 'elevenlabs'] as const;

const PROVIDER_LABEL: Record<string, string> = { gcp: 'Google' };

function VoicePurposeForm({
  zh,
  purpose,
  providers,
  savedKey,
  onSaved,
}: {
  zh: boolean;
  purpose: 'stt' | 'tts';
  providers: readonly string[];
  savedKey: VoiceKey | undefined;
  onSaved: () => void;
}) {
  const { toast } = useModal();
  const [provider, setProvider] = useState<string>(providers[0]);
  const [credentialType, setCredentialType] = useState<'api_key' | 'service_account_json'>('api_key');
  const [credential, setCredential] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const label = purpose === 'stt'
    ? (zh ? '語音輸入 (STT)' : 'Speech Input (STT)')
    : (zh ? '語音輸出 (TTS)' : 'Speech Output (TTS)');

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      await voice.upsertKey({ purpose, provider, credential, credential_type: credentialType });
      setCredential('');
      onSaved();
      toast({ message: zh ? '設定已儲存' : 'Settings saved', variant: 'success' });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    try {
      await voice.deleteKey(purpose);
      onSaved();
      toast({ message: zh ? '金鑰已移除' : 'Key removed', variant: 'success' });
    } catch (e: any) {
      toast({ message: e.message, variant: 'error' });
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: '12px 14px', background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: 8 }}>
      <div style={{ fontSize: 13, fontWeight: 600 }}>{label}</div>

      {savedKey && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12, color: 'var(--text-muted)' }}>
          <span style={{ textTransform: 'capitalize' }}>{savedKey.provider} — {savedKey.key_hint}</span>
          <button className="btn-secondary" style={{ color: 'var(--color-error)' }} onClick={handleDelete}>
            {zh ? '移除' : 'Remove'}
          </button>
        </div>
      )}

      <div style={{ display: 'flex', gap: 8 }}>
        {providers.map(p => (
          <button
            key={p}
            className={provider === p ? 'btn-primary' : 'btn-secondary'}
            onClick={() => { setProvider(p); setCredentialType('api_key'); }}
            style={{ flex: 1, textTransform: 'capitalize' }}
          >
            {PROVIDER_LABEL[p] ?? p}
          </button>
        ))}
      </div>

      {provider === 'gcp' && (
        <select className="mt-input" value={credentialType} onChange={e => setCredentialType(e.target.value as any)}>
          <option value="api_key">{zh ? 'API Key' : 'API Key'}</option>
          <option value="service_account_json">{zh ? 'Service Account JSON' : 'Service Account JSON'}</option>
        </select>
      )}

      {provider === 'gcp' && credentialType === 'api_key' && (
        <div style={{ fontSize: 11, color: 'var(--text-muted)', background: 'var(--bg-base)', border: '1px solid var(--border-default)', borderRadius: 6, padding: '6px 10px', lineHeight: 1.6 }}>
          {zh
            ? '注意：建立 GCP API 金鑰後，請在「應用程式限制」選擇「無」，否則從伺服器發出的請求會被 Google 封鎖。'
            : 'Note: when creating your GCP API key, set Application restrictions to "None" — server-side requests have no HTTP referrer and will be blocked otherwise.'}
        </div>
      )}

      {provider === 'azure' ? (
        <input
          className="mt-input"
          type="password"
          placeholder={zh ? '格式：<region>:<subscription_key>' : 'Format: <region>:<subscription_key>'}
          value={credential}
          onChange={e => setCredential(e.target.value)}
        />
      ) : credentialType === 'service_account_json' ? (
        <textarea
          className="mt-input"
          placeholder={zh ? '貼上 Service Account JSON 內容' : 'Paste Service Account JSON contents'}
          value={credential}
          onChange={e => setCredential(e.target.value)}
          rows={5}
        />
      ) : (
        <input
          className="mt-input"
          type="password"
          placeholder={`${provider.toUpperCase()} API Key`}
          value={credential}
          onChange={e => setCredential(e.target.value)}
        />
      )}

      {error && <div style={{ color: 'var(--color-error)', fontSize: 12 }}>{error}</div>}

      <button className="btn-primary" onClick={handleSave} disabled={saving || !credential} style={{ alignSelf: 'flex-start' }}>
        {saving ? (zh ? '儲存中...' : 'Saving...') : (zh ? '儲存' : 'Save')}
      </button>
    </div>
  );
}

export default function VoiceProviderSettings({ zh }: { zh: boolean }) {
  const [savedKeys, setSavedKeys] = useState<VoiceKey[]>([]);

  const fetchKeys = async () => {
    try {
      const keys = await voice.listKeys();
      setSavedKeys(keys);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>
        {zh
          ? '語音為個人設定，STT（語音輸入）與 TTS（語音輸出）可各自選擇不同服務商。金鑰由你自己的帳號負擔費用，系統僅代為呼叫，不儲存語音內容。'
          : 'Voice settings are personal. STT (speech input) and TTS (speech output) can use independent providers. You are billed directly by your chosen provider; MemTrace only proxies the call and never stores audio content.'}
      </p>
      <VoicePurposeForm
        zh={zh}
        purpose="stt"
        providers={STT_PROVIDERS}
        savedKey={savedKeys.find(k => k.purpose === 'stt')}
        onSaved={fetchKeys}
      />
      <VoicePurposeForm
        zh={zh}
        purpose="tts"
        providers={TTS_PROVIDERS}
        savedKey={savedKeys.find(k => k.purpose === 'tts')}
        onSaved={fetchKeys}
      />
    </div>
  );
}
