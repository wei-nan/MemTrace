import { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, User, Brain, ExternalLink, PlusCircle, Settings2, AlertCircle } from 'lucide-react';
import { ai, type ChatResponse, type ProposedChange, type ModelInfo, type CreditStatus } from '../api';
import ReactMarkdown from 'react-markdown';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  response?: ChatResponse;
}

export default function AiChatPanel({ wsId, zh }: { wsId: string; zh: boolean }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [provider, setProvider] = useState<'openai' | 'anthropic' | 'gemini'>('openai' as any);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [credits, setCredits] = useState<CreditStatus | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchCredits = async () => {
      try {
        const c = await ai.getCredits();
        setCredits(c);
        
        // Auto-switch provider if current one has no key
        if (c && !c.has_own_key[provider]) {
           const firstAvailable = (Object.keys(c.has_own_key) as Array<keyof typeof c.has_own_key>)
             .find(k => c.has_own_key[k]);
           if (firstAvailable) setProvider(firstAvailable);
        }
      } catch (e) {
        console.error("Failed to fetch credits", e);
      }
    };
    fetchCredits();
  }, [provider]);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const list = await ai.listModels(provider);
        setModels(list);
        if (list.length > 0) setSelectedModel(list[0].id);
      } catch (e) {
        console.error("Failed to fetch models", e);
      }
    };
    fetchModels();
  }, [provider]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const history = messages.map(m => ({ role: m.role, content: m.content }));
      const res = await ai.chat({ 
        workspace_id: wsId, 
        message: input, 
        history,
        preferred_provider: provider,
        preferred_model: selectedModel
      });
      
      const assistantMsg: Message = { 
        role: 'assistant', 
        content: res.answer,
        response: res
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (e: any) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${e.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg-surface)' }}>
      {/* Header */}
      <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--border-default)', display: 'flex', alignItems: 'center', gap: 10 }}>
        <Sparkles size={18} style={{ color: 'var(--color-primary)' }} />
        <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>
          {zh ? 'AI 助手' : 'AI Assistant'}
        </h3>
      </div>

      {/* Selector Bar */}
      <div style={{ 
        padding: '6px 16px', background: 'var(--bg-app)', borderBottom: '1px solid var(--border-default)', 
        display: 'flex', gap: 8, overflowX: 'auto', alignItems: 'center'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
          <Settings2 size={14} style={{ opacity: 0.6 }} />
          <select 
            value={provider} 
            onChange={e => setProvider(e.target.value as any)}
            style={{ fontSize: 11, padding: '2px 4px', borderRadius: 4, border: '1px solid var(--border-subtle)', background: 'var(--bg-surface)', fontWeight: 600 }}
          >
            <option value="openai" disabled={credits ? !credits.has_own_key.openai : false}>
              OpenAI {credits && !credits.has_own_key.openai ? (zh ? '(未設定)' : '(No Key)') : ''}
            </option>
            <option value="anthropic" disabled={credits ? !credits.has_own_key.anthropic : false}>
              Anthropic {credits && !credits.has_own_key.anthropic ? (zh ? '(未設定)' : '(No Key)') : ''}
            </option>
            <option value="gemini" disabled={credits ? !credits.has_own_key.gemini : false}>
              Gemini {credits && !credits.has_own_key.gemini ? (zh ? '(未設定)' : '(No Key)') : ''}
            </option>
          </select>
        </div>
        <div style={{ width: 1, height: 16, background: 'var(--border-default)' }} />
        <select 
          value={selectedModel} 
          onChange={e => setSelectedModel(e.target.value)}
          style={{ fontSize: 11, padding: '2px 4px', borderRadius: 4, border: '1px solid var(--border-subtle)', background: 'var(--bg-surface)', flex: 1, minWidth: 100 }}
        >
          {models.map(m => (
            <option key={m.id} value={m.id}>{m.display_name}</option>
          ))}
          {models.length === 0 && <option value="">Loading...</option>}
        </select>
      </div>

      {/* Messages List */}
      <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: 24 }}>
        {messages.length === 0 && (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>
            <Brain size={48} style={{ opacity: 0.2, marginBottom: 16 }} />
            <p style={{ fontSize: 14 }}>
              {zh ? '您可以詢問關於當前知識庫的問題，或請求 AI 協助優化圖譜結構。' : 'Ask questions about your KB or request structure optimizations.'}
            </p>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} style={{ display: 'flex', gap: 12, flexDirection: m.role === 'user' ? 'row-reverse' : 'row' }}>
            <div style={{ 
              width: 32, height: 32, borderRadius: 16, flexShrink: 0,
              background: m.role === 'user' ? 'var(--border-default)' : 'var(--color-primary-subtle)',
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              {m.role === 'user' ? <User size={16} /> : <Sparkles size={16} style={{ color: 'var(--color-primary)' }} />}
            </div>
            <div style={{ maxWidth: '85%' }}>
              <div style={{ 
                padding: '12px 16px', borderRadius: 16, fontSize: 14, lineHeight: 1.5,
                background: m.role === 'user' ? 'var(--color-primary)' : 'var(--bg-app)',
                color: m.role === 'user' ? 'white' : 'var(--text-default)',
                border: m.role === 'assistant' ? '1px solid var(--border-subtle)' : 'none'
              }}>
                <ReactMarkdown>{m.content}</ReactMarkdown>
                
                {/* Proposals */}
                {m.response?.proposals && m.response.proposals.length > 0 && (
                   <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
                      <div style={{ fontSize: 12, fontWeight: 600, opacity: 0.8, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <PlusCircle size={14} /> {zh ? 'AI 提案' : 'AI Proposals'}
                      </div>
                      {m.response.proposals.map((p, j) => (
                        <ProposalCard key={j} proposal={p} zh={zh} />
                      ))}
                   </div>
                )}
              </div>
              
              {/* Source Nodes */}
              {m.response?.source_nodes && m.response.source_nodes.length > 0 && (
                <div style={{ marginTop: 8, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {m.response.source_nodes.slice(0, 3).map((sn, j) => (
                    <div key={j} style={{ fontSize: 11, padding: '2px 8px', background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: 4, color: 'var(--text-muted)' }}>
                      {zh ? sn.title_zh : sn.title_en}
                    </div>
                  ))}
                  {m.response.source_nodes.length > 3 && (
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>+{m.response.source_nodes.length - 3} more</div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ display: 'flex', gap: 12 }}>
            <div style={{ width: 32, height: 32, borderRadius: 16, background: 'var(--color-primary-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <LoaderIcon />
            </div>
            <div style={{ padding: '12px 16px', borderRadius: 16, background: 'var(--bg-app)', border: '1px solid var(--border-subtle)', fontSize: 14 }}>
               <span className="animate-pulse">...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div style={{ padding: '16px 20px', borderTop: '1px solid var(--border-default)', background: 'var(--bg-surface)' }}>
        {credits && !credits.has_own_key[provider] && (
          <div style={{ 
            marginBottom: 12, padding: '12px', borderRadius: 8, 
            background: '#fee2e2', border: '1px solid #ef4444',
            fontSize: 12, color: '#b91c1c', display: 'flex', alignItems: 'center', gap: 8
          }}>
            <AlertCircle size={14} />
            <b>
              {zh 
                ? `您尚未設定 ${provider.toUpperCase()} 的 API Key。` 
                : `No API key configured for ${provider.toUpperCase()}.`}
            </b>
            <button 
              onClick={() => alert("Navigate to Settings to add key")}
              style={{ marginLeft: 'auto', fontWeight: 700, background: 'none', border: 'none', color: '#b91c1c', cursor: 'pointer', textDecoration: 'underline' }}
            >
              {zh ? '去設定' : 'Add Key'}
            </button>
          </div>
        )}

        <div style={{ display: 'flex', gap: 10, background: 'var(--bg-app)', padding: '8px 12px', borderRadius: 24, border: '1px solid var(--border-default)' }}>
          <input 
            style={{ flex: 1, background: 'none', border: 'none', outline: 'none', color: 'var(--text-default)', fontSize: 14, paddingLeft: 8 }}
            placeholder={zh ? '輸入訊息...' : 'Type a message...'}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && input.trim() && !loading) {
                const canSend = !credits || credits.has_own_key[provider];
                if (canSend) handleSend();
              }
            }}
          />
          <button 
            onClick={handleSend}
            disabled={!input.trim() || loading || (credits ? !credits.has_own_key[provider] : false)}
            style={{ 
              width: 32, height: 32, borderRadius: 16, border: 'none',
              background: (input.trim() && !loading && (!credits || credits.has_own_key[provider])) ? 'var(--color-primary)' : 'var(--border-default)',
              color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer'
            }}
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

function ProposalCard({ proposal, zh }: { proposal: ProposedChange; zh: boolean }) {
  return (
    <div style={{ background: 'var(--bg-surface)', padding: 12, borderRadius: 10, border: '1px solid var(--border-default)', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-primary)', background: 'var(--color-primary-subtle)', padding: '2px 6px', borderRadius: 4 }}>
          {proposal.operation}
        </span>
      </div>
      <div style={{ fontSize: 13, marginBottom: 10, fontWeight: 500 }}>
        {proposal.reason}
      </div>
      <button 
        className="btn-secondary" 
        style={{ width: '100%', fontSize: 12, height: 28, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
        onClick={() => {
           // To implement: Trigger the Review View for this node
           alert('Opening suggestion in Review Queue...');
        }}
      >
        <ExternalLink size={12} /> {zh ? '查看並審核' : 'Review Proposal'}
      </button>
    </div>
  );
}

function LoaderIcon() {
  return (
    <div className="animate-spin" style={{ width: 16, height: 16, border: '2px solid var(--color-primary)', borderTopColor: 'transparent', borderRadius: '50%' }}></div>
  );
}
