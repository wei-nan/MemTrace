import { useState, useEffect } from 'react';
import MDEditor from '@uiw/react-md-editor';
import ReactMarkdown from 'react-markdown';
import { nodes, edges as edgesApi, type Node, type Edge } from './api';

interface Props {
  wsId: string;
  node?: Node | null;           // null = create mode
  onSaved: (node: Node) => void;
  onClose: () => void;
}

const CONTENT_TYPES = ['factual', 'procedural', 'preference', 'context'];
const VISIBILITIES  = ['private', 'team', 'public'];
const RELATIONS     = ['depends_on', 'extends', 'related_to', 'contradicts'];

export default function NodeEditor({ wsId, node, onSaved, onClose }: Props) {
  const isEdit = !!node;

  const [titleZh, setTitleZh]       = useState(node?.title_zh ?? '');
  const [titleEn, setTitleEn]       = useState(node?.title_en ?? '');
  const [contentType, setContentType] = useState(node?.content_type ?? 'factual');
  const [format, setFormat]         = useState<'plain' | 'markdown'>(
    (node?.content_format as 'plain' | 'markdown') ?? 'plain'
  );
  const [bodyZh, setBodyZh]         = useState(node?.body_zh ?? '');
  const [bodyEn, setBodyEn]         = useState(node?.body_en ?? '');
  const [tags, setTags]             = useState((node?.tags ?? []).join(', '));
  const [visibility, setVisibility] = useState(node?.visibility ?? 'private');
  const [lang, setLang]             = useState<'zh' | 'en'>('en');

  const [saving, setSaving]   = useState(false);
  const [error, setError]     = useState('');

  // ── Edge creation sub-panel ──────────────────────────────────────────────
  const [showEdgePanel, setShowEdgePanel] = useState(false);
  const [nodeEdges, setNodeEdges]         = useState<Edge[]>([]);
  const [edgeTarget, setEdgeTarget]       = useState('');
  const [edgeRelation, setEdgeRelation]   = useState('related_to');
  const [edgeWeight, setEdgeWeight]       = useState(1.0);
  const [edgeHalfLife, setEdgeHalfLife]   = useState(30);
  const [edgeSaving, setEdgeSaving]       = useState(false);
  const [edgeError, setEdgeError]         = useState('');

  useEffect(() => {
    if (isEdit && node) {
      edgesApi.list(wsId, node.id).then(setNodeEdges).catch(() => {});
    }
  }, [isEdit, node, wsId]);

  // ── Save node ─────────────────────────────────────────────────────────────
  const handleSave = async () => {
    if (!titleZh.trim() || !titleEn.trim()) { setError('Both titles are required.'); return; }
    if (!bodyZh.trim() && !bodyEn.trim())   { setError('At least one body field must be non-empty.'); return; }
    setSaving(true); setError('');
    try {
      const payload = {
        title_zh: titleZh.trim(), title_en: titleEn.trim(),
        content_type: contentType, content_format: format,
        body_zh: bodyZh.trim(), body_en: bodyEn.trim(),
        tags: tags.split(',').map(t => t.trim()).filter(Boolean),
        visibility,
      };
      const saved = isEdit
        ? await nodes.update(wsId, node!.id, payload)
        : await nodes.create(wsId, payload);
      onSaved(saved);
      setShowEdgePanel(true);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  // ── Save edge ──────────────────────────────────────────────────────────────
  const handleAddEdge = async () => {
    if (!edgeTarget.trim() || !node) return;
    setEdgeSaving(true); setEdgeError('');
    try {
      const created = await edgesApi.create(wsId, {
        from_id: node.id, to_id: edgeTarget.trim(),
        relation: edgeRelation, weight: edgeWeight, half_life_days: edgeHalfLife,
      });
      setNodeEdges(prev => [...prev, created]);
      setEdgeTarget('');
    } catch (e: any) {
      setEdgeError(e.message);
    } finally {
      setEdgeSaving(false);
    }
  };

  // ── Delete node ───────────────────────────────────────────────────────────
  const handleDelete = async () => {
    if (!node) return;
    const edgeCount = nodeEdges.length;
    const msg = `Delete "${node.title_en}"?` +
      (edgeCount > 0 ? `\nThis will also remove ${edgeCount} edge(s).` : '');
    if (!window.confirm(msg)) return;
    await nodes.delete(wsId, node.id);
    onClose();
  };

  const body    = lang === 'zh' ? bodyZh : bodyEn;
  const setBody = lang === 'zh' ? setBodyZh : setBodyEn;

  return (
    <div className="node-editor glass-panel" style={{ padding: 24, minWidth: 520, maxWidth: 720 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h3 style={{ margin: 0 }}>{isEdit ? 'Edit Memory Node' : 'New Memory Node'}</h3>
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 18 }}>✕</button>
      </div>

      {/* Titles */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
        <label>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Title (zh-TW) *</span>
          <input className="mt-input" value={titleZh} onChange={e => setTitleZh(e.target.value)} />
        </label>
        <label>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Title (en) *</span>
          <input className="mt-input" value={titleEn} onChange={e => setTitleEn(e.target.value)} />
        </label>
      </div>

      {/* Type / Format / Visibility row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 12 }}>
        <label>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Content Type *</span>
          <select className="mt-input" value={contentType} onChange={e => setContentType(e.target.value)}>
            {CONTENT_TYPES.map(t => <option key={t}>{t}</option>)}
          </select>
        </label>
        <label>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Format</span>
          <select className="mt-input" value={format} onChange={e => setFormat(e.target.value as any)}>
            <option value="plain">plain</option>
            <option value="markdown">markdown</option>
          </select>
        </label>
        <label>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Visibility</span>
          <select className="mt-input" value={visibility} onChange={e => setVisibility(e.target.value)}>
            {VISIBILITIES.map(v => <option key={v}>{v}</option>)}
          </select>
        </label>
      </div>

      {/* Language tab */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
        {(['en', 'zh'] as const).map(l => (
          <button key={l} className={`tag ${lang === l ? 'tag-active' : ''}`}
            onClick={() => setLang(l)} style={{ cursor: 'pointer' }}>
            {l === 'en' ? 'English' : '中文'}
          </button>
        ))}
        <span style={{ fontSize: 11, color: 'var(--text-muted)', alignSelf: 'center' }}>
          (at least one required)
        </span>
      </div>

      {/* Body editor */}
      {format === 'markdown' ? (
        <div style={{ marginBottom: 12 }}>
          <MDEditor value={body} onChange={v => setBody(v ?? '')} height={200} />
        </div>
      ) : (
        <textarea
          className="mt-input"
          rows={6}
          value={body}
          onChange={e => setBody(e.target.value)}
          style={{ width: '100%', marginBottom: 12, fontFamily: 'monospace', resize: 'vertical' }}
        />
      )}

      {/* Tags */}
      <label style={{ display: 'block', marginBottom: 16 }}>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Tags (comma-separated)</span>
        <input className="mt-input" value={tags} onChange={e => setTags(e.target.value)}
          placeholder="e.g. graph, decay, core" />
      </label>

      {error && <p style={{ color: 'var(--error-color, #f87)', fontSize: 13, marginBottom: 8 }}>{error}</p>}

      {/* Actions */}
      <div style={{ display: 'flex', gap: 8, justifyContent: 'space-between' }}>
        <div>
          {isEdit && (
            <button className="btn btn-danger" onClick={handleDelete}>Delete</button>
          )}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving…' : isEdit ? 'Save Changes' : 'Create Node'}
          </button>
        </div>
      </div>

      {/* ── Associations ───────────────────────────────────────────── */}
      {showEdgePanel && node && (
        <div style={{ marginTop: 24, borderTop: '1px solid var(--border-color)', paddingTop: 16 }}>
          <h4 style={{ margin: '0 0 12px' }}>Associations</h4>

          {nodeEdges.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              {nodeEdges.map(e => (
                <div key={e.id} className="tag" style={{ display: 'inline-flex', gap: 6, marginRight: 8, marginBottom: 4 }}>
                  <span style={{ color: 'var(--accent-color)' }}>{e.relation}</span>
                  <span>→ {e.to_id}</span>
                  <span style={{ color: 'var(--text-muted)' }}>w:{e.weight.toFixed(2)}</span>
                </div>
              ))}
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 0.5fr 0.5fr auto', gap: 8, alignItems: 'end' }}>
            <label>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Target Node ID</span>
              <input className="mt-input" value={edgeTarget} onChange={e => setEdgeTarget(e.target.value)}
                placeholder="mem_xxxxxxxx" />
            </label>
            <label>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Relation</span>
              <select className="mt-input" value={edgeRelation} onChange={e => setEdgeRelation(e.target.value)}>
                {RELATIONS.map(r => <option key={r}>{r}</option>)}
              </select>
            </label>
            <label>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Weight</span>
              <input className="mt-input" type="number" min="0.1" max="1" step="0.1"
                value={edgeWeight} onChange={e => setEdgeWeight(parseFloat(e.target.value))} />
            </label>
            <label>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Half-life</span>
              <input className="mt-input" type="number" min="1"
                value={edgeHalfLife} onChange={e => setEdgeHalfLife(parseInt(e.target.value, 10))} />
            </label>
            <button className="btn btn-primary" onClick={handleAddEdge} disabled={edgeSaving || !edgeTarget.trim()}>
              + Link
            </button>
          </div>
          {edgeError && <p style={{ color: 'var(--error-color, #f87)', fontSize: 12, marginTop: 4 }}>{edgeError}</p>}

          <button className="btn btn-secondary" onClick={onClose} style={{ marginTop: 12 }}>
            Done
          </button>
        </div>
      )}

      {/* Markdown preview (read mode) */}
      {format === 'markdown' && body && !showEdgePanel && (
        <details style={{ marginTop: 12 }}>
          <summary style={{ fontSize: 12, color: 'var(--text-muted)', cursor: 'pointer' }}>Preview</summary>
          <div className="markdown-body" style={{ marginTop: 8, padding: 12, background: 'var(--bg-secondary)' }}>
            <ReactMarkdown>{body}</ReactMarkdown>
          </div>
        </details>
      )}
    </div>
  );
}
