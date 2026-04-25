import { Component, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[ErrorBoundary] Caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', height: '100%', padding: 40,
          color: 'var(--text-muted)',
        }}>
          <div style={{
            background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
            borderRadius: 16, padding: '32px 40px', textAlign: 'center',
            maxWidth: 480, boxShadow: 'var(--shadow-lg)',
          }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
            <h3 style={{ margin: '0 0 8px', color: 'var(--text-primary)' }}>Something went wrong</h3>
            <p style={{ fontSize: 13, lineHeight: 1.6, marginBottom: 20 }}>
              {this.state.error?.message ?? 'An unexpected error occurred.'}
            </p>
            <button
              className="btn-primary"
              onClick={() => this.setState({ hasError: false, error: null })}
              style={{ padding: '8px 24px' }}
            >
              Try Again
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
