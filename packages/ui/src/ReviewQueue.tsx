import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Check, X, Edit3, Clock, FileText,
  Trash2, Save, ExternalLink, AlertCircle
} from 'lucide-react';
import MDEditor from '@uiw/react-md-editor';
import { review, type ReviewItem } from './api';
import { useModal } from './components/ModalContext';

export function ReviewList({
  wsId,
  onItemsLoaded,
  compact = false
}: {
  wsId: string,
  onItemsLoaded?: (items: ReviewItem[]) => void,
  compact?: boolean
}) {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const { confirm, toast } = useModal();
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingItem, setEditingItem] = useState<ReviewItem | null>(null);

  const loadItems = async () => {
    setLoading(true);
    try {
      const data = await review.list(wsId);
      setItems(data);
      if (onItemsLoaded) onItemsLoaded(data);
    } catch (e) {
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
      toast({ message: zh ? '節點已接受' : 'Node accepted', variant: 'success' });
    } catch (e: any) {
      toast({ message: e.message, variant: 'error' });
    }
  };

  const handleReject = async (id: string) => {
    const ok = await confirm({
      title: zh ? '拒絕節點' : 'Reject Node',
      message: zh ? '確定要拒絕此節點？此動作無法復原。' : 'Reject this node? This action cannot be undone.',
      variant: 'danger',
      confirmLabel: zh ? '拒絕' : 'Reject',
    });
    if (!ok) return;
    try {
      await review.reject(id);
      setItems(prev => prev.filter(item => item.id !== id));
      toast({ message: zh ? '節點已拒絕' : 'Node rejected', variant: 'info' });
    } catch (e: any) {
      toast({ message: e.message, variant: 'error' });
    }
  };

  const handleSaveEdit = async (updatedNodeData: any) => {
    if (!editingItem) return;
    try {
      const updated = await review.update(editingItem.id, { node_data: updatedNodeData });
      setItems(prev => prev.map(item => item.id === updated.id ? updated : item));
      setEditingItem(null);
      toast({ message: zh ? '節點已更新' : 'Node updated', variant: 'success' });
    } catch (e: any) {
      toast({ message: e.message, variant: 'error' });
    }
  };

  if (loading) return (
    <div className="flex-center flex-col py-40 opacity-50">
      <div className="spinner mb-16" />
      <p>{zh ? '正在讀取候選節點...' : 'Reading candidates...'}</p>
    </div>
  );

  if (items.length === 0) return (
    <div className="flex-center flex-col py-40 opacity-40">
      <FileText size={compact ? 32 : 64} className="mb-16" />
      <p>{zh ? '目前沒有待審核內容' : 'No items for review'}</p>
    </div>
  );

  return (
    <div className={compact ? "review-list-compact" : "review-grid"}>
      {items.map(item => (
        <div key={item.id} className="review-card">
          <div className="card-top">
            <span className="source-label">{item.source_info}</span>
            <span className="date-label">{new Date(item.created_at).toLocaleDateString()}</span>
          </div>
          <div className="card-body">
             <h3 className="card-title">{zh ? item.node_data.title_zh : item.node_data.title_en}</h3>
             {!compact && <p className="card-excerpt">{zh ? item.node_data.body_zh : item.node_data.body_en}</p>}
             <div className="tag-list">
               {item.node_data.tags?.map((t: string) => <span key={t} className="mt-tag">#{t}</span>)}
             </div>
          </div>
          <div className="card-actions">
             <button className="btn-icon-error" onClick={() => handleReject(item.id)} title={zh ? '拒絕' : 'Reject'}><Trash2 size={18} /></button>
             <button className="btn-icon" onClick={() => setEditingItem(item)} title={zh ? '編輯' : 'Edit'}><Edit3 size={18} /></button>
             <div className="spacer" />
             <button className="btn-primary-sm" onClick={() => handleAccept(item.id)}>
                <Check size={16} /> {zh ? '接受' : 'Accept'}
             </button>
          </div>
        </div>
      ))}
      
      {editingItem && (
        <ReviewEditor 
          item={editingItem} 
          onSave={handleSaveEdit} 
          onClose={() => setEditingItem(null)} 
          zh={zh}
        />
      )}

      {!compact && (
        <style>{`
          .spinner { width: 32px; height: 32px; border: 3px solid var(--border-default); border-top-color: var(--color-primary); border-radius: 50%; animation: spin 1s linear infinite; }
          @keyframes spin { to { transform: rotate(360deg); } }
          .flex-center { display: flex; align-items: center; justify-content: center; }
          .flex-col { flex-direction: column; }
          .py-40 { padding: 40px 0; }
          .mb-16 { margin-bottom: 16px; }
          .review-grid { 
            display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); 
            gap: 24px; padding: 2px;
          }
          .review-card { 
            background: var(--bg-surface); border: 1px solid var(--border-default);
            border-radius: 16px; padding: 20px; display: flex; flex-direction: column; gap: 12px;
            transition: transform 0.2s, box-shadow 0.2s;
          }
          .review-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-lg); }
          .card-top { display: flex; justify-content: space-between; font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
          .card-title { font-size: 16px; font-weight: 600; margin: 0; }
          .card-excerpt { 
            font-size: 13px; color: var(--text-secondary); line-height: 1.5;
            display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
            margin: 4px 0;
          }
          .tag-list { display: flex; flex-wrap: wrap; gap: 6px; }
          .mt-tag { font-size: 10px; color: var(--color-primary); background: var(--color-primary-subtle); padding: 1px 6px; border-radius: 4px; }
          .card-actions { border-top: 1px solid var(--border-subtle); padding-top: 12px; display: flex; gap: 8px; align-items: center; margin-top: auto; }
          .btn-primary-sm { 
            background: var(--color-primary); color: white; border: none; padding: 5px 12px; 
            border-radius: 6px; font-size: 12px; font-weight: 500; cursor: pointer; display: flex; gap: 4px; align-items: center;
          }
          .btn-icon, .btn-icon-error { background: transparent; border: none; cursor: pointer; padding: 5px; border-radius: 6px; color: var(--text-muted); transition: all 0.2s; }
          .btn-icon:hover { background: var(--bg-elevated); color: var(--color-primary); }
          .btn-icon-error:hover { background: var(--color-error-subtle); color: var(--color-error); }
          .spacer { flex: 1; }
        `}</style>
      )}
      {compact && (
        <style>{`
          .review-list-compact { display: flex; flex-direction: column; gap: 12px; max-height: 400px; overflow-y: auto; padding-right: 8px; }
          .review-list-compact .review-card { padding: 16px; border-radius: 12px; }
          .review-list-compact .card-title { font-size: 14px; }
          .review-list-compact .card-actions { padding-top: 8px; gap: 6px; }
        `}</style>
      )}
    </div>
  );
}

export function ReviewEditor({ item, onSave, onClose, zh }: { item: ReviewItem, onSave: (data: any) => void, onClose: () => void, zh: boolean }) {
  const [data, setData] = useState(JSON.parse(JSON.stringify(item.node_data)));
  const [lang, setLang] = useState<'zh' | 'en'>(zh ? 'zh' : 'en');

  return (
    <div className="modal-overlay" style={{ zIndex: 4000 }} onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal-card">
        <div className="modal-header">
           <div className="flex-center gap-12">
             <Edit3 size={20} />
             <h3>{zh ? '編輯候選節點' : 'Edit Candidate'}</h3>
           </div>
           <button className="btn-icon" onClick={onClose}><X size={20} /></button>
        </div>
        
        <div className="modal-body">
           <div className="lang-toggle mb-24">
             <button className={lang === 'zh' ? 'active' : ''} onClick={() => setLang('zh')}>中文內容</button>
             <button className={lang === 'en' ? 'active' : ''} onClick={() => setLang('en')}>English Content</button>
           </div>

           <div className="form-group mb-16">
             <label>{zh ? '標題' : 'Title'}</label>
             <input 
               className="mt-input" 
               value={lang === 'zh' ? data.title_zh : data.title_en} 
               onChange={e => setData({...data, [lang === 'zh' ? 'title_zh' : 'title_en']: e.target.value})}
             />
           </div>

           <div className="form-group mb-16">
             <label>{zh ? '內容' : 'Content'}</label>
             <div data-color-mode="dark">
                <MDEditor 
                  value={lang === 'zh' ? data.body_zh : data.body_en} 
                  onChange={val => setData({...data, [lang === 'zh' ? 'body_zh' : 'body_en']: val || ''})}
                  height={200} preview="edit"
                />
             </div>
           </div>

           <div className="form-group">
             <label>{zh ? '標籤' : 'Tags'}</label>
             <input 
               className="mt-input" 
               value={data.tags?.join(', ')} 
               onChange={e => setData({...data, tags: e.target.value.split(',').map((s:string) => s.trim()).filter(Boolean)})}
               placeholder="tag1, tag2..."
             />
           </div>
        </div>

        <div className="modal-footer">
           <button className="btn-secondary" onClick={onClose}>{zh ? '取消' : 'Cancel'}</button>
           <button className="btn-primary" onClick={() => onSave(data)}><Save size={18} /> {zh ? '儲存修改' : 'Save Changes'}</button>
        </div>
      </div>

      <style>{`
        .modal-overlay { 
          position: fixed; inset: 0; background: var(--bg-overlay); 
          display: flex; align-items: center; justify-content: center;
        }
        .modal-card { 
          background: var(--bg-surface); width: 800px; max-width: 95vw; max-height: 90vh;
          border-radius: 20px; box-shadow: var(--shadow-2xl); display: flex; flex-direction: column; overflow: hidden;
        }
        .modal-header { padding: 20px 24px; border-bottom: 1px solid var(--border-default); display: flex; justify-content: space-between; align-items: center; }
        .modal-body { padding: 24px; overflow-y: auto; }
        .modal-footer { padding: 20px 24px; border-top: 1px solid var(--border-default); display: flex; justify-content: flex-end; gap: 12px; }
        
        .lang-toggle { display: flex; gap: 8px; }
        .lang-toggle button { 
          padding: 6px 14px; border-radius: 8px; border: 1px solid var(--border-default); 
          background: transparent; color: var(--text-muted); cursor: pointer; font-size: 13px;
        }
        .lang-toggle button.active { background: var(--color-primary-subtle); color: var(--color-primary); border-color: var(--color-primary); }
        
        .form-group label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 8px; color: var(--text-secondary); }
        .mb-16 { margin-bottom: 16px; }
        .mb-24 { margin-bottom: 24px; }
      `}</style>
    </div>
  );
}

export default function ReviewQueue({ wsId, onClose }: { wsId: string; onClose: () => void }) {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const { confirm, toast } = useModal();
  const [count, setCount] = useState(0);
  const [listKey, setListKey] = useState(0);

  const handleAcceptAll = async () => {
    const ok = await confirm({
      title: zh ? '全數接受' : 'Accept All',
      message: zh ? `確定要接受所有 ${count} 個候選節點？` : `Accept all ${count} candidate nodes?`,
      variant: 'warning',
      confirmLabel: zh ? '全數接受' : 'Accept All',
    });
    if (!ok) return;
    try {
      await review.acceptAll(wsId);
      setListKey(k => k + 1); // force ReviewList remount to refresh
      toast({ message: zh ? '所有節點已接受' : 'All nodes accepted', variant: 'success' });
    } catch (e: any) {
      toast({ message: e.message, variant: 'error' });
    }
  };

  return (
    <div className="review-layout">
      <div className="review-header">
        <div className="flex-center gap-12">
           <div className="brand-icon-primary"><Clock size={20} /></div>
           <h2 className="title-lg">{zh ? '審核佇列' : 'Review Queue'}</h2>
           <span className="badge-count">{count}</span>
        </div>
        <div className="flex-center gap-12">
          <button className="btn-primary" onClick={handleAcceptAll}>{zh ? '全數接受' : 'Accept All'}</button>
          <button onClick={onClose} className="btn-secondary">{zh ? '返回圖譜' : 'Back to Graph'}</button>
        </div>
      </div>

      <div className="review-content">
        <ReviewList key={listKey} wsId={wsId} onItemsLoaded={items => setCount(items.length)} />
      </div>

      <style>{`
        .review-layout { display: flex; flex-direction: column; height: 100vh; background: var(--bg-base); }
        .review-header { 
          padding: 24px 40px; border-bottom: 1px solid var(--border-default); 
          display: flex; justify-content: space-between; align-items: center;
          background: var(--bg-surface);
        }
        .review-content { flex: 1; overflow-y: auto; padding: 40px; }
        .badge-count { background: var(--bg-elevated); padding: 2px 10px; border-radius: 12px; font-size: 12px; color: var(--text-muted); }
        .flex-center { display: flex; align-items: center; justify-content: center; }
        .gap-12 { gap: 12px; }
        .title-lg { font-size: 20px; font-weight: 600; }
      `}</style>
    </div>
  );
}
