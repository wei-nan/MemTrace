import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { ai } from '../api';
import type { ModelInfo, AIKey } from '../api';
import { useModal } from './ModalContext';

export default function AiProviderSettings({ zh, onSaved }: { zh: boolean, onSaved: () => void }) {
  const { t } = useTranslation();
  const { toast } = useModal();
  const [provider, setProvider] = useState<'openai' | 'anthropic' | 'gemini' | 'ollama'>('openai');
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [authMode, setAuthMode] = useState<'none' | 'bearer'>('none');
  const [authToken, setAuthToken] = useState('');
  const [defaultChatModel, setDefaultChatModel] = useState('');
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [fetchingModels, setFetchingModels] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [savedKeys, setSavedKeys] = useState<AIKey[]>([]);

  const fetchKeys = async () => {
    try {
      const keys = await ai.listKeys();
      setSavedKeys(keys);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  // Reset states when provider changes
  useEffect(() => {
    setModels([]);
    setDefaultChatModel('');
    setError('');
  }, [provider]);

  const handleFetchModels = async () => {
    setFetchingModels(true);
    setError('');
    try {
      let params: any = {};
      if (provider === 'ollama') {
        params = { base_url: baseUrl, auth_mode: authMode, auth_token: authToken };
      } else {
        params = { api_key: apiKey };
      }
      const res = await ai.listModelsProxy(provider, params);
      const chatModels = res.filter(m => m.model_type !== 'embedding');
      setModels(chatModels);
      if (chatModels.length > 0 && !defaultChatModel) {
        setDefaultChatModel(chatModels[0].id);
      }
      toast({ message: zh ? '成功載入模型列表' : 'Models loaded', variant: 'success' });
    } catch (e: any) {
      setError(zh ? `無法載入模型: ${e.message}` : `Failed to load models: ${e.message}`);
    } finally {
      setFetchingModels(false);
    }
  };

  const handleSaveKey = async () => {
    setSaving(true);
    setError('');
    try {
      if (provider === 'ollama') {
        await ai.upsertKey({ provider: 'ollama', base_url: baseUrl, auth_mode: authMode, auth_token: authToken, default_chat_model: defaultChatModel });
      } else {
        await ai.upsertKey({ provider, api_key: apiKey, default_chat_model: defaultChatModel });
      }
      setApiKey('');
      setModels([]);
      setDefaultChatModel('');
      await fetchKeys();
      onSaved();
      toast({ message: zh ? '設定已儲存' : 'Settings saved', variant: 'success' });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteKey = async (delProvider: string) => {
    try {
      await ai.deleteKey(delProvider);
      await fetchKeys();
      toast({ message: zh ? '金鑰已移除' : 'Key removed', variant: 'success' });
    } catch (e: any) {
      toast({ message: e.message, variant: 'error' });
    }
  };

  return (
    <div className="card" style={{ padding: 24 }}>
      {savedKeys.length > 0 && (
        <div style={{ marginBottom: 32 }}>
          <h4 style={{ marginBottom: 16 }}>{zh ? '已配置的 AI 供應商' : 'Configured Providers'}</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {savedKeys.map(k => (
              <div key={k.provider} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', background: 'var(--color-bg-secondary)', borderRadius: 8 }}>
                <div>
                  <div style={{ fontWeight: 600, textTransform: 'capitalize' }}>{k.provider}</div>
                  <div style={{ fontSize: 13, color: 'var(--color-text-secondary)', marginTop: 4 }}>
                    {k.key_hint || k.base_url || 'Configured'}
                  </div>
                  {k.default_chat_model && (
                    <div style={{ fontSize: 13, color: 'var(--color-primary)', marginTop: 4 }}>
                      Model: {k.default_chat_model}
                    </div>
                  )}
                </div>
                <button className="btn-secondary" style={{ color: 'var(--color-error)' }} onClick={() => handleDeleteKey(k.provider)}>
                  {zh ? '移除' : 'Remove'}
                </button>
              </div>
            ))}
          </div>
          <hr style={{ margin: '32px 0 24px', borderColor: 'var(--color-border)' }} />
        </div>
      )}

      <h4 style={{ marginBottom: 16 }}>{zh ? '新增或更新設定' : 'Add or Update Configuration'}</h4>
      <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
        {['openai', 'anthropic', 'gemini', 'ollama'].map((p: any) => (
          <button
            key={p}
            className={provider === p ? 'btn-primary' : 'btn-secondary'}
            onClick={() => setProvider(p)}
            style={{ flex: 1, textTransform: 'capitalize' }}
          >
            {p}
          </button>
        ))}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {provider === 'ollama' ? (
          <>
            <input className="mt-input" placeholder="Base URL (e.g. http://localhost:11434)" value={baseUrl} onChange={e => setBaseUrl(e.target.value)} />
            <select className="mt-input" value={authMode} onChange={e => setAuthMode(e.target.value as any)}>
              <option value="none">No Auth</option>
              <option value="bearer">Bearer Token</option>
            </select>
            {authMode === 'bearer' && <input className="mt-input" type="password" placeholder="Token" value={authToken} onChange={e => setAuthToken(e.target.value)} />}
          </>
        ) : (
          <input className="mt-input" type="password" placeholder={`${provider.toUpperCase()} API Key`} value={apiKey} onChange={e => setApiKey(e.target.value)} />
        )}
        
        <button className="btn-secondary" onClick={handleFetchModels} disabled={fetchingModels}>
          {fetchingModels ? (zh ? '載入中...' : 'Loading...') : (zh ? '1. 驗證金鑰並載入模型' : '1. Test & Load Models')}
        </button>

        {models.length > 0 && (
          <select className="mt-input" value={defaultChatModel} onChange={e => setDefaultChatModel(e.target.value)}>
            <option value="" disabled>{zh ? '請選擇預設對話模型...' : 'Select default chat model...'}</option>
            {models.map(m => (
              <option key={m.id} value={m.id}>{m.display_name} ({m.id})</option>
            ))}
          </select>
        )}
      </div>

      {error && <div style={{ color: 'var(--color-error)', marginTop: 12, fontSize: 13 }}>{error}</div>}
      
      <button className="btn-primary" onClick={handleSaveKey} disabled={saving} style={{ marginTop: 20, width: '100%' }}>
        {saving ? t('common.saving') : (zh ? '2. 儲存設定' : '2. Save Settings')}
      </button>
    </div>
  );
}
