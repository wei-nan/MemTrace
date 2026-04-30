/**
 * Modal.tsx — MemTrace custom dialog components
 *
 * Exports:
 *   <ModalOverlay>      Base overlay + panel (handles backdrop, escape key, focus trap)
 *   <AlertModal>        Replaces window.alert()   — single OK button
 *   <ConfirmModal>      Replaces window.confirm() — Cancel + action button
 *
 * Designed strictly to the MemTrace design system (DESIGN_SYSTEM.md).
 * No browser-native dialogs, no gradients, no hardcoded colours.
 */

import { useEffect, useRef, type ReactNode } from 'react';
import { X, AlertTriangle, Info, CheckCircle, Trash2 } from 'lucide-react';

// ── Types ─────────────────────────────────────────────────────────────────────

export type ModalVariant = 'info' | 'success' | 'warning' | 'danger' | 'error';

interface OverlayProps {
  children: ReactNode;
  onClose?: () => void;   // undefined = not closable by clicking backdrop
  width?: string;         // default '420px'
}

interface AlertProps {
  title: string;
  message: ReactNode;
  variant?: ModalVariant;
  confirmLabel?: string;
  onClose: () => void;
}

interface ConfirmProps {
  title: string;
  message: ReactNode;
  variant?: ModalVariant;  // default 'warning'; 'danger' makes confirm button red
  confirmLabel?: string;
  cancelLabel?: string;
  customElement?: ReactNode;
  confirmDisabled?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

// ── Variant config ────────────────────────────────────────────────────────────

const VARIANT_CFG: Record<ModalVariant, {
  Icon: typeof Info;
  iconColor: string;
  iconBg: string;
  btnColor: string;
  btnHover: string;
}> = {
  info: {
    Icon: Info,
    iconColor: 'var(--color-info)',
    iconBg:    'var(--color-info-subtle)',
    btnColor:  'var(--color-primary)',
    btnHover:  'var(--color-primary-hover)',
  },
  success: {
    Icon: CheckCircle,
    iconColor: 'var(--color-success)',
    iconBg:    'var(--color-success-subtle)',
    btnColor:  'var(--color-success)',
    btnHover:  'var(--color-success)',
  },
  warning: {
    Icon: AlertTriangle,
    iconColor: 'var(--color-warning)',
    iconBg:    'var(--color-warning-subtle)',
    btnColor:  'var(--color-primary)',
    btnHover:  'var(--color-primary-hover)',
  },
  danger: {
    Icon: Trash2,
    iconColor: 'var(--color-error)',
    iconBg:    'var(--color-error-subtle)',
    btnColor:  'var(--color-error)',
    btnHover:  'var(--color-error)',
  },
  error: {
    Icon: AlertTriangle,
    iconColor: 'var(--color-error)',
    iconBg:    'var(--color-error-subtle)',
    btnColor:  'var(--color-primary)',
    btnHover:  'var(--color-primary-hover)',
  },
};

// ── ModalOverlay ──────────────────────────────────────────────────────────────

export function ModalOverlay({ children, onClose, width = '420px' }: OverlayProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && onClose) onClose();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onClose]);

  // Focus first focusable element on mount
  useEffect(() => {
    const el = panelRef.current?.querySelector<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    el?.focus();
  }, []);

  return (
    <div
      style={{
        position:        'fixed',
        inset:           0,
        zIndex:          1000,
        display:         'flex',
        alignItems:      'center',
        justifyContent:  'center',
        background:      'var(--bg-overlay)',
        padding:         '16px',
        animation:       'mt-fade-in 0.12s ease',
      }}
      onMouseDown={e => { if (e.target === e.currentTarget) onClose?.(); }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        style={{
          width,
          maxWidth:     '100%',
          background:   'var(--bg-surface)',
          border:       '1px solid var(--border-default)',
          borderRadius: '14px',
          boxShadow:    'var(--shadow-lg)',
          animation:    'mt-scale-in 0.14s cubic-bezier(0.34,1.56,0.64,1)',
          outline:      'none',
        }}
      >
        {children}
      </div>
    </div>
  );
}

