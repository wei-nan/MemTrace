/**
 * ReviewOverlay — T23
 * A slide-in overlay panel that shows pending review proposals over the graph.
 * Triggered by ReviewCounterBadge or the overlay toggle in GraphContainer.
 *
 * Usage:
 *   <ReviewOverlay wsId={wsId} onClose={() => setOverlayOpen(false)} />
 */
import { useEffect, useMemo, useState, useCallback } from 'react';
import { Check, Clock, RefreshCw, X } from 'lucide-react';
import { review, type ReviewItem } from './api';
import { useTranslation } from 'react-i18next';
import { useModal } from './components/ModalContext';

// ── Pending node list item ───────────────────────────────────────────────────

function PendingItem({
  item,
  onAccept,
  onReject,
  zh,
}: {
  item: ReviewItem;
  onAccept: (id: string) => void;
  onReject: (id: string) => void;
  zh: boolean;
}) {
  const changeLabel: Record<string, string> = {
    create:           zh ? '新增' : 'Create',
    update:           zh ? '更新' : 'Update',
    delete:           zh ? '刪除' : 'Delete',
    create_edge:      zh ? '建邊' : 'Edge',
    split_suggestion: zh ? '拆分' : 'Split',
  };

  return (
    <div
      style={{
        padding: '10px 14px',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {String(item.node_data?.title ?? item.node_data?.from_id ?? '—')}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
            <span style={{
              display: 'inline-block', padding: '1px 6px', borderRadius: 4, fontSize: 10, fontWeight: 700,
              background: 'rgba(251,191,36,0.14)', color: 'var(--color-warning)',
              border: '1px solid rgba(251,191,36,0.3)', marginRight: 6,
            }}>
              {changeLabel[item.change_type] ?? item.change_type}
            </span>
            {item.proposer_type === 'ai' ? '🤖 AI' : '👤 ' + (item.proposer_id ?? 'User')}
          </div>
        </div>
        {item.can_review && (
          <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
            <button
              className="btn-icon"
              style={{ color: 'var(--color-success)', background: 'rgba(52,211,153,0.1)', borderRadius: 6, width: 28, height: 28 }}
              title={zh ? '接受' : 'Accept'}
              onClick={() => onAccept(item.id)}
            >
              <Check size={13} />
            </button>
            <button
              className="btn-icon"
              style={{ color: 'var(--color-error)', background: 'rgba(248,113,113,0.1)', borderRadius: 6, width: 28, height: 28 }}
              title={zh ? '拒絕' : 'Reject'}
              onClick={() => onReject(item.id)}
            >
              <X size={13} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

interface Props {
  wsId: string;
  onClose: () => void;
}

export default function ReviewOverlay({ wsId, onClose }: Props) {
  const { i18n } = useTranslation();
  const zh = i18n.language.startsWith('zh');
  const { toast } = useModal();

  const [items, setItems] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'ai' | 'human'>('all');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setItems(await review.list(wsId, 'pending'));
    } catch (e) {
      toast({ message: String(e), variant: 'error' });
    } finally {
      setLoading(false);
    }
  }, [wsId]);

  useEffect(() => { load(); }, [load]);

  const visible = useMemo(() =>
    filter === 'all' ? items : items.filter(i => i.proposer_type === filter),
    [items, filter],
  );

  const handleAccept = async (id: string) => {
    try {
      await review.accept(id);
      setItems(prev => prev.filter(i => i.id !== id));
      toast({ message: zh ? '已接受提案' : 'Proposal accepted', variant: 'success' });
    } catch (e) {
      toast({ message: String(e), variant: 'error' });
    }
  };

  const handleReject = async (id: string) => {
    try {
      await review.reject(id);
      setItems(prev => prev.filter(i => i.id !== id));
      toast({ message: zh ? '已拒絕提案' : 'Proposal rejected', variant: 'success' });
    } catch (e) {
      toast({ message: String(e), variant: 'error' });
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="review-overlay-backdrop"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Side panel */}
      <div className="review-overlay-panel" role="dialog" aria-label={zh ? '審查覆蓋層' : 'Review Overlay'}>
        {/* Header */}
        <div style={{
          padding: '14px 16px',
          borderBottom: '1px solid var(--border-default)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'var(--bg-surface)',
          position: 'sticky',
          top: 0,
          zIndex: 1,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Clock size={15} style={{ color: 'var(--color-warning)' }} />
            <span style={{ fontWeight: 700, fontSize: 14 }}>
              {zh ? '待審提案' : 'Pending Reviews'}
            </span>
            <span style={{
              padding: '1px 8px', borderRadius: 10, fontSize: 11, fontWeight: 700,
              background: 'rgba(251,191,36,0.14)', color: 'var(--color-warning)',
              border: '1px solid rgba(251,191,36,0.3)',
            }}>
              {visible.length}
            </span>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button
              className="btn-icon"
              onClick={load}
              disabled={loading}
              title={zh ? '重新整理' : 'Refresh'}
            >
              <RefreshCw size={13} style={{ animation: loading ? 'mt-spin 1s linear infinite' : 'none' }} />
            </button>
            <button className="btn-icon" onClick={onClose} title={zh ? '關閉' : 'Close'}>
              <X size={14} />
            </button>
          </div>
        </div>

        {/* Filter tabs */}
        <div style={{
          display: 'flex',
          gap: 0,
          borderBottom: '1px solid var(--border-default)',
          background: 'var(--bg-base)',
        }}>
          {(['all', 'ai', 'human'] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                flex: 1,
                height: 32,
                fontSize: 11,
                fontWeight: 600,
                border: 'none',
                borderBottom: `2px solid ${filter === f ? 'var(--color-primary)' : 'transparent'}`,
                background: 'transparent',
                color: filter === f ? 'var(--color-primary)' : 'var(--text-muted)',
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
            >
              {f === 'all' ? (zh ? '全部' : 'All') : f === 'ai' ? '🤖 AI' : '👤 Human'}
            </button>
          ))}
        </div>

        {/* List */}
        <div style={{ overflowY: 'auto', flex: 1 }}>
          {loading ? (
            <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
              {zh ? '載入中…' : 'Loading…'}
            </div>
          ) : visible.length === 0 ? (
            <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
              {zh ? '目前沒有待審提案 ✓' : 'No pending proposals ✓'}
            </div>
          ) : (
            visible.map(item => (
              <PendingItem
                key={item.id}
                item={item}
                onAccept={handleAccept}
                onReject={handleReject}
                zh={zh}
              />
            ))
          )}
        </div>

        {/* Footer: open full review queue */}
        <div style={{
          padding: '12px 14px',
          borderTop: '1px solid var(--border-default)',
          background: 'var(--bg-surface)',
          position: 'sticky',
          bottom: 0,
        }}>
          <button
            className="btn-secondary"
            style={{ width: '100%', height: 34, fontSize: 12 }}
            onClick={onClose}
          >
            {zh ? '關閉覆蓋層' : 'Close Overlay'}
          </button>
        </div>
      </div>
    </>
  );
}
