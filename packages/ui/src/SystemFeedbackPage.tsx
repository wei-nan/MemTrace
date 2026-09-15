import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { MessageSquareHeart, RefreshCw } from 'lucide-react';
import { feedback, type AdminFeedbackItem } from './api';
import { useModal } from './components/ModalContext';
import { Button } from './components/ui';

function fmtDate(value: string) {
  return new Date(value).toLocaleString();
}

export default function SystemFeedbackPage() {
  const { t, i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const { toast } = useModal();
  const [items, setItems] = useState<AdminFeedbackItem[]>([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const rows = await feedback.all();
      setItems(rows);
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: 'error' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div style={{ padding: '32px 24px', maxWidth: 1120, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16, marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 20, margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
            <MessageSquareHeart size={20} /> {t('system_feedback.title') || (zh ? '意見回饋' : 'Feedback')}
          </h1>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 6 }}>
            {t('system_feedback.subtitle') || (zh ? '所有使用者提交的問題回報與功能建議' : 'Bug reports and feature requests submitted by all users')}
          </div>
        </div>
        <Button variant="secondary" onClick={load} loading={loading} leftIcon={<RefreshCw size={14} />}>
          {t('system_feedback.refresh') || (zh ? '重新整理' : 'Refresh')}
        </Button>
      </div>

      <div style={{ border: '1px solid var(--border-default)', borderRadius: 8, overflow: 'hidden', background: 'var(--bg-surface)' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(220px, 2fr) 110px minmax(160px, 1fr) 170px', gap: 12, padding: '10px 14px', fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', background: 'var(--bg-elevated)' }}>
          <div>{t('system_feedback.col_content') || (zh ? '內容' : 'Content')}</div>
          <div>{t('system_feedback.col_type') || (zh ? '類型' : 'Type')}</div>
          <div>{t('system_feedback.col_submitter') || (zh ? '提交者' : 'Submitter')}</div>
          <div>{t('system_feedback.col_submitted_at') || (zh ? '提交時間' : 'Submitted at')}</div>
        </div>
        {items.map((row) => (
          <div key={row.id} style={{ display: 'grid', gridTemplateColumns: 'minmax(220px, 2fr) 110px minmax(160px, 1fr) 170px', gap: 12, padding: '12px 14px', borderTop: '1px solid var(--border-subtle)' }}>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontWeight: 650, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{row.title}</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2, whiteSpace: 'pre-wrap' }}>{row.body}</div>
            </div>
            <div>
              <span
                className="tag"
                style={{
                  background: row.type === 'bug-report' ? 'var(--color-danger-subtle)' : 'var(--color-primary-subtle)',
                  color: row.type === 'bug-report' ? 'var(--color-danger)' : 'var(--color-primary)',
                }}
              >
                {row.type === 'bug-report'
                  ? (zh ? '問題回報' : 'Bug report')
                  : (zh ? '功能建議' : 'Feature request')}
              </span>
            </div>
            <div style={{ minWidth: 0 }}>
              <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{row.author_name || row.author_id}</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{row.author_email}</div>
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{fmtDate(row.created_at)}</div>
          </div>
        ))}
        {!loading && items.length === 0 && (
          <div style={{ padding: 28, color: 'var(--text-muted)', textAlign: 'center' }}>
            {t('system_feedback.no_items') || (zh ? '目前還沒有回饋' : 'No feedback yet')}
          </div>
        )}
        {loading && items.length === 0 && (
          <div style={{ padding: 28, color: 'var(--text-muted)', display: 'flex', justifyContent: 'center' }}>
            <RefreshCw className="animate-spin" />
          </div>
        )}
      </div>
    </div>
  );
}
