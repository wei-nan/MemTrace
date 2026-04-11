import { useRef, useState, useEffect, useCallback } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import type { ForceGraphMethods } from 'react-force-graph-3d';
import { useTranslation } from 'react-i18next';
import { RefreshCw, Save } from 'lucide-react';
import * as THREE from 'three';
import { nodes as nodesApi, edges as edgesApi, type Node as ApiNode } from './api';

interface Props {
  wsId?: string;
  reloadKey?: number;
  onEditNode?: (node: ApiNode) => void;
}

const RELATION_COLORS: Record<string, string> = {
  depends_on:  '#3b82f6',
  extends:     '#a78bfa',
  related_to:  '#94a3b8',
  contradicts: '#f87171',
};

export default function GraphView3D({ wsId, reloadKey, onEditNode }: Props) {
  const { t, i18n } = useTranslation();
  const fgRef = useRef<ForceGraphMethods>(null!);
  
  const [data, setData] = useState({ nodes: [] as any[], links: [] as any[] });
  const [hoveredNode, setHoveredNode] = useState<any>(null);
  const [isSpacePressed, setIsSpacePressed] = useState(false);
  const [apiNodes, setApiNodes] = useState<ApiNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

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

      const nodes = rawNodes.map(n => ({
        id: n.id,
        name: i18n.language === 'zh-TW' ? n.title_zh : n.title_en,
        val: n.trust_score * 5,
        group: n.content_type,
        color: RELATION_COLORS[n.content_type] || '#ffffff'
      }));

      const links = rawEdges.map(e => ({
        source: e.from_id,
        target: e.to_id,
        relation: e.relation,
        color: RELATION_COLORS[e.relation] || '#94a3b8'
      }));

      setData({ nodes, links });
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [wsId, i18n.language]);

  useEffect(() => { load(); }, [load, reloadKey]);

  // Handle Space key for Panning
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === 'Space') {
        // Only prevent default if we are not in an input/textarea
        const isInput = ['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement).tagName);
        if (!isInput) {
          setIsSpacePressed(true);
          e.preventDefault();
        }
      }
    };
    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.code === 'Space') {
        setIsSpacePressed(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, []);

  // Configure controls based on interaction state
  useEffect(() => {
    if (fgRef.current) {
      const controls = fgRef.current.controls() as any;
      if (controls && controls.mouseButtons) {
        // 1. Pan with Space + Left Click
        // 2. Right Click always Rotate
        controls.mouseButtons.LEFT = isSpacePressed ? THREE.MOUSE.PAN : THREE.MOUSE.ROTATE;
        controls.mouseButtons.RIGHT = THREE.MOUSE.ROTATE;
      }
    }
  }, [isSpacePressed]);

  const handleNodeClick = useCallback((node: any) => {
    const apiNode = apiNodes.find(n => n.id === node.id);
    if (apiNode && onEditNode) {
      onEditNode(apiNode);
    }
    
    // Aim at node
    const distance = 40;
    const distRatio = 1 + distance/Math.hypot(node.x, node.y, node.z);
    fgRef.current?.cameraPosition(
      { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio },
      node, // look at node
      3000  // transitions duration
    );
  }, [apiNodes, onEditNode]);

  const handleSaveGraph = () => {
    alert('3D Graph Layout State conceptually saved!');
  };

  if (!wsId) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 15 }}>
        Select a workspace to view the 3D graph.
      </div>
    );
  }

  return (
    <div style={{ height: 'calc(100vh - 40px)', width: '100%', display: 'flex', flexDirection: 'column' }}>
      <header className="page-header animate-fade-in" style={{ padding: '0 40px', marginTop: '40px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">3D {t('sidebar.graph')}</h1>
          <p className="page-subtitle">
            {loading ? 'Loading…' : error ? `Error: ${error}` : `${data.nodes.length} nodes · ${data.links.length} edges — click a node to open`}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn-secondary" onClick={load} disabled={loading}>
            <RefreshCw size={16} style={{ marginRight: 6, animation: loading ? 'spin 1s linear infinite' : 'none' }} />
            Refresh
          </button>
          <button className="btn-primary" onClick={handleSaveGraph}>
            <Save size={18} />
            Save Topology
          </button>
        </div>
      </header>

      <div style={{ flex: 1, position: 'relative', margin: '0 40px 40px 40px', borderRadius: '16px', overflow: 'hidden', border: '1px solid var(--panel-border)', background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(10px)' }}>
        <ForceGraph3D
          ref={fgRef}
          graphData={data}
          backgroundColor="rgba(0,0,0,0)"
          showNavInfo={false}
          nodeLabel="name"
          nodeRelSize={6}
          linkWidth={1}
          linkDirectionalArrowLength={3}
          linkDirectionalArrowRelPos={1}
          linkDirectionalParticles={2}
          linkDirectionalParticleSpeed={0.005}
          onNodeClick={handleNodeClick}
          onNodeHover={setHoveredNode}
          controlType="trackball"
          nodeThreeObject={(node: any) => {
            const group = new THREE.Group();
            
            // Sphere for node
            const sphere = new THREE.Mesh(
              new THREE.SphereGeometry(1, 16, 16),
              new THREE.MeshLambertMaterial({ color: node.color || '#3b82f6', transparent: true, opacity: 0.8 })
            );
            sphere.scale.set(node.val || 2, node.val || 2, node.val || 2);
            group.add(sphere);

            return group;
          }}
          onBackgroundRightClick={() => {
            // When right-clicking background, if we are hovering a node, 
            // set the rotation target to that node for "centered on mouse" feel.
            if (hoveredNode && fgRef.current) {
              const controls = fgRef.current.controls() as any;
              if (controls && controls.target) {
                controls.target.set(hoveredNode.x, hoveredNode.y, hoveredNode.z);
              }
            }
          }}
          onNodeRightClick={(node) => {
            // Similarly for direct node right-click
            if (fgRef.current) {
              const controls = fgRef.current.controls() as any;
              if (controls && controls.target) {
                controls.target.set(node.x!, node.y!, node.z!);
              }
            }
          }}
        />
        <div style={{ position: 'absolute', bottom: 20, left: 20, color: 'rgba(255,255,255,0.4)', fontSize: '11px', pointerEvents: 'none', display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <div>Left-click: Rotate | Space + Left-click: Pan | Scroll: Zoom</div>
          <div>Right-click: Rotate around node (aim at node while clicking)</div>
        </div>
      </div>
    </div>
  );
}
