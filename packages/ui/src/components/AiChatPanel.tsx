import { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, User, Brain, ExternalLink, PlusCircle, Settings2, AlertCircle, ToggleLeft, ToggleRight, Check, X } from 'lucide-react';
import { ai, review, type ChatResponse, type ProposedChange, type ModelInfo, type CreditStatus } from '../api';
import ReactMarkdown from 'react-markdown';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  response?: ChatResponse;
}

interface ProposalState {
  status: 'pending' | 'accepted' | 'rejected';
}

export default function AiChatPanel({ wsId, zh }: { wsId: string; zh: boolean }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [allowEdits, setAllowEdits] = useState(false);
  const [forceAutoActive, setForceAutoActive] = useState(false);
  const [provider, setProvider] = useState<'openai' | 'anthropic' | 'gemini' | 'ollama'>('openai');
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [credits, setCredits] = useState<CreditStatus | null>(null);
  // Map of "msgIndex:proposalIndex" -> status
  const [proposalStates, setProposalStates] = useState<Record<string, ProposalState>>({});
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchCredits = async () => {
      try {
        const c = await ai.getCredits();
        setCredits(c);
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
    const msgIdx = messages.length + 1; // index of the assistant message we're about to add
    setInput('');
    setLoading(true);

    try {
      const history = messages.map(m => ({ role: m.role, content: m.content }));
      
      // Add empty assistant message that we will populate
      setMessages(prev => [...prev, { role: 'assistant', content: '', response: { answer: '', proposals: [], source_nodes: [], tokens_used: 0 } }]);

      await ai.chatStream({
        workspace_id: wsId,
        message: input,
        history,
        allow_edits: allowEdits,
        preferred_provider: provider,
        preferred_model: selectedModel,
        force_auto_active: forceAutoActive,
      }, (chunk) => {
        if (chunk.type === 'source_nodes') {
          setMessages(prev => {
            const next = [...prev];
            if (next[msgIdx]) {
              next[msgIdx] = {
                ...next[msgIdx],
                response: { ...next[msgIdx].response!, source_nodes: chunk.nodes }
              };
            }
            return next;
          });
        } else if (chunk.type === 'content') {
          setMessages(prev => {
            const next = [...prev];
            if (next[msgIdx]) {
              next[msgIdx] = {
                ...next[msgIdx],
                content: next[msgIdx].content + chunk.delta
              };
            }
            return next;
          });
        } else if (chunk.type === 'proposals') {
          setMessages(prev => {
            const next = [...prev];
            if (next[msgIdx]) {
              next[msgIdx] = {
                ...next[msgIdx],
                response: { ...next[msgIdx].response!, proposals: chunk.proposals }
              };
            }
            return next;
          });
        } else if (chunk.type === 'done') {
          setMessages(prev => {
            const next = [...prev];
            if (next[msgIdx]) {
              next[msgIdx] = {
                ...next[msgIdx],
                response: { ...next[msgIdx].response!, tokens_used: chunk.tokens_used }
              };
            }
            return next;
          });
        } else if (chunk.type === 'error') {
          throw new Error(chunk.detail);
        }
      });

    } catch (e: any) {
      setMessages(prev => {
        const next = [...prev];
        if (next[msgIdx]) {
          next[msgIdx] = { ...next[msgIdx], content: next[msgIdx].content + `\n\nError: ${e.message}` };
        } else {
          next.push({ role: 'assistant', content: `Error: ${e.message}` });
        }
        return next;
      });
    } finally {
      setLoading(false);
    }
  };

  const handleAcceptProposal = async (msgIdx: number, propIdx: number, proposal: ProposedChange) => {
    const key = `${msgIdx}:${propIdx}`;
    setProposalStates(prev => ({ ...prev, [key]: { status: 'accepted' } }));
    try {
      if ((proposal as any).review_queue_id) {
        await review.accept((proposal as any).review_queue_id);
      }
    } catch (e: any) {
      console.error('Accept proposal failed', e);
      setProposalStates(prev => ({ ...prev, [key]: { status: 'pending' } }));
    }
  };

  const handleRejectProposal = async (msgIdx: number, propIdx: number, proposal: ProposedChange) => {
    const key = `${msgIdx}:${propIdx}`;
    setProposalStates(prev => ({ ...prev, [key]: { status: 'rejected' } }));
    try {
      if ((proposal as any).review_queue_id) {
        await review.reject((proposal as any).review_queue_id);
      }
    } catch (e: any) {
      console.error('Reject proposal failed', e);
      setProposalStates(prev => ({ ...prev, [key]: { status: 'pending' } }));
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

        {/* allow_edits toggle */}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            {zh ? '允許提案' : 'Allow proposals'}
          </span>
          <button
            onClick={() => setAllowEdits(v => !v)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', color: allowEdits ? 'var(--color-primary)' : 'var(--text-muted)' }}
            title={allowEdits ? (zh ? '關閉 AI 提案模式' : 'Disable AI proposals') : (zh ? '開啟 AI 提案模式' : 'Enable AI proposals')}
          >
            {allowEdits ? <ToggleRight size={22} /> : <ToggleLeft size={22} />}
          </button>
        </div>

        {/* force_auto_active toggle */}
        <div style={{ marginLeft: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            {zh ? '自動生效' : 'Auto Active'}
          </span>
          <button
            onClick={() => setForceAutoActive(v => !v)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', color: forceAutoActive ? 'var(--color-primary)' : 'var(--text-muted)' }}
            title={forceAutoActive ? (zh ? '關閉強制自動生效' : 'Disable force auto active') : (zh ? '開啟強制自動生效' : 'Enable force auto active')}
          >
            {forceAutoActive ? <ToggleRight size={22} /> : <ToggleLeft size={22} />}
          </button>
        </div>
      </div>

      {/* Selector Bar */}
      <div style={{
        padding: '8px 16px', background: 'var(--bg-base)', borderBottom: '1px solid var(--border-default)',
        display: 'flex', gap: 8, overflowX: 'auto', alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
          <Settings2 size={14} style={{ opacity: 0.6 }} />
          <select
            value={provider}
            onChange={e => setProvider(e.target.value as any)}
            style={{
              fontSize: 11, padding: '3px 6px', borderRadius: 6,
              border: `1px solid var(--ai-${provider})`,
              background: `var(--ai-${provider}-subtle)`,
              color: `var(--ai-${provider})`,
              fontWeight: 700, outline: 'none', cursor: 'pointer',
            }}
          >
            <option value="openai" disabled={credits ? !credits.has_own_key.openai : false} style={{ background: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
              OpenAI {credits && !credits.has_own_key.openai ? (zh ? '(未設定)' : '(No Key)') : ''}
            </option>
            <option value="anthropic" disabled={credits ? !credits.has_own_key.anthropic : false} style={{ background: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
              Anthropic {credits && !credits.has_own_key.anthropic ? (zh ? '(未設定)' : '(No Key)') : ''}
            </option>
            <option value="gemini" disabled={credits ? !credits.has_own_key.gemini : false} style={{ background: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
              Gemini {credits && !credits.has_own_key.gemini ? (zh ? '(未設定)' : '(No Key)') : ''}
            </option>
            <option value="ollama" disabled={credits ? !credits.has_own_key.ollama : false} style={{ background: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
              Ollama {credits && !credits.has_own_key.ollama ? (zh ? '(未設定)' : '(No Key)') : ''}
            </option>
          </select>
        </div>
        <div style={{ width: 1, height: 16, background: 'var(--border-default)' }} />
        <select
          value={selectedModel}
          onChange={e => setSelectedModel(e.target.value)}
          style={{
            fontSize: 11, padding: '3px 6px', borderRadius: 6,
            border: '1px solid var(--border-default)',
            background: 'var(--bg-surface)',
            color: 'var(--text-secondary)',
            flex: 1, minWidth: 100, outline: 'none', cursor: 'pointer',
          }}
        >
          {models.map(m => (
            <option key={m.id} value={m.id} style={{ background: 'var(--bg-surface)', color: 'var(--text-primary)' }}>{m.display_name}</option>
          ))}
          {models.length === 0 && <option value="">Loading...</option>}
        </select>
      </div>

      {/* allow_edits hint banner */}
      {allowEdits && (
        <div style={{
          padding: '8px 16px', background: 'var(--color-primary-subtle)',
          borderBottom: '1px solid var(--border-default)',
          fontSize: 12, color: 'var(--color-primary)', display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <PlusCircle size={12} />
          {zh
            ? 'AI 提案模式：AI 可能在回答後建議新增或修改節點，可在對話中直接接受或拒絕。'
            : 'Proposal mode: AI may suggest node additions or edits. Accept or reject inline.'}
        </div>
      )}

      {/* Messages List */}
      <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: 24 }}>
        {messages.length === 0 && (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>
            <Brain size={48} style={{ opacity: 0.2, marginBottom: 16 }} />
            <p style={{ fontSize: 14 }}>
              {zh ? '詢問關於當前知識庫的問題，或啟用「允許提案」讓 AI 協助優化圖譜。' : 'Ask about your KB, or enable proposals to let AI suggest graph improvements.'}
            </p>
          </div>
        )}
        {messages.map((m, msgIdx) => (
          <div key={msgIdx} style={{ display: 'flex', gap: 12, flexDirection: m.role === 'user' ? 'row-reverse' : 'row' }}>
            <div style={{
              width: 32, height: 32, borderRadius: 16, flexShrink: 0,
              background: m.role === 'user' ? 'var(--border-default)' : 'var(--color-primary-subtle)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              {m.role === 'user' ? <User size={16} /> : <Sparkles size={16} style={{ color: 'var(--color-primary)' }} />}
            </div>
            <div style={{ maxWidth: '85%' }}>
              <div style={{
                padding: '12px 16px', borderRadius: 16, fontSize: 14, lineHeight: 1.5,
                background: m.role === 'user' ? 'var(--color-primary)' : 'var(--bg-base)',
                color: m.role === 'user' ? 'white' : 'var(--text-primary)',
                border: m.role === 'assistant' ? '1px solid var(--border-default)' : 'none',
              }}>
                <ReactMarkdown>{m.content}</ReactMarkdown>

                {/* Inline Proposals */}
                {m.response?.proposals && m.response.proposals.length > 0 && (
                  <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, opacity: 0.8, display: 'flex', alignItems: 'center', gap: 6 }}>
                      <PlusCircle size={14} /> {zh ? 'AI 提案' : 'AI Proposals'}
                    </div>
                    {m.response.proposals.map((p, propIdx) => {
                      const key = `${msgIdx}:${propIdx}`;
                      const state = proposalStates[key];
                      return (
                        <ProposalCard
                          key={propIdx}
                          proposal={p}
                          zh={zh}
                          status={state?.status ?? 'pending'}
                          onAccept={() => handleAcceptProposal(msgIdx, propIdx, p)}
                          onReject={() => handleRejectProposal(msgIdx, propIdx, p)}
                        />
                      );
                    })}
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

              {/* Empty-context warning */}
              {m.role === 'assistant' && m.response !== undefined && (m.response.source_nodes?.length ?? -1) === 0 && (
                <div style={{
                  marginTop: 8, padding: '6px 10px', borderRadius: 6,
                  background: 'var(--color-warning-subtle, #fef3c7)',
                  border: '1px solid var(--color-warning, #f59e0b)',
                  fontSize: 11, color: 'var(--color-warning, #92400e)',
                  display: 'flex', alignItems: 'flex-start', gap: 6,
                }}>
                  <AlertCircle size={12} style={{ flexShrink: 0, marginTop: 1 }} />
                  <span>
                    {zh
                      ? '未找到相關節點，回答可能不夠準確。請確認節點已建立，或前往知識庫設定執行「重新嵌入所有節點」。'
                      : 'No matching nodes found — answer may be inaccurate. Add more nodes or run "Re-embed All" in workspace settings.'}
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ display: 'flex', gap: 12 }}>
            <div style={{ width: 32, height: 32, borderRadius: 16, background: 'var(--color-primary-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <SpinnerIcon />
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
            background: 'var(--color-error-subtle)', border: '1px solid var(--color-error)',
            fontSize: 12, color: 'var(--color-error)', display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <AlertCircle size={14} />
            <b>
              {zh
                ? `您尚未設定 ${provider.toUpperCase()} 的 API Key。`
                : `No API key configured for ${provider.toUpperCase()}.`}
            </b>
            <button
              onClick={() => alert(zh ? "請前往「系統設定」加入 Key" : "Please go to System Settings to add your key")}
              style={{ marginLeft: 'auto', fontWeight: 700, background: 'none', border: 'none', color: 'var(--color-error)', cursor: 'pointer', textDecoration: 'underline' }}
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
              color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
            }}
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

function ProposalCard({
  proposal, zh, status, onAccept, onReject,
}: {
  proposal: ProposedChange;
  zh: boolean;
  status: 'pending' | 'accepted' | 'rejected';
  onAccept: () => void;
  onReject: () => void;
}) {
  const isDone = status !== 'pending';
  return (
    <div style={{
      background: isDone ? 'var(--bg-app)' : 'var(--bg-surface)',
      padding: 12, borderRadius: 10,
      border: `1px solid ${status === 'accepted' ? 'var(--color-success)' : status === 'rejected' ? 'var(--color-error)' : 'var(--border-default)'}`,
      opacity: isDone ? 0.7 : 1,
      transition: 'all 0.2s',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-primary)', background: 'var(--color-primary-subtle)', padding: '2px 6px', borderRadius: 4 }}>
          {proposal.operation}
        </span>
        {isDone && (
          <span style={{ fontSize: 11, fontWeight: 600, color: status === 'accepted' ? 'var(--color-success)' : 'var(--color-error)' }}>
            {status === 'accepted' ? (zh ? '✓ 已接受' : '✓ Accepted') : (zh ? '✗ 已拒絕' : '✗ Rejected')}
          </span>
        )}
      </div>
      <div style={{ fontSize: 13, marginBottom: isDone ? 0 : 10, fontWeight: 500 }}>
        {proposal.reason}
      </div>
      {!isDone && (
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            className="btn-primary"
            style={{ flex: 1, fontSize: 12, height: 28, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}
            onClick={onAccept}
          >
            <Check size={12} /> {zh ? '接受' : 'Accept'}
          </button>
          <button
            className="btn-secondary"
            style={{ flex: 1, fontSize: 12, height: 28, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}
            onClick={onReject}
          >
            <X size={12} /> {zh ? '拒絕' : 'Reject'}
          </button>
          {(proposal as any).review_queue_id && (
            <button
              className="btn-secondary"
              style={{ fontSize: 12, height: 28, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4, padding: '0 10px' }}
              onClick={() => window.open(`/review`, '_blank')}
              title={zh ? '在審核佇列中查看' : 'View in Review Queue'}
            >
              <ExternalLink size={12} />
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function SpinnerIcon() {
  return (
    <div className="animate-spin" style={{ width: 16, height: 16, border: '2px solid var(--color-primary)', borderTopColor: 'transparent', borderRadius: '50%' }}></div>
  );
}
