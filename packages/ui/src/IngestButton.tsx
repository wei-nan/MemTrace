import { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Upload, Loader2 } from 'lucide-react';
import { ingest } from './api';

export default function IngestButton({ wsId, onStarted }: { wsId: string, onStarted: () => void }) {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      await ingest.upload(wsId, file);
      alert(zh ? '文件已上傳，背景處理中…' : 'File uploaded, processing in background…');
      onStarted();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div style={{ padding: '0 12px' }}>
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        style={{ display: 'none' }}
        accept=".txt,.md"
      />
      <button
        onClick={() => fileInputRef.current?.click()}
        disabled={uploading}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', gap: 10,
          padding: '10px 12px', background: 'var(--color-primary-subtle)',
          border: '1px dashed var(--color-primary)', borderRadius: 8,
          cursor: 'pointer', color: 'var(--color-primary)', fontSize: 13,
          transition: 'all 0.2s',
        }}
        onMouseOver={e => e.currentTarget.style.background = 'var(--color-primary-subtle)'}
        onMouseOut={e => e.currentTarget.style.background = 'var(--color-primary-subtle)'}
      >
        {uploading ? <Loader2 size={18} className="animate-spin" /> : <Upload size={18} />}
        <span style={{ fontWeight: 500 }}>{zh ? '攝入新文件' : 'Ingest File'}</span>
      </button>
    </div>
  );
}
