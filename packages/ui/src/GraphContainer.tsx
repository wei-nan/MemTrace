/**
 * GraphContainer — shared owner of graph state.
 *
 * Renders a single persistent header (search, mode toggle, refresh, new-node)
 * that survives 2D ↔ 3D switching, then mounts either GraphView (2D canvas)
 * or GraphView3D (3D canvas) below it — both are now pure renderers.
 */
import { useState, useCallback, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Archive, RefreshCw, Search, Sparkles, Network, Layers, PlusCircle, GitMerge, Table2, TriangleAlert } from 'lucide-react';
import { nodes as nodesApi, edges as edgesApi, workspaces, type Node as ApiNode, type Edge as ApiEdge } from './api';
import GraphView from './GraphView';
import GraphView3D from './GraphView3D';
import TableView from './TableView';

type GraphMode = '2d' | '3d' | 'table';

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
  userId?: string;
}

export default function GraphContainer({ wsId, reloadKey, onEditNode, onNewNode, userId }: Props) {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';

  // ── Shared graph state ────────────────────────────────────────────────────
  const [apiNodes, setApiNodes]     = useState<ApiNode[]>([]);
  const [apiEdges, setApiEdges]     = useState<ApiEdge[]>([]);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState('');
  const [graphMode, setGraphMode]   = useState<GraphMode>('2d');
  const [isPreview, setIsPreview]   = useState(false);
  const [requestSent, setRequestSent] = useState(false);
  const [workspace, setWorkspace]   = useState<any>(null);

  // ── Archive toggle (must precede load so it's in scope for the callback) ──
  const [showArchived, setShowArchived] = useState(false);

  // ── Search state ──────────────────────────────────────────────────────────
  const [searchQuery, setSearchQuery]   = useState('');
  const [searchMode, setSearchMode]     = useState<'keyword' | 'semantic'>('keyword');
  const [orphanFilter, setOrphanFilter] = useState<string | undefined>(undefined);

  // ── Load all data ─────────────────────────────────────────────────────────
  const load = useCallback(async () => {
    if (!wsId) return;
    setLoading(true);
    setError('');
    try {
      const [rawNodes, rawEdges, ws] = await Promise.all([
        nodesApi.list(wsId, showArchived ? { status: 'all', limit: '200' } : { limit: '200' }),
        edgesApi.list(wsId),
        workspaces.get(wsId),
      ]);
      setApiNodes(rawNodes);
      setApiEdges(rawEdges);
      setWorkspace(ws);
    } catch (e: any) {
      if (e.message.includes('403') || e.message.includes('401')) {
        try {
          const preview = await workspaces.graphPreview(wsId);
          setApiNodes(preview.nodes.map((n: any) => ({
             id: n.preview_id,
             title_en: '***',
             title_zh: '***',
             content_type: n.content_type,
             trust_score: 0.5,
             tags: [],
          } as any)));
          setApiEdges(preview.edges.map((e: any) => ({
            id: Math.random().toString(),
            from_id: e.from_preview_id,
            to_id: e.to_preview_id,
            relation: e.relation
          } as any)));
          setIsPreview(true);
        } catch (previewErr: any) {
          setError(e.message);
        }
      } else {
        setError(e.message);
      }

    } finally {
      setLoading(false);
    }
  }, [wsId, showArchived]);

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

  // ── Health mode state ────────────────────────────────────────────────────
  const [healthMode, setHealthMode] = useState(false);
  const [healthScores, setHealthScores] = useState<Record<string, any>>({});

  const loadHealthScores = useCallback(async () => {
    if (!wsId) return;
    try {
      const scores = await nodesApi.healthScores(wsId);
      const scoreMap: Record<string, any> = {};
      scores.forEach(s => { scoreMap[s.node_id] = s; });
      setHealthScores(scoreMap);
    } catch (e: any) {
      console.error('Failed to load health scores', e);
    }
  }, [wsId]);

  useEffect(() => {
    if (healthMode) loadHealthScores();
  }, [healthMode, loadHealthScores]);

  // ── Subtitle text ─────────────────────────────────────────────────────────
  const subtitle = loading
    ? (zh ? '載入中…' : 'Loading…')
    : error
      ? `Error: ${error}`
      : `${apiNodes.length} ${zh ? '節點' : 'nodes'} · ${apiEdges.length} ${zh ? '連結' : 'edges'}`;

  const orphanCount = apiNodes.filter(n => !apiEdges.some(e => e.from_id === n.id || e.to_id === n.id)).length;

  if (!wsId) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 15 }}>
        {zh ? '請選擇工作區以檢視圖譜' : 'Select a workspace to view the graph.'}
      </div>
    );
  }

  return (
    <div style={{ height: 'calc(100vh - 40px)', width: '100%', display: 'flex', flexDirection: 'column', position: 'relative' }}>
      
      {/* ── Preview Mode Banner ────────────────────────────────────────── */}
      {isPreview && (
        <div style={{
          background: 'var(--color-primary)', color: 'white',
          padding: '10px 40px', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          boxShadow: '0 2px 8px rgba(0,0,0,0.2)', zIndex: 10,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Sparkles size={18} />
            <span style={{ fontSize: 14, fontWeight: 500 }}>
              {zh ? '您正在預覽有條件公開的圖譜結構' : 'You are previewing a conditional public graph structure'}
            </span>
          </div>
          <button 
            className="btn-primary" 
            style={{ padding: '6px 16px', background: 'white', color: 'var(--color-primary)', border: 'none' }}
            disabled={requestSent}
            onClick={async () => {
              try {
                await workspaces.createJoinRequest(wsId);
                setRequestSent(true);
                alert(zh ? '申請已送出' : 'Join request sent');
              } catch (e: any) {
                alert(e.message);
              }
            }}
          >
            {requestSent ? (zh ? '申請待審核' : 'Request Pending') : (zh ? '申請加入以查看細節' : 'Request to Join')}
          </button>
        </div>
      )}

      {/* ── Shared header — always visible regardless of 2D/3D mode ────────── */}
      <header
        className="page-header animate-fade-in"
        style={{ padding: '0 40px', marginTop: '40px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}
      >
        <div>
          <h1 className="page-title">{zh ? '知識庫圖譜' : 'Knowledge Graph'}</h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <p className="page-subtitle" style={{ marginBottom: 0 }}>{subtitle}</p>
            {orphanCount > 0 && (
              <div 
                onClick={() => {
                  setOrphanFilter('orphan');
                  setGraphMode('table');
                }}
                style={{ 
                  fontSize: 11, padding: '2px 8px', borderRadius: 12, 
                  background: 'var(--color-warning-subtle)', color: 'var(--color-warning)', 
                  cursor: 'pointer', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4
                }}
              >
                <TriangleAlert size={10} />
                {orphanCount} {zh ? '個孤立節點' : 'Orphans'}
              </div>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {/* ── 2D / 3D mode toggle ─────────────────────────────────────── */}
          <div style={{
            display: 'flex',
            background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
            borderRadius: 8, overflow: 'hidden', boxShadow: 'var(--shadow-sm)',
          }}>
            {(['2d', '3d', 'table'] as GraphMode[]).map(mode => (
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
                {mode === '2d' ? <Network size={12} /> : mode === '3d' ? <Layers size={12} /> : <Table2 size={12} />}
                {mode.toUpperCase()}
              </button>
            ))}
          </div>

          <div style={{ width: 1, height: 24, background: 'var(--border-default)' }} />

          {/* ── Health mode toggle ────────────────────────────────────────── */}
          <button
            className={healthMode ? "btn-primary" : "btn-secondary"}
            onClick={() => setHealthMode(!healthMode)}
            style={{ height: 38, display: 'flex', alignItems: 'center', gap: 6 }}
          >
            <Sparkles size={16} className={healthMode ? "animate-pulse" : ""} />
            {zh ? '健康模式' : 'Health Mode'}
          </button>

          <button
            className={showArchived ? "btn-primary" : "btn-secondary"}
            onClick={() => setShowArchived(!showArchived)}
            style={{ height: 38, display: 'flex', alignItems: 'center', gap: 6 }}
            title={zh ? '顯示/隱藏已歸檔節點' : 'Toggle archived nodes'}
          >
            <Archive size={16} />
            {zh ? '歸檔' : 'Archived'}
          </button>

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
              {searchMode === 'semantic' ? 'AI' : (zh ? '文字' : 'Text')}
            </button>
          </div>

          {/* ── Auto-connect orphans ────────────────────────────────────── */}
          {!isPreview && wsId && (
            <ConnectOrphansButton wsId={wsId} zh={zh} onDone={load} />
          )}

          {/* ── Refresh ─────────────────────────────────────────────────── */}
          <button className="btn-secondary" onClick={load} disabled={loading} style={{ height: 38 }}>
            <RefreshCw
              size={16}
              style={{ marginRight: 6, animation: loading ? 'spin 1s linear infinite' : 'none' }}
            />
            {zh ? '重新整理' : 'Refresh'}
          </button>

          {/* ── New Node ────────────────────────────────────────────────── */}
          {!isPreview && (
          <button className="btn-primary" onClick={onNewNode} style={{ height: 38, display: 'flex', alignItems: 'center', gap: 6 }}>
            <PlusCircle size={15} />
            {zh ? '新增節點' : 'New Node'}
          </button>
          )}
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
            healthMode={healthMode}
            healthScores={healthScores}
            kbType={workspace?.kb_type}
            isPreview={isPreview}
          />
        ) : graphMode === '3d' ? (
          <GraphView3D
            apiNodes={apiNodes}
            apiEdges={apiEdges}
            relationColors={RELATION_COLORS}
            onEditNode={onEditNode}
            healthMode={healthMode}
            healthScores={healthScores}
            isPreview={isPreview}
          />
        ) : (
          <TableView 
            wsId={wsId} 
            onEditNode={onEditNode} 
            isAdmin={workspace?.owner_id === userId}
            initialFilter={orphanFilter}
          />
        )}
      </div>
    </div>
  );
}

function ConnectOrphansButton({ wsId, zh, onDone }: { wsId: string; zh: boolean; onDone: () => void }) {
  const [state, setState] = useState<'idle' | 'running' | 'done' | 'error'>('idle');
  const [msg, setMsg] = useState('');

  const handleClick = async () => {
    setState('running');
    setMsg('');
    try {
      const res = await edgesApi.connectOrphans(wsId);
      const count = res.orphan_count ?? 0;
      setMsg(count === 0
        ? (zh ? '沒有孤立節點' : 'No orphans found')
        : (zh ? `正在為 ${count} 個孤立節點補邊…` : `Connecting ${count} orphans in background…`));
      setState('done');
      if (count > 0) setTimeout(() => { onDone(); setState('idle'); }, 8000);
      else setTimeout(() => setState('idle'), 3000);
    } catch (e: any) {
      setMsg(e.message);
      setState('error');
      setTimeout(() => setState('idle'), 4000);
    }
  };

  return (
    <div style={{ position: 'relative' }}>
      <button
        className="btn-secondary"
        onClick={handleClick}
        disabled={state === 'running'}
        style={{ height: 38, display: 'flex', alignItems: 'center', gap: 6 }}
        title={zh ? '讓 AI 為孤立節點自動建立關聯' : 'Let AI connect orphan nodes'}
      >
        <GitMerge size={15} style={{ animation: state === 'running' ? 'spin 1s linear infinite' : 'none' }} />
        {zh ? '補邊' : 'Connect'}
      </button>
      {msg && (
        <div style={{
          position: 'absolute', top: 44, right: 0, whiteSpace: 'nowrap',
          background: state === 'error' ? 'var(--color-error)' : 'var(--color-primary)',
          color: 'white', fontSize: 12, padding: '4px 10px', borderRadius: 6,
          boxShadow: 'var(--shadow-md)', zIndex: 100,
        }}>
          {msg}
        </div>
      )}
    </div>
  );
}
