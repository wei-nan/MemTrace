/**
 * GraphView3D — interactive 3D knowledge graph with expandable nodes.
 *
 * Features:
 *  - Click a node to open the side-panel editor (via onEditNode)
 *  - Double-click to fly-to + expand connected nodes
 *  - Node colour = content_type
 *  - Edge labels and directional particles
 *  - Empty-state splash when no data
 *  - Space+drag = pan mode; scroll = zoom; left = rotate
 *  - Theme-aware: auto-switches background/text between dark ↔ light
 */
import { useRef, useState, useEffect, useCallback, useMemo } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import type { ForceGraphMethods } from 'react-force-graph-3d';
import * as THREE from 'three';
// @ts-expect-error Three examples typings are not exposed by this package version.
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer';
// @ts-expect-error Three examples typings are not exposed by this package version.
import { RenderPass }     from 'three/examples/jsm/postprocessing/RenderPass';
// @ts-expect-error Three examples typings are not exposed by this package version.
import { BokehPass }      from 'three/examples/jsm/postprocessing/BokehPass';
// @ts-expect-error Three examples typings are not exposed by this package version.
import { OutputPass }     from 'three/examples/jsm/postprocessing/OutputPass';
import { useTranslation } from 'react-i18next';
import { type Node as ApiNode, type Edge as ApiEdge } from './api';

// ── Theme palette ──────────────────────────────────────────────────────────────
interface ThemePalette {
  canvasBg:        string;   // ForceGraph3D backgroundColor (hex only)
  wrapperBg:       string;   // CSS wrapper background
  textPrimary:     string;   // overlay text
  textMuted:       string;   // legend / hint text
  textFaint:       string;   // controls hint
  tooltipBg:       string;   // node/edge tooltip background
  tooltipBorder:   string;   // tooltip border
  tooltipText:     string;   // tooltip text
  badgeBg:         string;   // stats badge background
  badgeBorder:     string;   // stats badge border
  legendDivider:   string;   // legend separator line
  labelStroke:     string;   // sprite text outline colour
  labelColor:      string;   // sprite text fill
  labelSelectedColor: string;
  emptyTextPrimary: string;
  emptyTextSecondary: string;
}

const DARK_PALETTE: ThemePalette = {
  canvasBg:        '#0d0f1a',
  wrapperBg:       '#0d0f1a',
  textPrimary:     'rgba(255,255,255,0.5)',
  textMuted:       'rgba(255,255,255,0.4)',
  textFaint:       'rgba(255,255,255,0.22)',
  tooltipBg:       'rgba(13,15,26,0.92)',
  tooltipBorder:   'rgba(255,255,255,0.12)',
  tooltipText:     '#e2e8f0',
  badgeBg:         'rgba(13,15,26,0.8)',
  badgeBorder:     'rgba(255,255,255,0.08)',
  legendDivider:   'rgba(255,255,255,0.08)',
  labelStroke:     '#0d0f1a',
  labelColor:      'rgba(255,255,255,0.75)',
  labelSelectedColor: '#ffffff',
  emptyTextPrimary:   'rgba(255,255,255,0.5)',
  emptyTextSecondary: 'rgba(255,255,255,0.35)',
};

const LIGHT_PALETTE: ThemePalette = {
  canvasBg:        '#f0f2f8',
  wrapperBg:       '#f0f2f8',
  textPrimary:     'rgba(0,0,0,0.55)',
  textMuted:       'rgba(0,0,0,0.45)',
  textFaint:       'rgba(0,0,0,0.25)',
  tooltipBg:       'rgba(255,255,255,0.96)',
  tooltipBorder:   'rgba(0,0,0,0.10)',
  tooltipText:     '#1e293b',
  badgeBg:         'rgba(255,255,255,0.85)',
  badgeBorder:     'rgba(0,0,0,0.08)',
  legendDivider:   'rgba(0,0,0,0.08)',
  labelStroke:     '#f0f2f8',
  labelColor:      'rgba(30,30,60,0.85)',
  labelSelectedColor: '#111827',
  emptyTextPrimary:   'rgba(0,0,0,0.5)',
  emptyTextSecondary: 'rgba(0,0,0,0.3)',
};