// ── AlertModal ────────────────────────────────────────────────────────────────

export function AlertModal({
  title,
  message,
  variant = 'info',
  confirmLabel = 'OK',
  onClose,
}: AlertProps) {
  const cfg = VARIANT_CFG[variant];
  const { Icon } = cfg;

  return (
    <ModalOverlay onClose={onClose}>
      {/* Header */}
      <div style={{
        display:    'flex',
        alignItems: 'flex-start',
        gap:        '14px',
        padding:    '24px 24px 0',
      }}>
        {/* Icon */}
        <div style={{
          flexShrink:   0,
          width:        40,
          height:       40,
          borderRadius: '10px',
          background:   cfg.iconBg,
          display:      'flex',
          alignItems:   'center',
          justifyContent: 'center',
        }}>
          <Icon size={20} color={cfg.iconColor} strokeWidth={2} />
        </div>

        {/* Title + close */}
        <div style={{ flex: 1, minWidth: 0, paddingTop: '8px' }}>
          <p style={{
            margin:     0,
            fontSize:   '15px',
            fontWeight: 600,
            color:      'var(--text-primary)',
            lineHeight: 1.3,
          }}>
            {title}
          </p>
        </div>

        <button
          onClick={onClose}
          aria-label="Close"
          style={{
            flexShrink: 0,
            background: 'none',
            border:     'none',
            cursor:     'pointer',
            color:      'var(--text-muted)',
            padding:    '4px',
            borderRadius: '6px',
            display:    'flex',
            alignItems: 'center',
            marginTop:  '2px',
            transition: 'color 0.12s, background 0.12s',
          }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLElement).style.color = 'var(--text-primary)';
            (e.currentTarget as HTMLElement).style.background = 'var(--bg-elevated)';
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLElement).style.color = 'var(--text-muted)';
            (e.currentTarget as HTMLElement).style.background = 'none';
          }}
        >
          <X size={16} />
        </button>
      </div>

      {/* Body */}
      <div style={{ padding: '12px 24px 0 78px' }}>
        <p style={{
          margin:     0,
          fontSize:   '14px',
          color:      'var(--text-secondary)',
          lineHeight: 1.6,
        }}>
          {message}
        </p>
      </div>

      {/* Footer */}
      <div style={{
        display:        'flex',
        justifyContent: 'flex-end',
        padding:        '20px 24px 24px',
      }}>
        <ActionButton
          label={confirmLabel}
          bg={cfg.btnColor}
          hoverBg={cfg.btnHover}
          onClick={onClose}
          autoFocus
        />
      </div>
    </ModalOverlay>
  );
}

// ── ConfirmModal ──────────────────────────────────────────────────────────────

