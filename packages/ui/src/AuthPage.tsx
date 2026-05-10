import { useState } from 'react';
import { auth } from './api';
import { Button, Input } from './components/ui';

interface Props {
  onAuthenticated: () => void;
}

type Mode = 'login' | 'register' | 'forgot' | 'sent';

export default function AuthPage({ onAuthenticated: _onAuthenticated }: Props) {
  const [mode, setMode] = useState<Mode>('login');

  const [email, setEmail]             = useState('');
  const [password, setPassword]       = useState('');
  const [purposeNote, setPurposeNote] = useState('');
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState('');
  const [message, setMessage]         = useState('');
  const [usePassword, setUsePassword] = useState(true);

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
      
      if (mode === 'login' && usePassword && password) {
        const resp = await auth.login({ email, password });
        localStorage.setItem('mt_token', resp.access_token);
        window.location.reload(); 
        return;
      }

      const resp = await auth.register({ email, purpose_note: mode === 'register' ? purposeNote : undefined });
      setMode('sent');
      setMessage(resp.message || 'Check your email for the magic link!');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const switchMode = (m: Mode) => { setMode(m); setError(''); setMessage(''); setPassword(''); };

  const bgStyles: React.CSSProperties = {
    position: 'fixed',
    inset: 0,
    background: 'radial-gradient(circle at 20% 20%, #1a1f2e 0%, #0b0d11 100%)',
    zIndex: -1,
    overflow: 'hidden',
  };

  const blobStyles: React.CSSProperties = {
    position: 'absolute',
    width: '60vw',
    height: '60vw',
    background: 'radial-gradient(circle, rgba(45, 212, 191, 0.05) 0%, transparent 70%)',
    borderRadius: '50%',
    filter: 'blur(80px)',
    animation: 'auth-blob-float 20s infinite alternate cubic-bezier(0.45, 0.05, 0.55, 0.95)',
  };

  if (mode === 'sent') {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', position: 'relative' }}>
        <div style={bgStyles}>
          <div style={{ ...blobStyles, top: '-10%', left: '-10%' }} />
          <div style={{ ...blobStyles, bottom: '-10%', right: '-10%', background: 'radial-gradient(circle, rgba(129, 140, 248, 0.05) 0%, transparent 70%)' }} />
        </div>
        <div className="glass-panel" style={{ padding: 48, minWidth: 400, maxWidth: 440, textAlign: 'center', backdropFilter: 'blur(20px)', border: '1px solid var(--glass-border)', boxShadow: 'var(--glass-shadow)' }}>
          <div style={{ fontSize: 48, marginBottom: 24, animation: 'mt-scale-in 0.5s ease-out' }}>✉️</div>
          <h2 style={{ marginBottom: 12, color: 'var(--text-primary)', fontSize: 24 }}>Check your inbox</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: 15, marginBottom: 32, lineHeight: 1.6 }}>
            {message || `We've sent a link to ${email}. Please check your email to continue.`}
          </p>
          <Button variant="primary" onClick={() => switchMode('login')} style={{ width: '100%', padding: '14px' }}>
            Back to Sign In
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', position: 'relative', overflow: 'hidden' }}>
      <style>{`
        @keyframes auth-blob-float {
          from { transform: translate(0, 0) scale(1); }
          to { transform: translate(5%, 10%) scale(1.1); }
        }
      `}</style>
      
      <div style={bgStyles}>
        <div style={{ ...blobStyles, top: '-15%', left: '-10%', animationDelay: '0s' }} />
        <div style={{ ...blobStyles, bottom: '-15%', right: '-10%', animationDelay: '-10s', background: 'radial-gradient(circle, rgba(129, 140, 248, 0.05) 0%, transparent 70%)' }} />
      </div>

      <div className="glass-panel" style={{ 
        padding: '48px', 
        minWidth: '400px', 
        maxWidth: '440px', 
        backdropFilter: 'blur(24px)', 
        background: 'rgba(21, 24, 30, 0.7)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
        animation: 'mt-scale-in 0.6s cubic-bezier(0.16, 1, 0.3, 1)'
      }}>

        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <div style={{ 
            fontSize: 32, 
            fontWeight: 800, 
            background: 'linear-gradient(135deg, #2DD4BF 0%, #818CF8 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            letterSpacing: '-1px',
            marginBottom: 8
          }}>
            MemTrace
          </div>
          <p style={{ fontSize: 14, color: 'var(--text-secondary)', margin: 0, fontWeight: 400 }}>
            {mode === 'forgot' ? 'Secure password recovery' : 'The intelligence layer for your ideas'}
          </p>
        </div>

        {(mode === 'login' || mode === 'register') && (
          <div style={{ 
            display: 'flex', 
            background: 'rgba(0,0,0,0.2)', 
            padding: '4px',
            borderRadius: '12px',
            marginBottom: 32,
            border: '1px solid var(--border-subtle)'
          }}>
            {(['login', 'register'] as const).map(m => (
              <Button key={m} variant="ghost" onClick={() => switchMode(m)}
                style={{
                  flex: 1, padding: '10px 0',
                  borderRadius: '8px',
                  background: mode === m ? 'rgba(45, 212, 191, 0.15)' : 'transparent',
                  color: mode === m ? 'var(--color-primary)' : 'var(--text-muted)',
                  fontWeight: mode === m ? 600 : 500, fontSize: 13,
                }}>
                {m === 'login' ? 'Sign In' : 'Register'}
              </Button>
            ))}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <Input
            label="Email"
            type="email"
            value={email}
            placeholder="name@company.com"
            onChange={e => setEmail(e.target.value)}
            required
          />

          {mode === 'login' && usePassword && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Password</span>
                <Button variant="link" onClick={() => switchMode('forgot')} style={{ fontSize: 12 }}>
                  Forgot?
                </Button>
              </div>
              <Input
                type="password"
                value={password}
                placeholder="••••••••"
                onChange={e => setPassword(e.target.value)}
                required={usePassword}
              />
            </div>
          )}

          {mode === 'register' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Purpose of Join</span>
              <textarea 
                className="mt-input" 
                value={purposeNote}
                placeholder="Help us understand your use case..."
                style={{ height: 100, resize: 'none', padding: '14px', borderRadius: '12px', fontSize: 15 }}
                onChange={e => setPurposeNote(e.target.value)} 
              />
            </div>
          )}

          {error && (
            <div style={{ 
              padding: '12px 16px', 
              background: 'rgba(248, 113, 113, 0.1)', 
              border: '1px solid rgba(248, 113, 113, 0.2)',
              borderRadius: '10px',
              color: '#F87171',
              fontSize: 13,
              fontWeight: 500
            }}>
              {error}
            </div>
          )}

          <Button 
            variant="primary" 
            type="submit" 
            loading={loading}
            style={{ 
              width: '100%', 
              padding: '16px', 
              fontSize: 16, 
              fontWeight: 600, 
              borderRadius: '12px',
              marginTop: 8,
              boxShadow: '0 10px 15px -3px var(--color-primary-subtle)',
              background: 'linear-gradient(135deg, #2DD4BF 0%, #14B8A6 100%)',
              color: '#0F172A'
            }}
          >
            {mode === 'login' ? (usePassword && password ? 'Sign In' : 'Send Magic Link')
              : mode === 'register' ? 'Create Account'
              : 'Reset Password'}
          </Button>

            <div style={{ textAlign: 'center', marginTop: 8 }}>
              <Button
                variant="ghost"
                onClick={() => { setUsePassword(!usePassword); setPassword(''); setError(''); }}
                style={{ color: 'var(--text-muted)', fontSize: 13 }}
              >
                {usePassword ? 'Sign in with magic link' : 'Sign in with password'}
              </Button>
            </div>
        </form>
      </div>
    </div>
  );
}
