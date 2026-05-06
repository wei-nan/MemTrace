import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { auth } from './api';

export default function MagicLinkVerifyPage({ onAuthenticated }: { onAuthenticated: () => void }) {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<'verifying' | 'success' | 'error'>('verifying');
  const [error, setError] = useState('');

  useEffect(() => {
    const token = searchParams.get('token');
    if (!token) {
      setStatus('error');
      setError('Missing token');
      return;
    }

    auth.verifyMagicLink(token)
      .then(resp => {
        localStorage.setItem('mt_token', resp.access_token);
        setStatus('success');
        setTimeout(() => {
          onAuthenticated();
        }, 1500);
      })
      .catch(err => {
        setStatus('error');
        setError(err.message || 'Verification failed');
      });
  }, []);

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: 'var(--bg-base)' }}>
      <div className="glass-panel" style={{ padding: 40, minWidth: 380, maxWidth: 440, textAlign: 'center' }}>
        {status === 'verifying' && (
          <>
            <div className="loading-spinner" style={{ margin: '0 auto 24px' }} />
            <h2 style={{ color: 'var(--text-primary)' }}>Verifying...</h2>
            <p style={{ color: 'var(--text-muted)' }}>Please wait while we secure your session.</p>
          </>
        )}

        {status === 'success' && (
          <>
            <div style={{ fontSize: 48, marginBottom: 16 }}>🎉</div>
            <h2 style={{ color: 'var(--text-primary)' }}>Welcome back!</h2>
            <p style={{ color: 'var(--text-muted)' }}>Redirecting to your workspace...</p>
          </>
        )}

        {status === 'error' && (
          <>
            <div style={{ fontSize: 48, marginBottom: 16 }}>❌</div>
            <h2 style={{ color: 'var(--color-error)' }}>Link Invalid</h2>
            <p style={{ color: 'var(--text-muted)', marginBottom: 24 }}>{error}</p>
            <a href="/auth" className="btn-primary" style={{ display: 'block', textDecoration: 'none' }}>
              Back to Login
            </a>
          </>
        )}
      </div>
    </div>
  );
}
