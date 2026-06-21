/**
 * NotificationBell — in-app notification center entry point.
 * Polls the unread count; the dropdown lists the user's notifications fanned out
 * from every audit/review finding (see migration 114 + routers/notifications.py).
 * Clicking an item marks it read AND navigates to the relevant page.
 */
import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Bell, Check } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { notifications as notifApi, type NotificationItem } from '../api';
import { notificationTitle, severityColor } from './notificationFormat';

const POLL_MS = 30_000;

interface Props {
  /** Navigate to the page/node a notification refers to. */
  onNavigate?: (n: NotificationItem) => void;
  /** Open the full notifications page. */
  onViewAll?: () => void;
}

const NotificationBell: React.FC<Props> = ({ onNavigate, onViewAll }) => {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const fetchUnread = useCallback(async () => {
    try {
      const res = await notifApi.unreadCount();
      setUnread(res.unread_count);
    } catch {
      // badge degrades gracefully — ignore transient failures
    }
  }, []);

  const fetchList = useCallback(async () => {
    setLoading(true);
    try {
      const res = await notifApi.list({ limit: 15 });
      setItems(res.notifications);
      setUnread(res.unread_count);
    } catch {
      // ignore — dropdown will show empty/loading state
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUnread();
    const id = setInterval(fetchUnread, POLL_MS);
    return () => clearInterval(id);
  }, [fetchUnread]);

  useEffect(() => {
    if (open) fetchList();
  }, [open, fetchList]);

  useEffect(() => {
    const onMouseDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onMouseDown);
    return () => document.removeEventListener('mousedown', onMouseDown);
  }, []);

  const handleItemClick = async (n: NotificationItem) => {
    if (!n.read_at) {
      try {
        await notifApi.markRead(n.id);
      } catch {
        // ignore — optimistic update below still reflects intent
      }
      setItems(prev => prev.map(x => (x.id === n.id ? { ...x, read_at: new Date().toISOString() } : x)));
      setUnread(c => Math.max(0, c - 1));
    }
    setOpen(false);
    onNavigate?.(n);
  };

  const handleMarkAll = async () => {
    try {
      await notifApi.markAllRead();
    } catch {
      // ignore
    }
    setItems(prev => prev.map(x => ({ ...x, read_at: x.read_at ?? new Date().toISOString() })));
    setUnread(0);
  };

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        title={zh ? '通知' : 'Notifications'}
        aria-label={zh ? '通知' : 'Notifications'}
        style={{
          position: 'relative', background: 'transparent', border: 'none', cursor: 'pointer',
          width: 38, height: 38, borderRadius: 8, display: 'flex', alignItems: 'center',
          justifyContent: 'center', color: 'var(--text-secondary)',
        }}
      >
        <Bell size={18} />
        {unread > 0 && (
          <span style={{
            position: 'absolute', top: 3, right: 3, minWidth: 16, height: 16, padding: '0 4px',
            borderRadius: 8, background: '#ef4444', color: '#fff', fontSize: 10, fontWeight: 700,
            display: 'flex', alignItems: 'center', justifyContent: 'center', lineHeight: 1,
          }}>
            {unread > 99 ? '99+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div style={{
          position: 'absolute', top: 'calc(100% + 8px)', right: 0, width: 360, maxHeight: 480,
          background: 'var(--bg-elevated)', border: '1px solid var(--border-default)', borderRadius: 10,
          boxShadow: 'var(--shadow-lg)', overflow: 'hidden', zIndex: 1100, display: 'flex', flexDirection: 'column',
        }}>
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '10px 14px', borderBottom: '1px solid var(--border-subtle)',
          }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
              {zh ? '通知' : 'Notifications'}{unread > 0 ? ` (${unread})` : ''}
            </span>
            {unread > 0 && (
              <button
                type="button"
                onClick={handleMarkAll}
                style={{
                  background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--color-primary)',
                  fontSize: 12, display: 'flex', alignItems: 'center', gap: 4,
                }}
              >
                <Check size={13} /> {zh ? '全部已讀' : 'Mark all read'}
              </button>
            )}
          </div>

          <div style={{ overflowY: 'auto', flex: 1 }}>
            {loading && items.length === 0 ? (
              <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)', fontSize: 12 }}>
                {zh ? '載入中…' : 'Loading…'}
              </div>
            ) : items.length === 0 ? (
              <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 12 }}>
                {zh ? '沒有通知' : 'No notifications'}
              </div>
            ) : (
              items.map(n => (
                <div
                  key={n.id}
                  onClick={() => handleItemClick(n)}
                  style={{
                    padding: '10px 14px', borderBottom: '1px solid var(--border-subtle)', cursor: 'pointer',
                    background: n.read_at ? 'transparent' : 'var(--color-primary-subtle)', display: 'flex', gap: 10,
                  }}
                >
                  <span style={{
                    width: 8, height: 8, borderRadius: '50%', marginTop: 5, flexShrink: 0,
                    background: severityColor(n.severity),
                  }} />
                  <div style={{ minWidth: 0 }}>
                    <div style={{
                      fontSize: 12.5, fontWeight: 600, color: 'var(--text-primary)',
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {notificationTitle(n, zh)}
                    </div>
                    {n.body && (
                      <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 2 }}>
                        {n.body.length > 100 ? `${n.body.slice(0, 100)}…` : n.body}
                      </div>
                    )}
                    <div style={{ fontSize: 10.5, color: 'var(--text-muted)', marginTop: 3 }}>
                      {new Date(n.created_at).toLocaleString()}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {onViewAll && (
            <button
              type="button"
              onClick={() => { setOpen(false); onViewAll(); }}
              style={{
                background: 'transparent', border: 'none', borderTop: '1px solid var(--border-subtle)',
                padding: '10px 14px', cursor: 'pointer', color: 'var(--color-primary)',
                fontSize: 12.5, fontWeight: 600, textAlign: 'center',
              }}
            >
              {zh ? '查看全部' : 'View all'}
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default NotificationBell;
