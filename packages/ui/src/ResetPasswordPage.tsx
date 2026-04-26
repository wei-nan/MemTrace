import { useState } from 'react';
import { auth } from './api';

interface Props {
  token: string;
  onSuccess: () => void;
}

export default function ResetPasswordPage({ token, onSuccess }: Props) {
  const [password, setPassword]               = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading]                 = useState(false);
  const [error, setError]                     = useState('');
  const [success, setSuccess]                 = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    if (password.length < 8 || password.length > 128) {
      setError('Password must be between 8 and 128 characters');
      return;
    }
    if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(password)) {
      setError('Password must contain at least one uppercase letter, one lowercase letter, and one number');
      return;
    }

    setLoading(true);
    setError('');
    try {
      await auth.resetPassword(token, password);
      setSuccess(true);
      setTimeout(onSuccess, 3000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: 'var(--bg-base)' }}>
        <div className="glass-panel" style={{ padding: 40, minWidth: 380, maxWidth: 440, textAlign: 'center' }}>
          <h2 style={{ color: 'var(--color-error)', marginBottom: 8 }}>Invalid Link</h2>
          <p style={{ color: 'var(--text-muted)' }}>The reset link is missing or invalid. Please request a new one.</p>
          <button className="btn-secondary" onClick={onSuccess} style={{ width: '100%', marginTop: 20 }}>
            Back to Sign In
          </button>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: 'var(--bg-base)' }}>
        <div className="glass-panel" style={{ padding: 40, minWidth: 380, maxWidth: 440, textAlign: 'center' }}>
          <div style={{ fontSize: 40, marginBottom: 16 }}>✅</div>
          <h2 style={{ marginBottom: 8, color: 'var(--color-success)' }}>Password Updated</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>
            Your password has been reset successfully. Redirecting to login...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: 'var(--bg-base)' }}>
      <div className="glass-panel" style={{ padding: 40, minWidth: 380, maxWidth: 440 }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--color-primary)', letterSpacing: '-0.5px', marginBottom: 4 }}>
            MemTrace
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
            Set your new password
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <label style={{ display: 'block', marginBottom: 14 }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>New Password</span>
            <input 
              className="mt-input" 
              type="password" 
              value={password}
              onChange={e => setPassword(e.target.value)} 
              required 
              autoFocus
            />
          </label>

          <label style={{ display: 'block', marginBottom: 20 }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Confirm New Password</span>
            <input 
              className="mt-input" 
              type="password" 
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)} 
              required 
            />
          </label>

          {error && (
            <p style={{ color: 'var(--color-error)', fontSize: 13, marginBottom: 12 }}>{error}</p>
          )}

          <button className="btn-primary" type="submit" disabled={loading}
            style={{ width: '100%', padding: '12px 0', fontSize: 15 }}>
            {loading ? 'Updating…' : 'Reset Password'}
          </button>
        </form>
      </div>
    </div>
  );
}
