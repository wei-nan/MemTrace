import { useState, useEffect } from 'react';
import MDEditor from '@uiw/react-md-editor';
import ReactMarkdown from 'react-markdown';
import { useTranslation } from 'react-i18next';
import { 
  X, Edit3, Save, Trash2, Link as LinkIcon, 
  ChevronRight, Calendar, User, Shield, Type 
} from 'lucide-react';
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
  const { i18n } = useTranslation();
  const isCreate = node === null;
  const [isEditing, setIsEditing] = useState(isCreate);

  const [titleZh, setTitleZh]       = useState(node?.title_zh ?? '');
  const [titleEn, setTitleEn]       = useState(node?.title_en ?? '');
  const [contentType, setContentType] = useState(node?.content_type ?? 'factual');
  const [format, setFormat]         = useState<'plain' | 'markdown'>(
    (node?.content_format as 'plain' | 'markdown') ?? 'markdown'
  );
  const [bodyZh, setBodyZh]         = useState(node?.body_zh ?? '');
  const [bodyEn, setBodyEn]         = useState(node?.body_en ?? '');
  const [tags, setTags]             = useState((node?.tags ?? []).join(', '));
  const [visibility, setVisibility] = useState(node?.visibility ?? 'private');
  const [displayLang, setDisplayLang] = useState<'zh' | 'en'>(i18n.language === 'zh-TW' ? 'zh' : 'en');

  const [saving, setSaving]   = useState(false);
  const [error, setError]     = useState('');

  // ── Edges ────────────────────────────────────────────────────────────────
  const [nodeEdges, setNodeEdges]         = useState<Edge[]>([]);
  const [edgeTarget, setEdgeTarget]       = useState('');
  const [edgeRelation, setEdgeRelation]   = useState('related_to');
  const [edgeSaving, setEdgeSaving]       = useState(false);

  useEffect(() => {
    if (node) {
      edgesApi.list(wsId, node.id).then(setNodeEdges).catch(() => {});
      nodes.traverse(node.id).catch(() => {});
      setIsEditing(false);
      // Update form fields when node changes
      setTitleZh(node.title_zh);
      setTitleEn(node.title_en);
      setContentType(node.content_type);
      setFormat(node.content_format as any);
      setBodyZh(node.body_zh);
      setBodyEn(node.body_en);
      setTags(node.tags.join(', '));
      setVisibility(node.visibility);
    } else {
      setIsEditing(true);
      setTitleZh(''); setTitleEn(''); setBodyZh(''); setBodyEn(''); setTags('');
    }
  }, [node, wsId]);

  const handleSave = async () => {
    if (!titleZh.trim() || !titleEn.trim()) { setError('Both titles are required.'); return; }
    setSaving(true); setError('');
    try {
      const payload = {
        title_zh: titleZh.trim(), title_en: titleEn.trim(),
        content_type: contentType, content_format: format,
        body_zh: bodyZh.trim(), body_en: bodyEn.trim(),
        tags: tags.split(',').map(t => t.trim()).filter(Boolean),
        visibility,
      };
      const saved = node
        ? await nodes.update(wsId, node.id, payload)
        : await nodes.create(wsId, payload);
      onSaved(saved);
      setIsEditing(false);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!node || !window.confirm(`Delete "${node.title_en}"?`)) return;
    await nodes.delete(wsId, node.id);
    onClose();
  };

  const handleAddEdge = async () => {
    if (!edgeTarget.trim() || !node) return;
    setEdgeSaving(true);
    try {
      const created = await edgesApi.create(wsId, {
        from_id: node.id, to_id: edgeTarget.trim(),
        relation: edgeRelation, weight: 1.0, half_life_days: 30,
      });
      setNodeEdges(prev => [...prev, created]);
      setEdgeTarget('');
    } catch (e: any) {
      alert(e.message);
    } finally {
      setEdgeSaving(false);
    }
  };

  const currentTitle = displayLang === 'zh' ? titleZh : titleEn;
  const currentBody = displayLang === 'zh' ? bodyZh : bodyEn;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--panel-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div className="brand-icon" style={{ width: 28, height: 28 }}><Type size={14} /></div>
          <h3 style={{ margin: 0, fontSize: '1.1rem' }}>
            {isCreate ? 'New Memory' : isEditing ? 'Edit Memory' : 'Memory Details'}
          </h3>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {!isCreate && !isEditing && (
            <button className="nav-item" style={{ padding: 6, margin: 0 }} onClick={() => setIsEditing(true)}>
              <Edit3 size={18} />
            </button>
          )}
          <button className="nav-item" style={{ padding: 6, margin: 0 }} onClick={onClose}>
            <X size={20} />
          </button>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
        {isEditing ? (
          <div className="animate-fade-in">
            <div className="form-group">
              <label className="form-label">Title (English / 中文)</label>
              <div style={{ display: 'grid', gap: 8 }}>
                <input className="mt-input" placeholder="English Title" value={titleEn} onChange={e => setTitleEn(e.target.value)} />
                <input className="mt-input" placeholder="中文名稱" value={titleZh} onChange={e => setTitleZh(e.target.value)} />
              </div>
            </div>

            <div className="form-group" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <label className="form-label">Type</label>
                <select className="mt-input" value={contentType} onChange={e => setContentType(e.target.value)}>
                  {CONTENT_TYPES.map(t => <option key={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label className="form-label">Visibility</label>
                <select className="mt-input" value={visibility} onChange={e => setVisibility(e.target.value)}>
                  {VISIBILITIES.map(v => <option key={v}>{v}</option>)}
                </select>
              </div>
            </div>

            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <label className="form-label" style={{ margin: 0 }}>Content</label>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className={`tag ${displayLang === 'en' ? 'tag-active' : ''}`} onClick={() => setDisplayLang('en')}>EN</button>
                  <button className={`tag ${displayLang === 'zh' ? 'tag-active' : ''}`} onClick={() => setDisplayLang('zh')}>中文</button>
                </div>
              </div>
              <div data-color-mode="dark">
                <MDEditor value={displayLang === 'zh' ? bodyZh : bodyEn} onChange={v => displayLang === 'zh' ? setBodyZh(v ?? '') : setBodyEn(v ?? '')} height={300} preview="edit" />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Tags</label>
              <input className="mt-input" value={tags} onChange={e => setTags(e.target.value)} placeholder="comma separated..." />
            </div>

            {error && <p style={{ color: 'var(--error-color)', fontSize: 13, marginBottom: 16 }}>{error}</p>}

            <div style={{ display: 'flex', gap: 12, marginTop: 32 }}>
              <button className="btn-primary" style={{ flex: 1 }} onClick={handleSave} disabled={saving}>
                <Save size={18} /> {saving ? 'Saving...' : 'Save Memory'}
              </button>
              {!isCreate && (
                <button className="btn-danger" onClick={handleDelete}>
                  <Trash2 size={18} />
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="animate-fade-in">
            <div style={{ marginBottom: 24 }}>
              <h1 style={{ fontSize: '1.75rem', marginBottom: 8 }}>{currentTitle}</h1>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12 }}>
                <span className="tag" style={{ background: 'var(--bg-secondary)' }}><Shield size={12} /> {contentType}</span>
                <span className="tag" style={{ background: 'var(--bg-secondary)' }}><Calendar size={12} /> {node?.created_at?.split('T')[0]}</span>
                <span className="tag" title={`accuracy ${(node?.dim_accuracy ?? 0).toFixed(2)} · freshness ${(node?.dim_freshness ?? 0).toFixed(2)} · utility ${(node?.dim_utility ?? 0).toFixed(2)} · author_rep ${(node?.dim_author_rep ?? 0).toFixed(2)}`} style={{ background: 'var(--bg-secondary)', cursor: 'default' }}>
                  <User size={12} /> trust {(node?.trust_score ?? 0).toFixed(2)}
                </span>
                {node?.tags.map(t => <span key={t} className="tag">#{t}</span>)}
              </div>
            </div>

            <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
              <button className={`tag ${displayLang === 'en' ? 'tag-active' : ''}`} onClick={() => setDisplayLang('en')}>English</button>
              <button className={`tag ${displayLang === 'zh' ? 'tag-active' : ''}`} onClick={() => setDisplayLang('zh')}>中文內容</button>
            </div>

            <div className="markdown-body" style={{ background: 'var(--panel-bg)', padding: 20, borderRadius: 12, border: '1px solid var(--panel-border)', lineHeight: 1.6 }}>
              <ReactMarkdown>{currentBody || '*No content available in this language.*'}</ReactMarkdown>
            </div>

            <div style={{ marginTop: 32 }}>
              <h4 style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, color: 'var(--text-muted)' }}>
                <LinkIcon size={16} /> Associations
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {nodeEdges.map(e => (
                  <div key={e.id} style={{ padding: '10px 14px', background: 'rgba(255,255,255,0.03)', borderRadius: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center', border: '1px solid var(--panel-border)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <span style={{ fontSize: 11, background: 'var(--accent-color)', color: 'white', padding: '2px 6px', borderRadius: 4 }}>{e.relation}</span>
                      <span style={{ fontSize: 13 }}>{e.to_id}</span>
                    </div>
                    <ChevronRight size={14} style={{ opacity: 0.3 }} />
                  </div>
                ))}
              </div>
              
              <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
                <input className="mt-input" style={{ flex: 1, margin: 0 }} placeholder="Target ID" value={edgeTarget} onChange={e => setEdgeTarget(e.target.value)} />
                <button className="btn-secondary" style={{ padding: '0 12px' }} onClick={handleAddEdge} disabled={edgeSaving || !edgeTarget}>Link</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
