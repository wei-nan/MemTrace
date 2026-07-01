import { BASE, authHeaders, writeHeaders } from './client';

export interface VoiceKey {
  id: string;
  purpose: 'stt' | 'tts';
  provider: string;
  credential_type: 'api_key' | 'service_account_json';
  key_hint: string;
  created_at: string;
  last_used_at: string | null;
}

export interface VoiceKeyCreate {
  purpose: 'stt' | 'tts';
  provider: string;
  credential: string;
  credential_type?: 'api_key' | 'service_account_json';
}

async function parseErrorDetail(res: Response): Promise<string> {
  try {
    const err = await res.json();
    return err.detail ?? err.message ?? res.statusText;
  } catch {
    return res.statusText;
  }
}

export const voice = {
  listKeys: async (): Promise<VoiceKey[]> => {
    const res = await fetch(`${BASE}/ai/voice-keys`, {
      method: 'GET',
      credentials: 'include',
      headers: { ...authHeaders() },
    });
    if (!res.ok) throw new Error(await parseErrorDetail(res));
    return res.json();
  },

  upsertKey: async (data: VoiceKeyCreate): Promise<VoiceKey> => {
    const res = await fetch(`${BASE}/ai/voice-keys`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...authHeaders(), ...writeHeaders() },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await parseErrorDetail(res));
    return res.json();
  },

  deleteKey: async (purpose: 'stt' | 'tts'): Promise<void> => {
    const res = await fetch(`${BASE}/ai/voice-keys/${purpose}`, {
      method: 'DELETE',
      credentials: 'include',
      headers: { ...authHeaders(), ...writeHeaders() },
    });
    if (!res.ok) throw new Error(await parseErrorDetail(res));
  },

  /** Send a recorded audio segment to the backend for transcription. */
  speechToText: async (blob: Blob, language: string): Promise<string> => {
    const form = new FormData();
    form.append('file', blob, 'audio.webm');
    const res = await fetch(`${BASE}/ai/speech/stt?language=${encodeURIComponent(language)}`, {
      method: 'POST',
      credentials: 'include',
      headers: { ...authHeaders(), ...writeHeaders() },
      body: form,
    });
    if (!res.ok) throw new Error(await parseErrorDetail(res));
    const data = await res.json();
    return data.transcript as string;
  },

  /** Synthesize speech for text; returns a playable object URL. */
  textToSpeech: async (text: string, language: string): Promise<string> => {
    const res = await fetch(`${BASE}/ai/speech/tts`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...authHeaders(), ...writeHeaders() },
      body: JSON.stringify({ text, language }),
    });
    if (!res.ok) throw new Error(await parseErrorDetail(res));
    const audioBlob = await res.blob();
    return URL.createObjectURL(audioBlob);
  },
};
