/**
 * ModalContext.tsx — Global modal/toast state management
 *
 * Wrap <App> with <ModalProvider>. Then anywhere in the tree:
 *
 *   const { alert, confirm, toast } = useModal();
 *
 *   // alert — resolves when user closes
 *   await alert({ title: '錯誤', message: e.message, variant: 'error' });
 *
 *   // confirm — resolves true (confirm) or false (cancel)
 *   const ok = await confirm({ title: '刪除節點？', message: '...', variant: 'danger' });
 *   if (!ok) return;
 *
 *   // toast — fire-and-forget, auto-dismisses
 *   toast({ message: '已儲存', variant: 'success' });
 */

import {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { AlertModal, ConfirmModal, type ModalVariant } from './Modal';
import { ToastContainer, type ToastItem } from './Toast';

// ── Types ─────────────────────────────────────────────────────────────────────

interface AlertOptions {
  title:         string;
  message:       ReactNode;
  variant?:      ModalVariant;
  confirmLabel?: string;
}

interface ConfirmOptions {
  title:         string;
  message:       ReactNode;
  variant?:      ModalVariant;
  confirmLabel?: string;
  cancelLabel?:  string;
  customElement?: ReactNode;
  confirmDisabled?: boolean;
}

interface ToastOptions {
  message:   string;
  variant?:  Exclude<ModalVariant, 'danger'>;
  duration?: number;
}

interface ModalContextValue {
  alert:   (opts: AlertOptions)   => Promise<void>;
  confirm: (opts: ConfirmOptions) => Promise<boolean>;
  toast:   (opts: ToastOptions)   => void;
}

// ── Context ───────────────────────────────────────────────────────────────────

const ModalContext = createContext<ModalContextValue | null>(null);

// ── Provider ──────────────────────────────────────────────────────────────────

type ActiveAlert = AlertOptions & { resolve: () => void };
type ActiveConfirm = ConfirmOptions & { resolve: (v: boolean) => void };

export function ModalProvider({ children }: { children: ReactNode }) {
  const [alertState,   setAlertState]   = useState<ActiveAlert | null>(null);
  const [confirmState, setConfirmState] = useState<ActiveConfirm | null>(null);
  const [toasts,       setToasts]       = useState<ToastItem[]>([]);
  const toastCounter = useRef(0);

  // ── alert ───────────────────────────���─────────────────────────────���────────

  const alert = useCallback((opts: AlertOptions): Promise<void> => {
    return new Promise(resolve => {
      setAlertState({ ...opts, resolve });
    });
  }, []);

  const closeAlert = useCallback(() => {
    setAlertState(prev => { prev?.resolve(); return null; });
  }, []);

  // ── confirm ────────────────────────────────────────────────────────────────

  const confirm = useCallback((opts: ConfirmOptions): Promise<boolean> => {
    return new Promise(resolve => {
      setConfirmState({ ...opts, resolve });
    });
  }, []);

  const handleConfirm = useCallback((value: boolean) => {
    setConfirmState(prev => { prev?.resolve(value); return null; });
  }, []);

  // ── toast ──────────────────────────────────────────────────────────────────

  const toast = useCallback((opts: ToastOptions) => {
    const id = `toast_${++toastCounter.current}`;
    setToasts(prev => [...prev, { id, ...opts }]);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <ModalContext.Provider value={{ alert, confirm, toast }}>
      {children}

      {/* Alert */}
      {alertState && (
        <AlertModal
          title={alertState.title}
          message={alertState.message}
          variant={alertState.variant}
          confirmLabel={alertState.confirmLabel}
          onClose={closeAlert}
        />
      )}

      {/* Confirm */}
      {confirmState && (
        <ConfirmModal
          title={confirmState.title}
          message={confirmState.message}
          variant={confirmState.variant}
          confirmLabel={confirmState.confirmLabel}
          cancelLabel={confirmState.cancelLabel}
          customElement={confirmState.customElement}
          confirmDisabled={confirmState.confirmDisabled}
          onConfirm={() => handleConfirm(true)}
          onCancel={() => handleConfirm(false)}
        />
      )}

      {/* Toasts */}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </ModalContext.Provider>
  );
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useModal(): ModalContextValue {
  const ctx = useContext(ModalContext);
  if (!ctx) throw new Error('useModal must be used inside <ModalProvider>');
  return ctx;
}
