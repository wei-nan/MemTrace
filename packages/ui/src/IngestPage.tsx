import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FileUp, Globe, Link as LinkIcon, Database } from 'lucide-react';
import { ingest } from './api';
import { useModal } from './components/ModalContext';
import IngestButton from './IngestButton';
import IngestionHistory from './IngestionHistory';
import ImportSourcesList from './components/ImportSourcesList';
import { Button, Input, Card } from './components/ui';

export default function IngestPage({ wsId, onGoToReview }: { wsId: string, onGoToReview: () => void }) {
  const { t } = useTranslation();
  const { toast } = useModal();
  
  const [tab, setTab] = useState<'file' | 'url' | 'sources'>('file');
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


        {/* ── Tabs ────────────────────────────────────────────────────────── */}
        <div style={{ 
          display: 'flex', gap: 8, marginBottom: 32, 
          background: 'var(--bg-surface)', padding: 4, borderRadius: 12, 
          border: '1px solid var(--border-default)', width: 'fit-content', margin: '0 auto 32px' 
        }}>
          <Button 
            variant={tab === 'file' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setTab('file')}
            leftIcon={<FileUp size={16} />}
          >
            {t('ingest.tab_file')}
          </Button>
          <Button 
            variant={tab === 'url' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setTab('url')}
            leftIcon={<Globe size={16} />}
          >
            {t('ingest.tab_url')}
          </Button>
          <Button 
            variant={tab === 'sources' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setTab('sources')}
            leftIcon={<Database size={16} />}
          >
            來源稽核 (Sources)
          </Button>
        </div>

        <Card variant="surface" padding="lg" className="animate-slide-up" style={{ border: '1px solid var(--border-subtle)' }}>
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
          ) : tab === 'url' ? (
            <div style={{ maxWidth: 500, margin: '0 auto' }}>
              <form onSubmit={handleUrlSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <Input
                  leftIcon={<LinkIcon size={18} />}
                  placeholder={t('ingest.url_ph')}
                  value={url}
                  onChange={e => setUrl(e.target.value)}
                  disabled={urlLoading}
                />
                <Button variant="primary" style={{ height: 48, width: '100%' }} loading={urlLoading} disabled={!url.trim()}>
                  {t('ingest.start_ingest')}
                </Button>
              </form>
              <div style={{ marginTop: 24, fontSize: 12, color: 'var(--text-muted)', textAlign: 'center' }}>
                {t('ingest.web_auto_extract')}
              </div>
            </div>
          ) : (
            <ImportSourcesList wsId={wsId} />
          )}
        </Card>

        <IngestionHistory 
          wsId={wsId} 
          refreshKey={refreshKey}
          onGoToReview={onGoToReview}
        />

        <Card variant="surface" padding="md" style={{ marginTop: 60, border: '1px solid var(--border-subtle)' }}>
          <h4 style={{ fontSize: 14, marginBottom: 12, fontWeight: 700 }}>{t('ingest.tips_title')}</h4>
          <ul style={{ fontSize: 13, color: 'var(--text-secondary)', paddingLeft: 20, lineHeight: 1.8, margin: 0 }}>
            <li>{t('ingest.tip_1')}</li>
            <li>{t('ingest.tip_2')}</li>
            <li>{t('ingest.tip_3')}</li>
          </ul>
        </Card>
      </div>
    </div>
  );
}
