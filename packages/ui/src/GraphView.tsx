/**
 * GraphView (2D) pure ReactFlow canvas renderer.
 * All data fetching and toolbar logic live in GraphContainer.
 */
import { useCallback, useEffect, useState } from 'react';
import ReactFlow, {
  Background, MiniMap,
  applyNodeChanges, applyEdgeChanges, addEdge,
  useViewport, ReactFlowProvider,
} from 'reactflow';
import type { Node, Edge, Connection, NodeChange, EdgeChange } from 'reactflow';
import 'reactflow/dist/style.css';
import { useTranslation } from 'react-i18next';
import MemoryNode from './MemoryNode';
import { type Node as ApiNode, type Edge as ApiEdge, type NodeHealthScore } from './api';

const nodeTypes = { memoryNode: MemoryNode };

interface Props {
  apiNodes: ApiNode[];
  apiEdges: ApiEdge[];
  relationColors: Record<string, string>;
  onEditNode?: (node: ApiNode) => void;
  healthMode?: boolean;
  healthScores?: Record<string, NodeHealthScore>;
  kbType?: 'evergreen' | 'ephemeral';
  isPreview?: boolean;
}

const HEALTH_COLORS: Record<string, string> = {
  healthy: '#22c55e',
  warning: '#eab308',
  critical: '#ef4444',
};

export default function GraphView(props: Props) {
  return (
    <ReactFlowProvider>
      <GraphViewInner {...props} />
    </ReactFlowProvider>
  );
}

function GraphViewInner({ apiNodes, apiEdges, relationColors, onEditNode, healthMode = false, healthScores = {}, kbType = 'evergreen', isPreview = false }: Props) {
  const { i18n } = useTranslation();

  const [rfNodes, setRfNodes] = useState<Node[]>([]);
  const [rfEdges, setRfEdges] = useState<Edge[]>([]);

  const zh = i18n.language === 'zh-TW';

  useEffect(() => {
    const cols = Math.ceil(Math.sqrt(apiNodes.length || 1));
    setRfNodes(apiNodes.map((n, i) => {
      const health = healthScores[n.id];
      const confirmedAt = n.validity_confirmed_at ? new Date(n.validity_confirmed_at) : null;
      const isExpired = kbType === 'ephemeral' && (!confirmedAt || (Date.now() - confirmedAt.getTime() > 90 * 24 * 3600 * 1000));
      
      return {
        id: n.id,
        type: 'memoryNode',
        position: { x: (i % cols) * 240, y: Math.floor(i / cols) * 160 },
        data: {
          title: isPreview ? (zh ? '受保護的節點' : 'Protected Node') : (zh ? n.title_zh : n.title_en),
          type: isPreview ? 'hidden' : n.content_type,
          tags: isPreview ? [] : n.tags,
          isEmpty: !isPreview && !n.body_zh && !n.body_en,
          healthColor: !isPreview && healthMode && health ? HEALTH_COLORS[health.label] : (isPreview ? '#94a3b8' : undefined),
          healthTooltip: !isPreview && healthMode && health ? `Health ${(health.score * 100).toFixed(0)}% · ${health.reason}` : undefined,
          validityExpired: !isPreview && isExpired,
          isPreview,
        },
      };
    }));

    setRfEdges(apiEdges.map(e => ({
      id: e.id,
      source: e.from_id,
      target: e.to_id,
      animated: e.relation === 'depends_on',
      label: e.relation,
      style: { 
        stroke: relationColors[e.relation] ?? 'var(--text-muted)',
        strokeDasharray: e.relation === 'related_to' ? '5,5' : undefined 
      },
    })));
  }, [apiNodes, apiEdges, zh, relationColors, healthMode, healthScores]);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setRfNodes(nds => applyNodeChanges(changes, nds)), [],
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setRfEdges(eds => applyEdgeChanges(changes, eds)), [],
  );
  const onConnect = useCallback(
    (params: Connection | Edge) =>
      setRfEdges(eds => addEdge(
        { ...params, animated: true, style: { stroke: 'var(--color-primary)' }, label: 'related_to' },
        eds,
      )),
    [],
  );

  const [isSpacePressed, setIsSpacePressed] = useState(false);
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.code === 'Space' && !['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement).tagName)) {
        setIsSpacePressed(true); e.preventDefault();
      }
    };
    const up = (e: KeyboardEvent) => { if (e.code === 'Space') setIsSpacePressed(false); };
    window.addEventListener('keydown', down);
    window.addEventListener('keyup', up);
    return () => { window.removeEventListener('keydown', down); window.removeEventListener('keyup', up); };
  }, []);

  const onNodeClick = useCallback((_: React.MouseEvent, rfNode: Node) => {
    if (isPreview) return;
    const apiNode = apiNodes.find(n => n.id === rfNode.id);
    if (apiNode && onEditNode) onEditNode(apiNode);
  }, [apiNodes, onEditNode, isPreview]);

  return (
    <div style={{ width: '100%', height: '100%', padding: '0 40px 40px', boxSizing: 'border-box' }}>
      <div style={{ width: '100%', height: '100%', borderRadius: 16, overflow: 'hidden', border: '1px solid var(--border-default)', background: 'var(--bg-surface)' }}>
        <GraphCanvas
          rfNodes={rfNodes}
          rfEdges={rfEdges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          isSpacePressed={isSpacePressed}
          zh={zh}
          apiNodes={apiNodes}
          i18n={i18n}
        />
      </div>
    </div>
  );
}