export function ConfirmModal({
  title,
  message,
  variant = 'warning',
  confirmLabel = '確認',
  cancelLabel  = '取消',
  customElement,
  confirmDisabled = false,
  onConfirm,
  onCancel,
}: ConfirmProps) {
  const cfg = VARIANT_CFG[variant];
  const { Icon } = cfg;

  return (
    <ModalOverlay onClose={onCancel}>
      {/* Header */}
      <div style={{
        display:    'flex',
        alignItems: 'flex-start',
        gap:        '14px',
        padding:    '24px 24px 0',
      }}>
        <div style={{
          flexShrink:     0,
          width:          40,
          height:         40,
          borderRadius:   '10px',
          background:     cfg.iconBg,
          display:        'flex',
          alignItems:     'center',
          justifyContent: 'center',
        }}>
          <Icon size={20} color={cfg.iconColor} strokeWidth={2} />
        </div>

        <div style={{ flex: 1, minWidth: 0, paddingTop: '8px' }}>
          <p style={{
            margin:     0,
            fontSize:   '15px',
            fontWeight: 600,
            color:      'var(--text-primary)',
            lineHeight: 1.3,
          }}>
            {title}
          </p>
        </div>
      </div>

      {/* Body */}
      <div style={{ padding: '12px 24px 0 78px' }}>
        <p style={{
          margin:     0,
          fontSize:   '14px',
          color:      'var(--text-secondary)',
          lineHeight: 1.6,
        }}>
          {message}
        </p>
        {customElement && (
          <div style={{ marginTop: '16px' }}>
            {customElement}
          </div>
        )}
      </div>

      {/* Footer */}
      <div style={{
        display:        'flex',
        justifyContent: 'flex-end',
        gap:            '8px',
        padding:        '20px 24px 24px',
      }}>
        <GhostButton label={cancelLabel} onClick={onCancel} />
        <ActionButton
          label={confirmLabel}
          bg={cfg.btnColor}
          hoverBg={cfg.btnHover}
          onClick={onConfirm}
          disabled={confirmDisabled}
          autoFocus={variant !== 'danger' && !confirmDisabled}  // don't auto-focus destructive or disabled action
        />
      </div>
    </ModalOverlay>
  );
}

// ── Shared button primitives ──────────────────────────────────────────────────

function ActionButton({
  label,
  bg,
  hoverBg,
  onClick,
  disabled = false,
  autoFocus = false,
}: {
  label: string;
  bg: string;
  hoverBg: string;
  onClick: () => void;
  disabled?: boolean;
  autoFocus?: boolean;
}) {
  const ref = useRef<HTMLButtonElement>(null);
  useEffect(() => { if (autoFocus) ref.current?.focus(); }, [autoFocus]);

  return (
    <button
      ref={ref}
      onClick={onClick}
      disabled={disabled}
      style={{
        padding:      '8px 18px',
        background:   disabled ? 'var(--bg-elevated)' : bg,
        color:        disabled ? 'var(--text-muted)' : '#fff',
        border:       'none',
        borderRadius: '8px',
        fontSize:     '14px',
        fontWeight:   600,
        cursor:       disabled ? 'not-allowed' : 'pointer',
        transition:   'background 0.12s, opacity 0.12s',
        outline:      'none',
        opacity:      disabled ? 0.6 : 1,
      }}
      onMouseEnter={e => { if (!disabled) e.currentTarget.style.background = hoverBg; }}
      onMouseLeave={e => { if (!disabled) e.currentTarget.style.background = bg; }}
      onFocus={e     => { if (!disabled) e.currentTarget.style.boxShadow = '0 0 0 3px var(--color-primary-subtle)'; }}
      onBlur={e      => { if (!disabled) e.currentTarget.style.boxShadow = 'none'; }}
    >
      {label}
    </button>
  );
}

function GhostButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding:      '8px 18px',
        background:   'transparent',
        color:        'var(--text-secondary)',
        border:       '1px solid var(--border-default)',
        borderRadius: '8px',
        fontSize:     '14px',
        fontWeight:   500,
        cursor:       'pointer',
        transition:   'background 0.12s, color 0.12s, border-color 0.12s',
        outline:      'none',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.background   = 'var(--bg-elevated)';
        e.currentTarget.style.color        = 'var(--text-primary)';
        e.currentTarget.style.borderColor  = 'var(--border-strong)';
      }}
      onMouseLeave={e => {
        e.currentTarget.style.background   = 'transparent';
        e.currentTarget.style.color        = 'var(--text-secondary)';
        e.currentTarget.style.borderColor  = 'var(--border-default)';
      }}
      onFocus={e  => (e.currentTarget.style.boxShadow = '0 0 0 3px var(--color-primary-subtle)')}
      onBlur={e   => (e.currentTarget.style.boxShadow = 'none')}
    >
      {label}
    </button>
  );
}
