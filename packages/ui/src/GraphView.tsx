import { useCallback, useState } from 'react';
import ReactFlow, { 
  Background, 
  Controls, 
  MiniMap,
  applyNodeChanges, 
  applyEdgeChanges, 
  addEdge
} from 'reactflow';
import type { 
  Node,
  Edge,
  Connection,
  NodeChange,
  EdgeChange
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useTranslation } from 'react-i18next';
import { Save } from 'lucide-react';
import MemoryNode from './MemoryNode';

const nodeTypes = {
  memoryNode: MemoryNode,
};

const initialNodes: Node[] = [
  {
    id: 'mem_1',
    type: 'memoryNode',
    position: { x: 250, y: 100 },
    data: { title: 'GKE 排程縮放模式', type: 'procedural', tags: ['gcp', 'kubernetes'] }
  },
  {
    id: 'mem_2',
    type: 'memoryNode',
    position: { x: 100, y: 300 },
    data: { title: 'Kubernetes 基礎知識', type: 'factual', tags: ['kubernetes'] }
  },
  {
    id: 'mem_3',
    type: 'memoryNode',
    position: { x: 400, y: 300 },
    data: { title: 'GCP 資源監控', type: 'factual', tags: ['gcp', 'monitoring'] }
  }
];

const initialEdges: Edge[] = [
  { id: 'edge_1_2', source: 'mem_2', target: 'mem_1', animated: true, label: 'depends_on', style: { stroke: 'var(--accent-color)' } },
  { id: 'edge_3_1', source: 'mem_3', target: 'mem_1', label: 'related_to', style: { stroke: 'var(--text-muted)' } }
];

export default function GraphView() {
  const { t } = useTranslation();
  const [nodes, setNodes] = useState<Node[]>(initialNodes);
  const [edges, setEdges] = useState<Edge[]>(initialEdges);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );

  const onConnect = useCallback(
    (params: Connection | Edge) => {
      // Allow manual connecting of nodes
      const newEdge = { ...params, animated: true, style: { stroke: 'var(--accent-color)' }, label: 'related_to' };
      setEdges((eds) => addEdge(newEdge, eds));
    },
    []
  );

  const handleSaveGraph = () => {
    // In a real implementation, this would save the edges to PostgreSQL
    alert('Graph relationships and node positions saved locally!');
  };

  return (
    <div style={{ height: 'calc(100vh - 40px)', width: '100%', display: 'flex', flexDirection: 'column' }}>
      <header className="page-header animate-fade-in" style={{ padding: '0 40px', marginTop: '40px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">{t('sidebar.graph')}</h1>
          <p className="page-subtitle">Drag nodes and connect edges manually to define memory relationships.</p>
        </div>
        <button className="btn-primary" onClick={handleSaveGraph}>
          <Save size={18} />
          Save Graph Topology
        </button>
      </header>

      <div style={{ flex: 1, position: 'relative', margin: '0 40px 40px 40px', borderRadius: '16px', overflow: 'hidden', border: '1px solid var(--panel-border)', background: 'rgba(0,0,0,0.4)', backdropFilter: 'blur(10px)' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          fitView
          theme="dark"
        >
          <Background color="var(--panel-border)" gap={20} size={1} />
          <Controls style={{ background: 'var(--bg-color)', fill: 'white' }} />
          <MiniMap style={{ background: 'var(--bg-color)' }} nodeColor={(n) => 'var(--accent-color)'} maskColor="rgba(0,0,0,0.5)" />
        </ReactFlow>
      </div>
    </div>
  );
}
