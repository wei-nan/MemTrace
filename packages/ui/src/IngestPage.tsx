import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Mail, Globe, Link as LinkIcon, Loader2 } from 'lucide-react';
import { ingest } from './api';
import { useModal } from './components/ModalContext';
import IngestButton from './IngestButton';
import IngestionHistory from './IngestionHistory';

export default function IngestPage({ wsId, onGoToReview }: { wsId: string, onGoToReview: () => void }) {
  const { t } = useTranslation();
  const { toast } = useModal();
  
  const [tab, setTab] = useState<'file' | 'url'>('file');
  const [url, setUrl] = useState('');
  const [urlLoading, setUrlLoading] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleUrlSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    
    setUrlLoading(true);
    try {
      await ingest.url(wsId, url);
      toast({ message: t('ingest.url_success'), variant: 'success' });
      setUrl('');
      setRefreshKey(prev => prev + 1);
    } catch (e: any) {
      toast({ message: e.message, variant: 'error' });
    } finally {
      setUrlLoading(false);
    }
  };

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 40 }}>
      <div style={{ maxWidth: 800, margin: '0 auto' }}>
        <header style={{ textAlign: 'center', marginBottom: 40 }}>
          <h2 style={{ fontSize: 24, fontWeight: 700, marginBottom: 12 }}>{t('ingest.title')}</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 15 }}>
            {t('ingest.desc')}
          </p>
        </header>

        {/* ── Tabs ────────────────────────────────────────────────────────── */}
        <div style={{ 
          display: 'flex', gap: 8, marginBottom: 32, 
          background: 'var(--bg-surface)', padding: 4, borderRadius: 12, 
          border: '1px solid var(--border-default)', width: 'fit-content', margin: '0 auto 32px' 
        }}>
          <button 
            onClick={() => setTab('file')}
            style={{
              padding: '8px 20px', borderRadius: 8, border: 'none', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, fontWeight: 600,
              background: tab === 'file' ? 'var(--color-primary)' : 'transparent',
              color: tab === 'file' ? 'white' : 'var(--text-secondary)',
              transition: 'all 0.2s'
            }}
          >
            <Mail size={16} />
            {t('ingest.tab_file')}
          </button>
          <button 
            onClick={() => setTab('url')}
            style={{
              padding: '8px 20px', borderRadius: 8, border: 'none', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, fontWeight: 600,
              background: tab === 'url' ? 'var(--color-primary)' : 'transparent',
              color: tab === 'url' ? 'white' : 'var(--text-secondary)',
              transition: 'all 0.2s'
            }}
          >
            <Globe size={16} />
            {t('ingest.tab_url')}
          </button>
        </div>

        <div className="glass-panel animate-slide-up" style={{ padding: 40, border: '1px solid var(--border-subtle)' }}>
          {tab === 'file' ? (
            <div style={{ maxWidth: 500, margin: '0 auto' }}>
              <IngestButton 
                wsId={wsId} 
                onStarted={() => setRefreshKey(prev => prev + 1)} 
              />
              <div style={{ marginTop: 24, fontSize: 12, color: 'var(--text-muted)', textAlign: 'center' }}>
                {t('ingest.file_support')}
              </div>
            </div>
          ) : (
            <div style={{ maxWidth: 500, margin: '0 auto' }}>
              <form onSubmit={handleUrlSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div style={{ position: 'relative' }}>
                  <LinkIcon size={18} style={{ position: 'absolute', left: 16, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                  <input 
                    className="mt-input"
                    style={{ paddingLeft: 48, height: 48 }}
                    placeholder={t('ingest.url_ph')}
                    value={url}
                    onChange={e => setUrl(e.target.value)}
                    disabled={urlLoading}
                  />
                </div>
                <button className="btn-primary" style={{ height: 48, width: '100%' }} disabled={urlLoading || !url.trim()}>
                  {urlLoading ? <Loader2 size={18} className="animate-spin" /> : t('ingest.start_ingest')}
                </button>
              </form>
              <div style={{ marginTop: 24, fontSize: 12, color: 'var(--text-muted)', textAlign: 'center' }}>
                {t('ingest.web_auto_extract')}
              </div>
            </div>
          )}
        </div>

        <IngestionHistory 
          wsId={wsId} 
          refreshKey={refreshKey}
          onGoToReview={onGoToReview}
        />

        <div style={{ marginTop: 60, padding: 24, background: 'var(--bg-elevated)', borderRadius: 16, border: '1px solid var(--border-subtle)' }}>
          <h4 style={{ fontSize: 14, marginBottom: 12, fontWeight: 700 }}>{t('ingest.tips_title')}</h4>
          <ul style={{ fontSize: 13, color: 'var(--text-secondary)', paddingLeft: 20, lineHeight: 1.8, margin: 0 }}>
            <li>{t('ingest.tip_1')}</li>
            <li>{t('ingest.tip_2')}</li>
            <li>{t('ingest.tip_3')}</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
