import { useState } from 'react';
import { auth } from './api';

interface Props {
  onAuthenticated: () => void;
}

export default function AuthPage({ onAuthenticated }: Props) {
  const [mode, setMode] = useState<'login' | 'register'>('login');

  const [displayName, setDisplayName] = useState('');
  const [email, setEmail]             = useState('');
  const [password, setPassword]       = useState('');
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      let resp;
      if (mode === 'register') {
        resp = await auth.register({ display_name: displayName, email, password });
      } else {
        resp = await auth.login({ email, password });
      }
      localStorage.setItem('mt_token', resp.access_token);
      onAuthenticated();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGoogle = () => {
    window.location.href = '/auth/google';
  };

  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      minHeight: '100vh', background: 'var(--bg-main)',
    }}>
      <div className="glass-panel" style={{ padding: 40, minWidth: 380, maxWidth: 440 }}>
        {/* Logo / Title */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <h1 style={{ fontSize: 28, marginBottom: 4 }}>MemTrace</h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
            Knowledge through connection
          </p>
        </div>

        {/* Mode tabs */}
        <div style={{ display: 'flex', gap: 0, marginBottom: 24, border: '1px solid var(--border-color)', borderRadius: 8, overflow: 'hidden' }}>
          {(['login', 'register'] as const).map(m => (
            <button key={m} onClick={() => { setMode(m); setError(''); }}
              style={{
                flex: 1, padding: '10px 0', border: 'none', cursor: 'pointer',
                background: mode === m ? 'var(--accent-color)' : 'transparent',
                color: mode === m ? '#fff' : 'var(--text-muted)',
                fontWeight: mode === m ? 600 : 400, fontSize: 14,
              }}>
              {m === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          ))}
        </div>

        {/* Google OAuth */}
        <button onClick={handleGoogle}
          style={{
            width: '100%', padding: '11px 0', marginBottom: 20,
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
            background: '#fff', color: '#333', border: '1px solid #ddd',
            borderRadius: 8, cursor: 'pointer', fontWeight: 500, fontSize: 14,
          }}>
          <svg width="18" height="18" viewBox="0 0 48 48">
            <path fill="#4285F4" d="M45.12 24.5c0-1.56-.14-3.06-.4-4.5H24v8.51h11.84c-.51 2.75-2.06 5.08-4.39 6.64v5.52h7.11c4.16-3.83 6.56-9.47 6.56-16.17z"/>
            <path fill="#34A853" d="M24 46c5.94 0 10.92-1.97 14.56-5.33l-7.11-5.52c-1.97 1.32-4.49 2.1-7.45 2.1-5.73 0-10.58-3.87-12.31-9.07H4.34v5.7C7.96 41.07 15.4 46 24 46z"/>
            <path fill="#FBBC05" d="M11.69 28.18C11.25 26.86 11 25.45 11 24s.25-2.86.69-4.18v-5.7H4.34C2.85 17.09 2 20.45 2 24c0 3.55.85 6.91 2.34 9.88l7.35-5.7z"/>
            <path fill="#EA4335" d="M24 10.75c3.23 0 6.13 1.11 8.41 3.29l6.31-6.31C34.91 4.18 29.93 2 24 2 15.4 2 7.96 6.93 4.34 14.12l7.35 5.7c1.73-5.2 6.58-9.07 12.31-9.07z"/>
          </svg>
          Continue with Google
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
          <hr style={{ flex: 1, border: 'none', borderTop: '1px solid var(--border-color)' }} />
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>or</span>
          <hr style={{ flex: 1, border: 'none', borderTop: '1px solid var(--border-color)' }} />
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}>
          {mode === 'register' && (
            <label style={{ display: 'block', marginBottom: 14 }}>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Display Name</span>
              <input className="mt-input" type="text" value={displayName}
                onChange={e => setDisplayName(e.target.value)} required />
            </label>
          )}
          <label style={{ display: 'block', marginBottom: 14 }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Email</span>
            <input className="mt-input" type="email" value={email}
              onChange={e => setEmail(e.target.value)} required />
          </label>
          <label style={{ display: 'block', marginBottom: 20 }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Password</span>
            <input className="mt-input" type="password" value={password}
              onChange={e => setPassword(e.target.value)} required />
            {mode === 'register' && (
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                8–128 characters, at least one uppercase, lowercase, and digit.
              </span>
            )}
          </label>

          {error && (
            <p style={{ color: 'var(--error-color, #f87)', fontSize: 13, marginBottom: 12 }}>{error}</p>
          )}

          <button className="btn btn-primary" type="submit" disabled={loading}
            style={{ width: '100%', padding: '12px 0', fontSize: 15 }}>
            {loading ? '…' : mode === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>

        {mode === 'login' && (
          <p style={{ textAlign: 'center', marginTop: 16, fontSize: 13 }}>
            <a href="#" onClick={e => { e.preventDefault(); /* TODO: forgot password flow */ }}
              style={{ color: 'var(--accent-color)' }}>
              Forgot password?
            </a>
          </p>
        )}
      </div>
    </div>
  );
}
