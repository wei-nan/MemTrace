import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Square, Sparkles, User, Brain, ExternalLink, PlusCircle, Settings2, AlertCircle, Check, X, RotateCcw, MessageSquare, Trash2, Pencil, ChevronUp, ChevronDown, Lock, GitPullRequest, Zap, Mic, MicOff, Volume2 } from 'lucide-react';
import { ai, voice, review, VoiceStreamSession, type ChatResponse, type ProposedChange, type ModelInfo, type CreditStatus, type ChatSession } from '../api';
import ReactMarkdown from 'react-markdown';
import { Button, Card } from './ui';
import { useModal } from './ModalContext';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  response?: ChatResponse;
  /** The condensed text spoken by TTS (D7), kept so it can be shown, not just heard. */
  spokenSummary?: string;
}

interface ProposalState {
  status: 'pending' | 'accepted' | 'rejected';
}


export default function AiChatPanel({ wsId, zh, onClose, fullPage }: { wsId: string; zh: boolean; onClose?: () => void; fullPage?: boolean }) {
  const { toast } = useModal();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [allowEdits, setAllowEdits] = useState(false);
  const [forceAutoActive, setForceAutoActive] = useState(false);
  // Remember the user's last provider/model choice across sessions so they don't
  // have to re-pick every time they open the assistant.
  const [provider, setProvider] = useState<'openai' | 'anthropic' | 'gemini' | 'ollama'>(() => {
    const saved = localStorage.getItem('mt_chat_provider');
    return (saved === 'openai' || saved === 'anthropic' || saved === 'gemini' || saved === 'ollama') ? saved : 'openai';
  });
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string>(() => localStorage.getItem('mt_chat_model') ?? '');
  const [credits, setCredits] = useState<CreditStatus | null>(null);
  const [proposalStates, setProposalStates] = useState<Record<string, ProposalState>>({});
  const [expandedNodes, setExpandedNodes] = useState<Record<number, boolean>>({});
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const abortedRef = useRef(false);
  const handleSendRef = useRef<((msg?: string) => Promise<void>) | null>(null);
  const lastEnterRef = useRef<number>(0);
  const [queue, setQueue] = useState<string[]>([]);
  const [providerMenuOpen, setProviderMenuOpen] = useState(false);
  const providerMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!providerMenuOpen) return;
    const handler = (e: MouseEvent) => {
      if (providerMenuRef.current && !providerMenuRef.current.contains(e.target as Node))
        setProviderMenuOpen(false);
    };
    window.addEventListener('mousedown', handler);
    return () => window.removeEventListener('mousedown', handler);
  }, [providerMenuOpen]);

  // ── Voice mode (mem_bede56ef): toggle-based mic control, TTS queue-not-interrupt,
  // explicit stop button separate from the mic toggle. Language follows the
  // browser/system locale, not the workspace language (V4).
  const voiceLanguage = typeof navigator !== 'undefined' ? navigator.language : 'en-US';
  const [voiceKeys, setVoiceKeys] = useState<{ stt: boolean; tts: boolean; sttProvider: string | null }>({ stt: false, tts: false, sttProvider: null });
  const [voiceModeActive, setVoiceModeActive] = useState(false);
  const [micOn, setMicOn] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [voiceQueueCount, setVoiceQueueCount] = useState(0);
  const isSpeakingRef = useRef(false);
  const voiceQueueRef = useRef<string[]>([]);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const streamSessionRef = useRef<VoiceStreamSession | null>(null);
  const finalTranscriptRef = useRef('');

  const loadVoiceKeys = useCallback(() => {
    voice.listKeys()
      .then(keys => setVoiceKeys({
        stt: keys.some(k => k.purpose === 'stt'),
        tts: keys.some(k => k.purpose === 'tts'),
        sttProvider: keys.find(k => k.purpose === 'stt')?.provider ?? null,
      }))
      .catch(() => {
        // Voice is opt-in; if the lookup fails, controls simply stay hidden.
      });
  }, []);

  // Load once on mount, and re-load whenever voice mode is switched on, so a
  // provider change made in Settings (e.g. switching STT to Deepgram) is picked
  // up without needing a full page reload.
  useEffect(() => { loadVoiceKeys(); }, [loadVoiceKeys]);
  useEffect(() => { if (voiceModeActive) loadVoiceKeys(); }, [voiceModeActive, loadVoiceKeys]);

  useEffect(() => { isSpeakingRef.current = isSpeaking; }, [isSpeaking]);

  // Leaving voice mode tears down any in-flight recording/playback.
  useEffect(() => {
    if (voiceModeActive) return;
    mediaRecorderRef.current?.stop();
    mediaStreamRef.current?.getTracks().forEach(t => t.stop());
    streamSessionRef.current?.stop();
    currentAudioRef.current?.pause();
    setMicOn(false);
    setIsSpeaking(false);
    voiceQueueRef.current = [];
    setVoiceQueueCount(0);
  }, [voiceModeActive]);

  useEffect(() => () => {
    mediaRecorderRef.current?.stop();
    mediaStreamRef.current?.getTracks().forEach(t => t.stop());
    streamSessionRef.current?.stop();
    currentAudioRef.current?.pause();
  }, []);

  /** Merge any queued voice segments (accumulated while TTS was speaking) plus an optional new one. */
  const flushVoiceQueue = (extra?: string): string => {
    const parts = [...voiceQueueRef.current];
    if (extra) parts.push(extra);
    voiceQueueRef.current = [];
    setVoiceQueueCount(0);
    return parts.join(' ');
  };

  const handleTTSEnded = () => {
    setIsSpeaking(false);
    currentAudioRef.current = null;
    if (voiceQueueRef.current.length > 0) {
      handleSendRef.current?.(flushVoiceQueue());
    }
  };

  // Explicit interrupt: a distinct control from the mic toggle, per spec —
  // talking while TTS plays queues (doesn't interrupt); this button does.
  const handleStopSpeaking = () => {
    currentAudioRef.current?.pause();
    handleTTSEnded();
  };

  /** Synthesize and play speech for already-spoken-ready text (no summarizing). */
  const speakText = async (spoken: string) => {
    try {
      const url = await voice.textToSpeech(spoken, voiceLanguage, localStorage.getItem('mt_tts_voice') || undefined);
      const audio = new Audio(url);
      currentAudioRef.current = audio;
      setIsSpeaking(true);
      audio.onended = () => { handleTTSEnded(); URL.revokeObjectURL(url); };
      audio.onerror = () => { handleTTSEnded(); URL.revokeObjectURL(url); };
      await audio.play();
    } catch (e: any) {
      setIsSpeaking(false);
      toast({ message: e.message, variant: 'error' });
    }
  };

  // Fallback path (used only when the stream did NOT provide a spoken summary,
  // e.g. the model ignored the instruction): summarize the full reply, then speak.
  // D7 (mem_77b74b8a): reading code/markdown aloud verbatim is jarring.
  const playTTS = async (text: string, msgIdx?: number) => {
    let spoken = text;
    try {
      spoken = await voice.summarizeForSpeech(text, voiceLanguage, provider, selectedModel);
    } catch {
      spoken = text;
    }
    if (msgIdx !== undefined && spoken.trim() && spoken.trim() !== text.trim()) {
      setMessages(prev => {
        const next = [...prev];
        if (next[msgIdx]) next[msgIdx] = { ...next[msgIdx], spokenSummary: spoken };
        return next;
      });
    }
    await speakText(spoken);
  };

  /** Route a completed transcript segment: queue during TTS, else send (V3). */
  const dispatchTranscript = (transcript: string) => {
    if (!transcript.trim()) return;
    if (isSpeakingRef.current) {
      voiceQueueRef.current.push(transcript);
      setVoiceQueueCount(voiceQueueRef.current.length);
    } else {
      handleSendRef.current?.(flushVoiceQueue(transcript));
    }
  };

  // Live streaming STT (Deepgram). Interim results stream into the input box so
  // the user sees words appear while speaking; the final text is dispatched when
  // the mic toggles off. Other providers fall through to the batch path below.
  const startStreamingMic = async () => {
    finalTranscriptRef.current = '';
    const session = new VoiceStreamSession({
      onTranscript: (text, isFinal) => {
        if (isFinal) {
          finalTranscriptRef.current = `${finalTranscriptRef.current} ${text}`.trim();
          setInput(finalTranscriptRef.current);
        } else {
          setInput(`${finalTranscriptRef.current} ${text}`.trim());
        }
      },
      onError: (msg) => toast({ message: msg, variant: 'error' }),
      onClose: () => {
        streamSessionRef.current = null;
        setMicOn(false);
        setTranscribing(false);
        const finalText = finalTranscriptRef.current.trim();
        finalTranscriptRef.current = '';
        setInput('');
        dispatchTranscript(finalText);
      },
    });
    try {
      await session.start(voiceLanguage);
      streamSessionRef.current = session;
      setMicOn(true);
    } catch {
      streamSessionRef.current = null;
      toast({ message: zh ? '無法存取麥克風' : 'Microphone access denied', variant: 'error' });
    }
  };

  const handleToggleMic = async () => {
    const streaming = voiceKeys.sttProvider === 'deepgram';
    if (micOn) {
      if (streaming) {
        setTranscribing(true);       // finalizing: waiting for the last results
        streamSessionRef.current?.stop();
      } else {
        mediaRecorderRef.current?.stop();
        setMicOn(false);
      }
      return;
    }
    if (streaming) {
      await startStreamingMic();
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      audioChunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
      recorder.onstop = async () => {
        mediaStreamRef.current?.getTracks().forEach(t => t.stop());
        mediaStreamRef.current = null;
        const blob = new Blob(audioChunksRef.current, { type: recorder.mimeType || 'audio/webm' });
        audioChunksRef.current = [];
        if (blob.size === 0) return;
        setTranscribing(true);
        try {
          const transcript = await voice.speechToText(blob, voiceLanguage);
          if (!transcript.trim()) return;
          if (isSpeakingRef.current) {
            // TTS still playing: queue, don't interrupt (V3 decision).
            voiceQueueRef.current.push(transcript);
            setVoiceQueueCount(voiceQueueRef.current.length);
          } else {
            handleSendRef.current?.(flushVoiceQueue(transcript));
          }
        } catch (e: any) {
          toast({ message: e.message, variant: 'error' });
        } finally {
          setTranscribing(false);
        }
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setMicOn(true);
    } catch {
      toast({ message: zh ? '無法存取麥克風' : 'Microphone access denied', variant: 'error' });
    }
  };

  // Session state
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [hasOlderMessages, setHasOlderMessages] = useState(false);
  const [oldestMessageId, setOldestMessageId] = useState<number | null>(null);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const isColdSession = sessionId
    ? sessions.find(s => s.id === sessionId)?.is_cold ?? false
    : false;

  const loadSessions = useCallback(async () => {
    try {
      const list = await ai.listSessions(wsId);
      setSessions(list);
    } catch {
      // Session list is optional; the active conversation remains usable.
    }
  }, [wsId]);

  useEffect(() => { loadSessions(); }, [loadSessions]);

  // Persist last-used session per workspace so it survives page refresh.
  useEffect(() => {
    if (sessionId) localStorage.setItem(`mt_last_session_${wsId}`, sessionId);
  }, [sessionId, wsId]);

  // On mount: restore the last session directly via API — no need to wait for sessions list.
  useEffect(() => {
    const savedId = localStorage.getItem(`mt_last_session_${wsId}`);
    if (!savedId) return;
    ai.getSessionMessages(savedId, 20)
      .then(msgs => {
        if (msgs.length === 0) return; // session exists but empty; skip
        setSessionId(savedId);
        setMessages(msgs.map(m => ({ role: m.role, content: m.content })));
        setOldestMessageId(msgs[0]?.id ?? null);
        setHasOlderMessages(msgs.length >= 20);
      })
      .catch(() => {
        // Session deleted or expired — clear stale reference.
        localStorage.removeItem(`mt_last_session_${wsId}`);
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Run exactly once on mount

  useEffect(() => {
    const fetchCredits = async () => {
      try {
        const c = await ai.getCredits();
        setCredits(c);
        if (c && !c.has_own_key[provider]) {
          const firstAvailable = (Object.keys(c.has_own_key) as Array<keyof typeof c.has_own_key>).find(k => c.has_own_key[k]);
          if (firstAvailable) setProvider(firstAvailable);
        }
      } catch {
        // Credit discovery falls back to the selected provider.
      }
    };
    fetchCredits();
  }, [provider]);

  useEffect(() => {
    const fetchModels = async () => {
      setModelsLoading(true);
      try {
        const list = await ai.listModels(provider);
        // Positive allowlist: only language (chat) models. Guards against providers
        // that surface image/tts/other non-language models (see is_non_text_model).
        const chatModels = list.filter(m => m.model_type === 'chat');
        setModels(chatModels);
        if (chatModels.length > 0) {
          // Keep the user's saved model if it's still offered by this provider;
          // otherwise default to the first available one.
          const saved = localStorage.getItem('mt_chat_model');
          const keep = saved && chatModels.some(m => m.id === saved) ? saved : chatModels[0].id;
          setSelectedModel(keep);
        }
      } catch {
        // No valid key / provider unavailable → no usable models.
        setModels([]);
      } finally {
        setModelsLoading(false);
      }
    };
    fetchModels();
  }, [provider]);

  // Persist provider/model choice so it's restored on the next visit.
  useEffect(() => { localStorage.setItem('mt_chat_provider', provider); }, [provider]);
  useEffect(() => { if (selectedModel) localStorage.setItem('mt_chat_model', selectedModel); }, [selectedModel]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const switchSession = async (s: ChatSession) => {
    try {
      const msgs = await ai.getSessionMessages(s.id);
      setSessionId(s.id);
      setMessages(msgs.map(m => ({ role: m.role, content: m.content })));
      setProposalStates({});
      setOldestMessageId(msgs[0]?.id ?? null);
      setHasOlderMessages(msgs.length >= 20);
    } catch {
      toast({ message: zh ? '載入對話失敗' : 'Failed to load session', variant: 'error' });
    }
  };

  const startNewSession = () => {
    setSessionId(null);
    setMessages([]);
    setProposalStates({});
    setOldestMessageId(null);
    setHasOlderMessages(false);
  };

  const loadOlderMessages = async () => {
    if (!sessionId || !oldestMessageId || loadingOlder) return;
    setLoadingOlder(true);
    try {
      const older = await ai.getSessionMessages(sessionId, 20, oldestMessageId);
      if (older.length > 0) {
        setMessages(prev => [...older.map(m => ({ role: m.role, content: m.content })), ...prev]);
        setOldestMessageId(older[0].id);
        setHasOlderMessages(older.length >= 20);
      } else {
        setHasOlderMessages(false);
      }
    } catch {
      // Keep the currently loaded history when pagination fails.
    } finally {
      setLoadingOlder(false);
    }
  };

  const handleDeleteSession = async (s: ChatSession, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await ai.deleteSession(s.id);
      if (sessionId === s.id) startNewSession();
      loadSessions();
    } catch {
      toast({ message: zh ? '刪除失敗' : 'Failed to delete', variant: 'error' });
    }
  };

  const handleRenameSession = async (s: ChatSession) => {
    if (!editingTitle.trim()) return;
    try {
      await ai.renameSession(s.id, editingTitle.trim());
      setSessions(prev => prev.map(x => x.id === s.id ? { ...x, title: editingTitle.trim() } : x));
    } catch {
      toast({ message: zh ? '重命名失敗' : 'Failed to rename', variant: 'error' });
    } finally {
      setEditingSessionId(null);
    }
  };

  const handleAbort = () => {
    abortedRef.current = true;
    abortControllerRef.current?.abort();
  };

  const handleSend = async (msgOverride?: string) => {
    const msg = msgOverride ?? input;
    if (!msg.trim() || loading) return;
    if (!msgOverride) setInput('');

    const userMsg: Message = { role: 'user', content: msg };
    setMessages(prev => [...prev, userMsg]);
    const msgIdx = messages.length + 1;
    setLoading(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const history = messages.map(m => ({ role: m.role, content: m.content }));
      setMessages(prev => [...prev, { role: 'assistant', content: '', response: { answer: '', proposals: [], source_nodes: [], tokens_used: 0 } }]);

      let currentSessionId = sessionId;
      let assistantText = '';
      // Voice mode (D7): the stream leads with a spoken summary that we show and
      // speak early, before the full answer finishes. Track it so the done handler
      // knows whether to fall back to the post-hoc summarize path.
      const wantSummary = voiceModeActive && voiceKeys.tts;
      let streamSummary = '';
      let spokeSummary = false;

      await ai.chatStream({
        workspace_id: wsId,
        message: msg,
        history: currentSessionId ? undefined : history,
        session_id: currentSessionId ?? undefined,
        allow_edits: allowEdits,
        preferred_provider: provider,
        preferred_model: selectedModel,
        force_auto_active: forceAutoActive,
        want_spoken_summary: wantSummary,
      }, (chunk) => {
        if (chunk.type === 'session') {
          currentSessionId = chunk.session_id;
          setSessionId(chunk.session_id);
          loadSessions();
        } else if (chunk.type === 'source_nodes') {
          setMessages(prev => {
            const next = [...prev];
            if (next[msgIdx]) next[msgIdx] = { ...next[msgIdx], response: { ...next[msgIdx].response!, source_nodes: chunk.nodes } };
            return next;
          });
        } else if (chunk.type === 'content') {
          assistantText += chunk.delta;
          setMessages(prev => {
            const next = [...prev];
            if (next[msgIdx]) next[msgIdx] = { ...next[msgIdx], content: next[msgIdx].content + chunk.delta };
            return next;
          });
        } else if (chunk.type === 'spoken_summary') {
          streamSummary += chunk.delta;
          setMessages(prev => {
            const next = [...prev];
            if (next[msgIdx]) next[msgIdx] = { ...next[msgIdx], spokenSummary: (next[msgIdx].spokenSummary ?? '') + chunk.delta };
            return next;
          });
        } else if (chunk.type === 'spoken_summary_done') {
          // Start speaking the summary now — the full answer keeps streaming meanwhile.
          if (voiceKeys.tts && streamSummary.trim()) {
            spokeSummary = true;
            speakText(streamSummary.trim());
          }
        } else if (chunk.type === 'proposals') {
          setMessages(prev => {
            const next = [...prev];
            if (next[msgIdx]) next[msgIdx] = { ...next[msgIdx], response: { ...next[msgIdx].response!, proposals: chunk.proposals } };
            return next;
          });
        } else if (chunk.type === 'done') {
          setMessages(prev => {
            const next = [...prev];
            if (next[msgIdx]) next[msgIdx] = { ...next[msgIdx], response: { ...next[msgIdx].response!, tokens_used: chunk.tokens_used } };
            return next;
          });
          // Refresh sessions to update token count & last_active_at
          loadSessions();
          // If the stream already delivered (and we spoke) a summary, we're done.
          // Otherwise fall back to summarizing the full reply post-hoc.
          if (voiceModeActive && voiceKeys.tts && assistantText.trim() && !spokeSummary) {
            playTTS(assistantText, msgIdx);
          }
        } else if (chunk.type === 'error') {
          setLoading(false);
          if (chunk.detail === 'session_frozen') {
            toast({ message: zh ? '此對話已封存，請開啟新對話' : 'Session is archived. Start a new conversation.', variant: 'warning' });
          } else {
            setMessages(prev => {
              const next = [...prev];
              if (next[msgIdx]) next[msgIdx] = { ...next[msgIdx], content: next[msgIdx].content + `\n\n**Error:** ${chunk.detail}` };
              else next.push({ role: 'assistant', content: `**Error:** ${chunk.detail}` });
              return next;
            });
          }
        }
      }, controller.signal);
    } catch (e: any) {
      if (e?.name === 'AbortError') {
        setMessages(prev => {
          const next = [...prev];
          if (next[msgIdx] && !next[msgIdx].content) next[msgIdx] = { ...next[msgIdx], content: zh ? '_(已中止)_' : '_(stopped)_' };
          return next;
        });
      } else {
        setMessages(prev => {
          const next = [...prev];
          if (next[msgIdx]) next[msgIdx] = { ...next[msgIdx], content: next[msgIdx].content + `\n\nError: ${e.message}` };
          else next.push({ role: 'assistant', content: `Error: ${e.message}` });
          return next;
        });
      }
    } finally {
      setLoading(false);
      abortControllerRef.current = null;
    }
  };

  handleSendRef.current = handleSend;

  useEffect(() => {
    if (abortedRef.current) { abortedRef.current = false; return; }
    if (!loading && queue.length > 0) {
      const [next, ...rest] = queue;
      setQueue(rest);
      handleSendRef.current?.(next);
    }
  }, [loading]);

  const handleAcceptProposal = async (msgIdx: number, propIdx: number, proposal: ProposedChange) => {
    const key = `${msgIdx}:${propIdx}`;
    const reviewId = (proposal as any).review_queue_id;
    if (!reviewId) {
      toast({ message: zh ? '請先開啟「允許提案」再送出訊息，才能建立可執行的提案。' : 'Enable "Allow proposals" before sending to create actionable proposals.', variant: 'warning' });
      return;
    }
    setProposalStates(prev => ({ ...prev, [key]: { status: 'accepted' } }));
    try {
      await review.accept(reviewId);
      toast({ message: zh ? '提案已執行' : 'Proposal applied', variant: 'success' });
    } catch (e: any) {
      setProposalStates(prev => ({ ...prev, [key]: { status: 'pending' } }));
      toast({ message: e?.message || (zh ? '執行提案失敗' : 'Failed to apply proposal'), variant: 'error' });
    }
  };

  const handleRejectProposal = async (msgIdx: number, propIdx: number, proposal: ProposedChange) => {
    const key = `${msgIdx}:${propIdx}`;
    setProposalStates(prev => ({ ...prev, [key]: { status: 'rejected' } }));
    try {
      if ((proposal as any).review_queue_id) await review.reject((proposal as any).review_queue_id);
    } catch (e: any) {
      setProposalStates(prev => ({ ...prev, [key]: { status: 'pending' } }));
      toast({ message: e?.message || (zh ? '拒絕提案失敗' : 'Failed to reject proposal'), variant: 'error' });
    }
  };

  const hotSessions = sessions.filter(s => !s.is_cold);
  const coldSessions = sessions.filter(s => s.is_cold);

  const renderSession = (s: ChatSession) => {
    const active = s.id === sessionId;
    return (
      <div
        key={s.id}
        onClick={() => switchSession(s)}
        style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '6px 10px', borderRadius: 8, cursor: 'pointer',
          background: active ? 'var(--color-primary-subtle)' : 'transparent',
          border: active ? '1px solid var(--color-primary)' : '1px solid transparent',
        }}
      >
        {s.is_cold ? <Lock size={11} style={{ color: 'var(--text-muted)', flexShrink: 0 }} /> : <MessageSquare size={11} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />}
        {editingSessionId === s.id ? (
          <input
            autoFocus
            value={editingTitle}
            onChange={e => setEditingTitle(e.target.value)}
            onBlur={() => handleRenameSession(s)}
            onKeyDown={e => { if (e.key === 'Enter') handleRenameSession(s); if (e.key === 'Escape') setEditingSessionId(null); }}
            onClick={e => e.stopPropagation()}
            style={{ flex: 1, fontSize: 12, background: 'none', border: 'none', outline: 'none', color: 'var(--text-primary)' }}
          />
        ) : (
          <span style={{ flex: 1, fontSize: 12, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {s.title || (zh ? '（無標題）' : '(Untitled)')}
          </span>
        )}
        <button
          onClick={e => { e.stopPropagation(); setEditingSessionId(s.id); setEditingTitle(s.title); }}
          style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, color: 'var(--text-muted)', display: 'flex', opacity: 0.6 }}
          title={zh ? '重命名' : 'Rename'}
        ><Pencil size={11} /></button>
        <button
          onClick={e => handleDeleteSession(s, e)}
          style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, color: 'var(--text-muted)', display: 'flex', opacity: 0.6 }}
          title={zh ? '刪除' : 'Delete'}
        ><Trash2 size={11} /></button>
      </div>
    );
  };

  return (
    <div style={{ display: 'flex', height: '100%', background: 'var(--bg-surface)' }}>
      {/* Sidebar */}
      {sidebarOpen && (
        <div style={{ width: fullPage ? 260 : 200, borderRight: '1px solid var(--border-default)', display: 'flex', flexDirection: 'column', flexShrink: 0, overflow: 'hidden' }}>
          <div style={{ padding: '10px 10px 6px', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', flex: 1 }}>
              {zh ? '對話紀錄' : 'Conversations'}
            </span>
            <Button variant="ghost" size="sm" onClick={startNewSession} title={zh ? '新對話' : 'New'} style={{ padding: 3 }}>
              <PlusCircle size={14} />
            </Button>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '0 6px 8px' }}>
            {hotSessions.length > 0 && (
              <>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', padding: '4px 4px 2px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  {zh ? '最近 7 天' : 'Recent'}
                </div>
                {hotSessions.map(renderSession)}
              </>
            )}
            {coldSessions.length > 0 && (
              <>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', padding: '8px 4px 2px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: 4 }}>
                  <Lock size={9} /> {zh ? '封存' : 'Archived'}
                </div>
                {coldSessions.map(renderSession)}
              </>
            )}
            {sessions.length === 0 && (
              <div style={{ fontSize: 11, color: 'var(--text-muted)', padding: '12px 4px', textAlign: 'center' }}>
                {zh ? '尚無對話' : 'No conversations'}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Main chat area */}
      <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0 }}>
        {/* Header */}
        <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--border-default)', display: 'flex', alignItems: 'center', gap: 4, minWidth: 0 }}>
          <Button variant="ghost" size="sm" onClick={() => setSidebarOpen(v => !v)} style={{ padding: 4, flexShrink: 0 }} title={zh ? '切換側欄' : 'Toggle sidebar'}>
            <MessageSquare size={15} />
          </Button>
          <Sparkles size={15} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
          <h3 style={{ fontSize: 14, fontWeight: 600, margin: 0, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', minWidth: 0 }}>
            {zh ? 'AI 助手' : 'AI Assistant'}
            {isColdSession && <Lock size={12} style={{ marginLeft: 6, color: 'var(--text-muted)', verticalAlign: 'middle' }} />}
          </h3>

          <Button variant="ghost" size="sm" onClick={startNewSession} title={zh ? '開新對話' : 'New Conversation'} style={{ padding: 4, flexShrink: 0 }}>
            <RotateCcw size={15} />
          </Button>

          <button
            onClick={() => setAllowEdits(v => !v)}
            title={zh ? `允許提案：${allowEdits ? '開啟' : '關閉'}` : `Allow proposals: ${allowEdits ? 'on' : 'off'}`}
            style={{
              display: 'flex', alignItems: 'center', gap: 3, padding: '3px 7px', borderRadius: 6,
              background: allowEdits ? 'var(--color-primary-subtle)' : 'transparent',
              border: `1px solid ${allowEdits ? 'var(--color-primary)' : 'var(--border-default)'}`,
              color: allowEdits ? 'var(--color-primary)' : 'var(--text-muted)',
              cursor: 'pointer', fontSize: 11, fontWeight: 500, flexShrink: 0,
            }}
          >
            <GitPullRequest size={12} />
            {zh ? '提案' : 'Propose'}
          </button>

          <button
            onClick={() => setForceAutoActive(v => !v)}
            title={zh ? `自動生效：${forceAutoActive ? '開啟' : '關閉'}` : `Auto active: ${forceAutoActive ? 'on' : 'off'}`}
            style={{
              display: 'flex', alignItems: 'center', gap: 3, padding: '3px 7px', borderRadius: 6,
              background: forceAutoActive ? 'color-mix(in srgb, var(--color-warning) 15%, transparent)' : 'transparent',
              border: `1px solid ${forceAutoActive ? 'var(--color-warning)' : 'var(--border-default)'}`,
              color: forceAutoActive ? 'var(--color-warning)' : 'var(--text-muted)',
              cursor: 'pointer', fontSize: 11, fontWeight: 500, flexShrink: 0,
            }}
          >
            <Zap size={12} />
            {zh ? '自動' : 'Auto'}
          </button>

          {(voiceKeys.stt || voiceKeys.tts) && (
            <button
              onClick={() => setVoiceModeActive(v => !v)}
              title={zh ? `語音模式：${voiceModeActive ? '開啟' : '關閉'}` : `Voice mode: ${voiceModeActive ? 'on' : 'off'}`}
              style={{
                display: 'flex', alignItems: 'center', gap: 3, padding: '3px 7px', borderRadius: 6,
                background: voiceModeActive ? 'var(--color-primary-subtle)' : 'transparent',
                border: `1px solid ${voiceModeActive ? 'var(--color-primary)' : 'var(--border-default)'}`,
                color: voiceModeActive ? 'var(--color-primary)' : 'var(--text-muted)',
                cursor: 'pointer', fontSize: 11, fontWeight: 500, flexShrink: 0,
              }}
            >
              <Mic size={12} />
              {zh ? '語音' : 'Voice'}
            </button>
          )}

          {onClose && (
            <Button variant="ghost" size="sm" onClick={onClose} title={zh ? '關閉' : 'Close'} style={{ padding: 4, flexShrink: 0 }}>
              <X size={16} />
            </Button>
          )}
        </div>

        {/* Selector Bar */}
        <div style={{ padding: '8px 16px', background: 'var(--bg-base)', borderBottom: '1px solid var(--border-default)', display: 'flex', gap: 8, alignItems: 'center', minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
            <Settings2 size={14} style={{ opacity: 0.6 }} />
            {/* Custom provider dropdown */}
            <div ref={providerMenuRef} style={{ position: 'relative' }}>
              <button
                onClick={() => setProviderMenuOpen(v => !v)}
                style={{ fontSize: 11, padding: '3px 8px', borderRadius: 6, border: `1px solid var(--ai-${provider})`, background: `var(--ai-${provider}-subtle)`, color: `var(--ai-${provider})`, fontWeight: 700, outline: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}
              >
                {{ openai: 'OpenAI', anthropic: 'Anthropic', gemini: 'Gemini', ollama: 'Ollama' }[provider]}
                <ChevronDown size={10} />
              </button>
              {providerMenuOpen && (
                <div style={{ position: 'absolute', top: 'calc(100% + 4px)', left: 0, background: 'var(--bg-elevated)', border: '1px solid var(--border-default)', borderRadius: 8, boxShadow: 'var(--shadow-md)', zIndex: 200, minWidth: 160, overflow: 'hidden' }}>
                  {(['openai', 'anthropic', 'gemini', 'ollama'] as const).map(p => {
                    const label = { openai: 'OpenAI', anthropic: 'Anthropic', gemini: 'Gemini', ollama: 'Ollama' }[p];
                    const hasKey = credits ? credits.has_own_key[p] : true;
                    const isSelected = provider === p;
                    return (
                      <button
                        key={p}
                        disabled={!hasKey}
                        onClick={() => { setProvider(p); setProviderMenuOpen(false); }}
                        style={{ width: '100%', textAlign: 'left', padding: '8px 12px', background: isSelected ? 'var(--color-primary-subtle)' : 'transparent', color: !hasKey ? 'var(--text-muted)' : isSelected ? 'var(--color-primary)' : 'var(--text-primary)', border: 'none', cursor: hasKey ? 'pointer' : 'not-allowed', fontSize: 12, fontWeight: isSelected ? 600 : 400, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}
                      >
                        <span>{label}</span>
                        {!hasKey && <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{zh ? '未設定' : 'No Key'}</span>}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
          <div style={{ width: 1, height: 16, background: 'var(--border-default)' }} />
          <select value={selectedModel} onChange={e => setSelectedModel(e.target.value)} className="model-select" style={{ fontSize: 11, padding: '3px 6px', borderRadius: 6, border: '1px solid var(--border-default)', background: 'var(--bg-surface)', color: 'var(--text-secondary)', flex: 1, minWidth: 100, outline: 'none', cursor: 'pointer' }}>
            {models.map(m => <option key={m.id} value={m.id}>{m.display_name}</option>)}
            {models.length === 0 && <option value="">{modelsLoading ? '載入中…' : '無可用模型（請設定有效金鑰）'}</option>}
          </select>
        </div>

        {allowEdits && (
          <div style={{ padding: '8px 16px', background: 'var(--color-primary-subtle)', borderBottom: '1px solid var(--border-default)', fontSize: 12, color: 'var(--color-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
            <PlusCircle size={12} />
            {zh ? 'AI 提案模式：AI 可能在回答後建議新增或修改節點，可在對話中直接接受或拒絕。' : 'Proposal mode: AI may suggest node additions or edits. Accept or reject inline.'}
          </div>
        )}

        {/* Load older messages */}
        {hasOlderMessages && (
          <div style={{ textAlign: 'center', padding: '6px 0', borderBottom: '1px solid var(--border-subtle)' }}>
            <Button variant="ghost" size="sm" onClick={loadOlderMessages} disabled={loadingOlder} style={{ fontSize: 11, gap: 4 }}>
              <ChevronUp size={12} />
              {loadingOlder ? (zh ? '載入中…' : 'Loading…') : (zh ? '載入更早的訊息' : 'Load earlier messages')}
            </Button>
          </div>
        )}

        {/* Messages List */}
        <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: fullPage ? '24px 20px' : '20px', display: 'flex', flexDirection: 'column', gap: 24, alignItems: fullPage ? 'center' : undefined }}>
          {messages.length === 0 && (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', textAlign: 'center', padding: 40, width: fullPage ? '100%' : undefined, maxWidth: fullPage ? 800 : undefined }}>
              <Brain size={48} style={{ opacity: 0.2, marginBottom: 16 }} />
              <p style={{ fontSize: 14 }}>
                {zh ? '詢問關於當前知識庫的問題，或啟用「允許提案」讓 AI 協助優化圖譜。' : 'Ask about your KB, or enable proposals to let AI suggest graph improvements.'}
              </p>
            </div>
          )}
          {messages.map((m, msgIdx) => (
            <div key={msgIdx} style={{ display: 'flex', gap: 12, flexDirection: m.role === 'user' ? 'row-reverse' : 'row', width: fullPage ? '100%' : undefined, maxWidth: fullPage ? 800 : undefined }}>
              <div style={{ width: 32, height: 32, borderRadius: 16, flexShrink: 0, background: m.role === 'user' ? 'var(--border-default)' : 'var(--color-primary-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {m.role === 'user' ? <User size={16} /> : <Sparkles size={16} style={{ color: 'var(--color-primary)' }} />}
              </div>
              <div style={{ maxWidth: '85%', minWidth: 0 }}>
                <div style={{ padding: '10px 14px', borderRadius: 12, fontSize: 13, lineHeight: 1.5, background: m.role === 'user' ? 'var(--color-primary)' : 'var(--bg-base)', color: m.role === 'user' ? 'white' : 'var(--text-primary)', border: m.role === 'assistant' ? '1px solid var(--border-default)' : 'none', wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                  {m.role === 'assistant' && m.content === '' && loading && msgIdx === messages.length - 1
                    ? <TypingDots />
                    : <div className={m.role === 'assistant' ? 'markdown-body' : undefined}><ReactMarkdown>{m.content}</ReactMarkdown></div>}
                  {m.spokenSummary && (
                    <div style={{ marginTop: 10, padding: '8px 10px', borderRadius: 8, background: 'var(--color-primary-subtle)', border: '1px solid var(--color-primary)', fontSize: 12, lineHeight: 1.5, color: 'var(--text-secondary)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontWeight: 600, color: 'var(--color-primary)', marginBottom: 4 }}>
                        <Volume2 size={13} /> {zh ? '語音摘要' : 'Spoken summary'}
                      </div>
                      {m.spokenSummary}
                    </div>
                  )}
                  {m.response?.proposals && m.response.proposals.length > 0 && (
                    <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
                      <div style={{ fontSize: 12, fontWeight: 600, opacity: 0.8, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <PlusCircle size={14} /> {zh ? 'AI 提案' : 'AI Proposals'}
                      </div>
                      {m.response.proposals.map((p, propIdx) => {
                        const key = `${msgIdx}:${propIdx}`;
                        return <ProposalCard key={propIdx} proposal={p} zh={zh} status={proposalStates[key]?.status ?? 'pending'} onAccept={() => handleAcceptProposal(msgIdx, propIdx, p)} onReject={() => handleRejectProposal(msgIdx, propIdx, p)} />;
                      })}
                    </div>
                  )}
                </div>
                {m.response?.source_nodes && m.response.source_nodes.length > 0 && (() => {
                  const nodes = m.response.source_nodes;
                  const COLLAPSED_LIMIT = 3;
                  const isExpanded = !!expandedNodes[msgIdx];
                  const visible = isExpanded ? nodes : nodes.slice(0, COLLAPSED_LIMIT);
                  const overflow = nodes.length - COLLAPSED_LIMIT;
                  return (
                    <div style={{ marginTop: 8, display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                      {visible.map((sn, j) => (
                        <div
                          key={j}
                          onClick={() => sn.id && (window as any).mt_focus_node?.(sn.id, true)}
                          title={sn.id ? (zh ? '定位節點並開啟詳情' : 'Focus node & open detail') : undefined}
                          style={{ fontSize: 11, padding: '2px 8px', background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: 4, color: 'var(--text-muted)', cursor: sn.id ? 'pointer' : 'default', transition: 'border-color 0.15s, color 0.15s' }}
                          onMouseEnter={e => { if (sn.id) { (e.currentTarget as HTMLElement).style.borderColor = 'var(--color-primary)'; (e.currentTarget as HTMLElement).style.color = 'var(--color-primary)'; } }}
                          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-subtle)'; (e.currentTarget as HTMLElement).style.color = 'var(--text-muted)'; }}
                        >
                          {sn.title}
                        </div>
                      ))}
                      {overflow > 0 && !isExpanded && (
                        <button
                          onClick={() => setExpandedNodes(prev => ({ ...prev, [msgIdx]: true }))}
                          style={{ fontSize: 11, padding: '2px 8px', background: 'transparent', border: '1px dashed var(--border-default)', borderRadius: 4, color: 'var(--color-primary)', cursor: 'pointer' }}
                        >
                          +{overflow} {zh ? '更多' : 'more'}
                        </button>
                      )}
                      {isExpanded && overflow > 0 && (
                        <button
                          onClick={() => setExpandedNodes(prev => ({ ...prev, [msgIdx]: false }))}
                          style={{ fontSize: 11, padding: '2px 8px', background: 'transparent', border: '1px dashed var(--border-default)', borderRadius: 4, color: 'var(--text-muted)', cursor: 'pointer' }}
                        >
                          {zh ? '收合' : 'collapse'}
                        </button>
                      )}
                    </div>
                  );
                })()}
                {m.role === 'assistant' && m.response !== undefined && (m.response.source_nodes?.length ?? -1) === 0 && (
                  <div style={{ marginTop: 8, padding: '6px 10px', borderRadius: 6, background: 'var(--color-warning-subtle, #fef3c7)', border: '1px solid var(--color-warning, #f59e0b)', fontSize: 11, color: 'var(--color-warning, #92400e)', display: 'flex', alignItems: 'flex-start', gap: 6 }}>
                    <AlertCircle size={12} style={{ flexShrink: 0, marginTop: 1 }} />
                    <span>{zh ? '未找到相關節點，回答可能不夠準確。請確認節點已建立，或前往知識庫設定執行「重新嵌入所有節點」。' : 'No matching nodes found — answer may be inaccurate. Add more nodes or run "Re-embed All" in workspace settings.'}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Input Area */}
        <div style={{ padding: fullPage ? '16px 0 24px' : '16px 20px', borderTop: '1px solid var(--border-default)', background: 'var(--bg-surface)', display: 'flex', flexDirection: 'column', alignItems: fullPage ? 'center' : undefined }}>
          {credits && !credits.has_own_key[provider] && (
            <div style={{ marginBottom: 12, padding: '12px', borderRadius: 8, background: 'var(--color-error-subtle)', border: '1px solid var(--color-error)', fontSize: 12, color: 'var(--color-error)', display: 'flex', alignItems: 'center', gap: 8 }}>
              <AlertCircle size={14} />
              <b>{zh ? `您尚未設定 ${provider.toUpperCase()} 的 API Key。` : `No API key configured for ${provider.toUpperCase()}.`}</b>
              <button onClick={() => alert(zh ? '請前往「系統設定」加入 Key' : 'Please go to System Settings to add your key')} style={{ marginLeft: 'auto', fontWeight: 700, background: 'none', border: 'none', color: 'var(--color-error)', cursor: 'pointer', textDecoration: 'underline' }}>
                {zh ? '去設定' : 'Add Key'}
              </button>
            </div>
          )}

          {isColdSession && (
            <div style={{ marginBottom: 10, padding: '8px 12px', borderRadius: 8, background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', fontSize: 12, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Lock size={13} />
              {zh ? '此對話已封存（超過 7 天），無法繼續發話。' : 'This conversation is archived (>7 days). Read-only.'}
              <Button variant="ghost" size="sm" onClick={startNewSession} style={{ marginLeft: 'auto', fontSize: 11 }}>
                {zh ? '開新對話' : 'New conversation'}
              </Button>
            </div>
          )}

          {voiceModeActive && (
            <div style={{ marginBottom: 10, display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', background: 'var(--bg-base)', borderRadius: 12, border: '1px solid var(--border-subtle)' }}>
              {voiceKeys.stt && (
                <button
                  onClick={handleToggleMic}
                  disabled={transcribing}
                  title={micOn ? (zh ? '結束本段語音' : 'End this segment') : (zh ? '開始說話' : 'Start talking')}
                  style={{
                    width: 36, height: 36, borderRadius: 18, border: 'none', flexShrink: 0,
                    background: micOn ? 'var(--color-error, #ef4444)' : 'var(--color-primary)',
                    color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    cursor: transcribing ? 'default' : 'pointer', opacity: transcribing ? 0.6 : 1,
                  }}
                >
                  {micOn ? <MicOff size={16} /> : <Mic size={16} />}
                </button>
              )}
              <div style={{ flex: 1, fontSize: 12, color: 'var(--text-muted)' }}>
                {transcribing
                  ? (zh ? '辨識中…' : 'Transcribing…')
                  : isSpeaking
                    ? (zh ? '模型說話中…' : 'Assistant speaking…')
                    : micOn
                      ? (zh ? '聆聽中，再次點擊結束本段' : 'Listening — click again to end')
                      : (zh ? '點擊麥克風開始說話' : 'Click the mic to talk')}
                {voiceQueueCount > 0 && (zh ? `（已佇列 ${voiceQueueCount} 段）` : ` (${voiceQueueCount} queued)`)}
              </div>
              {isSpeaking && (
                <button
                  onClick={handleStopSpeaking}
                  title={zh ? '打斷模型語音' : 'Interrupt speech'}
                  style={{ width: 32, height: 32, borderRadius: 16, border: 'none', background: 'var(--color-error, #ef4444)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', flexShrink: 0 }}
                >
                  <Square size={13} />
                </button>
              )}
            </div>
          )}

          {queue.length > 0 && (
            <div style={{ marginBottom: 8, display: 'flex', flexDirection: 'column', gap: 4 }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', paddingLeft: 4 }}>{zh ? `待送佇列 (${queue.length})` : `Queued (${queue.length})`}</div>
              {queue.map((q, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 10px', background: 'var(--bg-base)', borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
                  <span style={{ flex: 1, fontSize: 12, color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{q}</span>
                  <button onClick={() => setQueue(prev => prev.filter((_, j) => j !== i))} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, color: 'var(--text-muted)', display: 'flex' }}>
                    <X size={12} />
                  </button>
                </div>
              ))}
            </div>
          )}

          <div style={{ display: 'flex', gap: 10, background: 'var(--bg-app)', padding: '8px 12px', borderRadius: 24, border: '1px solid var(--border-default)', opacity: isColdSession ? 0.5 : 1, width: fullPage ? '100%' : undefined, maxWidth: fullPage ? 800 : undefined }}>
            <textarea
              style={{ flex: 1, background: 'none', border: 'none', outline: 'none', color: 'var(--text-default)', fontSize: 14, paddingLeft: 8, resize: 'none', paddingTop: 6, minHeight: 24, maxHeight: 160, fontFamily: 'inherit', lineHeight: 1.5 }}
              rows={Math.min(5, input.split('\n').length)}
              placeholder={isColdSession ? (zh ? '此對話已封存' : 'Conversation archived') : (zh ? '輸入訊息… (連按兩次 Enter 或 Ctrl+Enter 送出)' : 'Type a message… (double-Enter or Ctrl+Enter to send)')}
              value={input}
              disabled={isColdSession}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => {
                if (isColdSession) return;
                if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
                  const now = Date.now();
                  if (now - lastEnterRef.current < 400) {
                    e.preventDefault();
                    const msg = input.replace(/\n+$/, '');
                    const canSend = !credits || credits.has_own_key[provider];
                    if (msg.trim() && canSend) {
                      setInput('');
                      if (loading) setQueue(prev => [...prev, msg]);
                      else handleSend(msg);
                    }
                    lastEnterRef.current = 0;
                  } else {
                    lastEnterRef.current = now;
                  }
                  return;
                }
                if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                  e.preventDefault();
                  const canSend = !credits || credits.has_own_key[provider];
                  if (input.trim() && canSend) {
                    if (loading) { setQueue(prev => [...prev, input]); setInput(''); }
                    else handleSend();
                  }
                }
              }}
            />
            {loading && (
              <button onClick={handleAbort} style={{ width: 32, height: 32, borderRadius: 16, border: 'none', background: 'var(--color-error, #ef4444)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', flexShrink: 0 }}>
                <Square size={14} />
              </button>
            )}
            <button
              onClick={() => {
                if (isColdSession) return;
                const canSend = !credits || credits.has_own_key[provider];
                if (!input.trim() || !canSend) return;
                if (loading) { setQueue(prev => [...prev, input]); setInput(''); } else handleSend();
              }}
              disabled={isColdSession || !input.trim() || (credits ? !credits.has_own_key[provider] : false)}
              style={{ width: 32, height: 32, borderRadius: 16, border: 'none', background: !isColdSession && input.trim() && (!credits || credits.has_own_key[provider]) ? (loading ? 'var(--border-default)' : 'var(--color-primary)') : 'var(--border-default)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', flexShrink: 0 }}
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ProposalCard({ proposal, zh, status, onAccept, onReject }: { proposal: ProposedChange; zh: boolean; status: 'pending' | 'accepted' | 'rejected'; onAccept: () => void; onReject: () => void }) {
  const isDone = status !== 'pending';
  return (
    <Card variant="surface" padding="sm" style={{ background: isDone ? 'var(--bg-app)' : 'var(--bg-surface)', border: `1px solid ${status === 'accepted' ? 'var(--color-success)' : status === 'rejected' ? 'var(--color-error)' : 'var(--border-default)'}`, opacity: isDone ? 0.7 : 1, transition: 'all 0.2s' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-primary)', background: 'var(--color-primary-subtle)', padding: '2px 6px', borderRadius: 4 }}>{proposal.operation}</span>
        {isDone && <span style={{ fontSize: 11, fontWeight: 600, color: status === 'accepted' ? 'var(--color-success)' : 'var(--color-error)' }}>{status === 'accepted' ? (zh ? '✓ 已接受' : '✓ Accepted') : (zh ? '✗ 已拒絕' : '✗ Rejected')}</span>}
      </div>
      <div style={{ fontSize: 13, marginBottom: isDone ? 0 : 10, fontWeight: 500 }}>{proposal.reason}</div>
      {!isDone && (
        <div style={{ display: 'flex', gap: 8 }}>
          <Button variant="primary" size="sm" style={{ flex: 1, fontSize: 12, height: 28 }} onClick={onAccept} leftIcon={<Check size={12} />}>{zh ? '接受' : 'Accept'}</Button>
          <Button variant="secondary" size="sm" style={{ flex: 1, fontSize: 12, height: 28 }} onClick={onReject} leftIcon={<X size={12} />}>{zh ? '拒絕' : 'Reject'}</Button>
          {(proposal as any).review_queue_id && (
            <Button variant="secondary" size="sm" style={{ fontSize: 12, height: 28, padding: '0 10px' }} onClick={() => window.open('/review', '_blank')} leftIcon={<ExternalLink size={12} />} />
          )}
        </div>
      )}
    </Card>
  );
}

function TypingDots() {
  return (
    <span style={{ display: 'inline-flex', gap: 4, alignItems: 'center', height: 20 }}>
      {[0, 1, 2].map(i => (
        <span key={i} style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--text-muted)', display: 'inline-block', animation: 'typing-dot 1.2s ease-in-out infinite', animationDelay: `${i * 0.2}s` }} />
      ))}
      <style>{`
        @keyframes typing-dot {
          0%, 60%, 100% { opacity: 0.25; transform: translateY(0); }
          30% { opacity: 1; transform: translateY(-3px); }
        }
      `}</style>
    </span>
  );
}
