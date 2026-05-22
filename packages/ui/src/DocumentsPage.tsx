import { useEffect, useState, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
  FileText, Download, Trash2, RefreshCw, Search, ChevronRight,
  Link, Calendar, HardDrive, X, Edit2, Check, AlertTriangle, Upload, Plus,
} from 'lucide-react';
import { documents, DuplicateDocumentError, nodes, type Document, type DocumentDetail } from './api';
import { useModal } from './components/ModalContext';

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

function MimeIcon({ mime }: { mime: string }) {
  const color = mime.includes('pdf') ? '#ef4444' : mime.includes('markdown') || mime.includes('text') ? '#6366f1' : '#6b7280';
  const label = mime.includes('pdf') ? 'PDF' : mime.includes('markdown') ? 'MD' : mime.includes('json') ? 'JSON' : 'TXT';
  return (
    <div style={{
      width: 36, height: 36, borderRadius: 8, background: `${color}18`,
      border: `1px solid ${color}40`, display: 'flex', alignItems: 'center',
      justifyContent: 'center', fontSize: 9, fontWeight: 700, color, flexShrink: 0,
    }}>
      {label}
    </div>
  );
}

// ── Detail Panel ──────────────────────────────────────────────────────────────

function DocumentDetailPanel({
  wsId,
  docId,
  onClose,
  onDeleted,
  onEditNode,
}: {
  wsId: string;
  docId: string;
  onClose: () => void;
  onDeleted: () => void;
  onEditNode?: (nodeId: string) => void;
}) {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const { confirm, toast } = useModal();

  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState('');
  const [saving, setSaving] = useState(false);
  const [reloadTick, setReloadTick] = useState(0);

  // Attach-to-node state
  const [attachSearch, setAttachSearch] = useState('');
  const [attachResults, setAttachResults] = useState<Array<{ id: string; title: string; content_type: string }>>([]);
  const [attachSearching, setAttachSearching] = useState(false);
  const [attaching, setAttaching] = useState<string | null>(null);

  // Debounced node search
  useEffect(() => {
    if (!attachSearch.trim()) { setAttachResults([]); return; }
    const t = setTimeout(async () => {
      setAttachSearching(true);
      try {
        const res = await nodes.list(wsId, { q: attachSearch, limit: 8 });
        setAttachResults(res as any[]);
      } catch { setAttachResults([]); }
      finally { setAttachSearching(false); }
    }, 300);
    return () => clearTimeout(t);
  }, [attachSearch, wsId]);

  const handleAttach = async (nodeId: string) => {
    if (attaching) return;
    setAttaching(nodeId);
    try {
      await documents.attachToNode(wsId, nodeId, [docId]);
      toast({ message: zh ? '已成功關聯節點' : 'Document linked to node', variant: 'success' });
      setAttachSearch('');
      setAttachResults([]);
      setReloadTick(t => t + 1);
    } catch (e: any) {
      toast({ message: e.message, variant: 'error' });
    } finally {
      setAttaching(null);
    }
  };

  useEffect(() => {
    setDoc(null);
    setPreview(null);
    setLoadError('');
    documents.get(wsId, docId)
      .then(d => {
        setDoc(d);
        setTitleDraft(d.title || d.filename);
      })
      .catch(e => setLoadError(e.message || String(e)));
  }, [wsId, docId, reloadTick]);

  useEffect(() => {
    if (!doc) return;
    setPreviewLoading(true);
    documents.preview(wsId, docId)
      .then(text => setPreview(text as unknown as string))
      .catch(() => setPreview(null))
      .finally(() => setPreviewLoading(false));
  }, [wsId, docId, doc]);

  const saveTitle = async () => {
    if (!doc) return;
    setSaving(true);
    try {
      await documents.update(wsId, docId, { title: titleDraft.trim() || doc.filename });
      setDoc(d => d ? { ...d, title: titleDraft.trim() || doc.filename } : d);
      setEditingTitle(false);
    } catch (e: any) {
      toast({ message: e.message, variant: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!doc) return;
    const ok = await confirm({
      title: zh ? '刪除文件' : 'Delete Document',
      message: zh
        ? `確定刪除「${doc.title || doc.filename}」？關聯的記憶點連結也會一併移除。`
        : `Delete "${doc.title || doc.filename}"? All linked node associations will also be removed.`,
      variant: 'danger',
      confirmLabel: zh ? '刪除' : 'Delete',
    });
    if (!ok) return;
    try {
      await documents.delete(wsId, docId);
      toast({ message: zh ? '文件已刪除' : 'Document deleted', variant: 'success' });
      onDeleted();
    } catch (e: any) {
      toast({ message: e.message, variant: 'error' });
    }
  };

  if (loadError) return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 8, color: 'var(--color-error)' }}>
      <AlertTriangle size={24} />
      <span style={{ fontSize: 13 }}>{loadError}</span>
    </div>
  );

  if (!doc) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
      <RefreshCw size={18} className="animate-spin" />
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-default)', display: 'flex', alignItems: 'flex-start', gap: 12 }}>
        <MimeIcon mime={doc.mime_type} />
        <div style={{ flex: 1, minWidth: 0 }}>
          {editingTitle ? (
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <input
                className="mt-input"
                style={{ flex: 1, fontSize: 15, fontWeight: 600, padding: '4px 8px' }}
                value={titleDraft}
                onChange={e => setTitleDraft(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') saveTitle(); if (e.key === 'Escape') setEditingTitle(false); }}
                autoFocus
              />
              <button className="btn-primary" style={{ padding: '4px 10px', fontSize: 12 }} onClick={saveTitle} disabled={saving}>
                {saving ? <RefreshCw size={12} className="animate-spin" /> : <Check size={14} />}
              </button>
              <button className="btn-secondary" style={{ padding: '4px 8px' }} onClick={() => setEditingTitle(false)}>
                <X size={14} />
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <div style={{ fontSize: 15, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {doc.title || doc.filename}
              </div>
              <button onClick={() => setEditingTitle(true)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 2, flexShrink: 0 }}>
                <Edit2 size={12} />
              </button>
            </div>
          )}
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2, display: 'flex', gap: 10 }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}><HardDrive size={10} />{formatBytes(doc.size_bytes)}</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}><Calendar size={10} />{formatDate(doc.uploaded_at)}</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}><Link size={10} />{doc.linked_node_count} {zh ? '個節點' : 'nodes'}</span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
          <a
            href={documents.contentUrl(wsId, docId)}
            download={doc.filename}
            className="btn-secondary"
            style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, padding: '5px 10px', textDecoration: 'none' }}
          >
            <Download size={12} />
            {zh ? '下載' : 'Download'}
          </a>
          <button className="btn-secondary" style={{ color: 'var(--color-error)', borderColor: 'var(--color-error)', padding: '5px 8px' }} onClick={handleDelete}>
            <Trash2 size={13} />
          </button>
          <button className="btn-secondary" style={{ padding: '5px 8px' }} onClick={onClose}>
            <X size={13} />
          </button>
        </div>
      </div>

      <div style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 0 }}>
        {/* Preview */}
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {zh ? '內容預覽' : 'Content Preview'}
          </div>
          {previewLoading ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-muted)', fontSize: 13 }}>
              <RefreshCw size={13} className="animate-spin" />{zh ? '載入中…' : 'Loading…'}
            </div>
          ) : preview ? (
            <pre style={{
              fontSize: 12, lineHeight: 1.6, color: 'var(--text-secondary)',
              whiteSpace: 'pre-wrap', wordBreak: 'break-word',
              maxHeight: 300, overflow: 'auto',
              background: 'var(--bg-elevated)', borderRadius: 8, padding: 12,
              margin: 0,
            }}>
              {preview}
            </pre>
          ) : (
            <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>
              {zh ? '此格式不支援預覽，請下載查看' : 'Preview not available for this format. Download to view.'}
            </div>
          )}
        </div>

        {/* Linked Nodes */}
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {zh ? `衍生記憶點（${doc.linked_nodes.length}）` : `Derived Nodes (${doc.linked_nodes.length})`}
          </div>
          {doc.linked_nodes.length === 0 ? (
            <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>
              {zh ? '尚無關聯節點' : 'No linked nodes yet'}
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {doc.linked_nodes.map(n => (
                <div
                  key={n.id}
                  onClick={() => onEditNode?.(n.id)}
                  style={{
                    padding: '10px 12px', borderRadius: 8,
                    border: '1px solid var(--border-subtle)',
                    background: 'var(--bg-elevated)',
                    cursor: onEditNode ? 'pointer' : 'default',
                    transition: 'border-color 0.15s',
                  }}
                  onMouseEnter={e => { if (onEditNode) (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--color-primary)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--border-subtle)'; }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                    <div style={{ fontWeight: 500, fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{n.title || n.id}</div>
                    {onEditNode && <ChevronRight size={13} style={{ flexShrink: 0, color: 'var(--text-muted)' }} />}
                  </div>
                  {n.paragraph_ref && (
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>{n.paragraph_ref}</div>
                  )}
                  {n.excerpt && (
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4, lineHeight: 1.5, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                      {n.excerpt}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Attach to Node */}
        <div style={{ padding: '16px 20px' }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Plus size={12} />
            {zh ? '關聯記憶節點' : 'Attach to Node'}
          </div>
          <div style={{ position: 'relative' }}>
            <Search size={12} style={{ position: 'absolute', left: 9, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }} />
            <input
              className="mt-input"
              style={{ paddingLeft: 28, fontSize: 12, width: '100%' }}
              placeholder={zh ? '搜尋節點標題…' : 'Search node title…'}
              value={attachSearch}
              onChange={e => setAttachSearch(e.target.value)}
            />
          </div>
          {attachSearching && (
            <div style={{ marginTop: 6, fontSize: 11, color: 'var(--text-muted)', display: 'flex', gap: 4, alignItems: 'center' }}>
              <RefreshCw size={11} className="animate-spin" />
              {zh ? '搜尋中…' : 'Searching…'}
            </div>
          )}
          {!attachSearching && attachResults.length > 0 && (
            <div style={{ marginTop: 6, display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 200, overflowY: 'auto' }}>
              {attachResults.map(n => (
                <div
                  key={n.id}
                  onClick={() => handleAttach(n.id)}
                  style={{
                    padding: '7px 10px', borderRadius: 7,
                    border: '1px solid var(--border-subtle)',
                    background: 'var(--bg-elevated)',
                    cursor: attaching === n.id ? 'wait' : 'pointer',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8,
                    opacity: attaching === n.id ? 0.5 : 1,
                    transition: 'border-color 0.12s, opacity 0.12s',
                  }}
                  onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--color-primary)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--border-subtle)'; }}
                >
                  <span style={{ fontSize: 12, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{n.title || n.id}</span>
                  <span style={{ fontSize: 10, color: 'var(--text-muted)', flexShrink: 0, background: 'var(--bg-elevated)', padding: '1px 5px', borderRadius: 4, border: '1px solid var(--border-subtle)' }}>
                    {n.content_type}
                  </span>
                </div>
              ))}
            </div>
          )}
          {!attachSearching && attachSearch.trim() && attachResults.length === 0 && (
            <div style={{ marginTop: 6, fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic' }}>
              {zh ? '找不到相符節點' : 'No matching nodes'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function DocumentsPage({
  wsId,
  onEditNode,
}: {
  wsId: string;
  onEditNode?: (nodeId: string) => void;
}) {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const { toast } = useModal();

  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [dedupDialog, setDedupDialog] = useState<{ file: File; existing: Document } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const PAGE_SIZE = 30;

  const load = useCallback(() => {
    setLoading(true);
    setError('');
    documents.list(wsId, PAGE_SIZE, page * PAGE_SIZE)
      .then(list => setDocs(list))
      .catch(e => setError(e.message || String(e)))
      .finally(() => setLoading(false));
  }, [wsId, page]);

  useEffect(() => { load(); }, [load]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const doc = await documents.upload(wsId, file);
      toast({ message: zh ? '文件已上傳至文件庫' : 'Document uploaded successfully', variant: 'success' });
      load();
      setSelectedId(doc.id);
    } catch (err: any) {
      if (err instanceof DuplicateDocumentError) {
        setDedupDialog({ file, existing: err.existing });
      } else {
        toast({ message: err.message, variant: 'error' });
      }
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDedupCancel = () => setDedupDialog(null);

  const handleDedupUseExisting = () => {
    if (!dedupDialog) return;
    setSelectedId(dedupDialog.existing.id);
    load();
    setDedupDialog(null);
    toast({ message: zh ? '已選取現有文件' : 'Using existing document', variant: 'info' });
  };

  const handleDedupRename = async () => {
    if (!dedupDialog) return;
    const { existing, file } = dedupDialog;
    setDedupDialog(null);
    try {
      await documents.update(wsId, existing.id, { filename: file.name });
      toast({ message: zh ? '檔名已更新為新上傳的名稱' : 'Filename updated', variant: 'success' });
      load();
      setSelectedId(existing.id);
    } catch (e: any) {
      toast({ message: e.message, variant: 'error' });
    }
  };

  const filtered = docs.filter(d => {
    const q = search.toLowerCase();
    return !q || (d.title || d.filename).toLowerCase().includes(q);
  });

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* ── List Panel ── */}
      <div style={{
        width: selectedId ? 360 : '100%',
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        borderRight: selectedId ? '1px solid var(--border-default)' : 'none',
        overflow: 'hidden',
      }}>
        {/* Toolbar */}
        <div style={{ padding: '16px 20px 12px', borderBottom: '1px solid var(--border-default)', display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search size={13} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              className="mt-input"
              style={{ paddingLeft: 30, width: '100%' }}
              placeholder={zh ? '搜尋文件…' : 'Search documents…'}
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <input
            ref={fileInputRef}
            type="file"
            style={{ display: 'none' }}
            accept=".pdf,.txt,.md,.json,.csv,.docx,.xlsx"
            onChange={handleUpload}
          />
          <button
            className="btn-primary"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            style={{ padding: '6px 12px', display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, flexShrink: 0 }}
            title={zh ? '上傳文件（不萃取）' : 'Upload document (no extraction)'}
          >
            {uploading
              ? <RefreshCw size={12} className="animate-spin" />
              : <Upload size={13} />}
            {zh ? '上傳' : 'Upload'}
          </button>
          <button className="btn-secondary" onClick={load} style={{ padding: '6px 10px', flexShrink: 0 }}>
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {error && (
            <div style={{ padding: 20, color: 'var(--color-error)', display: 'flex', gap: 8, alignItems: 'center', fontSize: 13 }}>
              <AlertTriangle size={16} />{error}
            </div>
          )}
          {!loading && !error && filtered.length === 0 && (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
              <FileText size={32} style={{ marginBottom: 12, opacity: 0.4 }} />
              <div style={{ fontSize: 14 }}>{search ? (zh ? '沒有符合的文件' : 'No documents match') : (zh ? '尚無文件' : 'No documents yet')}</div>
              {!search && <div style={{ fontSize: 12, marginTop: 6 }}>{zh ? '點擊「上傳」按鈕直接新增，或透過「文件攝入」頁面以 AI 萃取' : 'Click "Upload" to add files directly, or use Ingest for AI extraction'}</div>}
            </div>
          )}

          {filtered.map(doc => (
            <div
              key={doc.id}
              onClick={() => setSelectedId(selectedId === doc.id ? null : doc.id)}
              style={{
                padding: '12px 20px',
                borderBottom: '1px solid var(--border-subtle)',
                cursor: 'pointer',
                background: selectedId === doc.id ? 'color-mix(in srgb, var(--color-primary) 8%, var(--bg-surface))' : 'transparent',
                borderLeft: selectedId === doc.id ? '3px solid var(--color-primary)' : '3px solid transparent',
                transition: 'background 0.1s',
                display: 'flex',
                gap: 12,
                alignItems: 'flex-start',
              }}
            >
              <MimeIcon mime={doc.mime_type} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 500, fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {doc.title || doc.filename}
                </div>
                {doc.title && doc.title !== doc.filename && (
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {doc.filename}
                  </div>
                )}
                <div style={{ display: 'flex', gap: 8, marginTop: 4, fontSize: 11, color: 'var(--text-muted)' }}>
                  <span>{formatBytes(doc.size_bytes)}</span>
                  <span>·</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                    <Link size={9} />{doc.linked_node_count}
                  </span>
                  <span>·</span>
                  <span>{formatDate(doc.uploaded_at)}</span>
                </div>
              </div>
            </div>
          ))}

          {/* Pagination */}
          {(page > 0 || docs.length === PAGE_SIZE) && (
            <div style={{ padding: '12px 20px', display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-default)' }}>
              <button className="btn-secondary" onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0} style={{ fontSize: 12 }}>
                {zh ? '上一頁' : 'Previous'}
              </button>
              <span style={{ fontSize: 12, color: 'var(--text-muted)', alignSelf: 'center' }}>
                {zh ? `第 ${page + 1} 頁` : `Page ${page + 1}`}
              </span>
              <button className="btn-secondary" onClick={() => setPage(p => p + 1)} disabled={docs.length < PAGE_SIZE} style={{ fontSize: 12 }}>
                {zh ? '下一頁' : 'Next'}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ── Detail Panel ── */}
      {selectedId && (
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <DocumentDetailPanel
            wsId={wsId}
            docId={selectedId}
            onClose={() => setSelectedId(null)}
            onDeleted={() => { setSelectedId(null); load(); }}
            onEditNode={onEditNode}
          />
        </div>
      )}

      {/* ── Dedup Dialog (S5-T21) ── */}
      {dedupDialog && (
        <div
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 1200,
          }}
          onClick={handleDedupCancel}
        >
          <div
            style={{
              background: 'var(--bg-surface)', borderRadius: 12, padding: 28,
              width: 440, maxWidth: '90vw',
              boxShadow: '0 24px 64px rgba(0,0,0,0.35)',
              border: '1px solid var(--border-default)',
            }}
            onClick={e => e.stopPropagation()}
          >
            {/* Icon + title */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
              <div style={{
                width: 40, height: 40, borderRadius: 10,
                background: 'rgba(245,158,11,0.12)', border: '1px solid rgba(245,158,11,0.3)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              }}>
                <AlertTriangle size={20} style={{ color: '#f59e0b' }} />
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: 15 }}>
                  {zh ? '此檔案內容已存在' : 'Duplicate Content Detected'}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                  {zh ? '相同內容已存在於文件庫中' : 'The same content already exists in this workspace'}
                </div>
              </div>
            </div>

            {/* Details */}
            <div style={{
              background: 'var(--bg-elevated)', borderRadius: 8, padding: '12px 14px',
              marginBottom: 20, display: 'flex', flexDirection: 'column', gap: 6, fontSize: 13,
            }}>
              <div style={{ display: 'flex', gap: 8 }}>
                <span style={{ color: 'var(--text-muted)', minWidth: 80 }}>
                  {zh ? '已存在：' : 'Existing:'}
                </span>
                <span style={{ fontWeight: 600, wordBreak: 'break-all' }}>
                  {dedupDialog.existing.filename}
                </span>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <span style={{ color: 'var(--text-muted)', minWidth: 80 }}>
                  {zh ? '新上傳：' : 'New file:'}
                </span>
                <span style={{ fontWeight: 600, wordBreak: 'break-all' }}>
                  {dedupDialog.file.name}
                </span>
              </div>
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', flexWrap: 'wrap' }}>
              <button className="btn-secondary" onClick={handleDedupCancel} style={{ fontSize: 13 }}>
                {zh ? '取消' : 'Cancel'}
              </button>
              <button className="btn-secondary" onClick={handleDedupUseExisting} style={{ fontSize: 13 }}>
                {zh ? '沿用舊名' : 'Use Existing'}
              </button>
              <button className="btn-primary" onClick={handleDedupRename} style={{ fontSize: 13 }}>
                {zh ? '改用新名' : 'Rename to New'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
