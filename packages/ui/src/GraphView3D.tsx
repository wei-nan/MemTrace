import { useRef, useMemo } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import type { ForceGraphMethods } from 'react-force-graph-3d';
import { useTranslation } from 'react-i18next';
import { Save } from 'lucide-react';
import * as THREE from 'three';

const initialNodes = [
  { id: 'mem_1', name: 'GKE 排程縮放模式', val: 2, group: 1 },
  { id: 'mem_2', name: 'Kubernetes 基礎知識', val: 1.5, group: 1 },
  { id: 'mem_3', name: 'GCP 資源監控', val: 1.5, group: 1 },
  { id: 'mem_4', name: 'Prometheus 指標設計', val: 1.2, group: 2 },
  { id: 'mem_5', name: 'Grafana 視覺化', val: 1.2, group: 2 },
];

const initialEdges = [
  { source: 'mem_2', target: 'mem_1', name: 'depends_on' },
  { source: 'mem_3', target: 'mem_1', name: 'related_to' },
  { source: 'mem_4', target: 'mem_3', name: 'extends' },
  { source: 'mem_5', target: 'mem_4', name: 'depends_on' },
];

export default function GraphView3D() {
  const { t } = useTranslation();
  const fgRef = useRef<ForceGraphMethods>();
  
  const graphData = useMemo(() => ({
    nodes: initialNodes,
    links: initialEdges
  }), []);

  const handleSaveGraph = () => {
    alert('3D Graph Layout State conceptually saved!');
  };

  return (
    <div style={{ height: 'calc(100vh - 40px)', width: '100%', display: 'flex', flexDirection: 'column' }}>
      <header className="page-header animate-fade-in" style={{ padding: '0 40px', marginTop: '40px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">3D {t('sidebar.graph')}</h1>
          <p className="page-subtitle">Interactive 3D Cosmos mapping of memories.</p>
        </div>
        <button className="btn-primary" onClick={handleSaveGraph}>
          <Save size={18} />
          Save Graph Topology
        </button>
      </header>

      <div style={{ flex: 1, position: 'relative', margin: '0 40px 40px 40px', borderRadius: '16px', overflow: 'hidden', border: '1px solid var(--panel-border)', background: 'rgba(0,0,0,0.6)' }}>
        <ForceGraph3D
          ref={fgRef}
          graphData={graphData}
          backgroundColor="#000000"
          showNavInfo={false}
          nodeLabel="name"
          nodeAutoColorBy="group"
          nodeResolution={16}
          linkWidth={1.5}
          linkDirectionalArrowLength={3.5}
          linkDirectionalArrowRelPos={1}
          nodeThreeObject={(node: any) => {
            const sprite = new THREE.Sprite(
              new THREE.SpriteMaterial({ color: node.color })
            );
            sprite.scale.set(12, 12, 1);
            return sprite;
          }}
        />
        <div style={{ position: 'absolute', bottom: 20, left: 20, color: 'rgba(255,255,255,0.5)', fontSize: '12px' }}>
          Left-click & drag to rotate | Scroll to zoom
        </div>
      </div>
    </div>
  );
}
