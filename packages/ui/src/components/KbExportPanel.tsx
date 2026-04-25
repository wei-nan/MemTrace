import { useRef, useState, useEffect } from 'react';
import { Download, CheckCircle, Clock, AlertCircle, Loader2, Upload, Tag, X } from 'lucide-react';
import { workspaces, type KBExport, type KBImportResponse } from '../api';
import { useTranslation } from 'react-i18next';

type ActiveTab = 'export' | 'import';

export default function KbExportPanel({ wsId }: { wsId: string; zh?: boolean }) {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<ActiveTab>('export');

  // ── Export state ──────────────────────────────────────────────────────────
  const [exports, setExports] = useState<KBExport[]>([]);
  const [exporting, setExporting] = useState(false);
  const [includeMarkdown, setIncludeMarkdown] = useState(true);
  const [includeArchived, setIncludeArchived] = useState(false);
  const [tagInput, setTagInput] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  // ── Import state ──────────────────────────────────────────────────────────
  const [importFile, setImportFile] = useState<File | null>(null);
  const [conflictMode, setConflictMode] = useState<'skip' | 'overwrite'>('skip');
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<KBImportResponse | null>(null);
  const [importError, setImportError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadExports = async () => {
    try {
      const data = await workspaces.listExports(wsId);
      setExports(data);
    } catch (e) {}
  };

  useEffect(() => {
    loadExports();
    const timer = setInterval(loadExports, 5000);
    return () => clearInterval(timer);
  }, [wsId]);

  const addTag = () => {
    const t = tagInput.trim();
    if (t && !tags.includes(t)) setTags(prev => [...prev, t]);
    setTagInput('');
  };

  const removeTag = (t: string) => setTags(prev => prev.filter(x => x !== t));

  const handleStartExport = async () => {
    setExporting(true);
    try {
      await workspaces.createExport(wsId, {
        include_markdown: includeMarkdown,
        include_archived: includeArchived,
        tags: tags.length > 0 ? tags : undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      });
      loadExports();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setExporting(false);
    }
  };

  const handleImport = async () => {
    if (!importFile) return;
    setImporting(true);
    setImportResult(null);
    setImportError('');
    try {
      const result = await workspaces.importKb(wsId, importFile, conflictMode);
      setImportResult(result);
      setImportFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (e: any) {
      setImportError(e.message);
    } finally {
      setImporting(false);
    }
  };

  const tabStyle = (tab: ActiveTab): React.CSSProperties => ({
    padding: '8px 20px', fontSize: 13, fontWeight: 600, cursor: 'pointer',
    border: 'none',
    borderBottom: activeTab === tab ? '2px solid var(--color-primary)' : '2px solid transparent',
    color: activeTab === tab ? 'var(--color-primary)' : 'var(--text-muted)',
    background: 'none',
    transition: 'all 0.15s',
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Tab bar */}
      <div style={{ display: 'flex', borderBottom: '1px solid var(--border-default)', gap: 0 }}>
        <button style={tabStyle('export')} onClick={() => setActiveTab('export')}>
          {t('export_import.export')}
        </button>
        <button style={tabStyle('import')} onClick={() => setActiveTab('import')}>
          {t('export_import.import')}
        </button>
      </div>

      {/* ── Export Tab ──────────────────────────────────────────────────────── */}
      {activeTab === 'export' && (
        <>
          <section style={{ background: 'var(--bg-surface)', padding: 20, borderRadius: 12, border: '1px solid var(--border-default)' }}>
            <h4 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>
              {t('export_import.new_task')}
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

              {/* Include markdown */}
              <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontSize: 14 }}>
                <input type="checkbox" checked={includeMarkdown} onChange={e => setIncludeMarkdown(e.target.checked)} style={{ width: 16, height: 16 }} />
                {t('export_import.include_markdown')}
              </label>

              {/* Include archived */}
              <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontSize: 14 }}>
                <input type="checkbox" checked={includeArchived} onChange={e => setIncludeArchived(e.target.checked)} style={{ width: 16, height: 16 }} />
                {t('export_import.include_archived')}
              </label>

              {/* Tag filter */}
              <div>
                <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                  {t('export_import.filter_tags')}
                </label>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input
                    className="mt-input"
                    style={{ flex: 1 }}
                    placeholder={t('export_import.tag_placeholder')}
                    value={tagInput}
                    onChange={e => setTagInput(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addTag(); } }}
                  />
                  <button className="btn-secondary" onClick={addTag} style={{ flexShrink: 0 }}>
                    <Tag size={14} />
                  </button>
                </div>
                {tags.length > 0 && (
                  <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {tags.map(t => (
                      <span key={t} style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '2px 8px', background: 'var(--color-primary-subtle)', color: 'var(--color-primary)', borderRadius: 12, fontSize: 12 }}>
                        {t}
                        <button onClick={() => removeTag(t)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, display: 'flex', alignItems: 'center', color: 'inherit' }}>
                          <X size={10} />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Date range */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <div>
                  <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                    {t('export_import.created_after')}
                  </label>
                  <input type="date" className="mt-input" value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
                </div>
                <div>
                  <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                    {t('export_import.created_before')}
                  </label>
                  <input type="date" className="mt-input" value={dateTo} onChange={e => setDateTo(e.target.value)} />
                </div>
              </div>

              <div style={{ fontSize: 12, color: 'var(--text-muted)', background: 'var(--bg-app)', padding: 10, borderRadius: 6 }}>
                {t('export_import.export_desc')}
              </div>

              <button
                className="btn-primary"
                onClick={handleStartExport}
                disabled={exporting}
                style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, height: 40 }}
              >
                {exporting ? <Loader2 className="animate-spin" size={18} /> : <Download size={18} />}
                {t('export_import.start_export')}
              </button>
            </div>
          </section>

          {/* Recent exports */}
          <section>
            <h4 style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Clock size={14} />
              {t('export_import.recent_exports')}
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {exports.length === 0 && (
                <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
                  {t('export_import.no_exports')}
                </div>
              )}
              {exports.map(exp => (
                <div
                  key={exp.id}
                  style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '12px 16px', background: 'var(--bg-surface)',
                    border: '1px solid var(--border-subtle)', borderRadius: 10,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{
                      width: 36, height: 36, borderRadius: 18,
                      background: exp.status === 'completed' ? 'var(--success-bg)' : 'var(--bg-app)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      {exp.status === 'completed' && <CheckCircle size={18} style={{ color: 'var(--success-color)' }} />}
                      {exp.status === 'processing' && <Loader2 size={18} className="animate-spin" />}
                      {exp.status === 'pending' && <Clock size={18} />}
                      {exp.status === 'failed' && <AlertCircle size={18} style={{ color: 'var(--error-color)' }} />}
                    </div>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 500 }}>
                        {exp.id}
                        <span style={{ marginLeft: 8, fontSize: 11, fontWeight: 400, opacity: 0.6 }}>
                          {new Date(exp.created_at).toLocaleString()}
                        </span>
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                        {exp.status}
                        {exp.filter_params?.tags && Array.isArray(exp.filter_params.tags) && (exp.filter_params.tags as any[]).length > 0 ? (
                          <span style={{ marginLeft: 8 }}>· tags: {(exp.filter_params.tags as string[]).join(', ')}</span>
                        ) : null}
                      </div>
                    </div>
                  </div>
                  {exp.status === 'completed' && (
                    <a
                      href={`/api/v1/workspaces/${wsId}/exports/${exp.id}/download`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-secondary"
                      style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px', fontSize: 13 }}
                    >
                      <Download size={14} />
                      {t('export_import.download')}
                    </a>
                  )}
                </div>
              ))}
            </div>
          </section>
        </>
      )}

      {/* ── Import Tab ──────────────────────────────────────────────────────── */}
      {activeTab === 'import' && (
        <section style={{ background: 'var(--bg-surface)', padding: 20, borderRadius: 12, border: '1px solid var(--border-default)' }}>
          <h4 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>
            {t('export_import.import_title')}
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

            {/* File picker */}
            <div
              onClick={() => fileInputRef.current?.click()}
              style={{
                border: `2px dashed ${importFile ? 'var(--color-primary)' : 'var(--border-default)'}`,
                borderRadius: 10, padding: '24px 16px', textAlign: 'center', cursor: 'pointer',
                background: importFile ? 'var(--color-primary-subtle)' : 'var(--bg-app)',
                transition: 'all 0.2s',
              }}
            >
              <Upload size={24} style={{ opacity: 0.5, marginBottom: 8, display: 'block', margin: '0 auto 8px' }} />
              {importFile ? (
                <span style={{ fontSize: 14, fontWeight: 500, color: 'var(--color-primary)' }}>{importFile.name}</span>
              ) : (
                <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                  {t('export_import.click_to_select')}
                </span>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept=".memtrace,.zip"
                style={{ display: 'none' }}
                onChange={e => { setImportFile(e.target.files?.[0] ?? null); setImportResult(null); setImportError(''); }}
              />
            </div>

            {/* Conflict mode */}
            <div>
              <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 8 }}>
                {t('export_import.conflict_res')}
              </label>
              <div style={{ display: 'flex', gap: 10 }}>
                {(['skip', 'overwrite'] as const).map(mode => (
                  <button
                    key={mode}
                    onClick={() => setConflictMode(mode)}
                    style={{
                      padding: '6px 16px', borderRadius: 8, fontSize: 13, cursor: 'pointer',
                      border: `1px solid ${conflictMode === mode ? 'var(--color-primary)' : 'var(--border-default)'}`,
                      background: conflictMode === mode ? 'var(--color-primary-subtle)' : 'transparent',
                      color: conflictMode === mode ? 'var(--color-primary)' : 'var(--text-muted)',
                      fontWeight: conflictMode === mode ? 600 : 400,
                    }}
                  >
                    {mode === 'skip'
                      ? t('export_import.keep_existing')
                      : t('export_import.replace_existing')}
                  </button>
                ))}
              </div>
              <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
                {conflictMode === 'skip'
                  ? t('export_import.skip_desc')
                  : t('export_import.overwrite_desc')}
              </p>
            </div>

            {/* Error */}
            {importError && (
              <div style={{ padding: 10, background: 'var(--color-error-subtle)', border: '1px solid var(--color-error)', borderRadius: 8, fontSize: 13, color: 'var(--color-error)', display: 'flex', alignItems: 'center', gap: 8 }}>
                <AlertCircle size={14} /> {importError}
              </div>
            )}

            {/* Result */}
            {importResult && (
              <div style={{ padding: 14, background: 'var(--bg-app)', border: '1px solid var(--border-default)', borderRadius: 10, fontSize: 13 }}>
                <div style={{ fontWeight: 600, marginBottom: 8, color: 'var(--color-success)' }}>
                  <CheckCircle size={14} style={{ display: 'inline', marginRight: 6 }} />
                  {t('export_import.import_complete')}
                </div>
                <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
                  <span>✅ {t('export_import.imported')}: <b>{importResult.imported_nodes}</b></span>
                  <span>⏭ {t('export_import.skipped')}: <b>{importResult.skipped}</b></span>
                  <span>❌ {t('export_import.failed')}: <b>{importResult.failed}</b></span>
                </div>
                {importResult.errors.length > 0 && (
                  <div style={{ marginTop: 10, color: 'var(--color-error)', fontSize: 12 }}>
                    <div style={{ fontWeight: 600, marginBottom: 4 }}>{t('export_import.error_details')}:</div>
                    {importResult.errors.map((err, i) => <div key={i}>{err}</div>)}
                  </div>
                )}
              </div>
            )}

            <button
              className="btn-primary"
              onClick={handleImport}
              disabled={!importFile || importing}
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, height: 40 }}
            >
              {importing ? <Loader2 className="animate-spin" size={18} /> : <Upload size={18} />}
              {t('export_import.start_import')}
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
