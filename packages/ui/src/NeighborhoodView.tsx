import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useNeighborhood } from './hooks/useNeighborhood';
import { Network, ArrowRight, Brain, Link as LinkIcon, Compass, ChevronRight, Clock, Shield } from 'lucide-react';
import { type Node as ApiNode } from './api';

interface Props {
  wsId: string;
  rootNodeId: string | null;
  onNodeClick: (node: ApiNode) => void;
  onExploreNode: (nodeId: string) => void;
  onClose: () => void;
}

/**
 * P4.7-S2-2 & S3-1: NeighborhoodView component for exploring local graph structures.
 */
export default function NeighborhoodView({ wsId, rootNodeId, onNodeClick, onExploreNode, onClose }: Props) {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const { nodes, edges, loading, error } = useNeighborhood(wsId, rootNodeId || '');

  // P4.7-S2-8 & S5-1: Suggestions state
  const [suggestions, setSuggestions] = useState<{ recent: ApiNode[]; highTrust: ApiNode[]; blindspots: ApiNode[] }>({ recent: [], highTrust: [], blindspots: [] });
  const [highlightBlindspots, setHighlightBlindspots] = useState(false);

  useEffect(() => {
    if (!rootNodeId) {
      import('./api').then(({ nodes: nodesApi }) => {
        Promise.all([
          nodesApi.list(wsId, { limit: 6 }), // Recently updated
          nodesApi.list(wsId, { limit: 6 }), // Highest Trust (Backend sort by trust_score needed, using default for now)
          nodesApi.list(wsId, { filter: 'never_traversed', limit: 6 }), // P4.7-S5-1: Blindspots
        ]).then(([recent, highTrust, blindspots]) => {
          setSuggestions({ recent, highTrust, blindspots });
        });
      });
    }
  }, [rootNodeId, wsId]);

  // P4.7-S3-1: Breadcrumb history (max 8 steps)
  const [history, setHistory] = useState<{ id: string; title: string }[]>([]);

  useEffect(() => {
    if (rootNodeId) {
      const rootNode = nodes.find(n => n.id === rootNodeId);
      if (rootNode) {
        const title = zh ? rootNode.title_zh : rootNode.title_en;
        setHistory(prev => {
          if (prev.length > 0 && prev[prev.length - 1].id === rootNodeId) return prev;
          const next = [...prev, { id: rootNodeId, title }];
          return next.length > 8 ? next.slice(-8) : next;
        });
      }
    } else {
      setHistory([]);
    }
  }, [rootNodeId, nodes, zh]);

  // P4.7-S3-5: Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.altKey && e.key === 'ArrowLeft') {
        if (history.length > 1) {
          const prev = history[history.length - 2];
          setHistory(h => h.slice(0, -2));
          onExploreNode(prev.id);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [history, onExploreNode]);

  if (!rootNodeId) {
    return (
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, background: 'var(--bg-app)', overflowY: 'auto' }}>
        <div style={{ padding: '60px 40px', maxWidth: 1200, margin: '0 auto', width: '100%' }}>
          <div style={{ textAlign: 'center', marginBottom: 60 }}>
            <Compass size={64} style={{ color: 'var(--color-primary)', marginBottom: 24, opacity: 0.8 }} />
            <h1 style={{ fontSize: 36, fontWeight: 800, margin: '0 0 16px 0', letterSpacing: '-0.03em' }}>
              {zh ? '開始探索您的知識網絡' : 'Explore Your Knowledge Network'}
            </h1>
            <p style={{ fontSize: 18, color: 'var(--text-muted)', maxWidth: 600, margin: '0 auto' }}>
              {zh ? '從最近更新或高信任度的節點開始，挖掘隱藏的關聯。' : 'Start from recently updated or high-trust nodes to discover hidden associations.'}
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 40 }}>
            <section>
              <h2 style={{ fontSize: 16, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-muted)', marginBottom: 20, display: 'flex', alignItems: 'center', gap: 8 }}>
                <Clock size={16} /> {zh ? '最近更新' : 'Recently Updated'}
              </h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {suggestions.recent.map(node => (
                  <div 
                    key={node.id} 
                    className="suggestion-item"
                    onClick={() => onExploreNode(node.id)}
                    style={{ 
                      padding: '16px 20px', background: 'var(--bg-surface)', border: '1px solid var(--border-default)', 
                      borderRadius: 12, cursor: 'pointer', transition: 'all 0.2s'
                    }}
                  >
                    <div style={{ fontWeight: 600, fontSize: 15 }}>{zh ? node.title_zh : node.title_en}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>{node.content_type}</div>
                  </div>
                ))}
              </div>
            </section>

            <section>
              <h2 style={{ fontSize: 16, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-muted)', marginBottom: 20, display: 'flex', alignItems: 'center', gap: 8 }}>
                <Shield size={16} /> {zh ? '高信任度' : 'Highest Trust'}
              </h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {suggestions.highTrust.map(node => (
                  <div 
                    key={node.id} 
                    className="suggestion-item"
                    onClick={() => onExploreNode(node.id)}
                    style={{ 
                      padding: '16px 20px', background: 'var(--bg-surface)', border: '1px solid var(--border-default)', 
                      borderRadius: 12, cursor: 'pointer', transition: 'all 0.2s'
                    }}
                  >
                    <div style={{ fontWeight: 600, fontSize: 15 }}>{zh ? node.title_zh : node.title_en}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4, display: 'flex', justifyContent: 'space-between' }}>
                      <span>{node.content_type}</span>
                      <span style={{ color: 'var(--color-primary)' }}>Trust: {node.trust_score.toFixed(2)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section>
              <h2 style={{ fontSize: 16, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: '#f59e0b', marginBottom: 20, display: 'flex', alignItems: 'center', gap: 8 }}>
                <Network size={16} /> {zh ? '🔍 盲點建議' : '🔍 Blindspots'}
              </h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {suggestions.blindspots.map(node => (
                  <div 
                    key={node.id} 
                    className="suggestion-item"
                    onClick={() => onExploreNode(node.id)}
                    style={{ 
                      padding: '16px 20px', background: 'var(--bg-surface)', border: '1px solid #fde68a', 
                      borderLeft: '4px solid #f59e0b',
                      borderRadius: 12, cursor: 'pointer', transition: 'all 0.2s'
                    }}
                  >
                    <div style={{ fontWeight: 600, fontSize: 15 }}>{zh ? node.title_zh : node.title_en}</div>
                    <div style={{ fontSize: 11, color: '#b45309', marginTop: 4 }}>{zh ? '從未走訪過的知識' : 'Knowledge never traversed'}</div>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </div>
        <style>{`
          .suggestion-item:hover {
            border-color: var(--color-primary) !important;
            transform: translateX(4px);
            box-shadow: var(--shadow-sm);
          }
        `}</style>
      </div>
    );
  }

  if (loading && nodes.length === 0) {
    return (
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
        <Compass size={48} className="spin" style={{ marginBottom: 16, opacity: 0.5 }} />
        <div style={{ fontSize: 15 }}>{zh ? '正在探索鄰近知識...' : 'Exploring neighborhood...'}</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 40 }}>
        <div style={{ color: 'var(--color-error)', marginBottom: 16 }}>{error.message}</div>
        <button className="btn-secondary" onClick={onClose}>{zh ? '返回圖譜' : 'Back to Graph'}</button>
      </div>
    );
  }

  const rootNode = nodes.find(n => n.id === rootNodeId);
  const neighbors = nodes.filter(n => n.id !== rootNodeId);
  const blindspotCount = neighbors.filter(n => (n as any).traversal_count === 0).length;

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, background: 'var(--bg-app)' }}>
      {/* Header Area */}
      <div style={{ padding: '24px 40px', background: 'var(--bg-surface)', borderBottom: '1px solid var(--border-subtle)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, color: 'var(--color-primary)' }}>
            <Compass size={24} />
            <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>{zh ? '探索模式' : 'Explore Mode'}</h2>
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            {blindspotCount > 0 && (
              <button 
                className={`btn-secondary ${highlightBlindspots ? 'active' : ''}`}
                onClick={() => setHighlightBlindspots(!highlightBlindspots)}
                style={{ 
                  fontSize: 12, padding: '6px 12px', borderRadius: 8, gap: 8,
                  borderColor: highlightBlindspots ? '#f59e0b' : 'var(--border-default)',
                  background: highlightBlindspots ? '#fffbeb' : 'transparent',
                  color: highlightBlindspots ? '#b45309' : 'var(--text-muted)',
                }}
              >
                <Network size={14} />
                {zh ? `${blindspotCount} 個相鄰盲點` : `${blindspotCount} Adjacent Blindspots`}
              </button>
            )}

            {/* Breadcrumbs */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--text-muted)' }}>
              {history.map((item, idx) => (
                <React.Fragment key={`${item.id}-${idx}`}>
                  <span 
                    onClick={() => onExploreNode(item.id)}
                    style={{ 
                      cursor: 'pointer', 
                      fontWeight: idx === history.length - 1 ? 700 : 400,
                      color: idx === history.length - 1 ? 'var(--text-default)' : 'inherit',
                      textDecoration: idx === history.length - 1 ? 'none' : 'underline'
                    }}
                  >
                    {item.title}
                  </span>
                  {idx < history.length - 1 && <ChevronRight size={14} />}
                </React.Fragment>
              ))}
            </div>
          </div>
        </div>
        
        {rootNode && (
          <div className="animate-fade-in">
            <h1 style={{ fontSize: 32, margin: '0 0 16px 0', fontWeight: 800, letterSpacing: '-0.02em' }}>
              {zh ? rootNode.title_zh : rootNode.title_en}
            </h1>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
              <span className="tag" style={{ background: 'var(--bg-app)', border: '1px solid var(--border-default)' }}>
                <Brain size={12} /> {zh ? '核心概念' : 'Core Concept'}
              </span>
              <span className="tag" style={{ background: 'var(--color-primary-subtle)', color: 'var(--color-primary)', border: 'none' }}>
                {zh ? rootNode.content_type : rootNode.content_type}
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginLeft: 8, fontSize: 13, color: 'var(--text-muted)' }}>
                <div style={{ width: 60, height: 4, background: 'var(--border-subtle)', borderRadius: 2, overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${rootNode.trust_score * 100}%`, background: 'var(--color-primary)' }} />
                </div>
                <span>Trust: {rootNode.trust_score.toFixed(2)}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Neighbors Grid */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '40px' }}>
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 32, color: 'var(--text-muted)' }}>
            <LinkIcon size={16} />
            <span style={{ fontSize: 14, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em' }}>
              {zh ? `關聯知識 (${neighbors.length})` : `Related Knowledge (${neighbors.length})`}
            </span>
          </div>

          {neighbors.length === 0 ? (
            <div style={{ padding: '80px 0', textAlign: 'center', color: 'var(--text-muted)', background: 'var(--bg-surface)', borderRadius: 20, border: '1px dashed var(--border-default)' }}>
              <Network size={48} style={{ marginBottom: 16, opacity: 0.3 }} />
              <div style={{ fontSize: 16, fontWeight: 500 }}>{zh ? '此節點暫時沒有鄰近關聯' : 'No neighborhood associations found for this node.'}</div>
              <p style={{ fontSize: 14, marginTop: 8, opacity: 0.7 }}>{zh ? '您可以嘗試在側邊欄手動建立關聯。' : 'You can try manually creating associations in the side panel.'}</p>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: 24 }}>
              {neighbors.map(node => {
                const edge = edges.find(e => (e.from_id === rootNodeId && e.to_id === node.id) || (e.from_id === node.id && e.to_id === rootNodeId));
                const isOutbound = edge?.from_id === rootNodeId;
                const isBlindspot = highlightBlindspots && (node as any).traversal_count === 0;
                
                return (
                  <div 
                    key={node.id}
                    onClick={() => onNodeClick(node)}
                    onDoubleClick={() => onExploreNode(node.id)}
                    className={`explore-card ${isBlindspot ? 'blindspot-active' : ''}`}
                    style={{
                      background: 'var(--bg-surface)', 
                      border: isBlindspot ? '2px dashed #f59e0b' : '1px solid var(--border-default)',
                      borderRadius: 20, padding: 28, cursor: 'pointer', transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                      display: 'flex', flexDirection: 'column', gap: 16,
                      position: 'relative',
                      overflow: 'hidden',
                      boxShadow: isBlindspot ? '0 0 15px rgba(245, 158, 11, 0.2)' : 'none',
                    }}
                  >
                    {isBlindspot && (
                      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 4, background: '#f59e0b' }} />
                    )}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div style={{ 
                        background: 'var(--color-primary-subtle)', color: 'var(--color-primary)',
                        padding: '5px 12px', borderRadius: 8, fontSize: 11, fontWeight: 800, 
                        textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: 6,
                        letterSpacing: '0.02em'
                      }}>
                        {isOutbound ? <ArrowRight size={12} /> : <ArrowRight size={12} style={{ transform: 'rotate(180deg)' }} />}
                        {edge?.relation || 'related'}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>
                        TRUST {node.trust_score.toFixed(2)}
                      </div>
                    </div>

                    <h3 style={{ margin: 0, fontSize: 19, fontWeight: 700, lineHeight: 1.4, color: 'var(--text-default)' }}>
                      {zh ? node.title_zh : node.title_en}
                    </h3>

                    <div style={{ 
                      fontSize: 14, color: 'var(--text-muted)', lineHeight: 1.7,
                      overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', 
                      WebkitLineClamp: 3, WebkitBoxOrient: 'vertical',
                      minHeight: '4.8em'
                    }}>
                      {zh ? node.body_zh : node.body_en}
                    </div>

                    <div style={{ marginTop: 'auto', display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                      {node.tags.slice(0, 3).map(t => (
                        <span key={t} style={{ fontSize: 11, color: 'var(--color-primary)', fontWeight: 600, background: 'var(--color-primary-subtle)', padding: '2px 8px', borderRadius: 4 }}>
                          #{t}
                        </span>
                      ))}
                    </div>

                    {/* Quality Operations & Faded Alerts */}
                    <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: 12 }}>
                      {edge?.status === 'faded' && (
                        <div style={{ 
                          background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.2)',
                          padding: '10px 14px', borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10
                        }}>
                          <div style={{ fontSize: 11, color: '#ef4444', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}>
                            <Clock size={12} />
                            {zh ? '連結已衰退' : 'Faded Link'}
                          </div>
                          <button 
                            className="btn-primary" 
                            style={{ padding: '4px 10px', fontSize: 11, background: '#ef4444' }}
                            onClick={(e) => { e.stopPropagation(); /* TODO: api.edges.update status to active */ }}
                          >
                            {zh ? '重新啟用' : 'Re-enable'}
                          </button>
                        </div>
                      )}

                      <div style={{ display: 'flex', gap: 8 }}>
                        <button 
                          className="btn-secondary" 
                          style={{ flex: 1, padding: '6px 0', fontSize: 11, fontWeight: 700 }}
                          onClick={(e) => { e.stopPropagation(); /* TODO: api.nodes.confirm */ }}
                        >
                          {zh ? '確認正確' : 'Confirm'}
                        </button>
                        <button 
                          className="btn-secondary" 
                          style={{ flex: 1, padding: '6px 0', fontSize: 11, fontWeight: 700 }}
                          onClick={(e) => { e.stopPropagation(); /* TODO: open proposal modal */ }}
                        >
                          {zh ? '審核提案' : 'Review'}
                        </button>
                        <button 
                          className="btn-secondary" 
                          style={{ flex: 1, padding: '6px 0', fontSize: 11, fontWeight: 700 }}
                          onClick={(e) => { e.stopPropagation(); /* TODO: api.edges.strengthen */ }}
                        >
                          {zh ? '強化連結' : 'Strengthen'}
                        </button>
                      </div>
                    </div>

                    <div className="card-hover-hint" style={{ 
                      position: 'absolute', bottom: 12, right: 28, fontSize: 11, fontWeight: 700, 
                      color: 'var(--color-primary)', opacity: 0, transition: 'opacity 0.2s',
                      textTransform: 'uppercase', letterSpacing: '0.05em'
                    }}>
                      {zh ? '雙擊探索' : 'Double click to explore'}
                    </div>

                    {/* Hover Effect Decoration */}
                    <div className="card-hover-edge" style={{
                      position: 'absolute', left: 0, top: 0, bottom: 0, width: 6,
                      background: 'var(--color-primary)', opacity: 0, transition: 'opacity 0.2s'
                    }} />
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      <style>{`
        .explore-card:hover {
          transform: translateY(-6px);
          border-color: var(--color-primary) !important;
          box-shadow: var(--shadow-lg) !important;
        }
        .explore-card:hover .card-hover-edge,
        .explore-card:hover .card-hover-hint {
          opacity: 1 !important;
        }
        .spin {
          animation: spin 2s linear infinite;
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .animate-fade-in {
          animation: fadeIn 0.4s ease-out;
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
