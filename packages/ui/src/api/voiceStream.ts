// Live streaming STT client (spec mem_77b74b8a / D6).
//
// Captures mic audio as raw PCM16 via an AudioWorklet and streams it over a
// WebSocket to the backend, which relays to Deepgram and returns interim/final
// transcripts. Used only when the user's STT provider supports streaming; the
// batch path (voice.speechToText) remains the fallback for other providers.

export interface VoiceStreamHandlers {
  /** Called for every interim (partial) and final transcript segment. */
  onTranscript: (text: string, isFinal: boolean) => void;
  onError: (message: string) => void;
  /** Called once the session has fully torn down (socket closed). */
  onClose: () => void;
}

// Inline AudioWorklet: converts each Float32 frame to little-endian PCM16 and
// ships the raw buffer back to the main thread. Kept as a string so there is no
// separate static asset to serve/configure.
const PCM_WORKLET = `
class PCMProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0];
    if (input && input[0]) {
      const ch = input[0];
      const out = new Int16Array(ch.length);
      for (let i = 0; i < ch.length; i++) {
        const s = Math.max(-1, Math.min(1, ch[i]));
        out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
      }
      this.port.postMessage(out.buffer, [out.buffer]);
    }
    return true;
  }
}
registerProcessor('pcm-processor', PCMProcessor);
`;

function wsUrl(language: string, sampleRate: number): string {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const token = localStorage.getItem('mt_token') ?? '';
  const q = new URLSearchParams({
    language,
    sample_rate: String(sampleRate),
    token,
  });
  return `${proto}//${location.host}/api/v1/ai/speech/stt-stream?${q.toString()}`;
}

export class VoiceStreamSession {
  private ws?: WebSocket;
  private ctx?: AudioContext;
  private stream?: MediaStream;
  private source?: MediaStreamAudioSourceNode;
  private node?: AudioWorkletNode;
  private sink?: GainNode;
  private moduleUrl?: string;
  private stopping = false;
  private closed = false;
  private handlers: VoiceStreamHandlers;

  constructor(handlers: VoiceStreamHandlers) {
    this.handlers = handlers;
  }

  async start(language: string): Promise<void> {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1 } });
    // Request 16 kHz; browsers may ignore it, so we forward the ACTUAL rate to
    // the backend and let the upstream provider match on it.
    this.ctx = new AudioContext({ sampleRate: 16000 });
    const rate = this.ctx.sampleRate;

    const blob = new Blob([PCM_WORKLET], { type: 'application/javascript' });
    this.moduleUrl = URL.createObjectURL(blob);
    await this.ctx.audioWorklet.addModule(this.moduleUrl);

    this.ws = new WebSocket(wsUrl(language, rate));
    this.ws.binaryType = 'arraybuffer';
    this.ws.onmessage = (e) => {
      let msg: any;
      try { msg = JSON.parse(e.data); } catch { return; }
      if (msg.type === 'transcript' && msg.transcript) {
        this.handlers.onTranscript(msg.transcript, !!msg.is_final);
      } else if (msg.type === 'error') {
        this.handlers.onError(msg.detail ?? 'STT stream error');
      }
    };
    this.ws.onclose = () => this.teardown();
    this.ws.onerror = () => {
      if (!this.stopping) this.handlers.onError('Voice stream connection failed');
    };

    this.source = this.ctx.createMediaStreamSource(this.stream);
    this.node = new AudioWorkletNode(this.ctx, 'pcm-processor');
    this.node.port.onmessage = (e: MessageEvent) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) this.ws.send(e.data);
    };
    // Route through a muted gain node so the worklet is pulled by the graph
    // without echoing the mic back to the speakers.
    this.sink = this.ctx.createGain();
    this.sink.gain.value = 0;
    this.source.connect(this.node);
    this.node.connect(this.sink);
    this.sink.connect(this.ctx.destination);
  }

  /** Stop capture and ask the backend to flush final results, then close. */
  stop(): void {
    if (this.stopping) return;
    this.stopping = true;
    try {
      this.source?.disconnect();
      this.node?.disconnect();
      this.sink?.disconnect();
    } catch { /* already gone */ }
    this.stream?.getTracks().forEach((t) => t.stop());
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try { this.ws.send(JSON.stringify({ action: 'stop' })); } catch { /* noop */ }
      // Give the backend a moment to relay final transcripts; then force-close.
      setTimeout(() => { try { this.ws?.close(); } catch { /* noop */ } }, 2500);
    } else {
      this.teardown();
    }
  }

  private teardown(): void {
    if (this.closed) return;
    this.closed = true;
    try { this.ctx?.close(); } catch { /* noop */ }
    if (this.moduleUrl) URL.revokeObjectURL(this.moduleUrl);
    this.handlers.onClose();
  }
}
