import { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Upload, Loader2, FileText } from 'lucide-react';
import { ingest } from './api';
import { useModal } from './components/ModalContext';
import { segmentDocument } from './utils/document';
import type { Segment } from './utils/document';
import ImportPreviewModal from './components/ImportPreviewModal';
import type { SheetInfo, SheetConfig } from './components/ExcelSheetSelector';

export default function IngestButton({ wsId, onStarted }: { wsId: string, onStarted: () => void }) {
  const { t } = useTranslation();
  const { toast } = useModal();
  const [uploading, setUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Preview State
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewFile, setPreviewFile] = useState<File | null>(null);
  const [segments, setSegments] = useState<Segment[]>([]);

  // B-3: Excel preview state
  const [excelSheets, setExcelSheets] = useState<SheetInfo[]>([]);
  const [selectedSheets, setSelectedSheets] = useState<string[]>([]);
  const [columnMapping, setColumnMapping] = useState<Record<string, SheetConfig>>({});

  const processFile = async (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase() || '';
    const textFormats = ['txt', 'md', 'sql', 'yaml', 'yml', 'json', 'py', 'js', 'ts', 'tsx', 'jsx', 'diff', 'patch', 'eml'];
    const binaryFormats = ['pdf', 'docx', 'pptx', 'xlsx', 'xls', 'csv'];
    
    if (!textFormats.includes(ext) && !binaryFormats.includes(ext)) {
      toast({ message: t('ingest.file_support_err'), variant: 'error' });
      return;
    }

    if (textFormats.includes(ext)) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target?.result as string;
        const segs = segmentDocument(text);
        setSegments(segs);
        setExcelSheets([]);
        setPreviewFile(file);
        setPreviewOpen(true);
      };
      reader.readAsText(file);
    } else if (['xlsx', 'xls', 'csv'].includes(ext)) {
      // B-3: Fetch Excel sheet preview from backend
      try {
        const preview = await ingest.excelPreview(wsId, file);
        setExcelSheets(preview.sheets || []);
        setSelectedSheets((preview.sheets || []).map((s: SheetInfo) => s.name));
        setColumnMapping({});
        setSegments([{
          id: 'excel_preview',
          heading: file.name,
          headingChain: [file.name],
          content: `Excel/CSV - ${(preview.sheets || []).length} sheet(s)\nFormat: ${ext.toUpperCase()}`,
          startIndex: 0,
          endIndex: file.size
        }]);
        setPreviewFile(file);
        setPreviewOpen(true);
      } catch (e: any) {
        toast({ message: e.message, variant: 'error' });
      }
    } else {
      setSegments([{ 
        id: 'binary_preview',
        heading: file.name, 
        headingChain: [file.name],
        content: `[Binary Content - ${file.size} bytes]\nFormat: ${ext.toUpperCase()}`,
        startIndex: 0,
        endIndex: file.size
      }]);
      setExcelSheets([]);
      setPreviewFile(file);
      setPreviewOpen(true);
    }
  };

  const handleConfirmIngest = async (docType: string, seeds?: string[]) => {
    if (!previewFile) return;
    
    setUploading(true);
    setPreviewOpen(false);
    try {
      // B-3: Pass Excel config if applicable
      const excelConfig = excelSheets.length > 0 ? {
        selected_sheets: selectedSheets,
        column_mapping: columnMapping,
      } : undefined;
      await ingest.upload(wsId, previewFile, docType, seeds, excelConfig);
      toast({ message: t('ingest.file_success'), variant: 'success' });
      onStarted();
    } catch (e: any) {
      toast({ message: e.message, variant: 'error' });
    } finally {
      setUploading(false);
      setPreviewFile(null);
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

      <div className="ingest-text">
        <div className="main-text">
          {uploading 
            ? t('ingest.uploading') 
            : t('ingest.btn_new')}
        </div>
        <div className="sub-text">
          {isDragging 
            ? t('ingest.drop_analyzing') 
            : t('ingest.click_or_drag')}
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

      {previewFile && (
        <ImportPreviewModal
          isOpen={previewOpen}
          onClose={() => setPreviewOpen(false)}
          filename={previewFile.name}
          segments={segments}
          onConfirm={handleConfirmIngest}
          loading={uploading}
          excelSheets={excelSheets}
          selectedSheets={selectedSheets}
          onSelectedSheetsChange={setSelectedSheets}
          columnMapping={columnMapping}
          onColumnMappingChange={setColumnMapping}
        />
      )}
    </div>
  );
}
