import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Shield, Cpu, Trash2, RefreshCw, ChevronDown, ChevronUp, CheckCircle2, AlertCircle } from 'lucide-react';
import { system, ai } from './api';
import type { SystemAIKey, SystemAIKeyUpsert } from './api/system';
import type { ModelInfo } from './api/ai';
import { useModal } from './components/ModalContext';

// ─── Provider card ────────────────────────────────────────────────────────────

type Target = 'system' | 'safety';
type Provider = 'openai' | 'anthropic' | 'gemini' | 'ollama';

const PROVIDER_LABELS: Record<Provider, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  gemini: 'Google Gemini',
  ollama: 'Ollama (local)',
};

const PROVIDER_HINTS: Record<Provider, string> = {
  openai: 'sk-...',
  anthropic: 'sk-ant-...',
  gemini: 'AIzaSy...',
  ollama: 'Base URL: http://localhost:11434',
};

interface ProviderFormProps {
  target: Target;
  provider: Provider;
  existingKey?: SystemAIKey;
  zh: boolean;
  onRefresh: () => void;
}

function ProviderForm({ target, provider, existingKey, zh, onRefresh }: ProviderFormProps) {
  const { toast } = useModal();
  const [expanded, setExpanded] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState(existingKey?.base_url || '');
  const [authMode, setAuthMode] = useState<'none' | 'bearer'>(
    (existingKey?.auth_mode as any) || 'none'
  );
  const [authToken, setAuthToken] = useState('');
  const [chatModel, setChatModel] = useState(existingKey?.default_chat_model || '');
  const [embedModel, setEmbedModel] = useState(existingKey?.default_embedding_model || '');
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [fetchingModels, setFetchingModels] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState('');

  const isOllama = provider === 'ollama';

  const handleFetchModels = async () => {
    setFetchingModels(true);
    setError('');
    try {
      const params: any = isOllama
        ? { base_url: baseUrl, auth_mode: authMode, auth_token: authToken }
        : { api_key: apiKey };
      const res = await ai.listModelsProxy(provider, params);
      setModels(res);
      toast({ message: zh ? `載入 ${res.length} 個模型` : `Loaded ${res.length} models`, variant: 'success' });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setFetchingModels(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      const payload: SystemAIKeyUpsert = {
        target,
        provider,
        default_chat_model: chatModel || undefined,
        default_embedding_model: embedModel || undefined,
      };
      if (isOllama) {
        payload.base_url = baseUrl;
        payload.auth_mode = authMode;
        payload.auth_token = authToken || undefined;
      } else if (apiKey) {
        payload.api_key = apiKey;
      }
      await system.upsertSystemAIKey(payload);
      toast({ message: zh ? '已儲存' : 'Saved', variant: 'success' });
      setApiKey('');
      setExpanded(false);
      onRefresh();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(zh ? '確定要移除這組金鑰嗎？' : 'Remove this key?')) return;
    setDeleting(true);
    try {
      await system.deleteSystemAIKey(target, provider);
      toast({ message: zh ? '已移除' : 'Removed', variant: 'success' });
      onRefresh();
    } catch (e: any) {
      toast({ message: e.message, variant: 'error' });
    } finally {
      setDeleting(false);
    }
  };

  const chatModels = models.filter(m => m.model_type !== 'embedding');
  const embedModels = models.filter(m => m.model_type === 'embedding');

  return (
    <div style={{
      border: `1px solid ${existingKey ? 'var(--color-success, #22c55e)' : 'var(--border-default)'}`,
      borderRadius: 10,
      overflow: 'hidden',
    }}>
      {/* Header row */}
      <div
        style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '12px 14px',
          background: existingKey ? 'var(--bg-elevated)' : 'var(--bg-surface)',
          cursor: 'pointer',
        }}
        onClick={() => setExpanded(v => !v)}
      >
        {existingKey
          ? <CheckCircle2 size={16} color="var(--color-success, #22c55e)" />
          : <AlertCircle size={16} color="var(--text-muted)" />
        }
        <span style={{ flex: 1, fontWeight: 600, fontSize: 13 }}>
          {PROVIDER_LABELS[provider]}
        </span>
        {existingKey && (
          <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
            ···{existingKey.key_hint || existingKey.base_url?.slice(-6) || ''}
            {existingKey.default_chat_model && ` · ${existingKey.default_chat_model}`}
          </span>
        )}
        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </div>

      {/* Expanded form */}
      {expanded && (
        <div style={{ padding: '14px 14px 16px', borderTop: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: 10 }}>
          {isOllama ? (
            <>
              <input
                className="mt-input"
                placeholder={zh ? '伺服器位址，例如 http://localhost:11434' : 'Base URL, e.g. http://localhost:11434'}
                value={baseUrl}
                onChange={e => setBaseUrl(e.target.value)}
              />
              <select className="mt-input" value={authMode} onChange={e => setAuthMode(e.target.value as any)}>
                <option value="none">{zh ? '無驗證' : 'No Auth'}</option>
                <option value="bearer">Bearer Token</option>
              </select>
              {authMode === 'bearer' && (
                <input className="mt-input" type="password" placeholder="Token" value={authToken} onChange={e => setAuthToken(e.target.value)} />
              )}
            </>
          ) : (
            <input
              className="mt-input"
              type="password"
              placeholder={existingKey ? (zh ? '留空保留現有金鑰' : 'Leave blank to keep existing key') : PROVIDER_HINTS[provider]}
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
            />
          )}

          {/* Model selector row */}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
            {chatModels.length > 0 ? (
              <select className="mt-input" style={{ flex: 1 }} value={chatModel} onChange={e => setChatModel(e.target.value)}>
                <option value="">{zh ? '── 預設對話模型 ──' : '── Default chat model ──'}</option>
                {chatModels.map(m => <option key={m.id} value={m.id}>{m.id}</option>)}
              </select>
            ) : (
              <input
                className="mt-input"
                style={{ flex: 1 }}
                placeholder={zh ? '對話模型 ID（可選）' : 'Chat model ID (optional)'}
                value={chatModel}
                onChange={e => setChatModel(e.target.value)}
              />
            )}
            {provider !== 'anthropic' && (
              embedModels.length > 0 ? (
                <select className="mt-input" style={{ flex: 1 }} value={embedModel} onChange={e => setEmbedModel(e.target.value)}>
                  <option value="">{zh ? '── 嵌入模型 ──' : '── Embedding model ──'}</option>
                  {embedModels.map(m => <option key={m.id} value={m.id}>{m.id}</option>)}
                </select>
              ) : (
                <input
                  className="mt-input"
                  style={{ flex: 1 }}
                  placeholder={zh ? '嵌入模型 ID（可選）' : 'Embedding model ID (optional)'}
                  value={embedModel}
                  onChange={e => setEmbedModel(e.target.value)}
                />
              )
            )}
          </div>

          {error && <div style={{ fontSize: 12, color: 'var(--color-error)' }}>{error}</div>}

          <div style={{ display: 'flex', gap: 8, marginTop: 2 }}>
            <button className="btn-secondary" style={{ flex: 1 }} onClick={handleFetchModels} disabled={fetchingModels}>
              {fetchingModels
                ? <><RefreshCw size={12} className="animate-spin" /> {zh ? '載入中…' : 'Loading…'}</>
                : (zh ? '驗證並載入模型' : 'Test & load models')
              }
            </button>
            <button className="btn-primary" style={{ flex: 1 }} onClick={handleSave} disabled={saving}>
              {saving ? (zh ? '儲存中…' : 'Saving…') : (zh ? '儲存' : 'Save')}
            </button>
            {existingKey && (
              <button
                className="btn-secondary"
                style={{ color: 'var(--color-error)' }}
                onClick={handleDelete}
                disabled={deleting}
                title={zh ? '移除金鑰' : 'Remove key'}
              >
                <Trash2 size={14} />
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Section (system / safety) ────────────────────────────────────────────────

interface SectionProps {
  target: Target;
  keys: SystemAIKey[];
  zh: boolean;
  onRefresh: () => void;
}

function AIKeySection({ target, keys, zh, onRefresh }: SectionProps) {
  const isSafety = target === 'safety';
  const providers: Provider[] = isSafety
    ? ['anthropic', 'openai', 'gemini']
    : ['openai', 'anthropic', 'gemini', 'ollama'];

  const keyMap = Object.fromEntries(keys.filter(k => k.target === target).map(k => [k.provider, k]));

  return (
    <div style={{ marginBottom: 32 }}>
      {/* Section header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
        {isSafety
          ? <Shield size={18} color="var(--color-warning, #f59e0b)" />
          : <Cpu size={18} color="var(--color-primary)" />
        }
        <div>
          <div style={{ fontWeight: 700, fontSize: 14 }}>
            {isSafety
              ? (zh ? '安全審查模型' : 'Safety Review Model')
              : (zh ? '系統共用模型' : 'System Shared Models')
            }
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
            {isSafety
              ? (zh
                  ? '用於節點提案的安全審查，建議使用高品質指令遵循能力的模型'
                  : 'Used for safety-reviewing node proposals. Prefer a model with strong instruction-following.')
              : (zh
                  ? '所有使用者的 Fallback 模型；當使用者未設定個人金鑰時使用'
                  : 'Fallback for all users when no personal key is configured')
            }
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {providers.map(p => (
          <ProviderForm
            key={p}
            target={target}
            provider={p}
            existingKey={keyMap[p]}
            zh={zh}
            onRefresh={onRefresh}
          />
        ))}
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function SystemAISettings() {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const { toast } = useModal();
  const [keys, setKeys] = useState<SystemAIKey[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await system.listSystemAIKeys();
      setKeys(data);
    } catch (e: any) {
      toast({ message: e.message, variant: 'error' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div style={{ maxWidth: 680, margin: '0 auto', padding: '32px 24px' }}>
      {/* Page title */}
      <div style={{ marginBottom: 28 }}>
        <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>
          {zh ? '系統 AI 模型設定' : 'System AI Model Settings'}
        </h2>
        <p style={{ margin: '6px 0 0', fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.6 }}>
          {zh
            ? '管理系統層級的 AI 供應商金鑰。系統金鑰是所有使用者的 Fallback；安全審查金鑰專用於 Consult 節點提案的安全過濾。'
            : 'Manage system-level AI provider keys. System keys act as fallback for all users; the safety key is used exclusively for Consult safety-filtering proposals.'
          }
        </p>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
          <RefreshCw size={20} className="animate-spin" />
        </div>
      ) : (
        <>
          <AIKeySection target="system" keys={keys} zh={zh} onRefresh={load} />
          <div style={{ borderTop: '1px solid var(--border-default)', margin: '8px 0 28px' }} />
          <AIKeySection target="safety" keys={keys} zh={zh} onRefresh={load} />
        </>
      )}
    </div>
  );
}
