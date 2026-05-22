import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Brain } from 'lucide-react';
import { workspaces, type Workspace } from '../api';
import { Modal, Button, Input, Card } from './ui';
import { useProviderModels } from '../hooks/useProviderModels';

export default function CreateWorkspaceModal({
  onCreated,
  onClose,
}: {
  onCreated: (ws: Workspace) => void;
  onClose: () => void;
}) {
  const { t, i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  
  const [name, setName] = useState('');
  const [language, setLanguage] = useState<'zh-TW' | 'en'>('zh-TW');
  const [kbType, setKbType] = useState<'evergreen' | 'ephemeral'>('evergreen');
  const [visibility, setVisibility] = useState<'private' | 'restricted' | 'conditional_public' | 'public'>('private');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const { models: embedModels, loading: modelsLoading } = useProviderModels('embedding');
  const [selectedEmbedModel, setSelectedEmbedModel] = useState<string>('');

  useEffect(() => {
    if (i18n.language === 'zh-TW' || i18n.language === 'en') {
      setLanguage(i18n.language as any);
    }
  }, [i18n.language]);

  useEffect(() => {
    if (embedModels.length > 0 && !selectedEmbedModel) {
      setSelectedEmbedModel(embedModels[0].id);
    }
  }, [embedModels]);

  const handleSubmit = async () => {
    if (!name.trim()) {
      setError(zh ? '請填寫工作區名稱' : 'Workspace name is required');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const ws = await workspaces.create({
        name: name.trim(),
        language,
        visibility,
        kb_type: kbType,
        embedding_model: selectedEmbedModel || undefined,
      });
      onCreated(ws);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const typeOptions: { value: 'evergreen' | 'ephemeral'; label: string; desc: string }[] = [
    {
      value: 'evergreen',
      label: zh ? '長效型 (Evergreen)' : 'Evergreen',
      desc: zh
        ? '規格書、參考資料。記憶不會因時間淡化，低參考率者才會封存。'
        : 'Specs, references. Nodes never decay by time — only archived by low traversal.',
    },
    {
      value: 'ephemeral',
      label: zh ? '短效型 (Ephemeral)' : 'Ephemeral',
      desc: zh
        ? '任務日誌、排障記錄。記憶隨時間與使用頻率衰減，過時內容自動封存。'
        : 'Task logs, troubleshooting. Nodes decay over time and usage; stale content is archived.',
    },
  ];

  const footer = (
    <>
      <Button variant="ghost" onClick={onClose} disabled={loading}>
        {zh ? '取消' : 'Cancel'}
      </Button>
      <Button onClick={handleSubmit} loading={loading} disabled={loading}>
        {zh ? '建立' : 'Create'}
      </Button>
    </>
  );

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title={zh ? '建立工作區' : 'Create Workspace'}
      width={520}
      footer={footer}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
          <Input
            label={zh ? '工作區名稱' : 'Workspace Name'}
            placeholder={zh ? '例：我的知識庫' : 'e.g. My Knowledge Base'}
            value={name}
            onChange={e => setName(e.target.value)}
          />
          <div>
            <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 8 }}>
              {zh ? '語言' : 'Language'}
            </label>
            <select
              className="mt-input-field"
              style={{ width: '100%', padding: '10px 12px', border: '1px solid var(--border-default)', borderRadius: 8, background: 'var(--bg-surface)', height: 40 }}
              value={language}
              onChange={e => setLanguage(e.target.value as any)}
            >
              <option value="zh-TW">繁體中文</option>
              <option value="en">English</option>
            </select>
          </div>
        </div>

        <div>
          <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 8 }}>
            {zh ? '知識庫類型' : 'KB Type'}
          </label>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {typeOptions.map(opt => (
              <Card
                key={opt.value}
                padding="sm"
                variant={kbType === opt.value ? 'elevated' : 'outline'}
                onClick={() => setKbType(opt.value)}
                style={{ 
                  borderColor: kbType === opt.value ? 'var(--color-primary)' : undefined,
                  background: kbType === opt.value ? 'var(--color-primary-subtle)' : undefined
                }}
              >
                <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>{opt.label}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.4 }}>{opt.desc}</div>
              </Card>
            ))}
          </div>
        </div>

        <div>
          <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 8 }}>
            {zh ? '可見度' : 'Visibility'}
          </label>
          <select
            className="mt-input-field"
            style={{ width: '100%', padding: '10px 12px', border: '1px solid var(--border-default)', borderRadius: 8, background: 'var(--bg-surface)' }}
            value={visibility}
            onChange={e => setVisibility(e.target.value as any)}
          >
            <option value="private">{t('ws_settings.vis_private')}</option>
            <option value="restricted">{t('ws_settings.vis_restricted')}</option>
            <option value="conditional_public">{t('ws_settings.vis_conditional_public')}</option>
            <option value="public">{t('ws_settings.vis_public')}</option>
          </select>
        </div>

        <div>
          <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
            <Brain size={14} />
            {zh ? '向量模型' : 'Embedding Model'}
          </label>
          {modelsLoading ? (
            <div style={{ height: 40, background: 'var(--bg-elevated)', borderRadius: 8, border: '1px dashed var(--border-default)', display: 'flex', alignItems: 'center', padding: '0 12px' }}>
              <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>{zh ? '載入中…' : 'Loading models…'}</span>
            </div>
          ) : (
            <select
              className="mt-input-field"
              style={{ width: '100%', padding: '10px 12px', border: '1px solid var(--border-default)', borderRadius: 8, background: 'var(--bg-surface)' }}
              value={selectedEmbedModel}
              onChange={e => setSelectedEmbedModel(e.target.value)}
            >
              {embedModels.map(m => (
                <option key={`${m.provider}-${m.id}`} value={m.id}>
                  {m.id} ({m.dim}d) — {m.provider.toUpperCase()}
                </option>
              ))}
            </select>
          )}
        </div>

        {error && (
          <div style={{ 
            padding: '10px 14px', borderRadius: 8, background: 'var(--color-error-subtle)', 
            color: 'var(--color-error)', fontSize: 13, border: '1px solid var(--color-error)' 
          }}>
            {error}
          </div>
        )}
      </div>
    </Modal>
  );
}