/** Read current theme from HTML attribute. */
function useThemePalette(): ThemePalette {
  const [palette, setPalette] = useState<ThemePalette>(() =>
    document.documentElement.getAttribute('data-theme') === 'light' ? LIGHT_PALETTE : DARK_PALETTE,
  );

  useEffect(() => {
    const observer = new MutationObserver(() => {
      const theme = document.documentElement.getAttribute('data-theme');
      setPalette(theme === 'light' ? LIGHT_PALETTE : DARK_PALETTE);
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    return () => observer.disconnect();
  }, []);

  return palette;
}

// ── Node colours ───────────────────────────────────────────────────────────────
const NODE_BASE: Record<string, [number, number, number]> = {
  factual:    [120, 122, 195],   // muted indigo   — sphere
  procedural: [85,  172, 128],   // muted teal-green — sphere
  preference: [192, 158,  88],   // muted gold     — torus
  context:    [128, 145, 165],   // muted slate    — octahedron
  inquiry:    [152, 165, 182],   // muted cool-gray — cone
  document:   [88,  168, 208],   // muted sky blue — box
};
const FALLBACK_RGB: [number, number, number] = [120, 122, 195];

// ── i18n labels ────────────────────────────────────────────────────────────────
const NODE_LABELS_ZH: Record<string, string> = {
  factual:    '事實',
  procedural: '程序',
  preference: '偏好',
  context:    '情境',
  inquiry:    '詢問',
  document:   '文件',
};

/** Shape symbol for each content_type (used in legend) */
const NODE_SHAPE_SYMBOL: Record<string, string> = {
  factual:    '●',
  procedural: '⬡',
  preference: '◎',
  context:    '◆',
  inquiry:    '▲',
  document:   '■',
};

// ── Node geometry factory ──────────────────────────────────────────────────────
function getNodeGeometry(ctype: string, r: number): THREE.BufferGeometry {
  switch (ctype) {
    case 'preference':
      // Torus — cyclic / personal loop
      return new THREE.TorusGeometry(r * 0.72, r * 0.28, 12, 28);
    case 'context':
      // Octahedron — structured, multi-faceted
      return new THREE.OctahedronGeometry(r * 1.15, 0);
    case 'inquiry':
      // Cone — pointing / questioning
      return new THREE.ConeGeometry(r * 0.82, r * 1.8, 14);
    case 'document':
      // Box — file / solid container
      return new THREE.BoxGeometry(r * 1.5, r * 1.5, r * 1.5);
    case 'factual':
    default:
      return new THREE.SphereGeometry(r, 22, 22);
  }
}

const EDGE_COLORS: Record<string, string> = {
  depends_on:  '#818cf8',
  extends:     '#4ade80',
  related_to:  '#64748b',
  contradicts: '#f87171',
  answered_by: '#a78bfa',
  similar_to:  '#94a3b8',
  queried_via_mcp: '#2dd4bf',
};

const RELATION_LABELS_ZH: Record<string, string> = {
  depends_on:  '依賴',
  extends:     '延伸',
  related_to:  '關聯',
  contradicts: '矛盾',
  answered_by: '答覆於',
  similar_to:  '相似於',
  queried_via_mcp: '經由 MCP 查詢',
};

/** Return a CSS hex string for an RGB triple. */
function nodeColor(rgb: [number, number, number]): string {
  const r = Math.round(rgb[0]);
  const g = Math.round(rgb[1]);
  const b = Math.round(rgb[2]);
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
}

/** Create a sprite label for a node. */
function makeNodeSprite(text: string, fillColor: string, strokeColor: string): THREE.Sprite {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d')!;
  const fontSize = 48;
  canvas.width = 512;
  canvas.height = 80;

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.font = `bold ${fontSize}px "Inter", "Noto Sans TC", system-ui, sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  // Draw outlined text for readability against any background
  ctx.strokeStyle = strokeColor;
  ctx.lineWidth = 6;
  ctx.strokeText(text, canvas.width / 2, canvas.height / 2, canvas.width - 16);
  ctx.fillStyle = fillColor;
  ctx.fillText(text, canvas.width / 2, canvas.height / 2, canvas.width - 16);

  const texture = new THREE.CanvasTexture(canvas);
  texture.minFilter = THREE.LinearFilter;
  const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true, depthWrite: false });
  const sprite = new THREE.Sprite(spriteMat);
  sprite.scale.set(28, 4.5, 1);
  return sprite;
}

const LABEL_VISIBLE_DISTANCE = 250; // Camera distance threshold to hide labels

// ── Component ──────────────────────────────────────────────────────────────────

interface Props {
  apiNodes: ApiNode[];
  apiEdges: ApiEdge[];
  onEditNode?: (node: ApiNode) => void;
  healthMode?: boolean;
  healthScores?: Record<string, { score: number; label: string }>;
  isPreview?: boolean;
  dofEnabled?: boolean;
  onNodeDoubleClick?: (nodeId: string) => void;
  mode?: '2d' | '3d' | 'table' | 'explore';
}

const HEALTH_COLORS: Record<string, string> = {
  healthy: '#22c55e',
  warning: '#eab308',
  critical: '#ef4444',
};

export default function GraphView3D({ 
  apiNodes, apiEdges, onEditNode, healthMode = false, healthScores = {}, 
  isPreview = false, dofEnabled = false, onNodeDoubleClick
}: Props) {
  const fgRef      = useRef<ForceGraphMethods>(null!);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const palette    = useThemePalette();
  const { i18n }   = useTranslation();
  const zh         = i18n.language === 'zh-TW';

  // ── Post-processing (DOF) ────────────────────────────────────────────────
  const composerRef  = useRef<EffectComposer | null>(null);
  const bokehPassRef = useRef<BokehPass | null>(null);

  useEffect(() => {
    // Wait for ForceGraph3D renderer to be ready
    const timer = setTimeout(() => {
      const fg = fgRef.current;
      if (!fg) return;

      const renderer = (fg as any).renderer() as THREE.WebGLRenderer;
      const scene    = (fg as any).scene()    as THREE.Scene;
      const camera   = (fg as any).camera()   as THREE.Camera;
      if (!renderer || !scene || !camera) return;

      const composer = new EffectComposer(renderer);
      composer.addPass(new RenderPass(scene, camera));

      const bokeh = new BokehPass(scene, camera, {
        focus:    500,
        aperture: 0.00008,
        maxblur:  0.004,
      });
      composer.addPass(bokeh);
      composer.addPass(new OutputPass());

      composerRef.current  = composer;
      bokehPassRef.current = bokeh;
    }, 500);

    return () => clearTimeout(timer);
  }, []);

  // ── Measure container (ForceGraph3D needs explicit px dimensions) ──────────
  const [dims, setDims] = useState({ width: 800, height: 600 });

  useEffect(() => {
    const el = wrapperRef.current;
    if (!el) return;
    const measure = () => {
      const { width, height } = el.getBoundingClientRect();
      if (width > 0 && height > 0) setDims({ width, height });
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // ── Expanded node tracking ───────────────────────────────────────────────
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // ── Label visibility tracking ────────────────────────────────────────────
  const labelGroupsRef = useRef<Map<string, THREE.Sprite>>(new Map());

  // ── Node body material refs for imperative opacity updates ───────────────
  // Stored here so hover changes don't trigger full node re-render
  const nodeBodyMatsRef = useRef<Map<string, THREE.MeshPhongMaterial>>(new Map());

  // ── Particle-arrival pulse halo refs ─────────────────────────────────────
  const nodeHaloMatsRef  = useRef<Map<string, THREE.SpriteMaterial>>(new Map());
  const nodeHaloMeshRef  = useRef<Map<string, THREE.Sprite>>(new Map());
  const activePulsesRef  = useRef<Map<string, number>>(new Map()); // nodeId → startTime (ms)

  // ── T22: Pending-review pulse ring refs ─────────────────────────────────
  const pendingRingMatsRef = useRef<Map<string, THREE.MeshBasicMaterial>>(new Map());

  // ── Convert API data → graph format ──────────────────────────────────────
  const graphData = useMemo(() => {
    const visibleNodeIds = new Set(apiNodes.map(n => n.id));

    const nodes = apiNodes.map(n => ({
      id:    n.id,
      name:  n.title,
      ctype: n.content_type,
      _api:  n,
    }));

    const links = apiEdges
      .filter(e => visibleNodeIds.has(e.from_id) && visibleNodeIds.has(e.to_id))
      .map(e => ({
        source:   e.from_id,
        target:   e.to_id,
        relation: e.relation,
        color:    EDGE_COLORS[e.relation] ?? '#64748b',
        weight:   e.weight ?? 1,
        status:   e.status ?? 'active',
        co_access_count: e.co_access_count,
        last_co_accessed: e.last_co_accessed,
      }));

    return { nodes: nodes as any[], links: links as any[] };
  }, [apiNodes, apiEdges, zh]);

  // ── Global focus API for cross-component navigation (e.g. AI chat source nodes) ──
  useEffect(() => {
    (window as any).mt_focus_node = (nodeId: string) => {
      const node = graphData.nodes.find((n: any) => n.id === nodeId);
      if (!node) return;
      setSelectedNodeId(nodeId);
      const dist = 80;
      const mag = Math.hypot((node as any).x ?? 1, (node as any).y ?? 1, (node as any).z ?? 1);
      const r = 1 + dist / mag;
      fgRef.current?.cameraPosition(
        { x: ((node as any).x ?? 0) * r, y: ((node as any).y ?? 0) * r, z: ((node as any).z ?? 0) * r },
        node,
        1200,
      );
    };
    return () => { delete (window as any).mt_focus_node; };
  }, [graphData.nodes]);

  // Cleanup label & material refs on data change to prevent memory leaks
  useEffect(() => {
    labelGroupsRef.current.clear();
    nodeBodyMatsRef.current.clear();
    nodeHaloMatsRef.current.clear();
    nodeHaloMeshRef.current.clear();
    activePulsesRef.current.clear();
    pendingRingMatsRef.current.clear(); // T22: clear pending ring refs
  }, [graphData]);

  // ── Particle-arrival pulse scheduler ────────────────────────────────────
  useEffect(() => {
    if (isPreview) return;
    const base = apiNodes.length > 300 ? 0.002 : 0.004;

    // Collect the highest-weight incoming edge per target node
    const targetWeights = new Map<string, number>();
    for (const link of graphData.links) {
      if (link.status === 'faded') continue;
      const rawTarget = link.target;
      const targetId = typeof rawTarget === 'object' ? (rawTarget as any).id : rawTarget;
      if (!targetId) continue;
      const w = Math.max(0.1, Math.min(1.0, link.weight ?? 1));
      if ((targetWeights.get(targetId) ?? 0) < w) targetWeights.set(targetId, w);
    }

    let cancelled = false;
    const intervals: ReturnType<typeof setInterval>[] = [];

    targetWeights.forEach((w, targetId) => {
      const speed      = base * (0.25 + w * 0.75);
      const travelMs   = Math.round((1 / speed) / 60 * 1000);  // exact particle travel time
      const intervalMs = Math.min(travelMs, 2800);              // cap at 2.8 s so effect stays visible
      const startDelay = Math.random() * intervalMs;            // stagger initial burst

      setTimeout(() => {
        if (cancelled) return;
        activePulsesRef.current.set(targetId, Date.now());
        const id = setInterval(() => {
          activePulsesRef.current.set(targetId, Date.now());
        }, intervalMs);
        intervals.push(id);
      }, startDelay);
    });

    return () => {
      cancelled = true;
      intervals.forEach(clearInterval);
      activePulsesRef.current.clear();
    };
  }, [graphData, isPreview, apiNodes.length]);

  // ── Space key → pan mode ──────────────────────────────────────────────────
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

  useEffect(() => {
    const c = fgRef.current?.controls() as any;
    if (c?.mouseButtons) {
      c.mouseButtons.LEFT  = isSpacePressed ? THREE.MOUSE.PAN : THREE.MOUSE.ROTATE;
      c.mouseButtons.RIGHT = THREE.MOUSE.ROTATE;
    }
  }, [isSpacePressed]);

  // ── Click → open editor + highlight ────────────────────────────────────
  const [hoveredNode, setHoveredNode] = useState<any>(null);
  const lastClickTime = useRef<number>(0);

  const handleNodeClick = useCallback((node: any) => {
    if (isPreview) return;
    
    const now = Date.now();
    if (now - lastClickTime.current < 300) {
      // Double click navigation
      if (onNodeDoubleClick) onNodeDoubleClick(node.id);
      lastClickTime.current = 0;
      return;
    }
    lastClickTime.current = now;

    if (node._api && onEditNode) onEditNode(node._api);
    setSelectedNodeId(node.id);


    // Fly to node
    const dist = 80;
    const mag  = Math.hypot(node.x ?? 1, node.y ?? 1, node.z ?? 1);
    const r    = 1 + dist / mag;
    fgRef.current?.cameraPosition(
      { x: (node.x ?? 0) * r, y: (node.y ?? 0) * r, z: (node.z ?? 0) * r },
      node,
      1200,
    );

    // Update focal length after fly-to
    setTimeout(() => {
      const cam = fgRef.current?.camera();
      if (cam && dofEnabled && bokehPassRef.current) {
        (bokehPassRef.current as any).uniforms['focus'].value = cam.position.length();
      }
    }, 1250);
  }, [onEditNode, dofEnabled]);

  // ── Imperative node opacity on hover ────────────────────────────────────
  useEffect(() => {
    nodeBodyMatsRef.current.forEach((mat, nodeId) => {
      if (!hoveredNode) {
        mat.opacity = 0.35;             // default: semi-transparent
      } else if (hoveredNode.id === nodeId) {
        mat.opacity = 0.95;             // hovered: fully clear
      } else {
        mat.opacity = 0.15;             // others: fade further back
      }
      mat.needsUpdate = true;
    });
  }, [hoveredNode]);

  // ── Hover link material (the only reliable way to change line appearance) ─
  // THREE.Color only reads 6-digit hex; alpha must go through material.opacity.
  // linkMaterial reference-change triggers three-forcegraph to re-apply to all links.
  const getLinkMaterial = useCallback((link: any): THREE.Material => {
    const baseColor = new THREE.Color(link.color ?? '#64748b');
    const faded = link.status === 'faded';

    if (!hoveredNode) {
      // Idle: dim lines always visible
      return new THREE.MeshBasicMaterial({
        color: baseColor,
        transparent: true,
        opacity: faded ? 0.04 : 0.15,
        depthWrite: false,
      });
    }

    const src = typeof link.source === 'object' ? (link.source as any).id : link.source;
    const tgt = typeof link.target === 'object' ? (link.target as any).id : link.target;
    const connected = src === hoveredNode.id || tgt === hoveredNode.id;

    return new THREE.MeshBasicMaterial({
      color: connected ? baseColor : new THREE.Color('#334155'),
      transparent: true,
      opacity: connected ? (faded ? 0.4 : 0.88) : 0.04,
      depthWrite: false,
    });
  }, [hoveredNode]);

  const getLinkParticles = useCallback((link: any): number => {
    if (link.status === 'faded') return 0;
    if (!hoveredNode) {
      if (apiNodes.length > 300) return 1;
      if (apiNodes.length > 100) return 1;
      return 2;
    }
    const src = typeof link.source === 'object' ? (link.source as any).id : link.source;
    const tgt = typeof link.target === 'object' ? (link.target as any).id : link.target;
    const connected = src === hoveredNode.id || tgt === hoveredNode.id;
    return connected ? 3 : 0;
  }, [hoveredNode, apiNodes.length]);

  const handleCameraPositionChange = useCallback(() => {
    const cam = fgRef.current?.camera();
    if (!cam) return;

    graphData.nodes.forEach((node: any) => {
      const label = labelGroupsRef.current.get(node.id);
      if (!label) return;
      const dist = cam.position.distanceTo(
        new THREE.Vector3(node.x ?? 0, node.y ?? 0, node.z ?? 0)
      );
      label.visible = dist < LABEL_VISIBLE_DISTANCE;
    });

    // Update DOF focal length
    if (dofEnabled && bokehPassRef.current) {
      const camPos = cam.position;
      (bokehPassRef.current as any).uniforms['focus'].value = camPos.length();
    }
  }, [graphData.nodes, dofEnabled]);

  // ── Custom node rendering (theme-aware) ──────────────────────────────────
  const nodeThreeObject = useCallback((node: any) => {
    const rgb = NODE_BASE[node.ctype] ?? FALLBACK_RGB;
    let color = isPreview ? '#94a3b8' : nodeColor(rgb);
    
    if (!isPreview && healthMode && healthScores[node.id]) {
      color = HEALTH_COLORS[healthScores[node.id].label] || color;
    }

    const n = node._api;
    const isSelected = !isPreview && node.id === selectedNodeId;
    const isPending = n?.status === 'pending_review';
    const isProtected = n?.is_protected;
    const hasSource = !!n?.source_document_id;

    const group = new THREE.Group();

    // ── Main body — shape by content_type ─────────────────────────────────
    const r = isSelected ? 1.25 : 1;
    const geo = getNodeGeometry(node.ctype, r);
    const mat = new THREE.MeshPhongMaterial({
      color,
      transparent: true,
      opacity: isPending ? 0.25 : 0.35,   // default: semi-transparent; hover updates this imperatively
      shininess: 40,
      specular: new THREE.Color(0x555555),
    });
    // Store material ref for imperative hover opacity updates
    nodeBodyMatsRef.current.set(node.id, mat);

    // Draft/pending nodes: wireframe overlay
    if (isPending) {
      const wireMat = new THREE.MeshBasicMaterial({
        color,
        wireframe: true,
        transparent: true,
        opacity: 0.25,
      });
      group.add(new THREE.Mesh(geo, wireMat));
    }
    const body = new THREE.Mesh(geo, mat);
    group.add(body);

    // ── Sci-fi glow: 3-layer additive-blended spheres ─────────────────────
    // Outer layers use sphere regardless of body shape for smooth falloff
    const glowLayers: { scale: number; opacity: number }[] = isSelected
      ? [{ scale: 3.5, opacity: 0.05 }, { scale: 2.4, opacity: 0.10 }, { scale: 1.6, opacity: 0.18 }]
      : [{ scale: 3.2, opacity: 0.03 }, { scale: 2.2, opacity: 0.07 }, { scale: 1.5, opacity: 0.13 }];

    for (const { scale, opacity } of glowLayers) {
      const glowGeo = new THREE.SphereGeometry(r * scale, 14, 14);
      const glowMat = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      });
      group.add(new THREE.Mesh(glowGeo, glowMat));
    }

    // T21: Audit badge ring — amber pulsing ring for pending_review nodes
    if (isPending) {
      const auditRingGeo = new THREE.RingGeometry(r * 1.8, r * 2.2, 32);
      const auditRingMat = new THREE.MeshBasicMaterial({
        color: '#fbbf24', // amber-400
        transparent: true,
        opacity: 0.85,
        side: THREE.DoubleSide,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      });
      pendingRingMatsRef.current.set(node.id, auditRingMat);
      group.add(new THREE.Mesh(auditRingGeo, auditRingMat));
    }

    // Selected node: bright accent ring (r-relative)
    if (isSelected) {
      const ringGeo = new THREE.RingGeometry(r * 1.6, r * 2.0, 32);
      const ringMat = new THREE.MeshBasicMaterial({
        color: '#818cf8',
        transparent: true,
        opacity: 0.7,
        side: THREE.DoubleSide,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      });
      group.add(new THREE.Mesh(ringGeo, ringMat));
    }

    // Lock icon for protected nodes (r-relative)
    if (isProtected) {
      const lockGeo = new THREE.PlaneGeometry(r * 0.75, r * 0.75);
      const lockTex = new THREE.TextureLoader().load('https://cdn-icons-png.flaticon.com/512/61/61457.png');
      const lockMat = new THREE.MeshBasicMaterial({ map: lockTex, transparent: true, color: '#f87171' });
      const lock = new THREE.Mesh(lockGeo, lockMat);
      lock.position.set(r * 0.9, r * 0.9, 0);
      group.add(lock);
    }

    // Document icon for nodes with source (r-relative)
    if (hasSource) {
      const docGeo = new THREE.PlaneGeometry(r * 0.75, r * 0.75);
      const docTex = new THREE.TextureLoader().load('https://cdn-icons-png.flaticon.com/512/2991/2991108.png');
      const docMat = new THREE.MeshBasicMaterial({ map: docTex, transparent: true, color: '#60a5fa' });
      const doc = new THREE.Mesh(docGeo, docMat);
      doc.position.set(-r * 0.9, r * 0.9, 0);
      group.add(doc);
    }

    // Particle-arrival pulse halo — billboard sprite so it's visible from any angle
    const haloCanvas = document.createElement('canvas');
    haloCanvas.width = 128; haloCanvas.height = 128;
    const hCtx = haloCanvas.getContext('2d')!;
    const sz = 128, cx2 = sz / 2;
    // Ring gradient: transparent centre → bright ring peak → transparent edge
    const grad = hCtx.createRadialGradient(cx2, cx2, sz * 0.25, cx2, cx2, sz * 0.5);
    grad.addColorStop(0,    'rgba(255,255,255,0)');
    grad.addColorStop(0.55, 'rgba(255,255,255,0.95)');
    grad.addColorStop(0.75, 'rgba(255,255,255,0.4)');
    grad.addColorStop(1.0,  'rgba(255,255,255,0)');
    hCtx.fillStyle = grad;
    hCtx.fillRect(0, 0, sz, sz);
    const haloTex = new THREE.CanvasTexture(haloCanvas);
    const haloMat = new THREE.SpriteMaterial({
      map: haloTex,
      transparent: true,
      opacity: 0,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      depthTest: false,
      color: new THREE.Color(color).lerp(new THREE.Color('#ffffff'), 0.4),
    });
    const haloSprite = new THREE.Sprite(haloMat);
    // r*8 → sprite diameter 8, ring visible at ~6r (outside outermost glow at r*3.2)
    haloSprite.scale.setScalar(r * 8);
    haloSprite.userData.haloBase = r * 8;
    nodeHaloMatsRef.current.set(node.id, haloMat);
    nodeHaloMeshRef.current.set(node.id, haloSprite);
    group.add(haloSprite);

    // Label sprite (theme-aware stroke + fill, r-relative)
    const label = makeNodeSprite(
      (node.name || '').slice(0, 20),
      isSelected ? palette.labelSelectedColor : palette.labelColor,
      palette.labelStroke,
    );
    label.position.set(0, -(r + 1.4), 0);
    label.visible = true; // Initial visibility
    group.add(label);

    // Track reference for distance-based hiding
    labelGroupsRef.current.set(node.id, label);

    return group;
  }, [selectedNodeId, palette]);

  // ── Edge count per node (for badge) ──────────────────────────────────────
  const edgeCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const e of apiEdges) {
      counts[e.from_id] = (counts[e.from_id] ?? 0) + 1;
      counts[e.to_id] = (counts[e.to_id] ?? 0) + 1;
    }
    return counts;
  }, [apiEdges]);

  // ── Empty state ──────────────────────────────────────────────────────────
  const isEmpty = apiNodes.length === 0;

  return (
    <div style={{ width: '100%', flex: 1, minHeight: 0, padding: '0 40px 40px', boxSizing: 'border-box', display: 'flex', flexDirection: 'column' }}>
      <div
        ref={wrapperRef}
        style={{
          width: '100%', flex: 1, minHeight: 0,
          borderRadius: 16, overflow: 'hidden',
          border: '1px solid var(--border-default)',
          background: palette.wrapperBg,
          position: 'relative',
          transition: 'background 0.3s',
        }}
      >
        {isEmpty ? (
          /* ── Empty state splash (theme-aware) ──────────────────────────── */
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
            color: palette.emptyTextSecondary,
          }}>
            <div style={{
              width: 80, height: 80, borderRadius: '50%',
              background: 'rgba(99,102,241,0.12)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              marginBottom: 20,
            }}>
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <circle cx="12" cy="12" r="3" />
                <circle cx="5" cy="6" r="2" />
                <circle cx="19" cy="6" r="2" />
                <circle cx="5" cy="18" r="2" />
                <circle cx="19" cy="18" r="2" />
                <line x1="9.5" y1="10.5" x2="6.5" y2="7.5" />
                <line x1="14.5" y1="10.5" x2="17.5" y2="7.5" />
                <line x1="9.5" y1="13.5" x2="6.5" y2="16.5" />
                <line x1="14.5" y1="13.5" x2="17.5" y2="16.5" />
              </svg>
            </div>
            <p style={{ fontSize: 15, margin: '0 0 6px', color: palette.emptyTextPrimary }}>
              {zh ? '目前沒有記憶節點' : 'No memory nodes yet'}
            </p>
            <p style={{ fontSize: 12, opacity: 0.6 }}>
              {zh ? '點擊「新增節點」開始建立你的知識圖譜' : 'Click "New Node" to start building your knowledge graph'}
            </p>
          </div>
        ) : (
          <ForceGraph3D
            ref={fgRef}
            width={dims.width}
            height={dims.height}
            graphData={graphData}
            backgroundColor={palette.canvasBg}
            showNavInfo={false}
            nodeLabel={(node: any) => {
              if (isPreview) return `<div style="background:${palette.tooltipBg};border:1px solid ${palette.tooltipBorder};border-radius:8px;padding:8px 12px;font-size:12px;color:${palette.tooltipText}">${zh ? '受保護的節點' : 'Protected Node'}</div>`;
              const n = node._api;
              if (!n) return node.name;
              const edges = edgeCounts[n.id] ?? 0;
              const title = n.title;


              return `<div style="background:${palette.tooltipBg};border:1px solid ${palette.tooltipBorder};border-radius:8px;padding:8px 12px;font-size:12px;line-height:1.5;max-width:260px;color:${palette.tooltipText}">
                <div style="font-weight:600;font-size:13px;margin-bottom:4px">${title}</div>
                <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:4px">
                  <span style="background:rgba(99,102,241,0.25);padding:1px 6px;border-radius:4px;font-size:10px">${zh ? (NODE_LABELS_ZH[n.content_type] || n.content_type) : n.content_type}</span>
                  <span style="opacity:0.5;font-size:10px">${edges} ${zh ? '關聯' : 'edges'}</span>
                </div>
                

                ${!n.body ? `<div style="color:#ef4444;font-size:10px;font-weight:600;margin-top:4px">⚠️ ${zh ? '內容為空' : 'Empty Body'}</div>` : ''}
                <div style="border-top:1px solid ${palette.legendDivider};margin-top:8px;padding-top:6px;font-size:9px;opacity:0.4;text-align:center">
                  ${zh ? '雙擊以鄰域探索' : 'Double-click to explore neighborhood'}
                </div>
              </div>`;
            }}
            nodeThreeObject={nodeThreeObject}
            nodeThreeObjectExtend={false}
            linkWidth={0.8}
            linkMaterial={getLinkMaterial}
            linkColor={(link: any) => link.color ?? '#64748b'}
            linkDirectionalArrowLength={0}
            linkDirectionalArrowRelPos={1}
            linkLabel={(link: any) => {
              const label = zh ? (RELATION_LABELS_ZH[link.relation] || link.relation) : link.relation.replace('_', ' ');
              const color = EDGE_COLORS[link.relation] || '#64748b';
              const isFaded = link.status === 'faded';
              
              let extra = '';
              if (isFaded && link.last_co_accessed) {
                const days = Math.floor((Date.now() - new Date(link.last_co_accessed).getTime()) / (1000 * 3600 * 24));
                extra = `<div style="font-size:10px;color:#ef4444;margin-top:4px">${zh ? `已衰退 (上次走訪：${days} 天前)` : `Faded (${days} days since last access)`}</div>`;
              }

              return `<div style="background:${palette.tooltipBg};border:1px solid ${isFaded ? '#94a3b8' : color}44;border-radius:6px;padding:6px 12px;font-size:11px;color:${isFaded ? '#94a3b8' : color}">
                <div style="font-weight:700">${label}</div>
                ${extra}
              </div>`;
            }}
            onNodeClick={handleNodeClick}
            onNodeHover={setHoveredNode}
            // @ts-expect-error onCameraPositionChange exists at runtime but is missing in upstream types.
            onCameraPositionChange={handleCameraPositionChange}
            onBackgroundRightClick={() => {
              if (hoveredNode) {
                const c = fgRef.current?.controls() as any;
                c?.target?.set(hoveredNode.x ?? 0, hoveredNode.y ?? 0, hoveredNode.z ?? 0);
              }
            }}
            onNodeRightClick={(node) => {
              const c = fgRef.current?.controls() as any;
              c?.target?.set(node.x ?? 0, node.y ?? 0, node.z ?? 0);
            }}
            d3AlphaDecay={0.02}
            d3VelocityDecay={0.3}
            warmupTicks={80}
            cooldownTime={3000}
            linkCurvature={0.2}
            linkDirectionalParticles={getLinkParticles}
            linkDirectionalParticleSpeed={(link: any) => {
              const base = apiNodes.length > 300 ? 0.002 : 0.004;
              const w = Math.max(0.1, Math.min(1.0, link.weight ?? 1));
              return base * (0.25 + w * 0.75);
            }}
            linkDirectionalParticleWidth={0.5}
            linkDirectionalParticleColor={(link: any) => {
              // Use source node's colour so particles feel like they "flow from" origin
              const srcNode = typeof link.source === 'object' ? link.source : null;
              if (srcNode?.ctype) {
                const rgb = NODE_BASE[srcNode.ctype] ?? FALLBACK_RGB;
                return nodeColor(rgb);
              }
              return link.color ?? '#64748b';
            }}
            onRenderFramePost={() => {
              if (dofEnabled && composerRef.current) {
                composerRef.current.render();
              }
              // Drive particle-arrival glow pulses
              const now = Date.now();
              activePulsesRef.current.forEach((startTime, nodeId) => {
                const mat  = nodeHaloMatsRef.current.get(nodeId);
                const mesh = nodeHaloMeshRef.current.get(nodeId);
                if (!mat || !mesh) { activePulsesRef.current.delete(nodeId); return; }
                const t = Math.min(1, (now - startTime) / 900);
                if (t >= 1) {
                  mat.opacity = 0;
                  mesh.scale.setScalar(mesh.userData.haloBase ?? 1);
                  activePulsesRef.current.delete(nodeId);
                } else {
                  const base = mesh.userData.haloBase ?? 1;
                  mesh.scale.setScalar(base * (1 + t * 2.0)); // expand 1× → 3× (r*8 → r*24)
                  mat.opacity = 0.85 * (1 - t) * (1 - t);    // quadratic fade: 0.85 → 0
                }
              });
              // T22: Drive pending-review ring pulse (sine oscillation)
              pendingRingMatsRef.current.forEach((mat) => {
                mat.opacity = 0.4 + 0.5 * Math.abs(Math.sin(now / 600));
              });
            }}
          />
        )}

        {/* Colour legend (theme-aware) */}
        <div style={{
          position: 'absolute', top: 16, left: 16,
          display: 'flex', flexDirection: 'column', gap: 5,
          pointerEvents: 'none',
        }}>
          {Object.entries(NODE_BASE).map(([type, rgb]) => (
            <div key={type} style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
              <span style={{
                fontSize: 11,
                color: nodeColor(rgb),
                flexShrink: 0,
                lineHeight: 1,
                width: 12,
                textAlign: 'center',
              }}>
                {NODE_SHAPE_SYMBOL[type] ?? '●'}
              </span>
              <span style={{ fontSize: 11, color: palette.textMuted }}>{zh ? (NODE_LABELS_ZH[type] || type) : type}</span>
            </div>
          ))}

          {/* Edge legend */}
          <div style={{ marginTop: 8, borderTop: `1px solid ${palette.legendDivider}`, paddingTop: 8 }}>
            {Object.entries(EDGE_COLORS).map(([rel, color]) => (
              <div key={rel} style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 3 }}>
                <div style={{
                  width: 14, height: 2, borderRadius: 1,
                  background: color, flexShrink: 0,
                }} />
                <span style={{ fontSize: 10, color: palette.textMuted }}>
                  {zh ? (RELATION_LABELS_ZH[rel] || rel) : rel.replace('_', ' ')}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Stats badge (theme-aware) */}
        {!isEmpty && (
          <div style={{
            position: 'absolute', top: 16, right: 16,
            background: palette.badgeBg, border: `1px solid ${palette.badgeBorder}`,
            borderRadius: 8, padding: '6px 12px',
            fontSize: 11, color: palette.textMuted,
            pointerEvents: 'none',
            display: 'flex', gap: 12,
          }}>
            <span>{apiNodes.length} {zh ? '節點' : 'nodes'}</span>
            <span>{apiEdges.length} {zh ? '關聯' : 'edges'}</span>
          </div>
        )}

        {/* Controls hint (theme-aware) */}
        <div style={{
          position: 'absolute', bottom: 14, left: 16,
          color: palette.textFaint, fontSize: 11,
          pointerEvents: 'none', lineHeight: 1.7,
        }}>
          {zh ? '左鍵旋轉 · Space+拖曳平移 · 滾輪縮放 · 點擊開啟節點' : 'Left-click rotate · Space+drag pan · Scroll zoom · Click to open node'}
        </div>
      </div>
    </div>
  );
}
