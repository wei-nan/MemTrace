import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { auth } from './api';

export default function JoinInvitationPage() {
  const { token } = useParams<{ token: string }>();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setLoading(true); setError('');
    try {
      await auth.registerWithInvite(token, { email });
      setSuccess(true);
    } catch (err: any) {
      // S1-3b: If server returns 403 magic_link_unavailable, show explicit error
      const msg: string = err.message || '';
      if (msg.includes('magic_link_unavailable') || msg.includes('403')) {
        setError('目前系統設定不允許透過 Magic Link 加入，請聯繫管理員');
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: 'var(--bg-base)' }}>
        <div className="glass-panel" style={{ padding: 40, textAlign: 'center', maxWidth: 400 }}>
          <div style={{ fontSize: 40, marginBottom: 16 }}>✨</div>
          <h2 style={{ marginBottom: 8, color: 'var(--text-primary)' }}>Check your email</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>
            We've sent a magic link to <b>{email}</b>. Please check your inbox and click the link to join the workspace.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: 'var(--bg-base)' }}>
      <div className="glass-panel" style={{ padding: 40, minWidth: 380, maxWidth: 440 }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--color-primary)', letterSpacing: '-0.5px' }}>MemTrace</div>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 8 }}>You've been invited to join a workspace</p>
        </div>

        <form onSubmit={handleSubmit}>
          <label style={{ display: 'block', marginBottom: 20 }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Enter your email to accept the invitation</span>
            <input className="mt-input" type="email" value={email}
              placeholder="name@example.com"
              onChange={e => setEmail(e.target.value)} required />
          </label>

          {error && (
            <p style={{ color: 'var(--color-error)', fontSize: 13, marginBottom: 12 }}>{error}</p>
          )}

          <button className="btn-primary" type="submit" disabled={loading}
            style={{ width: '100%', padding: '12px 0', fontSize: 15 }}>
            {loading ? '…' : 'Continue'}
          </button>
        </form>
      </div>
    </div>
  );
}
