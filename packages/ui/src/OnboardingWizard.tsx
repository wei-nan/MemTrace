import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  CheckCircle2, Mail, Database, FileUp, 
  Settings2, Eye, PartyPopper, ChevronRight 
} from 'lucide-react';
import { auth, type Onboarding } from './api';

const STEPS = [
  { id: 'account', icon: CheckCircle2 },
  { id: 'email', icon: Mail },
  { id: 'kb', icon: Database },
  { id: 'ingest', icon: FileUp },
  { id: 'ai', icon: Settings2 },
  { id: 'review', icon: Eye },
  { id: 'done', icon: PartyPopper },
];

export default function OnboardingWizard({ 
  state, 
  onUpdate,
  onComplete 
}: { 
  state: Onboarding, 
  onUpdate: (data: Partial<Onboarding>) => void,
  onComplete: () => void 
}) {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  
  // Current step calculation based on steps_done
  const [activeStepIdx, setActiveStepIdx] = useState(0);

  useEffect(() => {
    // Basic logic: first step not in steps_done is active
    const idx = STEPS.findIndex(s => !state.steps_done.includes(s.id));
    setActiveStepIdx(idx === -1 ? STEPS.length - 1 : idx);
  }, [state.steps_done]);

  const next = (stepId: string) => {
    const nextSteps = [...new Set([...state.steps_done, stepId])];
    onUpdate({ steps_done: nextSteps });
  };

  const renderAccount = () => (
    <div style={{ textAlign: 'center' }}>
      <CheckCircle2 size={48} color="#4ade80" style={{ marginBottom: 16 }} />
      <h3>{zh ? '帳號已建立' : 'Account Created'}</h3>
      <p style={{ color: 'var(--text-muted)' }}>{zh ? '歡迎來到 MemTrace！您已經成功踏出第一步。' : 'Welcome to MemTrace! You have successfully taken the first step.'}</p>
      <button className="btn-primary" style={{ marginTop: 24 }} onClick={() => next('account')}>
        {zh ? '繼續' : 'Continue'} <ChevronRight size={16} />
      </button>
    </div>
  );

  const renderEmail = () => (
    <div style={{ textAlign: 'center' }}>
      <Mail size={48} color="var(--accent-color)" style={{ marginBottom: 16 }} />
      <h3>{zh ? '驗證信箱' : 'Verify Email'}</h3>
      <p style={{ color: 'var(--text-muted)' }}>{zh ? '我們已發送驗證連結至您的信箱，請查看。' : 'We sent a verification link to your email, please check.'}</p>
      <button className="btn-secondary" style={{ marginTop: 12 }} onClick={() => auth.resendVerification()}>
        {zh ? '重新發送' : 'Resend Email'}
      </button>
      <div style={{ marginTop: 24 }}>
         <button className="btn-primary" onClick={() => next('email')}>
           {zh ? '我已驗證 / 稍後再說' : 'I verified / Skip for now'}
         </button>
      </div>
    </div>
  );

  const renderKb = () => (
    <div style={{ textAlign: 'center' }}>
      <Database size={48} color="var(--accent-color)" style={{ marginBottom: 16 }} />
      <h3>{zh ? '建立第一個知識庫' : 'Create First KB'}</h3>
      <p style={{ color: 'var(--text-muted)' }}>{zh ? '知識庫是您的記憶容器。' : 'A knowledge base is a container for your memories.'}</p>
      <button className="btn-primary" style={{ marginTop: 24 }} onClick={() => next('kb')}>
        {zh ? '進入下一步' : 'Next Step'}
      </button>
    </div>
  );

  const renderIngest = () => (
    <div style={{ textAlign: 'center' }}>
      <FileUp size={48} color="var(--accent-color)" style={{ marginBottom: 16 }} />
      <h3>{zh ? '匯入資料' : 'Ingest Data'}</h3>
      <p style={{ color: 'var(--text-muted)' }}>{zh ? '您可以上傳文件讓 AI 自動為您建立知識節點。' : 'You can upload documents to let AI build knowledge nodes for you.'}</p>
      <button className="btn-primary" style={{ marginTop: 24 }} onClick={() => next('ingest')}>
        {zh ? '進入下一步' : 'Next Step'}
      </button>
    </div>
  );

  const renderAi = () => (
    <div style={{ textAlign: 'center' }}>
      <Settings2 size={48} color="var(--accent-color)" style={{ marginBottom: 16 }} />
      <h3>{zh ? 'AI 設定' : 'AI Settings'}</h3>
      <p style={{ color: 'var(--text-muted)' }}>{zh ? '若您有自己的 OpenAI/Claude Key，可以在此設定。' : 'Provide your own OpenAI/Claude key if you have one.'}</p>
      <button className="btn-primary" style={{ marginTop: 24 }} onClick={() => next('ai')}>
        {zh ? '進入下一步' : 'Next Step'}
      </button>
    </div>
  );

  const renderReview = () => (
    <div style={{ textAlign: 'center' }}>
      <Eye size={48} color="var(--accent-color)" style={{ marginBottom: 16 }} />
      <h3>{zh ? '審核 AI 擷取內容' : 'Review AI Extractions'}</h3>
      <p style={{ color: 'var(--text-muted)' }}>{zh ? '所有 AI 產生的內容都會進入審核佇列，確保品質。' : 'Everything AI generates goes to the review queue to ensure quality.'}</p>
      <button className="btn-primary" style={{ marginTop: 24 }} onClick={() => next('review')}>
        {zh ? '進入下一步' : 'Next Step'}
      </button>
    </div>
  );

  const renderDone = () => (
    <div style={{ textAlign: 'center' }}>
      <PartyPopper size={48} color="#facc15" style={{ marginBottom: 16 }} />
      <h3>{zh ? '大功告成！' : 'All Set!'}</h3>
      <p style={{ color: 'var(--text-muted)' }}>{zh ? '您已準備好開始構建您的數位大腦。' : 'You are ready to start building your digital brain.'}</p>
      <button className="btn-primary" style={{ marginTop: 24 }} onClick={onComplete}>
        {zh ? '開始使用 MemTrace' : 'Start using MemTrace'}
      </button>
    </div>
  );

  return (
    <div className="onboarding-overlay" style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'var(--bg-primary)', display: 'flex', flexDirection: 'column'
    }}>
      {/* Progress Header */}
      <div style={{ padding: '32px 64px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'center' }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', maxWidth: 800, width: '100%' }}>
          {STEPS.map((step, i) => {
             const Icon = step.icon;
             const isDone = state.steps_done.includes(step.id);
             const isActive = i === activeStepIdx;
             return (
               <div key={step.id} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                 <div style={{
                   width: 32, height: 32, borderRadius: 16, display: 'flex', alignItems: 'center', justifyContent: 'center',
                   background: isDone ? '#4ade80' : isActive ? 'var(--accent-color)' : 'var(--bg-secondary)',
                   color: isDone || isActive ? '#fff' : 'var(--text-muted)',
                   transition: 'all 0.3s'
                 }}>
                   <Icon size={16} />
                 </div>
                 {i < STEPS.length - 1 && (
                   <div style={{ position: 'absolute', height: 2, background: 'var(--border-color)', width: '100%' }} />
                 )}
               </div>
             )
          })}
        </div>
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 32 }}>
        <div style={{ maxWidth: 480, width: '100%', animation: 'fadeInUp 0.5s ease-out' }}>
           {activeStepIdx === 0 && renderAccount()}
           {activeStepIdx === 1 && renderEmail()}
           {activeStepIdx === 2 && renderKb()}
           {activeStepIdx === 3 && renderIngest()}
           {activeStepIdx === 4 && renderAi()}
           {activeStepIdx === 5 && renderReview()}
           {activeStepIdx === 6 && renderDone()}
        </div>
      </div>
    </div>
  );
}
