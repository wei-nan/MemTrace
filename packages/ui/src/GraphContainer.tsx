/**
 * GraphContainer — shared owner of graph state.
 *
 * Renders a single persistent header (search, mode toggle, refresh, new-node)
 * that survives 2D ↔ 3D switching, then mounts either GraphView (2D canvas)
 * or GraphView3D (3D canvas) below it — both are now pure renderers.
 */
import { useState, useCallback, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { RefreshCw, Search, Sparkles, Network, Layers, PlusCircle } from 'lucide-react';
import { nodes as nodesApi, edges as edgesApi, type Node as ApiNode, type Edge as ApiEdge } from './api';
import GraphView from './GraphView';
import GraphView3D from './GraphView3D';

type GraphMode = '2d' | '3d';

const RELATION_COLORS: Record<string, string> = {
  depends_on:  'var(--color-primary)',
  extends:     'var(--node-secondary)',
  related_to:  'var(--text-muted)',
  contradicts: 'var(--color-error)',
};

interface Props {
  wsId?: string;
  reloadKey?: number;
  onEditNode: (node: ApiNode) => void;
  onNewNode: () => void;
}

export default function GraphContainer({ wsId, reloadKey, onEditNode, onNewNode }: Props) {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';

  // ── Shared graph state ────────────────────────────────────────────────────
  const [apiNodes, setApiNodes]     = useState<ApiNode[]>([]);
  const [apiEdges, setApiEdges]     = useState<ApiEdge[]>([]);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState('');
  const [graphMode, setGraphMode]   = useState<GraphMode>('2d');

  // ── Search state ──────────────────────────────────────────────────────────
  const [searchQuery, setSearchQuery]   = useState('');
  const [searchMode, setSearchMode]     = useState<'keyword' | 'semantic'>('keyword');

  // ── Load all data ─────────────────────────────────────────────────────────
  const load = useCallback(async () => {
    if (!wsId) return;
    setLoading(true);
    setError('');
    try {
      const [rawNodes, rawEdges] = await Promise.all([
        nodesApi.list(wsId),
        edgesApi.list(wsId),
      ]);
      setApiNodes(rawNodes);
      setApiEdges(rawEdges);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [wsId]);

  // ── Keyword / semantic search ─────────────────────────────────────────────
  const performSearch = useCallback(async () => {
    if (!wsId || !searchQuery.trim()) { load(); return; }
    setLoading(true);
    try {
      const results = searchMode === 'semantic'
        ? await nodesApi.searchSemantic(wsId, searchQuery)
        : await nodesApi.list(wsId, { q: searchQuery });
      setApiNodes(results);
      // Keep existing edges — they'll simply have dangling refs for hidden nodes
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [wsId, searchQuery, searchMode, load]);

  useEffect(() => { load(); }, [load, reloadKey]);

  // ── Subtitle text ─────────────────────────────────────────────────────────
  const subtitle = loading
    ? (zh ? '載入中…' : 'Loading…')
    : error
      ? `Error: ${error}`
      : `${apiNodes.length} ${zh ? '節點' : 'nodes'} · ${apiEdges.length} ${zh ? '連結' : 'edges'}`;

  if (!wsId) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 15 }}>
        {zh ? '請選擇工作區以檢視圖譜' : 'Select a workspace to view the graph.'}
      </div>
    );
  }

  return (
    <div style={{ height: 'calc(100vh - 40px)', width: '100%', display: 'flex', flexDirection: 'column' }}>

      {/* ── Shared header — always visible regardless of 2D/3D mode ────────── */}
      <header
        className="page-header animate-fade-in"
        style={{ padding: '0 40px', marginTop: '40px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}
      >
        <div>
          <h1 className="page-title">{zh ? '知識庫圖譜' : 'Knowledge Graph'}</h1>
          <p className="page-subtitle">{subtitle}</p>
        </div>

        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {/* ── 2D / 3D mode toggle ─────────────────────────────────────── */}
          <div style={{
            display: 'flex',
            background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
            borderRadius: 8, overflow: 'hidden', boxShadow: 'var(--shadow-sm)',
          }}>
            {(['2d', '3d'] as GraphMode[]).map(mode => (
              <button
                key={mode}
                onClick={() => setGraphMode(mode)}
                style={{
                  padding: '5px 14px', fontSize: 12, fontWeight: 600, cursor: 'pointer',
                  border: 'none',
                  background: graphMode === mode ? 'var(--color-primary)' : 'transparent',
                  color: graphMode === mode ? 'white' : 'var(--text-muted)',
                  transition: 'all 0.15s',
                  display: 'flex', alignItems: 'center', gap: 5,
                }}
              >
                {mode === '2d' ? <Network size={12} /> : <Layers size={12} />}
                {mode.toUpperCase()}
              </button>
            ))}
          </div>

          <div style={{ width: 1, height: 24, background: 'var(--border-default)' }} />

          {/* ── Search bar ──────────────────────────────────────────────── */}
          <div className="search-bar" style={{ width: 300, boxShadow: 'var(--shadow-md)' }}>
            <Search size={16} style={{ color: 'var(--text-muted)', marginLeft: 4 }} />
            <input
              className="search-input"
              placeholder={
                searchMode === 'keyword'
                  ? (zh ? '搜尋關鍵字…' : 'Search keyword…')
                  : (zh ? '語意搜尋…' : 'Semantic search…')
              }
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && performSearch()}
            />
            <button
              onClick={() => setSearchMode(m => m === 'keyword' ? 'semantic' : 'keyword')}
              style={{
                display: 'flex', alignItems: 'center', gap: 6, padding: '4px 10px',
                borderRadius: 8,
                background: searchMode === 'semantic' ? 'var(--color-primary)' : 'transparent',
                border: searchMode === 'semantic' ? 'none' : '1px solid var(--border-default)',
                color: searchMode === 'semantic' ? 'var(--text-on-primary)' : 'var(--text-secondary)',
                fontSize: 11, cursor: 'pointer', transition: 'all 0.2s',
              }}
            >
              <Sparkles size={12} />
              {searchMode === 'semantic' ? 'AI' : 'Text'}
            </button>
          </div>

          {/* ── Refresh ─────────────────────────────────────────────────── */}
          <button className="btn-secondary" onClick={load} disabled={loading} style={{ height: 38 }}>
            <RefreshCw
              size={16}
              style={{ marginRight: 6, animation: loading ? 'spin 1s linear infinite' : 'none' }}
            />
            {zh ? '重新整理' : 'Refresh'}
          </button>

          {/* ── New Node ────────────────────────────────────────────────── */}
          <button className="btn-primary" onClick={onNewNode} style={{ height: 38, display: 'flex', alignItems: 'center', gap: 6 }}>
            <PlusCircle size={15} />
            {zh ? '新增節點' : 'New Node'}
          </button>
        </div>
      </header>

      {/* ── Canvas area — swaps on mode change, header stays ────────────────── */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {graphMode === '2d' ? (
          <GraphView
            apiNodes={apiNodes}
            apiEdges={apiEdges}
            relationColors={RELATION_COLORS}
            onEditNode={onEditNode}
          />
        ) : (
          <GraphView3D
            apiNodes={apiNodes}
            apiEdges={apiEdges}
            relationColors={RELATION_COLORS}
            onEditNode={onEditNode}
          />
        )}
      </div>
    </div>
  );
}
