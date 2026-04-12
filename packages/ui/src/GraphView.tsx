/**
 * GraphView (2D) — pure ReactFlow canvas renderer.
 * All data fetching and toolbar logic live in GraphContainer.
 */
import { useCallback, useState, useEffect } from 'react';
import ReactFlow, {
  Background, Controls, MiniMap,
  applyNodeChanges, applyEdgeChanges, addEdge,
} from 'reactflow';
import type { Node, Edge, Connection, NodeChange, EdgeChange } from 'reactflow';
import 'reactflow/dist/style.css';
import { useTranslation } from 'react-i18next';
import MemoryNode from './MemoryNode';
import { type Node as ApiNode, type Edge as ApiEdge } from './api';

const nodeTypes = { memoryNode: MemoryNode };

interface Props {
  apiNodes: ApiNode[];
  apiEdges: ApiEdge[];
  relationColors: Record<string, string>;
  onEditNode?: (node: ApiNode) => void;
}

export default function GraphView({ apiNodes, apiEdges, relationColors, onEditNode }: Props) {
  const { i18n } = useTranslation();

  const [rfNodes, setRfNodes] = useState<Node[]>([]);
  const [rfEdges, setRfEdges] = useState<Edge[]>([]);

  // ── Convert API nodes/edges → ReactFlow format whenever data changes ───────
  useEffect(() => {
    const cols = Math.ceil(Math.sqrt(apiNodes.length || 1));
    setRfNodes(apiNodes.map((n, i) => ({
      id: n.id,
      type: 'memoryNode',
      position: { x: (i % cols) * 240, y: Math.floor(i / cols) * 160 },
      data: {
        title: i18n.language === 'zh-TW' ? n.title_zh : n.title_en,
        type: n.content_type,
        tags: n.tags,
      },
    })));

    setRfEdges(apiEdges.map(e => ({
      id: e.id,
      source: e.from_id,
      target: e.to_id,
      animated: e.relation === 'depends_on',
      label: e.relation,
      style: { stroke: relationColors[e.relation] ?? 'var(--text-muted)' },
    })));
  }, [apiNodes, apiEdges, i18n.language, relationColors]);

  // ── ReactFlow handlers ────────────────────────────────────────────────────
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
  const onNodeDoubleClick = useCallback((_: React.MouseEvent, rfNode: Node) => {
    const apiNode = apiNodes.find(n => n.id === rfNode.id);
    if (apiNode && onEditNode) onEditNode(apiNode);
  }, [apiNodes, onEditNode]);

  return (
    <div style={{ width: '100%', height: '100%', padding: '0 40px 40px', boxSizing: 'border-box' }}>
      <div style={{ width: '100%', height: '100%', borderRadius: 16, overflow: 'hidden', border: '1px solid var(--border-default)', background: 'var(--bg-surface)' }}>
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
          <Background color="var(--border-default)" gap={20} size={1} />
          <Controls style={{ background: 'var(--bg-surface)', fill: 'var(--text-primary)' }} />
          <MiniMap
            style={{ background: 'var(--bg-surface)' }}
            nodeColor={() => 'var(--color-primary)'}
            maskColor="var(--bg-overlay)"
          />
        </ReactFlow>
      </div>
    </div>
  );
}
