import { useState, useEffect } from 'react';
import { Table, ChevronDown, ChevronRight } from 'lucide-react';

interface SheetInfo {
  name: string;
  columns: string[];
  row_count: number;
  detected_mode: 'row' | 'table';
  detected_title_col: string | null;
  detected_desc_col: string | null;
  detected_tag_col: string | null;
  sample_rows: Record<string, any>[];
}

interface SheetConfig {
  title_col: string | null;
  desc_col: string | null;
  tag_col: string | null;
  mode: 'row' | 'table';
}

interface ExcelSheetSelectorProps {
  sheets: SheetInfo[];
  selectedSheets: string[];
  onSelectedSheetsChange: (sheets: string[]) => void;
  columnMapping: Record<string, SheetConfig>;
  onColumnMappingChange: (mapping: Record<string, SheetConfig>) => void;
}

export default function ExcelSheetSelector({
  sheets,
  selectedSheets,
  onSelectedSheetsChange,
  columnMapping,
  onColumnMappingChange,
}: ExcelSheetSelectorProps) {
  const [expandedSheet, setExpandedSheet] = useState<string | null>(null);

  // Initialize mapping from detected values
  useEffect(() => {
    if (Object.keys(columnMapping).length === 0 && sheets.length > 0) {
      const initial: Record<string, SheetConfig> = {};
      for (const s of sheets) {
        initial[s.name] = {
          title_col: s.detected_title_col,
          desc_col: s.detected_desc_col,
          tag_col: s.detected_tag_col,
          mode: s.detected_mode,
        };
      }
      onColumnMappingChange(initial);
    }
  }, [sheets]);

  const toggleSheet = (name: string) => {
    onSelectedSheetsChange(
      selectedSheets.includes(name)
        ? selectedSheets.filter(s => s !== name)
        : [...selectedSheets, name]
    );
  };

  const updateMapping = (sheetName: string, field: keyof SheetConfig, value: string | null) => {
    onColumnMappingChange({
      ...columnMapping,
      [sheetName]: {
        ...(columnMapping[sheetName] || {}),
        [field]: value,
      } as SheetConfig,
    });
  };

  return (
    <div style={{
      border: '1px solid var(--border-subtle)',
      borderRadius: 12,
      background: 'var(--bg-elevated)',
      overflow: 'hidden',
    }}>
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid var(--border-subtle)',
        fontSize: 12,
        fontWeight: 700,
        color: 'var(--text-muted)',
        textTransform: 'uppercase',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <span>Sheet 選擇與欄位映射</span>
        <span style={{ color: 'var(--color-primary)', fontWeight: 600 }}>
          {selectedSheets.length} / {sheets.length} sheets
        </span>
      </div>

      {sheets.map(sheet => {
        const isSelected = selectedSheets.includes(sheet.name);
        const isExpanded = expandedSheet === sheet.name;
        const config = columnMapping[sheet.name] || {
          title_col: sheet.detected_title_col,
          desc_col: sheet.detected_desc_col,
          tag_col: sheet.detected_tag_col,
          mode: sheet.detected_mode,
        };

        return (
          <div key={sheet.name} style={{
            borderBottom: '1px solid var(--border-subtle)',
            opacity: isSelected ? 1 : 0.5,
            transition: 'opacity 0.2s',
          }}>
            {/* Sheet header row */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              padding: '10px 16px',
              gap: 12,
              cursor: 'pointer',
            }}>
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => toggleSheet(sheet.name)}
                style={{ cursor: 'pointer', width: 16, height: 16 }}
              />
              <div
                onClick={() => setExpandedSheet(isExpanded ? null : sheet.name)}
                style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 8 }}
              >
                {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                <Table size={14} color="var(--color-primary)" />
                <span style={{ fontWeight: 600, fontSize: 13 }}>{sheet.name}</span>
                <span style={{
                  fontSize: 11,
                  color: 'var(--text-muted)',
                  padding: '2px 8px',
                  background: 'var(--bg-surface)',
                  borderRadius: 10,
                }}>
                  {sheet.row_count} rows · {sheet.columns.length} cols
                </span>
              </div>

              {/* Mode toggle */}
              <div style={{ display: 'flex', gap: 4 }}>
                {(['row', 'table'] as const).map(m => (
                  <button
                    key={m}
                    onClick={(e) => { e.stopPropagation(); updateMapping(sheet.name, 'mode', m); }}
                    style={{
                      padding: '3px 10px',
                      borderRadius: 4,
                      border: '1px solid',
                      borderColor: config.mode === m ? 'var(--color-primary)' : 'var(--border-default)',
                      background: config.mode === m ? 'var(--color-primary-subtle)' : 'transparent',
                      color: config.mode === m ? 'var(--color-primary)' : 'var(--text-muted)',
                      fontSize: 11,
                      fontWeight: 500,
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                    }}
                  >
                    {m === 'row' ? '列模式' : '表模式'}
                  </button>
                ))}
              </div>
            </div>

            {/* Expanded: Column mapping */}
            {isExpanded && isSelected && (
              <div style={{
                padding: '12px 16px 16px 44px',
                background: 'var(--bg-surface)',
                borderTop: '1px solid var(--border-subtle)',
              }}>
                <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 12 }}>
                  {/* Title column selector */}
                  <ColumnSelector
                    label="標題欄位 (Title)"
                    value={config.title_col}
                    columns={sheet.columns}
                    onChange={(v) => updateMapping(sheet.name, 'title_col', v)}
                  />
                  {/* Description column selector */}
                  <ColumnSelector
                    label="說明欄位 (Description)"
                    value={config.desc_col}
                    columns={sheet.columns}
                    onChange={(v) => updateMapping(sheet.name, 'desc_col', v)}
                  />
                  {/* Tag column selector */}
                  <ColumnSelector
                    label="標籤欄位 (Tags)"
                    value={config.tag_col}
                    columns={sheet.columns}
                    onChange={(v) => updateMapping(sheet.name, 'tag_col', v)}
                  />
                </div>

                {/* Sample data preview */}
                {sheet.sample_rows.length > 0 && (
                  <div style={{
                    maxHeight: 150,
                    overflow: 'auto',
                    borderRadius: 8,
                    border: '1px solid var(--border-subtle)',
                  }}>
                    <table style={{
                      width: '100%',
                      borderCollapse: 'collapse',
                      fontSize: 11,
                      fontFamily: 'var(--font-mono)',
                    }}>
                      <thead>
                        <tr>
                          {sheet.columns.map(col => (
                            <th key={col} style={{
                              padding: '6px 8px',
                              background: 'var(--bg-elevated)',
                              borderBottom: '1px solid var(--border-subtle)',
                              textAlign: 'left',
                              fontWeight: 700,
                              color: [config.title_col, config.desc_col, config.tag_col].includes(col)
                                ? 'var(--color-primary)'
                                : 'var(--text-muted)',
                              whiteSpace: 'nowrap',
                            }}>
                              {col}
                              {col === config.title_col && ' 📌'}
                              {col === config.desc_col && ' 📝'}
                              {col === config.tag_col && ' 🏷️'}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {sheet.sample_rows.map((row, i) => (
                          <tr key={i}>
                            {sheet.columns.map(col => (
                              <td key={col} style={{
                                padding: '4px 8px',
                                borderBottom: '1px solid var(--border-subtle)',
                                maxWidth: 200,
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap',
                                color: 'var(--text-secondary)',
                              }}>
                                {String(row[col] ?? '')}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function ColumnSelector({
  label,
  value,
  columns,
  onChange,
}: {
  label: string;
  value: string | null;
  columns: string[];
  onChange: (v: string | null) => void;
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)' }}>
        {label}
      </label>
      <select
        value={value || ''}
        onChange={(e) => onChange(e.target.value || null)}
        style={{
          padding: '5px 8px',
          borderRadius: 6,
          border: '1px solid var(--border-default)',
          background: 'var(--bg-elevated)',
          fontSize: 12,
          color: 'var(--text-primary)',
          minWidth: 140,
          cursor: 'pointer',
        }}
      >
        <option value="">— 不選擇 —</option>
        {columns.map(col => (
          <option key={col} value={col}>{col}</option>
        ))}
      </select>
    </div>
  );
}

export type { SheetInfo, SheetConfig };
