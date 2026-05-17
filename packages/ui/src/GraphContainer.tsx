/**
 * GraphContainer — shared owner of graph state.
 *
 * Renders a single persistent header (search, mode toggle, refresh, new-node)
 * that survives 2D ↔ 3D switching, then mounts either GraphView (2D canvas)
 * or GraphView3D (3D canvas) below it — both are now pure renderers.
 */
import { useState, useCallback, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Archive, RefreshCw, Sparkles, Network, Layers, PlusCircle, GitMerge, Table2, TriangleAlert, FileUp, Compass } from 'lucide-react';
import { nodes as nodesApi, edges as edgesApi, workspaces, clusters as clustersApi, type Node as ApiNode, type Edge as ApiEdge, type NodeCluster } from './api';
import GraphView from './GraphView';
import GraphView3D from './GraphView3D';
import TableView from './TableView';
import NeighborhoodView from './NeighborhoodView';

type GraphMode = '2d' | '3d' | 'table' | 'explore';

const CLUSTER_ACCENT: Record<string, string> = {
  blue:    '#3b82f6',
  teal:    '#14b8a6',
  violet:  '#8b5cf6',
  amber:   '#f59e0b',
  rose:    '#f43f5e',
  primary: '#6366f1',
  green:   '#10b981',
  red:     '#ef4444',
};

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
  onSwitchView: (view: any) => void;
  userId?: string;
  user?: any;
  onLogout?: () => void;
  showMcpStatus?: boolean;
  setShowMcpStatus?: (v: boolean) => void;
  onExplore?: (nodeId: string) => void;
}

