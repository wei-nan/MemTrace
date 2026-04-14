import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, User, Brain, ExternalLink, PlusCircle } from 'lucide-react';
import { ai, type ChatResponse, type ProposedChange } from '../api';
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
  const scrollRef = useRef<HTMLDivElement>(null);

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
      const res = await ai.chat({ workspace_id: wsId, message: input, history });
      
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
      <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-default)', display: 'flex', alignItems: 'center', gap: 10 }}>
        <Sparkles size={18} style={{ color: 'var(--color-primary)' }} />
        <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>
          {zh ? 'AI 助手' : 'AI Assistant'}
        </h3>
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
      <div style={{ padding: '20px', borderTop: '1px solid var(--border-default)' }}>
        <div style={{ display: 'flex', gap: 10, background: 'var(--bg-app)', padding: '8px 12px', borderRadius: 24, border: '1px solid var(--border-default)' }}>
          <input 
            style={{ flex: 1, background: 'none', border: 'none', outline: 'none', color: 'var(--text-default)', fontSize: 14, paddingLeft: 8 }}
            placeholder={zh ? '輸入訊息...' : 'Type a message...'}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
          />
          <button 
            onClick={handleSend}
            disabled={!input.trim() || loading}
            style={{ 
              width: 32, height: 32, borderRadius: 16, border: 'none',
              background: input.trim() ? 'var(--color-primary)' : 'var(--border-default)',
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
