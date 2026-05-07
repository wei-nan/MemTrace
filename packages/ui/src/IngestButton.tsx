import { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Upload, Loader2, FileText, CheckCircle2, XCircle, Clock, Trash2 } from 'lucide-react';
import { ingest } from './api';
import { useModal } from './components/ModalContext';

export default function IngestButton({ wsId, onStarted }: { wsId: string, onStarted: () => void }) {
  const { t, i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const { toast } = useModal();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [fileQueue, setFileQueue] = useState<{ file: File; status: 'pending' | 'processing' | 'done' | 'failed'; jobId?: string; error?: string }[]>([]);

  const processFiles = (files: File[]) => {
    const textFormats = ['txt', 'md', 'sql', 'yaml', 'yml', 'json', 'py', 'js', 'ts', 'tsx', 'jsx', 'diff', 'patch', 'eml'];
    const binaryFormats = ['pdf', 'docx', 'pptx', 'xlsx', 'xls', 'csv'];
    
    const validFiles = files.filter(file => {
      const ext = file.name.split('.').pop()?.toLowerCase() || '';
      return textFormats.includes(ext) || binaryFormats.includes(ext);
    });

    if (validFiles.length < files.length) {
      toast({ message: t('ingest.file_support_err'), variant: 'warning' });
    }

    setFileQueue(prev => [
      ...prev,
      ...validFiles.map(f => ({ file: f, status: 'pending' as const }))
    ]);
  };

  const startBatchIngest = async () => {
    if (fileQueue.length === 0 || uploading) return;
    
    setUploading(true);
    const newBatchId = `batch_${Date.now()}`;

    const updatedQueue = [...fileQueue];
    
    for (let i = 0; i < updatedQueue.length; i++) {
      if (updatedQueue[i].status !== 'pending') continue;

      updatedQueue[i].status = 'processing';
      setFileQueue([...updatedQueue]);

      try {
        const res = await ingest.upload(wsId, updatedQueue[i].file, 'generic', undefined, undefined, { batch_id: newBatchId, queue_position: i });
        updatedQueue[i].status = 'done';
        updatedQueue[i].jobId = res.job_id;
      } catch (e: any) {
        updatedQueue[i].status = 'failed';
        updatedQueue[i].error = e.message;
      }
      setFileQueue([...updatedQueue]);
    }

    setUploading(false);
    onStarted();
    toast({ message: t('ingest.batch_complete', { defaultValue: 'Batch ingestion complete' }), variant: 'success' });
  };

  const removeFromQueue = (index: number) => {
    setFileQueue(prev => prev.filter((_, i) => i !== index));
  };

  const cancelJob = async (index: number) => {
    const item = fileQueue[index];
    if (!item.jobId) return;
    try {
      await ingest.cancel(wsId, item.jobId);
      setFileQueue(prev => {
        const next = [...prev];
        next[index].status = 'failed';
        next[index].error = 'Cancelled';
        return next;
      });
    } catch (e: any) {
      toast({ message: e.message, variant: 'error' });
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) processFiles(files);
    if (fileInputRef.current) fileInputRef.current.value = '';
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
    const files = Array.from(e.dataTransfer.files || []);
    if (files.length > 0) processFiles(files);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div 
        className={`ingest-dropzone ${isDragging ? 'dragging' : ''} ${uploading ? 'uploading' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !uploading && fileInputRef.current?.click()}
      >
        <input
          type="file"
          multiple
          ref={fileInputRef}
          onChange={handleFileChange}
          style={{ display: 'none' }}
          accept=".txt,.md,.pdf,.docx,.pptx,.xlsx,.xls,.csv,.sql,.yaml,.yml,.json,.py,.js,.ts,.tsx,.jsx,.eml,.diff,.patch"
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

        <div style={{ textAlign: 'center' }}>
          <p style={{ margin: 0, fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>
            {zh ? '拖放檔案至此或點擊上傳' : 'Drag & drop files here or click to upload'}
          </p>
          <p style={{ margin: '8px 0 0', fontSize: 12, opacity: 0.6 }}>
            {zh ? '支援多檔案選取 (TXT, PDF, DOCX, Excel, JSON...)' : 'Support multi-file selection (TXT, PDF, DOCX, Excel, JSON...)'}
          </p>
        </div>
      </div>

      {fileQueue.length > 0 && (
        <div style={{ background: 'var(--bg-elevated)', borderRadius: 16, padding: 20, border: '1px solid var(--border-subtle)', marginTop: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>{zh ? '待處理佇列' : 'Ingestion Queue'}</h3>
            <button 
              className="btn-primary" 
              onClick={startBatchIngest} 
              disabled={uploading || !fileQueue.some(i => i.status === 'pending')}
              style={{ fontSize: 12, padding: '6px 12px' }}
            >
              {uploading ? (zh ? '處理中...' : 'Processing...') : (zh ? '開始全部攝入' : 'Start Ingest All')}
            </button>
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {fileQueue.map((item, idx) => (
              <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 13, padding: '8px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1, minWidth: 0 }}>
                  {item.status === 'processing' ? <Loader2 size={14} className="animate-spin" color="var(--color-primary)" /> : 
                   item.status === 'done' ? <CheckCircle2 size={14} color="var(--color-success)" /> :
                   item.status === 'failed' ? <XCircle size={14} color="var(--color-error)" /> :
                   <Clock size={14} color="var(--text-muted)" />}
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.file.name}</span>
                </div>
                
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {item.status === 'pending' ? (zh ? '等待中' : 'Pending') :
                     item.status === 'processing' ? (zh ? '處理中' : 'Processing') :
                     item.status === 'done' ? (zh ? '完成' : 'Done') :
                     (item.error || (zh ? '失敗' : 'Failed'))}
                  </span>
                  
                  {item.status === 'failed' && (
                    <button 
                      onClick={() => {
                        const newQueue = [...fileQueue];
                        newQueue[idx].status = 'pending';
                        newQueue[idx].error = undefined;
                        setFileQueue(newQueue);
                      }} 
                      style={{ background: 'none', border: 'none', color: 'var(--color-primary)', cursor: 'pointer', padding: 4, fontSize: 11, fontWeight: 700 }}
                    >
                      {zh ? '重試' : 'Retry'}
                    </button>
                  )}
                  {item.status === 'pending' && (
                    <button onClick={() => removeFromQueue(idx)} style={{ background: 'none', border: 'none', color: 'var(--color-error)', cursor: 'pointer', padding: 4 }}>
                      <Trash2 size={14} />
                    </button>
                  )}
                  {item.status === 'processing' && (
                    <button onClick={() => cancelJob(idx)} style={{ background: 'none', border: 'none', color: 'var(--color-error)', cursor: 'pointer', padding: 4 }}>
                      <XCircle size={14} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

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
