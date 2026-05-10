import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  CheckCircle2, Mail, Database, FileUp, 
  Settings2, PartyPopper, ChevronRight,
  Upload, AlertCircle, RefreshCw,
  Languages, GitMerge, Key, Brain
} from 'lucide-react';
import { auth, workspaces, ai, ingest, type Onboarding } from './api';
import { Button, Input } from './components/ui';

const STEPS = [
  { id: 'welcome', icon: Languages },
  { id: 'account', icon: CheckCircle2 },
  { id: 'security', icon: Key },
  { id: 'email', icon: Mail },
  { id: 'kb', icon: Database },
  { id: 'ingest', icon: FileUp },
  { id: 'ai', icon: Settings2 },
  { id: 'done', icon: PartyPopper },
];

export default function OnboardingWizard({
  user,
  state,
  onUpdate,
  onComplete,
  onOpenSpecKb,
}: {
  user: any,
  state: Onboarding,
  onUpdate: (data: Partial<Onboarding>) => void,
  onComplete: () => void,
  onOpenSpecKb?: () => void, 
}) {
  const { t, i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  
  const [activeStepIdx, setActiveStepIdx] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // KB State
  const [kbNameZh, setKbNameZh] = useState('');
  const [kbNameEn, setKbNameEn] = useState('');
  const [kbVisibility, setKbVisibility] = useState<'private' | 'restricted' | 'conditional_public' | 'public'>('private');
  const [qaArchiveMode, setQaArchiveMode] = useState<'auto_active' | 'manual_review'>('manual_review');
  
  // AI State
  const [provider, setProvider] = useState<'openai' | 'anthropic' | 'gemini' | 'ollama'>('openai');
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [authMode, setAuthMode] = useState<'none' | 'bearer'>('none');
  const [authToken, setAuthToken] = useState('');
  // Ollama model selection
  const [ollamaModels, setOllamaModels] = useState<any[]>([]);
  const [fetchingModels, setFetchingModels] = useState(false);
  const [modelFetchSource, setModelFetchSource] = useState<'server' | 'fallback' | null>(null);
  const [defaultChatModel, setDefaultChatModel] = useState('');
  const [defaultEmbeddingModel, setDefaultEmbeddingModel] = useState('');
  const chatModels = ollamaModels.filter((m: any) => m.model_type !== 'embedding');
  const embeddingModels = ollamaModels.filter((m: any) => m.model_type === 'embedding');
  const selectedEmbedDim = embeddingModels.find((m: any) => m.id === defaultEmbeddingModel)?.embedding_dim ?? null;


  // P4.1-E: Embedding model selection for KB creation
  const [kbEmbedModels, setKbEmbedModels] = useState<{ id: string; dim: number }[]>([]);
  const [selectedKbEmbedModel, setSelectedKbEmbedModel] = useState<string>('');

  const KNOWN_EMBED_MODELS_WIZ: Record<string, { id: string; dim: number }[]> = {
    openai:  [{ id: 'text-embedding-3-small', dim: 1536 }, { id: 'text-embedding-3-large', dim: 3072 }, { id: 'text-embedding-ada-002', dim: 1536 }],
    gemini:  [{ id: 'text-embedding-004', dim: 768 }],
    anthropic: [],
  };

  useEffect(() => {
    ai.getResolvedModel('embedding').then(async resolved => {
      const provider = resolved.provider?.toLowerCase() ?? '';
      const autoModel = resolved.model ?? '';

      if (provider === 'ollama') {
        try {
          const all = await ai.listModels('ollama');
          const list = all.filter((m: any) => m.model_type === 'embedding')
                         .map((m: any) => ({ id: m.id, dim: m.embedding_dim ?? 768 }));
          setKbEmbedModels(list.length ? list : [{ id: autoModel, dim: 768 }]);
        } catch {
          setKbEmbedModels([{ id: autoModel, dim: 768 }]);
        }
      } else {
        const knownList = KNOWN_EMBED_MODELS_WIZ[provider] ?? [{ id: autoModel, dim: 1536 }];
        setKbEmbedModels(knownList.length ? knownList : [{ id: autoModel, dim: 1536 }]);
      }
      setSelectedKbEmbedModel(autoModel);
    }).catch(() => {
      setKbEmbedModels([{ id: 'text-embedding-3-small', dim: 1536 }]);
      setSelectedKbEmbedModel('text-embedding-3-small');
    });
  }, [state.steps_done]);

  // Review State
  const [isProcessing, setIsProcessing] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    const idx = STEPS.findIndex(s => !state.steps_done.includes(s.id));
    setActiveStepIdx(idx === -1 ? STEPS.length - 1 : idx);
  }, [state.steps_done]);

  const next = (stepId: string) => {
    const nextSteps = [...new Set([...state.steps_done, stepId])];
    onUpdate({ steps_done: nextSteps });
    setError('');
  };

  const skip = (stepId: string) => {
    const nextSteps = [...new Set([...state.steps_done, stepId])];
    const nextSkipped = [...new Set([...state.steps_skipped, stepId])];
    onUpdate({ steps_done: nextSteps, steps_skipped: nextSkipped });
    setError('');
  };

  const handleCreateKb = async () => {
    if (!kbNameZh.trim() || !kbNameEn.trim()) {
      setError(t('onboarding.kb_name_zh') + ' & ' + t('onboarding.kb_name_en'));
      return;
    }
    setLoading(true);
    try {
      const ws = await workspaces.create({
        name_zh: kbNameZh.trim(),
        name_en: kbNameEn.trim(),
        visibility: kbVisibility,
        kb_type: 'evergreen',
        embedding_model: selectedKbEmbedModel || undefined,  // P4.1-E
        qa_archive_mode: qaArchiveMode,
      });
      onUpdate({ first_kb_id: ws.id, steps_done: [...new Set([...state.steps_done, 'kb'])] });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSkipKb = () => {
    onUpdate({ 
      steps_done: [...new Set([...state.steps_done, 'kb', 'ingest'])],
      steps_skipped: [...new Set([...state.steps_skipped, 'kb', 'ingest'])]
    });
  };

  const handleUpload = async (file?: File) => {
    if (!file || !state.first_kb_id) return;
    setLoading(true);
    setError('');
    try {
      await ingest.upload(state.first_kb_id, file);
      setIsProcessing(true);
      // Simulate processing time for AI
      setTimeout(() => {
        setIsProcessing(false);
        next('ingest');
      }, 3000);
    } catch (e: any) {
      setError(e.message);
      setLoading(false);
    }
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = () => {
    setIsDragging(false);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleUpload(file);
  };

  const fetchOllamaModelsOnboarding = async () => {
    if (!baseUrl) {
      setError(zh ? '請先輸入 Base URL' : 'Please enter Base URL first');
      return;
    }
    setFetchingModels(true);
    setModelFetchSource(null);
    setError('');
    try {
      const ms = await ai.listModelsProxy('ollama', { base_url: baseUrl, auth_mode: authMode, auth_token: authToken });
      setOllamaModels(ms);
      const knownFallbackIds = new Set(['llama3','mistral','mixtral','phi3','phi4','gemma2','qwen2.5','deepseek-r1','nomic-embed-text','mxbai-embed-large','all-minilm','bge-m3','llama3:8b','llama3:70b','llama3.2']);
      const chatFromServer = ms.filter((m: any) => m.model_type !== 'embedding');
      const looksLive = chatFromServer.some((m: any) => !knownFallbackIds.has(m.id));
      setModelFetchSource(looksLive ? 'server' : 'fallback');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setFetchingModels(false);
    }
  };

  const handleSaveAiKey = async () => {
    if (provider !== 'ollama' && apiKey.length < 10) {
      setError(t('onboarding.configure_ai'));
      return;
    }
    if (provider === 'ollama') {
      if (!baseUrl) { setError(zh ? '請輸入 Base URL' : 'Base URL required'); return; }
      if (!defaultChatModel) { setError(zh ? '請選擇預設對話模型' : 'Please select a default chat model'); return; }
      if (!defaultEmbeddingModel) { setError(zh ? '請選擇預設向量模型' : 'Please select a default embedding model'); return; }
    }
    setLoading(true);
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
      next('ai');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const renderWelcome = () => (
    <div className="onboard-card">
      <div className="onboard-icon"><Languages size={48} /></div>
      <h3 style={{ fontFamily: 'Outfit, sans-serif' }}>{t('onboarding.welcome_title')}</h3>
      <p>{t('onboarding.welcome_subtitle')}</p>
      <div className="flex-center mt-32">
        <select 
          className="mt-input"
          style={{ width: 200, textAlign: 'center' }}
          value={i18n.language}
          onChange={(e) => i18n.changeLanguage(e.target.value)}
        >
          <option value="zh-TW">繁體中文</option>
          <option value="en">English</option>
        </select>
      </div>

      {/* Concept Explanation */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginTop: 32, textAlign: "left" }}>
        <div style={{ background: "var(--bg-elevated)", padding: 16, borderRadius: 12, border: "1px solid var(--border-subtle)" }}>
          <div style={{ color: "var(--color-primary)", marginBottom: 8 }}><Database size={20} /></div>
          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{t('onboarding.concept_node_title')}</div>
          <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{t('onboarding.concept_node_desc')}</div>
        </div>
        <div style={{ background: "var(--bg-elevated)", padding: 16, borderRadius: 12, border: "1px solid var(--border-subtle)" }}>
          <div style={{ color: "var(--color-primary)", marginBottom: 8 }}><GitMerge size={20} /></div>
          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{t('onboarding.concept_edge_title')}</div>
          <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{t('onboarding.concept_edge_desc')}</div>
        </div>
        <div style={{ background: "var(--bg-elevated)", padding: 16, borderRadius: 12, border: "1px solid var(--border-subtle)" }}>
          <div style={{ color: "var(--color-primary)", marginBottom: 8 }}><CheckCircle2 size={20} /></div>
          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{t('onboarding.concept_trust_title')}</div>
          <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{t('onboarding.concept_trust_desc')}</div>
        </div>
      </div>
      <Button variant="primary" style={{ display: 'block', margin: '32px auto 0' }} onClick={() => next('welcome')} rightIcon={<ChevronRight size={16} />}>
        {zh ? '下一步' : 'Next Step'}
      </Button>
    </div>
  );

  const renderAccount = () => (
    <div className="onboard-card">
      <div className="onboard-icon-success"><CheckCircle2 size={48} /></div>
      <h3>{t('onboarding.account_ready')}</h3>
      <p>{t('onboarding.account_subtitle')}</p>
      <Button variant="primary" style={{ display: 'block', margin: '32px auto 0' }} onClick={() => next('account')} rightIcon={<ChevronRight size={16} />}>
        {t('onboarding.start_setup')}
      </Button>
    </div>
  );

  const renderEmail = () => (
    <div className="onboard-card">
      <div className="onboard-icon"><Mail size={48} /></div>
      <h3>{t('onboarding.verify_email')}</h3>
      <p>{t('onboarding.verify_subtitle')}</p>
      <div className="status-tag" style={{ background: user?.email_verified ? 'var(--color-success-subtle)' : 'var(--color-warning-subtle)', color: user?.email_verified ? 'var(--color-success)' : 'var(--color-warning)' }}>
        {user?.email_verified ? t('onboarding.verified') : t('onboarding.awaiting_verify')}
      </div>
      <div className="flex-center mt-32 gap-12">
        {!user?.email_verified && (
          <Button variant="secondary" onClick={() => auth.resendVerification()} leftIcon={<RefreshCw size={14} />}>
            {t('onboarding.resend')}
          </Button>
        )}
        <Button variant="primary" onClick={() => next('email')}>
          {user?.email_verified ? t('onboarding.next') : t('onboarding.verify_later')}
        </Button>
      </div>
    </div>
  );

  const renderKb = () => (
    <div className="onboard-card">
      <div className="onboard-icon"><Database size={48} /></div>
      <h3>{t('onboarding.create_kb')}</h3>
      <p>{t('onboarding.kb_subtitle')}</p>
      <div className="onboard-form mt-24">
        <Input 
          placeholder={t('onboarding.kb_name_zh')} 
          value={kbNameZh} onChange={e => setKbNameZh(e.target.value)}
        />
        <Input 
          placeholder={t('onboarding.kb_name_en')} 
          value={kbNameEn} onChange={e => setKbNameEn(e.target.value)}
        />
        
        {/* Visibility toggle */}
        <div style={{ textAlign: 'left' }}>
          <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 8 }}>
            {zh ? '可見度' : 'Visibility'}
          </label>
          <select
            className="mt-input"
            value={kbVisibility}
            onChange={e => setKbVisibility(e.target.value as any)}
            style={{ width: '100%' }}
          >
            <option value="private">{t('ws_settings.vis_private')}</option>
            <option value="restricted">{t('ws_settings.vis_restricted')}</option>
            <option value="conditional_public">{t('ws_settings.vis_conditional_public')}</option>
            <option value="public">{t('ws_settings.vis_public')}</option>
          </select>
          {kbVisibility === 'public' && (
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
              {zh ? '任何人均可瀏覽此知識庫。' : 'Anyone can browse this workspace.'}
            </div>
          )}
        </div>

        {/* P4.5-1A-5: QA Archive Mode */}
        <div style={{ textAlign: 'left' }}>
          <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 8 }}>
            {zh ? 'QA 存檔模式' : 'QA Archive Mode'}
          </label>
          <div style={{ display: 'flex', gap: 8 }}>
            <Button 
              variant={qaArchiveMode === 'manual_review' ? 'primary' : 'secondary'}
              size="sm"
              style={{ flex: 1, fontSize: 11 }}
              onClick={() => setQaArchiveMode('manual_review')}
            >
              {zh ? '手動審核 (預設)' : 'Manual Review'}
            </Button>
            <Button 
              variant={qaArchiveMode === 'auto_active' ? 'primary' : 'secondary'}
              size="sm"
              style={{ flex: 1, fontSize: 11 }}
              onClick={() => setQaArchiveMode('auto_active')}
            >
              {zh ? '自動存檔' : 'Auto Active'}
            </Button>
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
            {qaArchiveMode === 'manual_review' 
              ? (zh ? 'AI 提取的內容需經人工確認後才進入正式圖譜。' : 'AI-extracted content requires manual approval.')
              : (zh ? 'AI 提取的內容將直接生效（發生衝突時除外）。' : 'AI-extracted content goes live immediately (unless conflicted).')}
          </div>
        </div>

        {/* P4.1-E: Embedding model selector */}
        <div style={{ textAlign: 'left' }}>
          <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
            <Brain size={12} />
            {zh ? '向量模型（建立後鎖定）' : 'Embedding Model (locked after creation)'}
          </label>
          {kbEmbedModels.length > 1 ? (
            <select
              className="mt-input"
              value={selectedKbEmbedModel}
              onChange={e => setSelectedKbEmbedModel(e.target.value)}
              style={{ width: '100%' }}
            >
              {kbEmbedModels.map(m => (
                <option key={m.id} value={m.id}>{m.id} ({m.dim}d)</option>
              ))}
            </select>
          ) : (
            <div style={{ background: 'var(--bg-elevated)', padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border-subtle)', fontSize: 12 }}>
              {selectedKbEmbedModel
                ? `${selectedKbEmbedModel} (${kbEmbedModels[0]?.dim ?? '?'}d)`
                : (zh ? '載入中…' : 'Loading…')}
            </div>
          )}
        </div>
      </div>
      {error && <div className="error-text mt-12"><AlertCircle size={14}/> {error}</div>}
      <div className="flex-center mt-32 gap-12">
        <Button variant="ghost" onClick={handleSkipKb}>{t('onboarding.skip')}</Button>
        <Button variant="primary" onClick={handleCreateKb} loading={loading}>
          {t('onboarding.create_kb_btn')}
        </Button>
      </div>
    </div>
  );

  const renderIngest = () => (
    <div className="onboard-card">
      <div className="onboard-icon">{isProcessing ? <RefreshCw className="animate-spin" size={48} /> : <FileUp size={48} />}</div>
      <h3>{isProcessing ? t('onboarding.ingest_analyzing') : t('onboarding.ingest_title')}</h3>
      <p>
        {isProcessing 
          ? t('onboarding.ingest_analyzing_subtitle')
          : t('onboarding.ingest_subtitle')}
      </p>
      {!isProcessing && (
        <label 
          className={`onboard-upload mt-24 ${isDragging ? 'dragging' : ''}`}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
        >
          <input type="file" accept=".md,.txt" onChange={e => handleUpload(e.target.files?.[0])} hidden disabled={loading}/>
          <Upload size={32} />
          <span>
            {loading ? t('onboarding.upload_processing') : 
             isDragging ? t('onboarding.drop_to_ingest') :
             t('onboarding.click_to_upload')}
          </span>
        </label>
      )}
      {isProcessing && (
        <div className="mt-24">
           <div className="progress-bar-indet" />
        </div>
      )}
      <div className="flex-center mt-32 gap-12">
        {!isProcessing && <Button variant="ghost" onClick={() => skip('ingest')}>{t('onboarding.skip')}</Button>}
      </div>
    </div>
  );

  const renderAi = () => (
    <div className="onboard-card">
      <div className="onboard-icon"><Settings2 size={48} /></div>
      <h3>{t('onboarding.configure_ai')}</h3>
      <p>{t('onboarding.ai_subtitle')}</p>
      <div className="provider-selector mt-24">
        {(['openai', 'anthropic', 'gemini', 'ollama'] as const).map(p => (
          <Button 
            key={p}
            variant={provider === p ? 'primary' : 'secondary'}
            onClick={() => setProvider(p)}
          >
            {p.charAt(0).toUpperCase() + p.slice(1)}
          </Button>
        ))}
      </div>
      
      {provider === 'ollama' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 16 }}>
          {/* ── Connection ── */}
          <Input
            placeholder="Base URL (e.g. http://localhost:11434)"
            value={baseUrl} onChange={e => { setBaseUrl(e.target.value); setModelFetchSource(null); }}
          />
          <div style={{ display: 'flex', gap: 10 }}>
            <select className="mt-input" style={{ flex: 1 }} value={authMode} onChange={e => setAuthMode(e.target.value as any)}>
              <option value="none">{zh ? '無認證（本機）' : 'No Auth (local)'}</option>
              <option value="bearer">Bearer Token</option>
            </select>
            {authMode === 'bearer' && (
              <Input
                type="password" style={{ flex: 2 }}
                placeholder="Token"
                value={authToken} onChange={e => setAuthToken(e.target.value)}
              />
            )}
          </div>

          {/* ── Fetch models ── */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Button
              variant="secondary"
              onClick={fetchOllamaModelsOnboarding}
              loading={fetchingModels}
              disabled={!baseUrl}
              style={{ whiteSpace: 'nowrap' }}
            >
              {zh ? '取得模型列表' : 'Fetch Models'}
            </Button>
            {modelFetchSource === 'server' && (
              <span style={{ fontSize: 11, color: 'var(--color-success)' }}>
                ✓ {zh ? `${ollamaModels.length} 個模型` : `${ollamaModels.length} models from server`}
              </span>
            )}
            {modelFetchSource === 'fallback' && (
              <span style={{ fontSize: 11, color: 'var(--color-warning, #f59e0b)' }}>
                ⚠ {zh ? '顯示預設清單' : 'Showing default list'}
              </span>
            )}
          </div>

          {/* ── Chat model ── */}
          <div>
            <label style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>
              {zh ? '預設對話模型 *' : 'Default Chat Model *'}
            </label>
            <select
              className="mt-input"
              value={defaultChatModel}
              onChange={e => setDefaultChatModel(e.target.value)}
              disabled={ollamaModels.length === 0}
            >
              <option value="">{ollamaModels.length === 0 ? (zh ? '請先取得模型列表' : 'Fetch models first') : (zh ? '-- 選擇對話模型 --' : '-- Select chat model --')}</option>
              {chatModels.map((m: any) => <option key={m.id} value={m.id}>{m.display_name}</option>)}
            </select>
          </div>

          {/* ── Embedding model ── */}
          <div>
            <label style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>
              {zh ? '預設向量模型 *' : 'Default Embedding Model *'}
            </label>
            <select
              className="mt-input"
              value={defaultEmbeddingModel}
              onChange={e => setDefaultEmbeddingModel(e.target.value)}
              disabled={ollamaModels.length === 0}
            >
              <option value="">{ollamaModels.length === 0 ? (zh ? '請先取得模型列表' : 'Fetch models first') : (zh ? '-- 選擇向量模型 --' : '-- Select embedding model --')}</option>
              {embeddingModels.map((m: any) => (
                <option key={m.id} value={m.id}>
                  {/* needs_install models already include "(需安裝)" in display_name from backend */}
                  {m.needs_install
                    ? m.display_name
                    : `${m.display_name}${m.embedding_dim ? ` (${m.embedding_dim}d)` : ''}`}
                </option>
              ))}
            </select>
            {selectedEmbedDim ? (
              <div style={{ fontSize: 11, color: 'var(--color-error)', marginTop: 4, fontWeight: 500 }}>
                ⚠ {zh ? `向量維度 ${selectedEmbedDim}d — 工作區建立後鎖定，無法更改` : `Embedding dim ${selectedEmbedDim}d — locked after workspace creation`}
              </div>
            ) : (
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                {zh ? '取得模型列表後可自動顯示向量維度' : 'Embedding dim will be shown after fetching models'}
              </div>
            )}
          </div>
        </div>
      ) : (
        <Input 
          type="password" 
          placeholder={provider === 'openai' ? 'sk-...' : provider === 'anthropic' ? 'sk-ant-...' : 'AIza...'}
          value={apiKey} onChange={e => setApiKey(e.target.value)}
        />
      )}
      {error && <div className="error-text mt-12"><AlertCircle size={14}/> {error}</div>}
      <div className="flex-center mt-32 gap-12">
        <Button variant="ghost" onClick={() => skip('ai')}>{t('onboarding.skip')}</Button>
        <Button variant="primary" onClick={handleSaveAiKey} loading={loading}>
          {t('onboarding.save_finish')}
        </Button>
      </div>
    </div>
  );


  const renderSecurity = () => {
    const [pwd, setPwd] = useState('');
    const [confirmPwd, setConfirmPwd] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [pwdError, setPwdError] = useState('');

    const handleSetPassword = async () => {
      if (pwd.length < 8) {
        setPwdError(zh ? '密碼長度需至少 8 個字元' : 'Password must be at least 8 characters');
        return;
      }
      if (pwd !== confirmPwd) {
        setPwdError(zh ? '兩次輸入的密碼不一致' : 'Passwords do not match');
        return;
      }
      setSubmitting(true);
      setPwdError('');
      try {
        await auth.updatePassword(pwd);
        next('security');
      } catch (e: any) {
        setPwdError(e.message);
      } finally {
        setSubmitting(false);
      }
    };

    return (
      <div className="onboard-card">
        <div className="onboard-icon"><Key size={48} /></div>
        <h3>{zh ? '設定登入密碼' : 'Set Login Password'}</h3>
        <p>{zh ? '為了方便下次直接登入，請設定您的密碼。設定後您可以使用 Email + 密碼 登入。' : 'To log in directly next time, please set a password. After this, you can sign in using Email + Password.'}</p>
        <div className="onboard-form mt-24">
          <Input 
            type="password" 
            placeholder={zh ? '新密碼 (至少 8 字元)' : 'New password (min 8 chars)'} 
            value={pwd} onChange={e => setPwd(e.target.value)} 
          />
          <Input 
            type="password" 
            placeholder={zh ? '確認密碼' : 'Confirm password'} 
            value={confirmPwd} onChange={e => setConfirmPwd(e.target.value)} 
          />
          {pwdError && <div className="error-text" style={{ fontSize: 12 }}><AlertCircle size={12}/> {pwdError}</div>}
        </div>
        <div className="flex-center mt-32 gap-12">
          <Button variant="ghost" onClick={() => skip('security')}>{zh ? '稍後設定' : 'Skip for now'}</Button>
          <Button variant="primary" onClick={handleSetPassword} loading={submitting}>
            {zh ? '設定密碼並繼續' : 'Set Password & Continue'}
          </Button>
        </div>
      </div>
    );
  };

  const renderDone = () => (
    <div className="onboard-card">
      <div className="onboard-icon-warn"><PartyPopper size={48} /></div>
      <h3>{t('onboarding.ready_title')}</h3>
      <p>{t('onboarding.ready_subtitle')}</p>

      {/* Example KB hint */}
      <div style={{
        marginTop: 28, padding: '14px 18px', borderRadius: 12,
        background: 'var(--color-primary-subtle)', border: '1px solid var(--color-primary)',
        textAlign: 'left', display: 'flex', alignItems: 'flex-start', gap: 12,
      }}>
        <Database size={20} style={{ color: 'var(--color-primary)', flexShrink: 0, marginTop: 2 }} />
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--color-primary)', marginBottom: 4 }}>
            {t('onboarding.spec_kb_title')}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            {t('onboarding.spec_kb_desc')}
          </div>
          {onOpenSpecKb && (
            <button
              style={{
                marginTop: 10, padding: '5px 14px', borderRadius: 8,
                background: 'var(--color-primary)', color: 'var(--text-on-primary)',
                border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 600,
              }}
              onClick={() => { onComplete(); onOpenSpecKb(); }}
            >
              {t('onboarding.open_spec_kb')} →
            </button>
          )}
        </div>
      </div>

      {/* API Key Guidance */}
      <div style={{
        marginTop: 16, padding: '14px 18px', borderRadius: 12,
        background: 'var(--bg-elevated)', border: '1px solid var(--border-default)',
        textAlign: 'left', display: 'flex', alignItems: 'flex-start', gap: 12,
      }}>
        <Key size={20} style={{ color: 'var(--color-primary)', flexShrink: 0, marginTop: 2 }} />
        <div>
          <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>
            {t('onboarding.api_key_guide_title')}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            {t('onboarding.api_key_guide_desc')}
          </div>
        </div>
      </div>

      <Button variant="primary" style={{ display: 'block', margin: '24px auto 0' }} onClick={onComplete}>
        {t('onboarding.enter_app')}
      </Button>
    </div>
  );

  return (
    <div className="onboarding-overlay">
      <progress className="onboarding-progress" value={activeStepIdx + 1} max={STEPS.length} />
      
      <div className="onboarding-content">
        <div className="onboarding-steps">
          {STEPS.map((s, i) => (
            <div key={s.id} className={`onboarding-step-dot ${i <= activeStepIdx ? 'done' : ''} ${i === activeStepIdx ? 'active' : ''}`}>
               <s.icon size={14} />
            </div>
          ))}
        </div>

        <div className="onboarding-view">
          {activeStepIdx === 0 && renderWelcome()}
          {activeStepIdx === 1 && renderAccount()}
          {activeStepIdx === 2 && renderSecurity()}
          {activeStepIdx === 3 && renderEmail()}
          {activeStepIdx === 4 && renderKb()}
          {activeStepIdx === 5 && renderIngest()}
          {activeStepIdx === 6 && renderAi()}
          {activeStepIdx === 7 && renderDone()}
        </div>
      </div>

      <style>{`
        .onboarding-overlay {
          position: fixed; inset: 0; z-index: 2000;
          background: var(--bg-base);
          display: flex; flex-direction: column;
          align-items: center; justify-content: center;
          animation: fadeIn 0.4s ease-out;
        }
        .onboarding-progress {
          position: fixed; top: 0; left: 0; width: 100%; height: 4px;
          appearance: none; border: none; background: transparent;
        }
        .onboarding-progress::-webkit-progress-bar { background: transparent; }
        .onboarding-progress::-webkit-progress-value { background: var(--color-primary); transition: width 0.3s; }
        
        .onboarding-content {
          max-width: 600px; width: 90%;
          display: flex; flex-direction: column; align-items: center;
          gap: 40px;
        }
        .onboarding-steps {
          display: flex; gap: 12px;
        }
        .onboarding-step-dot {
          width: 32px; height: 32px; border-radius: 16px;
          display: flex; align-items: center; justify-content: center;
          background: var(--bg-surface); border: 1px solid var(--border-default);
          color: var(--text-muted); transition: all 0.3s;
        }
        .onboarding-step-dot.done { background: var(--color-primary-subtle); color: var(--color-primary); border-color: var(--color-primary); }
        .onboarding-step-dot.active { background: var(--color-primary); color: white; transform: scale(1.15); box-shadow: var(--shadow-md); }

        .onboard-card {
          background: var(--bg-surface); border: 1px solid var(--border-default);
          padding: 48px; border-radius: 24px; text-align: center;
          box-shadow: var(--shadow-xl);
          animation: slideUp 0.5s ease-out;
        }
        .onboard-card h3 { font-size: 24px; margin-bottom: 12px; }
        .onboard-card p { color: var(--text-muted); line-height: 1.6; max-width: 380px; margin: 0 auto; }
        
        .onboard-icon { color: var(--color-primary); margin-bottom: 24px; }
        .onboard-icon-success { color: var(--color-success); margin-bottom: 24px; }
        .onboard-icon-warn { color: var(--color-warning); margin-bottom: 24px; }

        .onboard-form { display: flex; flex-direction: column; gap: 12px; }
        .status-tag { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-top: 16px; }
        
        .onboard-upload {
          border: 2px dashed var(--border-default); border-radius: 16px; padding: 40px;
          display: flex; flex-direction: column; align-items: center; gap: 16px;
          cursor: pointer; transition: all 0.2s; color: var(--text-muted);
        }
        .onboard-upload:hover { border-color: var(--color-primary); background: var(--color-primary-subtle); color: var(--color-primary); }
        .onboard-upload.dragging { border-color: var(--color-primary); background: var(--color-primary-subtle); color: var(--color-primary); transform: scale(1.02); }
        
        .provider-selector { display: flex; gap: 8px; justify-content: center; }
        .provider-selector button {
          padding: 8px 16px; border-radius: 8px; border: 1px solid var(--border-default);
          background: transparent; color: var(--text-muted); cursor: pointer; transition: all 0.2s;
        }
        .provider-selector button.active { background: var(--color-primary); color: var(--text-on-primary); border-color: var(--color-primary); }
        
        .error-text { color: var(--color-error); font-size: 13px; display: flex; alignItems: center; gap: 6px; justify-content: center; }
        

        .mt-32 { margin-top: 32px; }
        .mt-24 { margin-top: 24px; }
        .mt-16 { margin-top: 16px; }
        .flex-center { display: flex; align-items: center; justify-content: center; }
        .gap-12 { gap: 12px; }
        
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        .progress-bar-indet {
          width: 200px; height: 4px; background: var(--border-default); border-radius: 2px; position: relative; overflow: hidden;
        }
        .progress-bar-indet::after {
          content: ""; position: absolute; left: -50%; width: 50%; height: 100%; background: var(--color-primary);
          animation: slideIndet 1.5s infinite linear;
        }
        @keyframes slideIndet {
          from { left: -50%; }
          to { left: 100%; }
        }
        .mb-24 { margin-bottom: 24px; }
      `}</style>
    </div>
  );
}
