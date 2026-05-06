import { useState } from 'react';
import { auth } from './api';

interface Props {
  onAuthenticated: () => void;
}

type Mode = 'login' | 'register' | 'forgot' | 'sent';

export default function AuthPage({ onAuthenticated: _onAuthenticated }: Props) {
  const [mode, setMode] = useState<Mode>('login');

  const [email, setEmail]             = useState('');
  const [purposeNote, setPurposeNote] = useState('');
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState('');
  const [message, setMessage]         = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true); setError(''); setMessage('');
    try {
      if (mode === 'forgot') {
        await auth.forgotPassword(email);
        setMode('sent');
        setMessage('If an account exists, a reset link has been sent.');
        return;
      }
      
      const resp = await auth.register({ email, purpose_note: purposeNote });
      setMode('sent');
      setMessage(resp.message || 'Check your email for the magic link!');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const switchMode = (m: Mode) => { setMode(m); setError(''); setMessage(''); };

  if (mode === 'sent') {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: 'var(--bg-base)' }}>
        <div className="glass-panel" style={{ padding: 40, minWidth: 380, maxWidth: 440, textAlign: 'center' }}>
          <div style={{ fontSize: 40, marginBottom: 16 }}>📧</div>
          <h2 style={{ marginBottom: 8, color: 'var(--text-primary)' }}>Check your email</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 24 }}>
            {message || `A link has been sent to ${email}. Please check your inbox (and spam folder).`}
          </p>
          <button className="btn-secondary" onClick={() => switchMode('login')} style={{ width: '100%' }}>
            Back to Sign In
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: 'var(--bg-base)' }}>
      <div className="glass-panel" style={{ padding: 40, minWidth: 380, maxWidth: 440 }}>

        {/* Title */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--color-primary)', letterSpacing: '-0.5px', marginBottom: 4 }}>
            MemTrace
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
            {mode === 'forgot' ? 'Reset your password' : 'Knowledge through connection'}
          </p>
        </div>

        {/* Mode tabs (login / register only) */}
        {(mode === 'login' || mode === 'register') && (
          <div style={{ display: 'flex', gap: 0, marginBottom: 24, border: '1px solid var(--border-default)', borderRadius: 8, overflow: 'hidden' }}>
            {(['login', 'register'] as const).map(m => (
              <button key={m} onClick={() => switchMode(m)}
                style={{
                  flex: 1, padding: '10px 0', border: 'none', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: mode === m ? 'var(--color-primary)' : 'transparent',
                  color: mode === m ? 'var(--text-on-primary)' : 'var(--text-secondary)',
                  fontWeight: mode === m ? 600 : 400, fontSize: 14,
                  transition: 'all 0.2s',
                }}>
                {m === 'login' ? 'Sign In' : 'Register'}
              </button>
            ))}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <label style={{ display: 'block', marginBottom: 14 }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Email</span>
            <input className="mt-input" type="email" value={email}
              placeholder="you@company.com"
              onChange={e => setEmail(e.target.value)} required />
          </label>

          {mode === 'register' && (
            <label style={{ display: 'block', marginBottom: 20 }}>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Purpose (Optional)</span>
              <textarea 
                className="mt-input" 
                value={purposeNote}
                placeholder="Why do you want to join?"
                style={{ height: 80, resize: 'none', padding: '10px 12px' }}
                onChange={e => setPurposeNote(e.target.value)} 
              />
            </label>
          )}

          {error && (
            <p style={{ color: 'var(--color-error)', fontSize: 13, marginBottom: 12 }}>{error}</p>
          )}

          <button className="btn-primary" type="submit" disabled={loading}
            style={{ width: '100%', padding: '12px 0', fontSize: 15 }}>
            {loading ? '…'
              : mode === 'login' ? 'Send Login Link'
              : mode === 'register' ? 'Request Access'
              : 'Send Reset Link'}
          </button>
        </form>

        {/* Footer links */}
        <div style={{ textAlign: 'center', marginTop: 16, fontSize: 13 }}>
          {mode === 'login' && (
            <a href="#" onClick={e => { e.preventDefault(); switchMode('forgot'); }}
              style={{ color: 'var(--color-primary)' }}>
              Forgot password?
            </a>
          )}
          {mode === 'forgot' && (
            <a href="#" onClick={e => { e.preventDefault(); switchMode('login'); }}
              style={{ color: 'var(--text-muted)' }}>
              ← Back to Sign In
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
