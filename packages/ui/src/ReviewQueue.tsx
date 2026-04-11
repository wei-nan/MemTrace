import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Check, X, Edit3, Clock, FileText } from 'lucide-react';
import { review, type ReviewItem } from './api';

export default function ReviewQueue({ wsId, onClose }: { wsId: string; onClose: () => void }) {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadItems = async () => {
    setLoading(true);
    try {
      const data = await review.list(wsId);
      setItems(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadItems();
  }, [wsId]);

  const handleAccept = async (id: string) => {
    try {
      await review.accept(id);
      setItems(prev => prev.filter(item => item.id !== id));
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleReject = async (id: string) => {
    if (!confirm(zh ? '確定要拒絕此節點？' : 'Reject this node?')) return;
    try {
      await review.reject(id);
      setItems(prev => prev.filter(item => item.id !== id));
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleAcceptAll = async () => {
    if (!confirm(zh ? `確定要接受所有 ${items.length} 個節點？` : `Accept all ${items.length} nodes?`)) return;
    try {
      await review.acceptAll(wsId);
      setItems([]);
    } catch (e: any) { alert(e.message); }
  };

  const handleRejectAll = async () => {
    if (!confirm(zh ? `確定要拒絕所有 ${items.length} 個節點？` : `Reject all ${items.length} nodes?`)) return;
    try {
      await review.rejectAll(wsId);
      setItems([]);
    } catch (e: any) { alert(e.message); }
  };

  return (
    <div className="review-queue-container" style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ fontSize: 20, display: 'flex', alignItems: 'center', gap: 10 }}>
          <Clock size={20} className="text-accent" />
          {zh ? '審核佇列' : 'Review Queue'}
          <span style={{ fontSize: 13, background: 'var(--bg-secondary)', padding: '2px 8px', borderRadius: 10, color: 'var(--text-muted)' }}>
            {items.length}
          </span>
        </h2>
        <div style={{ display: 'flex', gap: 10 }}>
          {items.length > 0 && (
            <>
              <button onClick={handleRejectAll} className="btn-secondary" style={{ color: 'var(--error-color)', borderColor: 'var(--error-color)', padding: '6px 14px' }}>
                {zh ? '全部拒絕' : 'Reject All'}
              </button>
              <button onClick={handleAcceptAll} className="btn-primary" style={{ padding: '6px 14px' }}>
                {zh ? '全部接受' : 'Accept All'}
              </button>
            </>
          )}
          <button onClick={onClose} className="btn-secondary" style={{ padding: '6px 12px' }}>
            {zh ? '關閉' : 'Close'}
          </button>
        </div>
      </div>

      {error && <div className="error-msg" style={{ marginBottom: 16 }}>{error}</div>}

      {loading ? (
        <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>{zh ? '載入中…' : 'Loading…'}</div>
      ) : items.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 80, border: '2px dashed var(--border-color)', borderRadius: 16 }}>
          <div style={{ color: 'var(--text-muted)', marginBottom: 12 }}>
            <FileText size={48} style={{ opacity: 0.2, marginBottom: 16 }} />
            <p>{zh ? '目前沒有待審核的節點' : 'No pending nodes for review'}</p>
          </div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 20 }}>
          {items.map(item => (
            <div key={item.id} className="review-card" style={{
              background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
              borderRadius: 12, padding: 20, display: 'flex', flexDirection: 'column', gap: 12,
              boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
            }}>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between' }}>
                <span>{item.source_info}</span>
                <span>{new Date(item.created_at).toLocaleDateString()}</span>
              </div>
              <h3 style={{ fontSize: 16, fontWeight: 600 }}>{zh ? item.node_data.title_zh : item.node_data.title_en}</h3>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                {zh ? item.node_data.body_zh : item.node_data.body_en}
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {item.node_data.tags?.map((t: string) => (
                  <span key={t} style={{ fontSize: 10, background: 'rgba(99,102,241,0.1)', color: 'var(--accent-color)', padding: '2px 6px', borderRadius: 4 }}>
                    #{t}
                  </span>
                ))}
              </div>
              
              <div style={{ marginTop: 'auto', paddingTop: 12, borderTop: '1px solid var(--border-color)', display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                <button onClick={() => handleReject(item.id)} className="btn-icon" title={zh ? '拒絕' : 'Reject'} style={{ color: 'var(--error-color)' }}>
                  <X size={18} />
                </button>
                <button className="btn-icon" title={zh ? '編輯' : 'Edit'}>
                  <Edit3 size={18} />
                </button>
                <button onClick={() => handleAccept(item.id)} className="btn-primary" style={{ padding: '6px 16px', borderRadius: 8, fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Check size={16} />
                  {zh ? '接受' : 'Accept'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
