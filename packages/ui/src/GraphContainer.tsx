/**
 * GraphContainer — shared owner of graph state.
 *
 * Renders a single persistent header (search, mode toggle, refresh, new-node)
 * that survives 2D ↔ 3D switching, then mounts either GraphView (2D canvas)
 * or GraphView3D (3D canvas) below it — both are now pure renderers.
 */
import { useState, useCallback, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Archive, RefreshCw, Sparkles, Network, Layers, PlusCircle, GitMerge, Table2, TriangleAlert, Brain, FileUp } from 'lucide-react';
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
  onSwitchView: (view: any) => void;
  userId?: string;
  user?: any;
  onLogout?: () => void;
  showMcpStatus?: boolean;
  setShowMcpStatus?: (v: boolean) => void;
}

export default function GraphContainer({ 
  wsId, reloadKey, onEditNode, onNewNode, onSwitchView, userId
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

  // ── Archive toggle (must precede load so it's in scope for the callback) ──
  const [showArchived, setShowArchived] = useState(false);

  // ── Display limit ─────────────────────────────────────────────────────────
  const LIMIT_OPTIONS = [100, 200, 500, 1000, 'unlimited'] as const;
  type LimitOption = typeof LIMIT_OPTIONS[number];
  const [displayLimit, setDisplayLimit] = useState<LimitOption>(200);
  const [orphanFilter, setOrphanFilter] = useState<string | undefined>(undefined);
  const [dofEnabled, setDofEnabled] = useState(true);

  // ── Load all data ─────────────────────────────────────────────────────────
  const load = useCallback(async () => {
    if (!wsId) return;
    setLoading(true);
    setError('');
    try {
      const queryLimit = displayLimit === 'unlimited' ? '50000' : String(displayLimit);
      const [rawNodes, rawEdges, ws, analytics] = await Promise.all([
        nodesApi.list(wsId, showArchived ? { status: 'all', limit: queryLimit } : { limit: queryLimit }),
        edgesApi.list(wsId),
        workspaces.get(wsId),
        workspaces.analytics(wsId).catch(() => null),
      ]);
      setApiNodes(rawNodes);
      setApiEdges(rawEdges);
      setWorkspace(ws);
      setTotalNodes(analytics?.total_nodes ?? null);
      setTotalOrphans(analytics?.orphan_node_count ?? 0);
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
  const healthMode = false; // setHealthMode removed to fix build error. Restore if health toggle is added.
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
      setDofEnabled(false); // Disable DOF in health mode for clarity
    }
  }, [healthMode, loadHealthScores]);


  // ── Subtitle text ─────────────────────────────────────────────────────────
  const atDisplayCap = !loading && !error && displayLimit !== 'unlimited' && apiNodes.length >= displayLimit && totalNodes !== null && totalNodes > displayLimit;
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

      {/* ── Public Spec KB Banner ─────────────────────────────────────── */}
      {wsId === 'ws_spec0001' && !isPreview && (
        <div style={{
          background: 'var(--bg-elevated)', borderBottom: '1px solid var(--border-default)',
          color: 'var(--text-primary)', padding: '8px 40px', display: 'flex', alignItems: 'center', gap: 10,
          fontSize: 13, fontWeight: 500, zIndex: 10
        }}>
          <Brain size={16} style={{ color: 'var(--color-primary)' }} />
          <span>
            {zh ? '📘 此為公開展示用知識庫' : '📘 This is a public demonstration knowledge base'}
            <span style={{ marginLeft: 8, opacity: 0.7, fontWeight: 400 }}>
              {zh ? '展示 MemTrace 的核心功能，可透過 MCP 直接探索' : 'Demonstrates core features; explore directly via MCP'}
            </span>
          </span>
        </div>
      )}

      {/* ── Page Title & Stats (Absolute, vertically aligned with the user menu @ top-right) ── */}
      <div
        style={{
          position: 'absolute', top: 22, left: 40,
          height: 38, display: 'flex', alignItems: 'center', gap: 12,
          zIndex: 1100, maxWidth: 'calc(100% - 320px)', overflow: 'hidden'
        }}
      >
        <h1 className="page-title" style={{ fontSize: 18, fontWeight: 700, margin: 0, color: 'var(--text-primary)', whiteSpace: 'nowrap', lineHeight: '38px' }}>
          {zh ? '知識圖譜' : 'Knowledge Graph'}
        </h1>
        <div style={{ width: 1, height: 16, background: 'var(--border-default)', flexShrink: 0 }} />
        <p style={{ margin: 0, fontSize: 13, color: 'var(--text-muted)', fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {subtitle}
        </p>
      </div>

      {/* ── Toolbar — left group (filters) + right group (view & actions) ───── */}
      <header
        className="page-header animate-fade-in"
        style={{
          padding: '0 40px',
          marginTop: 80,
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          rowGap: 10,
          columnGap: 16,
          minHeight: 38,
        }}
      >
        {/* ─── LEFT GROUP: badges + display limit ─────────────────────────── */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          {orphanCount > 0 && (
            <div
              onClick={() => { setOrphanFilter('orphan'); setGraphMode('table'); }}
              style={{
                fontSize: 11, padding: '0 10px', borderRadius: 20, height: 28,
                background: 'var(--color-warning-subtle)', color: 'var(--color-warning)',
                cursor: 'pointer', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6,
                border: '1px solid var(--color-warning)', whiteSpace: 'nowrap'
              }}
            >
              <TriangleAlert size={14} />
              {orphanCount} {zh ? '個孤立節點' : 'Orphans'}
            </div>
          )}
          {atDisplayCap && (
            <div
              onClick={() => setGraphMode('table')}
              title={zh ? '圖形視圖最多顯示 200 個節點，點擊切換至表格視圖以查看全部' : 'Graph view shows up to 200 nodes. Click to switch to Table view for all nodes.'}
              style={{
                fontSize: 11, padding: '0 10px', borderRadius: 20, height: 28,
                background: 'var(--color-error-subtle)', color: 'var(--color-error)',
                cursor: 'pointer', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6,
                border: '1px solid var(--color-error)', whiteSpace: 'nowrap'
              }}
            >
              <TriangleAlert size={14} />
              {zh ? `圖形上限 ${displayLimit}` : `Graph cap ${displayLimit}`}
            </div>
          )}
          {(orphanCount > 0 || atDisplayCap) && (
            <div style={{ width: 1, height: 24, background: 'var(--border-default)' }} />
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
              {zh ? '顯示上限' : 'Show'}
            </span>
            <select
              value={displayLimit}
              onChange={(e) => setDisplayLimit(e.target.value === 'unlimited' ? 'unlimited' : Number(e.target.value) as LimitOption)}
              style={{
                padding: '0 28px 0 12px', fontSize: 12, fontWeight: 600, cursor: 'pointer',
                background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
                borderRadius: 8, color: 'var(--text-primary)', outline: 'none', height: 38,
                boxShadow: 'var(--shadow-sm)',
                appearance: 'none',
                backgroundImage: `url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e")`,
                backgroundRepeat: 'no-repeat',
                backgroundPosition: 'right 8px center',
                backgroundSize: '14px',
              }}
            >
              {LIMIT_OPTIONS.map(opt => (
                <option key={opt} value={opt}>
                  {opt === 'unlimited' ? (zh ? '無限制' : 'Unlimited') : opt}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* ─── RIGHT GROUP: view mode + tools + actions ───────────────────── */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          {/* 2D / 3D / Table toggle */}
          <div style={{
            display: 'flex',
            background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
            borderRadius: 8, overflow: 'hidden', boxShadow: 'var(--shadow-sm)',
            height: 38
          }}>
            {(['2d', '3d', 'table'] as GraphMode[]).map(mode => (
              <button
                key={mode}
                onClick={() => setGraphMode(mode)}
                style={{
                  padding: '0 14px', fontSize: 12, fontWeight: 600, cursor: 'pointer',
                  border: 'none', height: '100%',
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

          {/* Tool toggles */}
          <button
            className={showArchived ? "btn-primary" : "btn-secondary"}
            onClick={() => setShowArchived(!showArchived)}
            style={{ height: 38, display: 'flex', alignItems: 'center', gap: 6 }}
            title={zh ? '顯示/隱藏已歸檔節點' : 'Toggle archived nodes'}
          >
            <Archive size={16} />
            {zh ? '歸檔' : 'Archived'}
          </button>

          {graphMode === '3d' && (
            <button
              className={dofEnabled ? "btn-primary" : "btn-secondary"}
              onClick={() => setDofEnabled(!dofEnabled)}
              style={{ height: 38, display: 'flex', alignItems: 'center', gap: 6 }}
              title={zh ? '景深模糊效果（Depth of Field）' : 'Depth of Field blur effect'}
            >
              <Sparkles size={16} />
              {zh ? '景深' : 'DOF'}
            </button>
          )}

          {!isPreview && wsId && (
            <ConnectOrphansButton wsId={wsId} zh={zh} onDone={load} />
          )}

          <button
            className="btn-secondary"
            onClick={load}
            disabled={loading}
            style={{ height: 38, display: 'flex', alignItems: 'center', gap: 6 }}
          >
            <RefreshCw
              size={16}
              style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }}
            />
            {zh ? '重新整理' : 'Refresh'}
          </button>

          <div style={{ width: 1, height: 24, background: 'var(--border-default)' }} />

          {!isPreview && (
            <button
              className="btn-primary"
              onClick={onNewNode}
              style={{ height: 38, display: 'flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap' }}
            >
              <PlusCircle size={15} />
              {zh ? '新增節點' : 'New Node'}
            </button>
          )}
        </div>
      </header>

      {/* ── Canvas area — swaps on mode change, header stays ────────────────── */}
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', marginTop: '20px' }}>
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
            dofEnabled={dofEnabled}
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
