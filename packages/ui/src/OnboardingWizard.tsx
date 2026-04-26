import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  CheckCircle2, Mail, Database, FileUp, 
  Settings2, PartyPopper, ChevronRight,
  Upload, Loader2, AlertCircle, RefreshCw,
  Languages, GitMerge, Key
} from 'lucide-react';
import { auth, workspaces, ai, ingest, type Onboarding } from './api';

const STEPS = [
  { id: 'welcome', icon: Languages },
  { id: 'account', icon: CheckCircle2 },
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
  onComplete 
}: { 
  user: any,
  state: Onboarding, 
  onUpdate: (data: Partial<Onboarding>) => void,
  onComplete: () => void 
}) {
  const { t, i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  
  const [activeStepIdx, setActiveStepIdx] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // KB State
  const [kbNameZh, setKbNameZh] = useState('');
  const [kbNameEn, setKbNameEn] = useState('');
  
  // AI State
  const [provider, setProvider] = useState<'openai' | 'anthropic' | 'gemini'>('openai');
  const [apiKey, setApiKey] = useState('');

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
        visibility: 'private',
        kb_type: 'evergreen'
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

  const handleSaveAiKey = async () => {
    if (apiKey.length < 10) {
      setError(t('onboarding.configure_ai'));
      return;
    }
    setLoading(true);
    try {
      await ai.createKey({ provider, api_key: apiKey });
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
      <div className="flex-center mt-32 gap-12">
        <button 
          className={`btn-secondary ${i18n.language === 'en' ? 'active' : ''}`} 
          onClick={() => i18n.changeLanguage('en')}
          style={i18n.language === 'en' ? { borderColor: 'var(--color-primary)', background: 'var(--color-primary-subtle)', color: 'var(--color-primary)' } : {}}
        >
          English
        </button>
        <button 
          className={`btn-secondary ${i18n.language === 'zh-TW' ? 'active' : ''}`} 
          onClick={() => i18n.changeLanguage('zh-TW')}
          style={i18n.language === 'zh-TW' ? { borderColor: 'var(--color-primary)', background: 'var(--color-primary-subtle)', color: 'var(--color-primary)' } : {}}
        >
          繁體中文
        </button>
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
      <button className="btn-primary mt-32" style={{ display: 'block', margin: '32px auto 0' }} onClick={() => next('welcome')}>
        {zh ? '下一步' : 'Next Step'} <ChevronRight size={16} />
      </button>
    </div>
  );

  const renderAccount = () => (
    <div className="onboard-card">
      <div className="onboard-icon-success"><CheckCircle2 size={48} /></div>
      <h3>{t('onboarding.account_ready')}</h3>
      <p>{t('onboarding.account_subtitle')}</p>
      <button className="btn-primary mt-32" style={{ display: 'block', margin: '32px auto 0' }} onClick={() => next('account')}>
        {t('onboarding.start_setup')} <ChevronRight size={16} />
      </button>
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
          <button className="btn-secondary" onClick={() => auth.resendVerification()}>
            <RefreshCw size={14} /> {t('onboarding.resend')}
          </button>
        )}
        <button className="btn-primary" onClick={() => next('email')}>
          {user?.email_verified ? t('onboarding.next') : t('onboarding.verify_later')}
        </button>
      </div>
    </div>
  );

  const renderKb = () => (
    <div className="onboard-card">
      <div className="onboard-icon"><Database size={48} /></div>
      <h3>{t('onboarding.create_kb')}</h3>
      <p>{t('onboarding.kb_subtitle')}</p>
      <div className="onboard-form mt-24">
        <input 
          className="mt-input" 
          placeholder={t('onboarding.kb_name_zh')} 
          value={kbNameZh} onChange={e => setKbNameZh(e.target.value)}
        />
        <input 
          className="mt-input" 
          placeholder={t('onboarding.kb_name_en')} 
          value={kbNameEn} onChange={e => setKbNameEn(e.target.value)}
        />
      </div>
      {error && <div className="error-text mt-12"><AlertCircle size={14}/> {error}</div>}
      <div className="flex-center mt-32 gap-12">
        <button className="btn-ghost" onClick={handleSkipKb}>{t('onboarding.skip')}</button>
        <button className="btn-primary" onClick={handleCreateKb} disabled={loading}>
          {loading ? <Loader2 className="animate-spin" /> : t('onboarding.create_kb_btn')}
        </button>
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
        {!isProcessing && <button className="btn-ghost" onClick={() => skip('ingest')}>{t('onboarding.skip')}</button>}
      </div>
    </div>
  );

  const renderAi = () => (
    <div className="onboard-card">
      <div className="onboard-icon"><Settings2 size={48} /></div>
      <h3>{t('onboarding.configure_ai')}</h3>
      <p>{t('onboarding.ai_subtitle')}</p>
      <div className="provider-selector mt-24">
        <button 
          className={provider === 'openai' ? 'active' : ''} 
          onClick={() => setProvider('openai')}
          style={provider === 'openai' ? { background: 'var(--ai-openai-subtle)', color: 'var(--ai-openai)', borderColor: 'var(--ai-openai)' } : {}}
        >
          OpenAI
        </button>
        <button 
          className={provider === 'anthropic' ? 'active' : ''} 
          onClick={() => setProvider('anthropic')}
          style={provider === 'anthropic' ? { background: 'var(--ai-anthropic-subtle)', color: 'var(--ai-anthropic)', borderColor: 'var(--ai-anthropic)' } : {}}
        >
          Anthropic
        </button>
        <button 
          className={provider === 'gemini' ? 'active' : ''} 
          onClick={() => setProvider('gemini')}
          style={provider === 'gemini' ? { background: 'var(--ai-gemini-subtle)', color: 'var(--ai-gemini)', borderColor: 'var(--ai-gemini)' } : {}}
        >
          Gemini
        </button>
      </div>
      <input 
        type="password" className="mt-input mt-16" 
        placeholder={provider === 'openai' ? 'sk-...' : provider === 'anthropic' ? 'sk-ant-...' : 'AIza...'}
        value={apiKey} onChange={e => setApiKey(e.target.value)}
      />
      {error && <div className="error-text mt-12"><AlertCircle size={14}/> {error}</div>}
      <div className="flex-center mt-32 gap-12">
        <button className="btn-ghost" onClick={() => skip('ai')}>{t('onboarding.skip')}</button>
        <button className="btn-primary" onClick={handleSaveAiKey} disabled={loading}>
          {loading ? <Loader2 className="animate-spin" /> : t('onboarding.save_finish')}
        </button>
      </div>
    </div>
  );


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
        <div>
          <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--color-primary)', marginBottom: 4 }}>
            {t('onboarding.spec_kb_title')}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            {t('onboarding.spec_kb_desc')}
          </div>
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

      <button className="btn-primary mt-32" style={{ display: 'block', margin: '24px auto 0' }} onClick={onComplete}>
        {t('onboarding.enter_app')}
      </button>
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
          {activeStepIdx === 2 && renderEmail()}
          {activeStepIdx === 3 && renderKb()}
          {activeStepIdx === 4 && renderIngest()}
          {activeStepIdx === 5 && renderAi()}
          {activeStepIdx === 6 && renderDone()}
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
        .provider-selector button.active { background: var(--color-primary); color: white; border-color: var(--color-primary); }
        
        .error-text { color: var(--color-error); font-size: 13px; display: flex; alignItems: center; gap: 6px; justify-content: center; }
        
        .btn-ghost {
          background: transparent; border: none;
          color: var(--text-muted); cursor: pointer;
          padding: 8px 16px; border-radius: 8px;
          transition: all 0.2s; font-size: 14px;
        }
        .btn-ghost:hover { background: var(--bg-elevated); color: var(--text-primary); }

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
