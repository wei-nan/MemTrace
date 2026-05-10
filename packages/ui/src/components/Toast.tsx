/**
 * Toast.tsx — MemTrace non-blocking notification toasts
 *
 * Stacks in the top-right corner. Auto-dismisses after `duration` ms.
 * Supports manual close. Four variants: success / error / warning / info.
 */

import { useEffect, useRef, useState } from 'react';
import { CheckCircle, AlertTriangle, Info, X } from 'lucide-react';
import type { ModalVariant } from './ui';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ToastItem {
  id:       string;
  message:  string;
  variant?: Exclude<ModalVariant, 'danger'>;  // toast doesn't support danger
  duration?: number;  // ms, default 3500
}

// ── Variant config ────────────────────────────────────────────────────────────

const TOAST_CFG: Record<Exclude<ModalVariant, 'danger'>, {
  Icon:      typeof Info;
  iconColor: string;
  barColor:  string;
}> = {
  info: {
    Icon:      Info,
    iconColor: 'var(--color-info)',
    barColor:  'var(--color-info)',
  },
  success: {
    Icon:      CheckCircle,
    iconColor: 'var(--color-success)',
    barColor:  'var(--color-success)',
  },
  warning: {
    Icon:      AlertTriangle,
    iconColor: 'var(--color-warning)',
    barColor:  'var(--color-warning)',
  },
  error: {
    Icon:      AlertTriangle,
    iconColor: 'var(--color-error)',
    barColor:  'var(--color-error)',
  },
};

// ── Single Toast ──────────────────────────────────────────────────────────────

function ToastCard({
  item,
  onDismiss,
}: {
  item: ToastItem;
  onDismiss: (id: string) => void;
}) {
  const duration  = item.duration ?? 3500;
  const variant   = item.variant ?? 'info';
  const cfg       = TOAST_CFG[variant];
  const { Icon }  = cfg;
  const timerRef  = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [exiting, setExiting] = useState(false);

  const dismiss = () => {
    setExiting(true);
    setTimeout(() => onDismiss(item.id), 220);
  };

  useEffect(() => {
    timerRef.current = setTimeout(dismiss, duration);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, []);

  return (
    <div
      style={{
        position:     'relative',
        display:      'flex',
        alignItems:   'flex-start',
        gap:          '10px',
        background:   'var(--bg-surface)',
        border:       '1px solid var(--border-default)',
        borderLeft:   `3px solid ${cfg.barColor}`,
        borderRadius: '10px',
        boxShadow:    'var(--shadow-md)',
        padding:      '12px 14px',
        minWidth:     '280px',
        maxWidth:     '360px',
        animation:    exiting
          ? 'mt-toast-out 0.22s ease forwards'
          : 'mt-toast-in 0.22s cubic-bezier(0.34,1.3,0.64,1)',
        cursor:       'default',
      }}
      onMouseEnter={() => { if (timerRef.current) clearTimeout(timerRef.current); }}
      onMouseLeave={() => { timerRef.current = setTimeout(dismiss, 1500); }}
    >
      {/* Icon */}
      <div style={{ flexShrink: 0, paddingTop: '1px' }}>
        <Icon size={16} color={cfg.iconColor} strokeWidth={2.5} />
      </div>

      {/* Message */}
      <p style={{
        margin:     0,
        flex:       1,
        fontSize:   '13px',
        fontWeight: 500,
        color:      'var(--text-primary)',
        lineHeight: 1.5,
      }}>
        {item.message}
      </p>

      {/* Close */}
      <button
        onClick={dismiss}
        aria-label="Dismiss"
        style={{
          flexShrink:  0,
          background:  'none',
          border:      'none',
          cursor:      'pointer',
          color:       'var(--text-muted)',
          padding:     '0 0 0 4px',
          display:     'flex',
          alignItems:  'center',
          paddingTop:  '2px',
          transition:  'color 0.12s',
        }}
        onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-primary)')}
        onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
      >
        <X size={13} />
      </button>
    </div>
  );
}

// ── ToastContainer ────────────────────────────────────────────────────────────

export function ToastContainer({
  toasts,
  onDismiss,
}: {
  toasts:    ToastItem[];
  onDismiss: (id: string) => void;
}) {
  if (toasts.length === 0) return null;

  return (
    <div
      style={{
        position:      'fixed',
        top:           '20px',
        right:         '20px',
        zIndex:        1100,
        display:       'flex',
        flexDirection: 'column',
        gap:           '8px',
        alignItems:    'flex-end',
        pointerEvents: 'none',
      }}
    >
      {toasts.map(t => (
        <div key={t.id} style={{ pointerEvents: 'all' }}>
          <ToastCard item={t} onDismiss={onDismiss} />
        </div>
      ))}
    </div>
  );
}
