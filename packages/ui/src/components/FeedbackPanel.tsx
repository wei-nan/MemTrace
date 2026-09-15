import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Bug, Lightbulb } from 'lucide-react';
import { feedback, type FeedbackType } from '../api';
import { Modal, Button } from './ui';

export default function FeedbackPanel({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [type, setType] = useState<FeedbackType>('bug-report');
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);

  const reset = () => {
    setType('bug-report');
    setTitle('');
    setBody('');
    setError('');
    setDone(false);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleSubmit = async () => {
    if (!title.trim()) {
      setError(t('feedback.title_required'));
      return;
    }
    setLoading(true);
    setError('');
    try {
      await feedback.submit({ type, title: title.trim(), body: body.trim() });
      setDone(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t('feedback.error'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title={t('feedback.panel_title')} width={420}>
      {done ? (
        <div style={{ padding: '8px 0 16px', fontSize: 13, color: 'var(--text-primary)' }}>
          {t('feedback.success')}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <Button
              type="button"
              variant={type === 'bug-report' ? 'primary' : 'secondary'}
              onClick={() => setType('bug-report')}
              leftIcon={<Bug size={14} />}
              style={{ flex: 1 }}
            >
              {t('feedback.type_bug')}
            </Button>
            <Button
              type="button"
              variant={type === 'feature-request' ? 'primary' : 'secondary'}
              onClick={() => setType('feature-request')}
              leftIcon={<Lightbulb size={14} />}
              style={{ flex: 1 }}
            >
              {t('feedback.type_feature')}
            </Button>
          </div>

          <div className="mt-input-wrapper">
            <label className="mt-input-label">{t('feedback.title_label')}</label>
            <div className="mt-input-container">
              <input
                className="mt-input-field"
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder={t('feedback.title_ph')}
                maxLength={200}
              />
            </div>
          </div>

          <div className="mt-input-wrapper">
            <label className="mt-input-label">{t('feedback.body_label')}</label>
            <div className="mt-input-container" style={{ padding: '8px 12px' }}>
              <textarea
                className="mt-input-field"
                value={body}
                onChange={e => setBody(e.target.value)}
                placeholder={t('feedback.body_ph')}
                rows={5}
                style={{ resize: 'vertical', minHeight: 96, padding: 0 }}
              />
            </div>
          </div>

          {error && <div style={{ fontSize: 12, color: 'var(--color-error)' }}>{error}</div>}

          <Button onClick={handleSubmit} loading={loading} disabled={loading} style={{ width: '100%', height: 36 }}>
            {loading ? t('feedback.submitting') : t('feedback.submit')}
          </Button>
        </div>
      )}
    </Modal>
  );
}
