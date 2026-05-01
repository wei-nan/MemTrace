import { useState, useMemo, useEffect } from 'react';
import { FileText, CheckCircle2 } from 'lucide-react';
import type { Segment } from '../utils/document';
import { injectContext } from '../utils/document';
import Modal from './Modal';
import ExcelSheetSelector from './ExcelSheetSelector';
import type { SheetInfo, SheetConfig } from './ExcelSheetSelector';

interface ImportPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  filename: string;
  segments: Segment[];
  onConfirm: (docType: string, seeds?: string[]) => void;
  loading?: boolean;
  // B-3: Excel sheet selection
  excelSheets?: SheetInfo[];
  selectedSheets?: string[];
  onSelectedSheetsChange?: (sheets: string[]) => void;
  columnMapping?: Record<string, SheetConfig>;
  onColumnMappingChange?: (mapping: Record<string, SheetConfig>) => void;
}

const DOC_TYPES = [
  { id: 'generic', label: '通用文件 (Generic)' },
  { id: 'FRD', label: '功能需求文件 (FRD)' },
  { id: 'TSD', label: '技術規格文件 (TSD)' },
  { id: 'ADR', label: '架構決策紀錄 (ADR)' },
];

export default function ImportPreviewModal({
  isOpen,
  onClose,
  filename,
  segments,
  onConfirm,
  loading = false,
  excelSheets = [],
  selectedSheets = [],
  onSelectedSheetsChange,
  columnMapping = {},
  onColumnMappingChange,
}: ImportPreviewModalProps) {
  const [docType, setDocType] = useState('generic');
  const [selectedSegIndex, setSelectedSegIndex] = useState(0);

  // D-2: Heuristic scan for API seeds across all segments
  const apiSeeds = useMemo(() => {
    const fullContent = segments.map(s => s.content).join('\n');
    const regex = /(GET|POST|PUT|DELETE|PATCH)\s+(\/[a-zA-Z0-9_\-/{}]+)/gi;
    const found = new Set<string>();
    let match;
    while ((match = regex.exec(fullContent)) !== null) {
      found.add(`${match[1].toUpperCase()} ${match[2]}`);
    }
    return Array.from(found);
  }, [segments]);

  const [approvedSeeds, setApprovedSeeds] = useState<string[]>([]);
  
  // Sync approvedSeeds when apiSeeds changes (e.g. new file loaded)
  useEffect(() => {
    setApprovedSeeds(apiSeeds);
  }, [apiSeeds]);
  
  // Toggle seed approval
  const toggleSeed = (seed: string) => {
    setApprovedSeeds(prev => 
      prev.includes(seed) ? prev.filter(s => s !== seed) : [...prev, seed]
    );
  };

  const currentSegment = segments[selectedSegIndex];
  const injectedContent = useMemo(() => 
    currentSegment ? injectContext(currentSegment) : ''
  , [currentSegment]);

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose} 
      title={`匯入預覽: ${filename}`}
      width={1000}
    >
      <div style={{ display: 'flex', flexDirection: 'column', height: '70vh', gap: 20 }}>
        
        {/* Top Controls: Doc Type Selection */}
        <div style={{ 
          padding: '16px 20px', 
          background: 'var(--bg-surface)', 
          borderRadius: 12, 
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 16
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <label style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)' }}>
              文件類型分析引導:
            </label>
            <div style={{ display: 'flex', gap: 8 }}>
              {DOC_TYPES.map(type => (
                <button
                  key={type.id}
                  onClick={() => setDocType(type.id)}
                  style={{
                    padding: '6px 12px',
                    borderRadius: 6,
                    border: '1px solid',
                    borderColor: docType === type.id ? 'var(--color-primary)' : 'var(--border-default)',
                    background: docType === type.id ? 'var(--color-primary-subtle)' : 'transparent',
                    color: docType === type.id ? 'var(--color-primary)' : 'var(--text-secondary)',
                    fontSize: 13,
                    fontWeight: 500,
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                >
                  {type.label}
                </button>
              ))}
            </div>
          </div>

          {apiSeeds.length > 0 && (
            <div style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
              <CheckCircle2 size={14} color="var(--color-success)" />
              偵測到 {apiSeeds.length} 個 API 種子
            </div>
          )}

          {/* Format Badge */}
          <div style={{
            padding: '4px 10px',
            borderRadius: 20,
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-default)',
            fontSize: 11,
            fontWeight: 600,
            color: 'var(--text-muted)',
            display: 'flex',
            alignItems: 'center',
            gap: 6
          }}>
            <div style={{ width: 6, height: 6, borderRadius: 3, background: 'var(--color-success)' }} />
            {filename.split('.').pop()?.toUpperCase() || 'FILE'} ADAPTER
          </div>
        </div>

        {/* Main Content Area: Split View */}
        <div style={{ display: 'flex', flex: 1, overflow: 'hidden', gap: 20 }}>
          
          {/* Left Sidebar: Segment List / Excel Sheet Selector / Seed Approval */}
          <div style={{ 
            width: 300, 
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
            overflow: 'hidden'
          }}>
            {/* B-3: Excel Sheet Selector (replaces segment list for Excel files) */}
            {excelSheets.length > 0 && onSelectedSheetsChange && onColumnMappingChange ? (
              <div style={{ flex: 1, overflowY: 'auto' }}>
                <ExcelSheetSelector
                  sheets={excelSheets}
                  selectedSheets={selectedSheets}
                  onSelectedSheetsChange={onSelectedSheetsChange}
                  columnMapping={columnMapping}
                  onColumnMappingChange={onColumnMappingChange}
                />
              </div>
            ) : (
              /* Segments */
              <div style={{ 
                flex: 1,
                overflowY: 'auto', 
                border: '1px solid var(--border-subtle)', 
                borderRadius: 12,
                background: 'var(--bg-elevated)'
              }}>
                <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-subtle)', fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  掃描到 {segments.length} 個區塊
                </div>
                {segments.map((seg, idx) => (
                  <div 
                    key={seg.id}
                    onClick={() => setSelectedSegIndex(idx)}
                    style={{
                      padding: '12px 16px',
                      cursor: 'pointer',
                      borderBottom: '1px solid var(--border-subtle)',
                      background: selectedSegIndex === idx ? 'var(--color-primary-subtle)' : 'transparent',
                      borderLeft: selectedSegIndex === idx ? '3px solid var(--color-primary)' : '3px solid transparent',
                      transition: 'all 0.2s'
                    }}
                  >
                    <div style={{ 
                      fontSize: 13, 
                      fontWeight: 600, 
                      color: selectedSegIndex === idx ? 'var(--color-primary)' : 'var(--text-primary)',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }}>
                      {seg.heading || `Block ${idx + 1}`}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                      {seg.content.length} characters
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* API Seeds (D-2) */}
            {apiSeeds.length > 0 && (
              <div style={{ 
                height: 200,
                overflowY: 'auto', 
                border: '1px solid var(--border-subtle)', 
                borderRadius: 12,
                background: 'var(--bg-elevated)'
              }}>
                <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-subtle)', fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', display: 'flex', justifyContent: 'space-between' }}>
                  <span>API 種子節點 (核可清單)</span>
                  <span style={{ color: 'var(--color-primary)' }}>{approvedSeeds.length} / {apiSeeds.length}</span>
                </div>
                {apiSeeds.map((seed) => (
                  <div 
                    key={seed}
                    onClick={() => toggleSeed(seed)}
                    style={{
                      padding: '8px 16px',
                      cursor: 'pointer',
                      borderBottom: '1px solid var(--border-subtle)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 10,
                      opacity: approvedSeeds.includes(seed) ? 1 : 0.5,
                      background: approvedSeeds.includes(seed) ? 'var(--bg-surface)' : 'transparent',
                      transition: 'all 0.2s'
                    }}
                  >
                    <input 
                      type="checkbox" 
                      checked={approvedSeeds.includes(seed)} 
                      onChange={() => {}} // Controlled by parent div click
                      style={{ cursor: 'pointer' }}
                    />
                    <div style={{ fontSize: 12, fontWeight: 500, fontFamily: 'var(--font-mono)' }}>
                      {seed}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right Content: Preview */}
          <div style={{ 
            flex: 1, 
            display: 'flex', 
            flexDirection: 'column',
            overflow: 'hidden',
            border: '1px solid var(--border-subtle)', 
            borderRadius: 12,
            background: 'white'
          }}>
            <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, fontWeight: 600 }}>
                <FileText size={16} />
                區塊內容預覽 (含 Context 注入)
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                {currentSegment?.headingChain.join(' > ')}
              </div>
            </div>
            <div style={{ flex: 1, padding: 20, overflowY: 'auto', fontFamily: 'var(--font-mono)', fontSize: 13, lineHeight: 1.6, whiteSpace: 'pre-wrap', color: 'var(--text-secondary)' }}>
              {injectedContent}
            </div>
          </div>

        </div>

        {/* Footer Actions */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, paddingTop: 10 }}>
          <button 
            className="btn-secondary" 
            onClick={onClose}
            disabled={loading}
          >
            取消
          </button>
          <button 
            className="btn-primary" 
            style={{ minWidth: 140 }}
            onClick={() => onConfirm(docType, approvedSeeds)}
            disabled={loading}
          >
            {loading ? '處理中...' : '開始分析與匯入'}
          </button>
        </div>

      </div>
    </Modal>
  );
}