export default function GraphContainer({ 
  wsId, reloadKey, onEditNode, onNewNode, onSwitchView, userId, onExplore
}: Props) {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';

  // ── Shared graph state ────────────────────────────────────────────────────
  const [apiNodes, setApiNodes]     = useState<ApiNode[]>([]);
  const [apiEdges, setApiEdges]     = useState<ApiEdge[]>([]);
  const [totalNodes, setTotalNodes] = useState<number | null>(null);
  const [totalOrphans, setTotalOrphans] = useState<number>(0);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState('');
  const [graphMode, setGraphMode]   = useState<GraphMode>('2d');
  const [isPreview, setIsPreview]   = useState(false);
  const [requestSent, setRequestSent] = useState(false);
  const [workspace, setWorkspace]   = useState<any>(null);
  const [exploreRootNodeId, setExploreRootNodeId] = useState<string | null>(null);

  // Expose onExplore to parent via imperative-like prop update if needed,
  // but here we just handle it if passed.
  useEffect(() => {
    if (onExplore) {
      // This is a bit hacky, but lets the parent trigger explore mode
      (window as any).mt_trigger_explore = (nodeId: string) => {
        setExploreRootNodeId(nodeId);
        setGraphMode('explore');
      };
    }
  }, [onExplore]);

  // ── Archive toggle (must precede load so it's in scope for the callback) ──
  const [showArchived, setShowArchived] = useState(false);

  // ── Clusters ──────────────────────────────────────────────────────────────
  const [wsClusters, setWsClusters] = useState<NodeCluster[]>([]);
  const [activeClusters, setActiveClusters] = useState<Set<string>>(new Set());

  const toggleCluster = useCallback((id: string) => {
    setActiveClusters(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }, []);

  // ── Display limit ─────────────────────────────────────────────────────────
  const LIMIT_OPTIONS = [50, 100, 200, 500] as const;
  type LimitOption = typeof LIMIT_OPTIONS[number];
  const [displayLimit, setDisplayLimit] = useState<LimitOption>(100);
  const [orphanFilter, setOrphanFilter] = useState<string | undefined>(undefined);
  const [dofEnabled, setDofEnabled] = useState(true);

  // ── Load all data ─────────────────────────────────────────────────────────
  const load = useCallback(async () => {
    if (!wsId) return;
    setLoading(true);
    setError('');
    try {
      const queryLimit = String(displayLimit);
      const [rawNodes, rawEdges, ws, analytics, clusterList] = await Promise.all([
        nodesApi.list(wsId, showArchived ? { status: 'all', limit: queryLimit } : { limit: queryLimit }),
        edgesApi.list(wsId),
        workspaces.get(wsId),
        workspaces.analytics(wsId).catch(() => null),
        clustersApi.list(wsId).catch(() => [] as NodeCluster[]),
      ]);
      setApiNodes(rawNodes);
      setApiEdges(rawEdges);
      setWorkspace(ws);
      setTotalNodes(analytics?.total_nodes ?? null);
      setTotalOrphans(analytics?.orphan_node_count ?? 0);
      setWsClusters(clusterList);
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
  }, [wsId, showArchived, displayLimit]);

  useEffect(() => { load(); }, [load, reloadKey]);

  // ── Health mode state ────────────────────────────────────────────────────
  const healthMode = false;
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
    if (healthMode) {
      loadHealthScores();
      setDofEnabled(false);
    }
  }, [healthMode, loadHealthScores]);


  // ── Subtitle text ─────────────────────────────────────────────────────────
  const atDisplayCap = !loading && !error && apiNodes.length >= displayLimit && totalNodes !== null && totalNodes > displayLimit;
  const subtitle = loading
    ? (zh ? '載入中…' : 'Loading…')
    : error
      ? `Error: ${error}`
      : atDisplayCap
        ? (zh
            ? `顯示 ${apiNodes.length} / ${totalNodes} 節點 · ${apiEdges.length} 連結`
            : `Showing ${apiNodes.length} of ${totalNodes} nodes · ${apiEdges.length} edges`)
        : `${apiNodes.length} ${zh ? '節點' : 'nodes'} · ${apiEdges.length} ${zh ? '連結' : 'edges'}`;

  const orphanCount = totalOrphans;

  useEffect(() => {
    window.dispatchEvent(new CustomEvent('mt:update-header', { detail: { subtitle } }));
  }, [subtitle]);

  if (!wsId) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 15 }}>
        {zh ? '請選擇工作區以檢視圖譜' : 'Select a workspace to view the graph.'}
      </div>
    );
  }

  return (
    <div style={{ flex: 1, minHeight: 0, width: '100%', display: 'flex', flexDirection: 'column', position: 'relative' }}>
      
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

      {/* ── Toolbar ────────────────────────────────────────────────────────── */}
      <header
        className="page-header animate-fade-in"
        style={{
          padding: '8px 24px',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          rowGap: 6,
          columnGap: 12,
          background: 'var(--bg-base)',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        {/* ─── LEFT: badges + limit ───────────────────────────────────────── */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          {orphanCount > 0 && (
            <div
              onClick={() => { setOrphanFilter('orphan'); setGraphMode('table'); }}
              style={{
                fontSize: 11, padding: '0 8px', borderRadius: 20, height: 26,
                background: 'var(--color-warning-subtle)', color: 'var(--color-warning)',
                cursor: 'pointer', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4,
                border: '1px solid var(--color-warning)', whiteSpace: 'nowrap',
              }}
            >
              <TriangleAlert size={12} />
              {orphanCount} {zh ? '孤立' : 'Orphans'}
            </div>
          )}
          {atDisplayCap && (
            <div
              onClick={() => setGraphMode('table')}
              title={zh ? '已達顯示上限，點擊切換表格視圖' : 'Display cap reached, click for table view'}
              style={{
                fontSize: 11, padding: '0 8px', borderRadius: 20, height: 26,
                background: 'var(--color-error-subtle)', color: 'var(--color-error)',
                cursor: 'pointer', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4,
                border: '1px solid var(--color-error)', whiteSpace: 'nowrap',
              }}
            >
              <TriangleAlert size={12} />
              {displayLimit}
            </div>
          )}

          <select
            value={displayLimit}
            onChange={(e) => setDisplayLimit(Number(e.target.value) as LimitOption)}
            title={zh ? '顯示上限' : 'Display limit'}
            style={{
              padding: '0 24px 0 10px', fontSize: 12, fontWeight: 600, cursor: 'pointer',
              background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
              borderRadius: 7, color: 'var(--text-primary)', outline: 'none', height: 32,
              appearance: 'none',
              backgroundImage: `url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e")`,
              backgroundRepeat: 'no-repeat', backgroundPosition: 'right 7px center', backgroundSize: '12px',
            }}
          >
            {LIMIT_OPTIONS.map(opt => <option key={opt} value={opt}>{opt}</option>)}
          </select>
        </div>

        {/* ─── RIGHT: view toggle + tools + actions ───────────────────────── */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          {/* View mode tabs */}
          <div style={{
            display: 'flex', background: 'var(--bg-surface)',
            border: '1px solid var(--border-default)', borderRadius: 7,
            overflow: 'hidden', height: 32,
          }}>
            {(['2d', '3d', 'table', 'explore'] as GraphMode[]).map(mode => (
              <button
                key={mode}
                onClick={() => { setGraphMode(mode); if (mode !== 'explore') setExploreRootNodeId(null); }}
                disabled={mode === 'explore' && !exploreRootNodeId}
                style={{
                  padding: '0 11px', fontSize: 11, fontWeight: 600, cursor: 'pointer',
                  border: 'none', height: '100%',
                  background: graphMode === mode ? 'var(--color-primary)' : 'transparent',
                  color: graphMode === mode ? 'white' : (mode === 'explore' && !exploreRootNodeId ? 'var(--text-disabled)' : 'var(--text-muted)'),
                  transition: 'all 0.15s', display: 'flex', alignItems: 'center', gap: 4,
                  opacity: mode === 'explore' && !exploreRootNodeId ? 0.4 : 1,
                }}
              >
                {mode === '2d' ? <Network size={11} /> : mode === '3d' ? <Layers size={11} /> : mode === 'table' ? <Table2 size={11} /> : <Compass size={11} />}
                {mode.toUpperCase()}
              </button>
            ))}
          </div>

          <div style={{ width: 1, height: 20, background: 'var(--border-default)' }} />

          <button
            className={showArchived ? 'btn-primary' : 'btn-secondary'}
            onClick={() => setShowArchived(!showArchived)}
            style={{ height: 32, width: 32, padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            title={zh ? '顯示/隱藏已歸檔節點' : 'Toggle archived nodes'}
          >
            <Archive size={14} />
          </button>

          {graphMode === '3d' && (
            <button
              className={dofEnabled ? 'btn-primary' : 'btn-secondary'}
              onClick={() => setDofEnabled(!dofEnabled)}
              style={{ height: 32, width: 32, padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              title={zh ? '景深效果' : 'Depth of Field'}
            >
              <Sparkles size={14} />
            </button>
          )}

          {!isPreview && wsId && (
            <ConnectOrphansButton wsId={wsId} zh={zh} onDone={load} compact />
          )}

          <button
            className="btn-secondary"
            onClick={load}
            disabled={loading}
            style={{ height: 32, width: 32, padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            title={zh ? '重新整理' : 'Refresh'}
          >
            <RefreshCw size={14} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
          </button>

          <div style={{ width: 1, height: 20, background: 'var(--border-default)' }} />

          {!isPreview && (
            <button
              className="btn-primary"
              onClick={onNewNode}
              style={{ height: 32, display: 'flex', alignItems: 'center', gap: 5, padding: '0 12px', whiteSpace: 'nowrap', fontSize: 12 }}
            >
              <PlusCircle size={13} />
              {zh ? '新增節點' : 'New Node'}
            </button>
          )}
        </div>
      </header>

      {/* ── Cluster filter chips (shown when clusters exist, 2D/3D mode) ─── */}
      {wsClusters.length > 0 && (graphMode === '2d' || graphMode === '3d') && (
        <div style={{
          padding: '6px 24px',
          display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap',
          background: 'var(--bg-base)', borderBottom: '1px solid var(--border-subtle)',
        }}>
          <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase', marginRight: 2 }}>
            {zh ? '群組' : 'Clusters'}
          </span>
          {activeClusters.size > 0 && (
            <button
              onClick={() => setActiveClusters(new Set())}
              style={{ fontSize: 10, color: 'var(--color-primary)', background: 'none', border: 'none', cursor: 'pointer', padding: '0 4px' }}
            >
              {zh ? '顯示全部' : 'Show all'}
            </button>
          )}
          {wsClusters.map(cl => {
            const accent = CLUSTER_ACCENT[cl.color] ?? 'var(--color-primary)';
            const isActive = activeClusters.size === 0 || activeClusters.has(cl.id);
            return (
              <button
                key={cl.id}
                onClick={() => toggleCluster(cl.id)}
                style={{
                  height: 22, padding: '0 9px', borderRadius: 11, fontSize: 11, fontWeight: 600,
                  border: `1px solid ${accent}`,
                  background: isActive ? `${accent}20` : 'transparent',
                  color: isActive ? accent : 'var(--text-muted)',
                  cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
                  transition: 'all 0.15s', opacity: isActive ? 1 : 0.45,
                }}
              >
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: accent, flexShrink: 0 }} />
                {zh ? cl.name_zh : cl.name_en}
                <span style={{ opacity: 0.6, fontSize: 10 }}>{cl.node_count}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* ── Canvas area ── */}
      <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {!loading && apiNodes.length === 0 && !error ? (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-surface)' }}>
            <div style={{ maxWidth: 450, textAlign: 'center', padding: 40 }} className="animate-fade-in">
              <div style={{ 
                width: 80, height: 80, borderRadius: 24, background: 'var(--color-primary-subtle)', 
                display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 24px',
                color: 'var(--color-primary)'
              }}>
                <Network size={40} />
              </div>
              <h2 style={{ fontSize: 24, marginBottom: 12 }}>{zh ? '開始建立您的知識圖譜' : 'Start building your graph'}</h2>
              <p style={{ color: 'var(--text-muted)', fontSize: 15, lineHeight: 1.6, marginBottom: 32 }}>
                {zh 
                  ? '這個工作區目前還是空的。您可以手動新增節點，或上傳文件讓 AI 自動提取知識點。' 
                  : 'This workspace is currently empty. You can manually add nodes or upload documents to let AI extract knowledge for you.'}
              </p>
              <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
                <button className="btn-primary" onClick={onNewNode} style={{ padding: '10px 24px', height: 44, display: 'flex', alignItems: 'center', gap: 8, borderRadius: 10 }}>
                  <PlusCircle size={18} />
                  {zh ? '手動新增' : 'Add Node'}
                </button>
                <button className="btn-secondary" onClick={() => onSwitchView('ingest')} style={{ padding: '10px 24px', height: 44, display: 'flex', alignItems: 'center', gap: 8, borderRadius: 10 }}>
                  <FileUp size={18} />
                  {zh ? '上傳文件' : 'Ingest Docs'}
                </button>
              </div>
            </div>
          </div>
        ) : graphMode === '2d' ? (
          <GraphView
            apiNodes={apiNodes}
            apiEdges={apiEdges}
            relationColors={RELATION_COLORS}
            onEditNode={onEditNode}
            healthMode={healthMode}
            healthScores={healthScores}
            kbType={workspace?.kb_type}
            isPreview={isPreview}
            clusters={wsClusters}
            activeClusters={activeClusters}
          />
        ) : graphMode === '3d' ? (
          <GraphView3D
            apiNodes={apiNodes}
            apiEdges={apiEdges}
            onEditNode={onEditNode}
            healthMode={healthMode}
            healthScores={healthScores}
            isPreview={isPreview}
            dofEnabled={dofEnabled}
          />
        ) : graphMode === 'explore' && wsId ? (
          <NeighborhoodView
            wsId={wsId}
            rootNodeId={exploreRootNodeId}
            onNodeClick={onEditNode}
            onExploreNode={(nodeId) => {
              setExploreRootNodeId(nodeId);
            }}
            onClose={() => setGraphMode('2d')}
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

function ConnectOrphansButton({ wsId, zh, onDone, compact = false }: { wsId: string; zh: boolean; onDone: () => void; compact?: boolean }) {
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
        style={compact
          ? { height: 32, width: 32, padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }
          : { height: 38, display: 'flex', alignItems: 'center', gap: 6 }}
        title={zh ? '讓 AI 為孤立節點自動建立關聯' : 'Let AI connect orphan nodes'}
      >
        <GitMerge size={compact ? 14 : 15} style={{ animation: state === 'running' ? 'spin 1s linear infinite' : 'none' }} />
        {!compact && (zh ? '補邊' : 'Connect')}
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
