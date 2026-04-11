import { useState, useEffect, useRef } from 'react';
import MDEditor from '@uiw/react-md-editor';
import ReactMarkdown from 'react-markdown';
import { useTranslation } from 'react-i18next';
import {
  X, Edit3, Save, Trash2, Link as LinkIcon,
  ChevronRight, ChevronLeft, Calendar, User, Shield, Type, Search,
} from 'lucide-react';
import { nodes as nodesApi, edges as edgesApi, type Node, type Edge } from './api';

interface Props {
  wsId: string;
  node?: Node | null;           // null = create mode
  onSaved: (node: Node) => void;
  onClose: () => void;
  onSelectNode?: (node: Node) => void;
  sourceNodeId?: string;        // highlights the node we navigated from
}

const CONTENT_TYPES = ['factual', 'procedural', 'preference', 'context'];
const VISIBILITIES  = ['private', 'team', 'public'];
const RELATIONS     = ['depends_on', 'extends', 'related_to', 'contradicts'];

export default function NodeEditor({ wsId, node, onSaved, onClose, onSelectNode, sourceNodeId }: Props) {
  const { i18n } = useTranslation();
  const isCreate = node === null;
  const [isEditing, setIsEditing] = useState(isCreate);

  const [titleZh, setTitleZh]         = useState(node?.title_zh ?? '');
  const [titleEn, setTitleEn]         = useState(node?.title_en ?? '');
  const [contentType, setContentType] = useState(node?.content_type ?? 'factual');
  const [format, setFormat]           = useState<'plain' | 'markdown'>(
    (node?.content_format as 'plain' | 'markdown') ?? 'markdown'
  );
  const [bodyZh, setBodyZh]           = useState(node?.body_zh ?? '');
  const [bodyEn, setBodyEn]           = useState(node?.body_en ?? '');
  const [tags, setTags]               = useState((node?.tags ?? []).join(', '));
  const [visibility, setVisibility]   = useState(node?.visibility ?? 'private');
  const [displayLang, setDisplayLang] = useState<'zh' | 'en'>(i18n.language === 'zh-TW' ? 'zh' : 'en');

  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState('');

  // ── All workspace nodes (for search + association labels) ─────────────────
  const [allNodes, setAllNodes] = useState<Node[]>([]);

  useEffect(() => {
    if (wsId) nodesApi.list(wsId).then(setAllNodes).catch(() => {});
  }, [wsId]);

  const nodeMap: Record<string, Node> = Object.fromEntries(allNodes.map(n => [n.id, n]));

  // ── Edges ─────────────────────────────────────────────────────────────────
  const [nodeEdges, setNodeEdges]       = useState<Edge[]>([]);
  const [edgeRelation, setEdgeRelation] = useState('related_to');
  const [edgeSaving, setEdgeSaving]     = useState(false);
  const [hoveredEdgeId, setHoveredEdgeId] = useState<string | null>(null);

  // ── Node search (for edge target) ─────────────────────────────────────────
  const [searchQuery, setSearchQuery]           = useState('');
  const [searchOpen, setSearchOpen]             = useState(false);
  const [selectedTargetNode, setSelectedTargetNode] = useState<Node | null>(null);
  const searchRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as globalThis.Node)) {
        setSearchOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const searchResults = allNodes.filter(n => {
    if (n.id === node?.id) return false;
    if (!searchQuery.trim()) return false;
    const q = searchQuery.toLowerCase();
    return n.title_zh.toLowerCase().includes(q) || n.title_en.toLowerCase().includes(q);
  });

  useEffect(() => {
    if (node) {
      edgesApi.list(wsId, node.id).then(setNodeEdges).catch(() => {});
      nodesApi.traverse(node.id).catch(() => {});
      setIsEditing(false);
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
    // Reset edge search state when switching nodes
    setSearchQuery('');
    setSelectedTargetNode(null);
    setSearchOpen(false);
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
        ? await nodesApi.update(wsId, node.id, payload)
        : await nodesApi.create(wsId, payload);
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
    await nodesApi.delete(wsId, node.id);
    onClose();
  };

  const handleAddEdge = async () => {
    if (!selectedTargetNode || !node) return;
    setEdgeSaving(true);
    try {
      const created = await edgesApi.create(wsId, {
        from_id: node.id, to_id: selectedTargetNode.id,
        relation: edgeRelation, weight: 1.0, half_life_days: 30,
      });
      setNodeEdges(prev => [...prev, created]);
      setSearchQuery('');
      setSelectedTargetNode(null);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setEdgeSaving(false);
    }
  };

  const handleSelectSearchResult = (target: Node) => {
    setSelectedTargetNode(target);
    setSearchQuery(displayLang === 'zh' ? target.title_zh : target.title_en);
    setSearchOpen(false);
  };

  const currentTitle = displayLang === 'zh' ? titleZh : titleEn;
  const currentBody  = displayLang === 'zh' ? bodyZh  : bodyEn;

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
            {/* ── Node details ─────────────────────────────────────────────── */}
            <div style={{ marginBottom: 24 }}>
              <h1 style={{ fontSize: '1.75rem', marginBottom: 8 }}>{currentTitle}</h1>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12 }}>
                <span className="tag" style={{ background: 'var(--bg-secondary)' }}><Shield size={12} /> {contentType}</span>
                <span className="tag" style={{ background: 'var(--bg-secondary)' }}><Calendar size={12} /> {node?.created_at?.split('T')[0]}</span>
                <span
                  className="tag"
                  title={`accuracy ${(node?.dim_accuracy ?? 0).toFixed(2)} · freshness ${(node?.dim_freshness ?? 0).toFixed(2)} · utility ${(node?.dim_utility ?? 0).toFixed(2)} · author_rep ${(node?.dim_author_rep ?? 0).toFixed(2)}`}
                  style={{ background: 'var(--bg-secondary)', cursor: 'default' }}
                >
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

            {/* ── Associations ─────────────────────────────────────────────── */}
            <div style={{ marginTop: 32 }}>
              <h4 style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, color: 'var(--text-muted)' }}>
                <LinkIcon size={16} /> Associations
              </h4>

              {/* Association list */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {nodeEdges.length === 0 && (
                  <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>No associations yet.</p>
                )}
                {nodeEdges.map(e => {
                  const isFrom     = e.from_id === node?.id;
                  const otherId    = isFrom ? e.to_id : e.from_id;
                  const otherNode  = nodeMap[otherId];
                  const otherTitle = otherNode
                    ? (displayLang === 'zh' ? otherNode.title_zh : otherNode.title_en)
                    : otherId;
                  const canNavigate = !!otherNode && !!onSelectNode;
                  const isSource    = otherId === sourceNodeId;
                  const isHovered   = hoveredEdgeId === e.id;

                  // Style priority: source > hover > default
                  const bg = isSource
                    ? 'rgba(99,102,241,0.18)'
                    : isHovered
                      ? 'rgba(99,102,241,0.10)'
                      : 'rgba(255,255,255,0.03)';
                  const borderColor = isSource || isHovered
                    ? 'var(--accent-color)'
                    : 'var(--panel-border)';

                  return (
                    <div
                      key={e.id}
                      onClick={() => canNavigate && onSelectNode!(otherNode!)}
                      onMouseEnter={() => canNavigate && setHoveredEdgeId(e.id)}
                      onMouseLeave={() => setHoveredEdgeId(null)}
                      style={{
                        padding: '10px 14px',
                        background: bg,
                        borderRadius: 8,
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        border: `1px solid ${borderColor}`,
                        cursor: canNavigate ? 'pointer' : 'default',
                        transition: 'background 0.15s, border-color 0.15s',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
                        {/* Direction indicator */}
                        <span style={{ fontSize: 11, opacity: 0.5, flexShrink: 0 }}>
                          {isFrom ? '→' : '←'}
                        </span>
                        {/* Relation badge */}
                        <span style={{ fontSize: 11, background: 'var(--accent-color)', color: 'white', padding: '2px 6px', borderRadius: 4, flexShrink: 0 }}>
                          {e.relation}
                        </span>
                        {/* Node title */}
                        <span style={{ fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {otherTitle}
                        </span>
                        {/* Source badge */}
                        {isSource && (
                          <span style={{ fontSize: 10, background: 'var(--accent-color)', color: 'white', padding: '1px 5px', borderRadius: 3, flexShrink: 0, opacity: 0.85 }}>
                            came from
                          </span>
                        )}
                      </div>
                      {canNavigate && (
                        <ChevronRight size={14} style={{ opacity: isHovered || isSource ? 0.9 : 0.3, flexShrink: 0, transition: 'opacity 0.15s' }} />
                      )}
                    </div>
                  );
                })}
              </div>

              {/* ── Add new association ───────────────────────────────────── */}
              <div style={{ marginTop: 16 }}>
                <label className="form-label" style={{ marginBottom: 6 }}>Link to node</label>

                {/* Node search input */}
                <div ref={searchRef} style={{ position: 'relative', marginBottom: 8 }}>
                  <div style={{ position: 'relative' }}>
                    <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', opacity: 0.4, pointerEvents: 'none' }} />
                    <input
                      className="mt-input"
                      style={{
                        margin: 0,
                        paddingLeft: 32,
                        borderColor: selectedTargetNode ? 'var(--accent-color)' : undefined,
                        background: selectedTargetNode ? 'rgba(99,102,241,0.08)' : undefined,
                      }}
                      placeholder="Search node by title…"
                      value={searchQuery}
                      onChange={e => {
                        setSearchQuery(e.target.value);
                        setSearchOpen(true);
                        setSelectedTargetNode(null);
                      }}
                      onFocus={() => { if (searchQuery) setSearchOpen(true); }}
                    />
                  </div>

                  {/* Search dropdown */}
                  {searchOpen && searchResults.length > 0 && (
                    <div style={{
                      position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100,
                      background: 'var(--bg-secondary)', border: '1px solid var(--panel-border)',
                      borderRadius: 8, overflow: 'hidden', boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
                      maxHeight: 220, overflowY: 'auto',
                    }}>
                      {searchResults.map(n => (
                        <div
                          key={n.id}
                          onMouseDown={() => handleSelectSearchResult(n)}
                          style={{
                            padding: '9px 14px', cursor: 'pointer', fontSize: 13,
                            display: 'flex', flexDirection: 'column', gap: 2,
                          }}
                          onMouseEnter={e2 => { (e2.currentTarget as HTMLElement).style.background = 'rgba(99,102,241,0.2)'; }}
                          onMouseLeave={e2 => { (e2.currentTarget as HTMLElement).style.background = 'transparent'; }}
                        >
                          <span style={{ fontWeight: 500 }}>{displayLang === 'zh' ? n.title_zh : n.title_en}</span>
                          <span style={{ fontSize: 11, opacity: 0.5 }}>{displayLang === 'zh' ? n.title_en : n.title_zh} · {n.content_type}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* No results hint */}
                  {searchOpen && searchQuery.trim() && searchResults.length === 0 && (
                    <div style={{
                      position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100,
                      background: 'var(--bg-secondary)', border: '1px solid var(--panel-border)',
                      borderRadius: 8, padding: '10px 14px', fontSize: 13,
                      color: 'var(--text-muted)', boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
                    }}>
                      No nodes found
                    </div>
                  )}
                </div>

                {/* Relation + Link button row */}
                <div style={{ display: 'flex', gap: 8 }}>
                  <select className="mt-input" style={{ margin: 0, flex: '0 0 auto', width: 'auto' }} value={edgeRelation} onChange={e => setEdgeRelation(e.target.value)}>
                    {RELATIONS.map(r => <option key={r}>{r}</option>)}
                  </select>
                  <button
                    className="btn-secondary"
                    style={{ flex: 1 }}
                    onClick={handleAddEdge}
                    disabled={edgeSaving || !selectedTargetNode}
                  >
                    {edgeSaving ? 'Linking…' : selectedTargetNode ? `Link → ${displayLang === 'zh' ? selectedTargetNode.title_zh : selectedTargetNode.title_en}` : 'Link'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
