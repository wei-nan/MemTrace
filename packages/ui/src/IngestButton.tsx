import { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Upload, Loader2, FileText } from 'lucide-react';
import { ingest } from './api';
import { useModal } from './components/ModalContext';

export default function IngestButton({ wsId, onStarted }: { wsId: string, onStarted: () => void }) {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const { toast } = useModal();
  const [uploading, setUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const processFile = async (file: File) => {
    // Only allow .txt and .md
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (ext !== 'txt' && ext !== 'md') {
      toast({ 
        message: zh ? '僅支援 .txt 與 .md 檔案' : 'Only .txt and .md files are supported', 
        variant: 'error' 
      });
      return;
    }

    setUploading(true);
    try {
      await ingest.upload(wsId, file);
      toast({ 
        message: zh ? '文件已上傳，背景處理中…' : 'File uploaded, processing in background…', 
        variant: 'success' 
      });
      onStarted();
    } catch (e: any) {
      toast({ message: e.message, variant: 'error' });
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) processFile(file);
  };

  return (
    <div 
      className={`ingest-dropzone ${isDragging ? 'dragging' : ''} ${uploading ? 'uploading' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => !uploading && fileInputRef.current?.click()}
    >
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        style={{ display: 'none' }}
        accept=".txt,.md"
      />
      
      <div className="ingest-icon-wrapper">
        {uploading ? (
          <Loader2 size={32} className="animate-spin" />
        ) : isDragging ? (
          <FileText size={32} />
        ) : (
          <Upload size={32} />
        )}
      </div>

      <div className="ingest-text">
        <div className="main-text">
          {uploading 
            ? (zh ? '正在上傳文件...' : 'Uploading file...') 
            : (zh ? '攝入新文件' : 'Ingest New File')}
        </div>
        <div className="sub-text">
          {isDragging 
            ? (zh ? '放開以開始解析' : 'Drop to start analyzing') 
            : (zh ? '點擊或將檔案拖移至此' : 'Click or drag file here')}
        </div>
      </div>

      <style>{`
        .ingest-dropzone {
          width: 100%;
          min-height: 160px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 16px;
          padding: 32px;
          background: var(--bg-surface);
          border: 2px dashed var(--border-default);
          border-radius: 16px;
          cursor: pointer;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          color: var(--text-secondary);
        }

        .ingest-dropzone:hover {
          border-color: var(--color-primary);
          background: var(--color-primary-subtle);
          color: var(--color-primary);
        }

        .ingest-dropzone.dragging {
          border-color: var(--color-primary);
          background: var(--color-primary-subtle);
          color: var(--color-primary);
          transform: scale(1.02);
          box-shadow: var(--shadow-xl);
        }

        .ingest-dropzone.uploading {
          cursor: wait;
          opacity: 0.8;
          border-style: solid;
        }

        .ingest-icon-wrapper {
          width: 64px;
          height: 64px;
          border-radius: 32px;
          background: var(--bg-elevated);
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.3s;
          color: inherit;
        }

        .ingest-dropzone:hover .ingest-icon-wrapper,
        .ingest-dropzone.dragging .ingest-icon-wrapper {
          background: white;
          color: var(--color-primary);
          box-shadow: var(--shadow-md);
        }

        .ingest-text {
          text-align: center;
        }

        .main-text {
          font-size: 16px;
          font-weight: 600;
          margin-bottom: 4px;
        }

        .sub-text {
          font-size: 13px;
          opacity: 0.7;
        }

        @keyframes animate-spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .animate-spin {
          animation: animate-spin 1s linear infinite;
        }
      `}</style>
    </div>
  );
}
