import React, { useEffect, useRef, type ReactNode } from 'react';
import { X, AlertTriangle, Info, CheckCircle, Trash2 } from 'lucide-react';
import { Button } from './Button';
import './Modal.css';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  width?: number | string;
  footer?: ReactNode;
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  width = '420px',
  footer,
}) => {
  if (!isOpen) return null;

  return (
    <ModalOverlay onClose={onClose} width={typeof width === 'number' ? `${width}px` : width}>
      <div className="modal-header">
        <h3 className="modal-title">{title}</h3>
        <Button variant="icon" onClick={onClose} aria-label="Close">
          <X size={20} />
        </Button>
      </div>
      <div className="modal-body">
        {children}
      </div>
      {footer && <div className="modal-footer">{footer}</div>}
    </ModalOverlay>
  );
};

interface OverlayProps {
  children: ReactNode;
  onClose?: () => void;
  width?: string;
}

export const ModalOverlay: React.FC<OverlayProps> = ({ children, onClose, width = '420px' }) => {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && onClose) onClose();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onClose]);

  useEffect(() => {
    const el = panelRef.current?.querySelector<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    el?.focus();
  }, []);

  return (
    <div className="modal-overlay" onMouseDown={e => { if (e.target === e.currentTarget) onClose?.(); }}>
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        className="modal-panel"
        style={{ width }}
      >
        {children}
      </div>
    </div>
  );
};

export type ModalVariant = 'info' | 'success' | 'warning' | 'danger' | 'error';

const VARIANT_ICON = {
  info: Info,
  success: CheckCircle,
  warning: AlertTriangle,
  danger: Trash2,
  error: AlertTriangle,
};

export const AlertModal: React.FC<{
  title: string;
  message: ReactNode;
  variant?: ModalVariant;
  confirmLabel?: string;
  onClose: () => void;
}> = ({ title, message, variant = 'info', confirmLabel = 'OK', onClose }) => {
  const Icon = VARIANT_ICON[variant];

  return (
    <ModalOverlay onClose={onClose}>
      <div className="modal-alert-header">
        <div className={`modal-alert-icon-wrapper variant-${variant}`}>
          <Icon size={20} strokeWidth={2} />
        </div>
        <div className="modal-alert-title-container">
          <p className="modal-alert-title">{title}</p>
        </div>
        <Button variant="icon" onClick={onClose} aria-label="Close">
          <X size={16} />
        </Button>
      </div>
      <div className="modal-alert-body">
        <p className="modal-alert-message">{message}</p>
      </div>
      <div className="modal-alert-footer">
        <Button onClick={onClose} autoFocus>
          {confirmLabel}
        </Button>
      </div>
    </ModalOverlay>
  );
};

export const ConfirmModal: React.FC<{
  title: string;
  message: ReactNode;
  variant?: ModalVariant;
  confirmLabel?: string;
  cancelLabel?: string;
  customElement?: ReactNode;
  confirmDisabled?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}> = ({
  title,
  message,
  variant = 'warning',
  confirmLabel = '確認',
  cancelLabel = '取消',
  customElement,
  confirmDisabled = false,
  onConfirm,
  onCancel,
}) => {
  const Icon = VARIANT_ICON[variant];

  return (
    <ModalOverlay onClose={onCancel}>
      <div className="modal-alert-header">
        <div className={`modal-alert-icon-wrapper variant-${variant}`}>
          <Icon size={20} strokeWidth={2} />
        </div>
        <div className="modal-alert-title-container">
          <p className="modal-alert-title">{title}</p>
        </div>
      </div>
      <div className="modal-alert-body">
        <p className="modal-alert-message">{message}</p>
        {customElement && <div className="modal-custom-element">{customElement}</div>}
      </div>
      <div className="modal-alert-footer">
        <Button variant="ghost" onClick={onCancel}>
          {cancelLabel}
        </Button>
        <Button
          variant={variant === 'danger' ? 'danger' : 'primary'}
          onClick={onConfirm}
          disabled={confirmDisabled}
          autoFocus={variant !== 'danger' && !confirmDisabled}
        >
          {confirmLabel}
        </Button>
      </div>
    </ModalOverlay>
  );
};
