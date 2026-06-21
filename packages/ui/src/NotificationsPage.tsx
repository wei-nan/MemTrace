/**
 * NotificationsPage — full-page notification center.
 * The header bell dropdown only shows recent items; this page lists everything
 * with all/unread filtering and pagination.
 */
import React, { useEffect, useState, useCallback } from 'react';
import { Check, RefreshCw } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { notifications as notifApi, type NotificationItem } from './api';
import { notificationTitle, severityLabel, severityColor } from './components/notificationFormat';

const PAGE = 30;

interface Props {
  onNavigate?: (n: NotificationItem) => void;
}

const NotificationsPage: React.FC<Props> = ({ onNavigate }) => {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unread, setUnread] = useState(0);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);

  const fetchPage = useCallback(async (startOffset: number, replace: boolean) => {
    setLoading(true);
    try {
      const res = await notifApi.list({ unread_only: unreadOnly, limit: PAGE, offset: startOffset });
      setUnread(res.unread_count);
      setItems(prev => (replace ? res.notifications : [...prev, ...res.notifications]));
      setHasMore(res.notifications.length === PAGE);
      setOffset(startOffset + res.notifications.length);
    } catch {
      // ignore — list stays as-is
    } finally {
      setLoading(false);
    }
  }, [unreadOnly]);

  // Re-fetch from the top whenever the filter changes (fetchPage identity tracks unreadOnly).
  useEffect(() => { fetchPage(0, true); }, [fetchPage]);

  const handleClick = async (n: NotificationItem) => {
    if (!n.read_at) {
      try {
        await notifApi.markRead(n.id);
      } catch {
        // ignore
      }
      setItems(prev => prev.map(x => (x.id === n.id ? { ...x, read_at: new Date().toISOString() } : x)));
      setUnread(c => Math.max(0, c - 1));
    }
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
    if (unreadOnly) fetchPage(0, true);
  };

  const tabBtn = (active: boolean): React.CSSProperties => ({
    padding: '6px 14px', borderRadius: 8, border: '1px solid var(--border-default)', cursor: 'pointer',
    fontSize: 13, fontWeight: 600,
    background: active ? 'var(--color-primary)' : 'transparent',
    color: active ? '#fff' : 'var(--text-secondary)',
  });

  return (
    <div style={{ maxWidth: 760, margin: '0 auto', padding: '8px 4px 40px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, gap: 12 }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <button type="button" style={tabBtn(!unreadOnly)} onClick={() => setUnreadOnly(false)}>
            {zh ? '全部' : 'All'}
          </button>
          <button type="button" style={tabBtn(unreadOnly)} onClick={() => setUnreadOnly(true)}>
            {zh ? '未讀' : 'Unread'}{unread > 0 ? ` (${unread})` : ''}
          </button>
        </div>
        {unread > 0 && (
          <button
            type="button"
            onClick={handleMarkAll}
            style={{
              background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--color-primary)',
              fontSize: 13, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 5,
            }}
          >
            <Check size={15} /> {zh ? '全部已讀' : 'Mark all read'}
          </button>
        )}
      </div>

      <div style={{ border: '1px solid var(--border-default)', borderRadius: 12, overflow: 'hidden' }}>
        {items.length === 0 && !loading ? (
          <div style={{ padding: 48, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
            {zh ? '沒有通知' : 'No notifications'}
          </div>
        ) : (
          items.map(n => (
            <div
              key={n.id}
              onClick={() => handleClick(n)}
              style={{
                padding: '14px 18px', borderBottom: '1px solid var(--border-subtle)', cursor: 'pointer',
                background: n.read_at ? 'transparent' : 'var(--color-primary-subtle)', display: 'flex', gap: 12,
              }}
            >
              <span style={{
                width: 9, height: 9, borderRadius: '50%', marginTop: 5, flexShrink: 0,
                background: severityColor(n.severity),
              }} />
              <div style={{ minWidth: 0, flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
                    {notificationTitle(n, zh)}
                  </span>
                  {n.severity && (
                    <span style={{
                      fontSize: 10.5, fontWeight: 700, padding: '1px 7px', borderRadius: 10,
                      color: severityColor(n.severity), border: `1px solid ${severityColor(n.severity)}`,
                    }}>
                      {severityLabel(n.severity, zh)}
                    </span>
                  )}
                </div>
                {n.body && (
                  <div style={{ fontSize: 12.5, color: 'var(--text-muted)', marginTop: 4, lineHeight: 1.5 }}>
                    {n.body}
                  </div>
                )}
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 5 }}>
                  {new Date(n.created_at).toLocaleString()}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {hasMore && (
        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <button
            type="button"
            disabled={loading}
            onClick={() => fetchPage(offset, false)}
            style={{
              padding: '8px 20px', borderRadius: 8, border: '1px solid var(--border-default)',
              background: 'transparent', cursor: loading ? 'default' : 'pointer', color: 'var(--text-secondary)',
              fontSize: 13, fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 6,
            }}
          >
            {loading && <RefreshCw size={14} className="animate-spin" />}
            {zh ? '載入更多' : 'Load more'}
          </button>
        </div>
      )}
    </div>
  );
};

export default NotificationsPage;