interface GraphCanvasProps {
  rfNodes: Node[];
  rfEdges: Edge[];
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  onConnect: (params: Connection | Edge) => void;
  onNodeClick: (event: React.MouseEvent, node: Node) => void;
  isSpacePressed: boolean;
  zh: boolean;
  apiNodes: ApiNode[];
  i18n: any;
}

function GraphCanvas({
  rfNodes, rfEdges, onNodesChange, onEdgesChange, onConnect, onNodeClick,
  isSpacePressed, zh, apiNodes, i18n,
}: GraphCanvasProps) {
  const lod = useLod();

  const nodesWithLod = rfNodes.map(n => {
    const apiNode = apiNodes.find(a => a.id === n.id);
    return {
      ...n,
      data: {
        ...n.data,
        lod,
        bodyPreview: apiNode
          ? (i18n.language === 'zh-TW' ? apiNode.body_zh : apiNode.body_en) ?? ''
          : '',
      },
    };
  });

  return (
    <ReactFlow
      nodes={nodesWithLod}
      edges={rfEdges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      onNodeClick={onNodeClick}
      nodeTypes={nodeTypes}
      panOnDrag={isSpacePressed}
      selectionOnDrag={!isSpacePressed}
      onlyRenderVisibleElements
      fitView
    >
      <Background color="var(--border-default)" gap={20} size={1} />

      <div style={{
        position: 'absolute', bottom: 14, left: 16,
        color: 'var(--text-muted)', fontSize: 11, opacity: 0.5,
        pointerEvents: 'none', lineHeight: 1.7, zIndex: 10
      }}>
        {zh
          ? '左鍵拖曳旋轉 · Space+拖曳平移 · 滾輪縮放 · 點擊開啟節點'
          : 'Left-click rotate · Space+drag pan · Scroll zoom · Click to open node'}
      </div>

      <MiniMap
        style={{ background: 'var(--bg-surface)' }}
        nodeColor={(node) => ((node?.data as any)?.healthColor || 'var(--color-primary)')}
        maskColor="var(--bg-overlay)"
      />
    </ReactFlow>
  );
}

type LodLevel = 'dot' | 'compact' | 'full' | 'expanded';

function useLod(): LodLevel {
  const { zoom } = useViewport();
  if (zoom < 0.25) return 'dot';
  if (zoom < 0.6)  return 'compact';
  if (zoom < 1.2)  return 'full';
  return 'expanded';
}
