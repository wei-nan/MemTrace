/**
 * GraphView3D — interactive 3D knowledge graph with expandable nodes.
 *
 * Features:
 *  - Click a node to open the side-panel editor (via onEditNode)
 *  - Double-click to fly-to + expand connected nodes
 *  - Node colour = content_type, brightness scaled by trust_score
 *  - Edge labels and directional particles
 *  - Empty-state splash when no data
 *  - Space+drag = pan mode; scroll = zoom; left = rotate
 *  - Theme-aware: auto-switches background/text between dark ↔ light
 */
import { useRef, useState, useEffect, useCallback, useMemo } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import type { ForceGraphMethods } from 'react-force-graph-3d';
import * as THREE from 'three';
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
  factual:    [99,  102, 241],   // indigo
  procedural: [34,  197,  94],   // green
  preference: [245, 158,  11],   // amber
  context:    [100, 116, 139],   // slate
};
const FALLBACK_RGB: [number, number, number] = [99, 102, 241];

// ── i18n labels ────────────────────────────────────────────────────────────────
const NODE_LABELS_ZH: Record<string, string> = {
  factual:    '事實',
  procedural: '程序',
  preference: '偏好',
  context:    '情境',
};

const EDGE_COLORS: Record<string, string> = {
  depends_on:  '#818cf8',
  extends:     '#4ade80',
  related_to:  '#64748b',
  contradicts: '#f87171',
};

const RELATION_LABELS_ZH: Record<string, string> = {
  depends_on:  '依賴',
  extends:     '延伸',
  related_to:  '關聯',
  contradicts: '矛盾',
};

/** Scale an RGB triple by `factor` (0.2–1.0) and return a CSS hex string. */
function trustColor(rgb: [number, number, number], factor: number): string {
  const f = Math.max(0.2, Math.min(1.0, factor));
  const r = Math.round(rgb[0] * f);
  const g = Math.round(rgb[1] * f);
  const b = Math.round(rgb[2] * f);
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

// ── Component ──────────────────────────────────────────────────────────────────

interface Props {
  apiNodes: ApiNode[];
  apiEdges: ApiEdge[];
  relationColors: Record<string, string>; // kept for API compat
  onEditNode?: (node: ApiNode) => void;
}

export default function GraphView3D({ apiNodes, apiEdges, onEditNode }: Props) {
  const fgRef      = useRef<ForceGraphMethods>(null!);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const palette    = useThemePalette();
  const { i18n }   = useTranslation();
  const zh         = i18n.language === 'zh-TW';

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

  // ── Convert API data → graph format ──────────────────────────────────────
  const graphData = useMemo(() => {
    const visibleNodeIds = new Set(apiNodes.map(n => n.id));

    const nodes = apiNodes.map(n => ({
      id:    n.id,
      name:  n.title_zh || n.title_en,
      ctype: n.content_type,
      trust: Math.max(0.2, Math.min(1.0, n.trust_score ?? 0.7)),
      _api:  n,
    }));

    const links = apiEdges
      .filter(e => visibleNodeIds.has(e.from_id) && visibleNodeIds.has(e.to_id))
      .map(e => ({
        source:   e.from_id,
        target:   e.to_id,
        relation: e.relation,
        color:    EDGE_COLORS[e.relation] ?? '#64748b',
      }));

    return { nodes, links };
  }, [apiNodes, apiEdges]);

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

  const handleNodeClick = useCallback((node: any) => {
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
  }, [onEditNode]);

  // ── Custom node rendering (theme-aware) ──────────────────────────────────
  const nodeThreeObject = useCallback((node: any) => {
    const rgb = NODE_BASE[node.ctype] ?? FALLBACK_RGB;
    const color = trustColor(rgb, node.trust);
    const isSelected = node.id === selectedNodeId;

    const group = new THREE.Group();

    // Main sphere
    const sphereGeo = new THREE.SphereGeometry(isSelected ? 5 : 4, 24, 24);
    const sphereMat = new THREE.MeshLambertMaterial({
      color,
      transparent: true,
      opacity: 0.9,
    });
    const sphere = new THREE.Mesh(sphereGeo, sphereMat);
    group.add(sphere);

    // Glow ring for selected node
    if (isSelected) {
      const ringGeo = new THREE.RingGeometry(6, 7.5, 32);
      const ringMat = new THREE.MeshBasicMaterial({
        color: '#818cf8',
        transparent: true,
        opacity: 0.6,
        side: THREE.DoubleSide,
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      group.add(ring);
    }

    // Label sprite (theme-aware stroke + fill)
    const label = makeNodeSprite(
      (node.name || '').slice(0, 20),
      isSelected ? palette.labelSelectedColor : palette.labelColor,
      palette.labelStroke,
    );
    label.position.set(0, isSelected ? -8 : -7, 0);
    group.add(label);

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
    <div style={{ width: '100%', height: '100%', padding: '0 40px 40px', boxSizing: 'border-box' }}>
      <div
        ref={wrapperRef}
        style={{
          width: '100%', height: '100%',
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
              const n = node._api;
              if (!n) return node.name;
              const edges = edgeCounts[n.id] ?? 0;
              const typeLabel = zh ? (NODE_LABELS_ZH[n.content_type] || n.content_type) : n.content_type;
              const title = zh ? (n.title_zh || n.title_en) : (n.title_en || n.title_zh);
              const subtitle = zh ? n.title_en : n.title_zh;
              return `<div style="background:${palette.tooltipBg};border:1px solid ${palette.tooltipBorder};border-radius:8px;padding:8px 12px;font-size:12px;line-height:1.5;max-width:260px;color:${palette.tooltipText}">
                <div style="font-weight:600;font-size:13px;margin-bottom:4px">${title}</div>
                ${subtitle ? `<div style="opacity:0.5;font-size:11px;margin-bottom:6px">${subtitle}</div>` : ''}
                <div style="display:flex;gap:6px;flex-wrap:wrap">
                  <span style="background:rgba(99,102,241,0.25);padding:1px 6px;border-radius:4px;font-size:10px">${typeLabel}</span>
                  <span style="opacity:0.5;font-size:10px">${zh ? '信任' : 'trust'}: ${(n.trust_score ?? 0).toFixed(2)}</span>
                  <span style="opacity:0.5;font-size:10px">${edges} ${zh ? '關聯' : 'edges'}</span>
                </div>
              </div>`;
            }}
            nodeThreeObject={nodeThreeObject}
            nodeThreeObjectExtend={false}
            linkWidth={1.5}
            linkColor={(link: any) => link.color}
            linkDirectionalArrowLength={5}
            linkDirectionalArrowRelPos={1}
            linkDirectionalParticles={2}
            linkDirectionalParticleSpeed={0.004}
            linkDirectionalParticleWidth={1.5}
            linkLabel={(link: any) => {
              const label = zh ? (RELATION_LABELS_ZH[link.relation] || link.relation) : link.relation.replace('_', ' ');
              const color = EDGE_COLORS[link.relation] || '#64748b';
              return `<div style="background:${palette.tooltipBg};border:1px solid ${color}44;border-radius:6px;padding:4px 10px;font-size:11px;color:${color}">${label}</div>`;
            }}
            linkOpacity={0.5}
            onNodeClick={handleNodeClick}
            onNodeHover={setHoveredNode}
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
              <div style={{
                width: 9, height: 9, borderRadius: '50%',
                background: trustColor(rgb, 1.0),
                flexShrink: 0,
              }} />
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
