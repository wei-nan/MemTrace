import { useCallback, useState, useEffect } from 'react';
import ReactFlow, {
  Background, Controls, MiniMap,
  applyNodeChanges, applyEdgeChanges, addEdge,
} from 'reactflow';
import type { Node, Edge, Connection, NodeChange, EdgeChange } from 'reactflow';
import 'reactflow/dist/style.css';
import { useTranslation } from 'react-i18next';
import { RefreshCw } from 'lucide-react';
import MemoryNode from './MemoryNode';
import { nodes as nodesApi, edges as edgesApi, type Node as ApiNode } from './api';

const nodeTypes = { memoryNode: MemoryNode };

const RELATION_COLORS: Record<string, string> = {
  depends_on:  'var(--accent-color)',
  extends:     '#a78bfa',
  related_to:  'var(--text-muted)',
  contradicts: '#f87171',
};

interface Props {
  wsId?: string;
  reloadKey?: number;
  onEditNode?: (node: ApiNode) => void;
  onNewNode?: () => void;
}

export default function GraphView({ wsId, reloadKey, onEditNode, onNewNode }: Props) {
  const { t, i18n } = useTranslation();

  const [rfNodes, setRfNodes] = useState<Node[]>([]);
  const [rfEdges, setRfEdges] = useState<Edge[]>([]);
  const [apiNodes, setApiNodes] = useState<ApiNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // ── Load data ─────────────────────────────────────────────────────────────
  const load = useCallback(async () => {
    if (!wsId) return;
    setLoading(true); setError('');
    try {
      const [rawNodes, rawEdges] = await Promise.all([
        nodesApi.list(wsId),
        edgesApi.list(wsId),
      ]);
      setApiNodes(rawNodes);

      // Layout: simple grid until we have positions from DB
      const cols = Math.ceil(Math.sqrt(rawNodes.length || 1));
      const rfN: Node[] = rawNodes.map((n, i) => ({
        id: n.id,
        type: 'memoryNode',
        position: { x: (i % cols) * 240, y: Math.floor(i / cols) * 160 },
        data: {
          title: i18n.language === 'zh-TW' ? n.title_zh : n.title_en,
          type: n.content_type,
          tags: n.tags,
        },
      }));

      const rfE: Edge[] = rawEdges.map(e => ({
        id: e.id,
        source: e.from_id,
        target: e.to_id,
        animated: e.relation === 'depends_on',
        label: e.relation,
        style: { stroke: RELATION_COLORS[e.relation] ?? 'var(--text-muted)' },
      }));

      setRfNodes(rfN);
      setRfEdges(rfE);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [wsId]);

  useEffect(() => { load(); }, [load, reloadKey]);

  // ── ReactFlow handlers ────────────────────────────────────────────────────
  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setRfNodes(nds => applyNodeChanges(changes, nds)), [],
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setRfEdges(eds => applyEdgeChanges(changes, eds)), [],
  );
  const onConnect = useCallback(
    (params: Connection | Edge) =>
      setRfEdges(eds => addEdge({ ...params, animated: true, style: { stroke: 'var(--accent-color)' }, label: 'related_to' }, eds)),
    [],
  );

  const onNodeDoubleClick = useCallback((_: React.MouseEvent, rfNode: Node) => {
    const apiNode = apiNodes.find(n => n.id === rfNode.id);
    if (apiNode && onEditNode) onEditNode(apiNode);
  }, [apiNodes, onEditNode]);

  // ── Empty / no workspace state ────────────────────────────────────────────
  if (!wsId) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 15 }}>
        Select a workspace to view the graph.
      </div>
    );
  }

  return (
    <div style={{ height: 'calc(100vh - 40px)', width: '100%', display: 'flex', flexDirection: 'column' }}>
      <header className="page-header animate-fade-in" style={{ padding: '0 40px', marginTop: '40px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">{t('sidebar.graph')}</h1>
          <p className="page-subtitle">
            {loading ? 'Loading…' : error ? `Error: ${error}` : `${rfNodes.length} nodes · ${rfEdges.length} edges — double-click a node to edit`}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn-secondary" onClick={load} disabled={loading}>
            <RefreshCw size={16} style={{ marginRight: 6, animation: loading ? 'spin 1s linear infinite' : 'none' }} />
            Refresh
          </button>
          {onNewNode && (
            <button className="btn-primary" onClick={onNewNode}>
              + New Node
            </button>
          )}
        </div>
      </header>

      <div style={{ flex: 1, position: 'relative', margin: '0 40px 40px', borderRadius: 16, overflow: 'hidden', border: '1px solid var(--panel-border)', background: 'rgba(0,0,0,0.4)', backdropFilter: 'blur(10px)' }}>
        <ReactFlow
          nodes={rfNodes}
          edges={rfEdges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeDoubleClick={onNodeDoubleClick}
          nodeTypes={nodeTypes}
          fitView
        >
          <Background color="var(--panel-border)" gap={20} size={1} />
          <Controls style={{ background: 'var(--bg-color)', fill: 'white' }} />
          <MiniMap style={{ background: 'var(--bg-color)' }} nodeColor={() => 'var(--accent-color)'} maskColor="rgba(0,0,0,0.5)" />
        </ReactFlow>
      </div>
    </div>
  );
}
