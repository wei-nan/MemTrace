// graph-3d.jsx — pseudo-3D force-directed knowledge-graph viewer.
// Uses a simple Coulomb + spring simulation in 3D, then projects to 2D
// with rotation matrices. Drag = orbit, wheel = zoom.

const { useState: use3State, useEffect: use3Effect, useRef: use3Ref, useMemo: use3Memo, useCallback: use3Callback } = React;

function rgbToCss([r, g, b], factor = 1) {
  const f = Math.max(0.25, Math.min(1, factor));
  return `rgb(${Math.round(r*f)}, ${Math.round(g*f)}, ${Math.round(b*f)})`;
}

function simulate3D(nodes, edges, opts = {}) {
  const { iterations = 280, k = 28, c = 800, gravity = 0.04, damping = 0.85 } = opts;
  let seed = 1337;
  const rand = () => { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; };

  const sim = nodes.map(n => ({
    id: n.id,
    x: (rand() - 0.5) * 80,
    y: (rand() - 0.5) * 80,
    z: (rand() - 0.5) * 80,
    vx: 0, vy: 0, vz: 0,
    mass: 1 + (n.trust || 0.5),
  }));
  const idx = Object.fromEntries(sim.map((s, i) => [s.id, i]));
  const edgePairs = edges
    .map(([a, b]) => [idx[a], idx[b]])
    .filter(([a, b]) => a !== undefined && b !== undefined);

  for (let it = 0; it < iterations; it++) {
    const alpha = 1 - it / iterations;
    for (let i = 0; i < sim.length; i++) {
      for (let j = i + 1; j < sim.length; j++) {
        const a = sim[i], b = sim[j];
        let dx = a.x - b.x, dy = a.y - b.y, dz = a.z - b.z;
        let d2 = dx*dx + dy*dy + dz*dz + 0.5;
        const force = c / d2;
        const d = Math.sqrt(d2);
        const fx = (dx/d) * force, fy = (dy/d) * force, fz = (dz/d) * force;
        a.vx += fx / a.mass; a.vy += fy / a.mass; a.vz += fz / a.mass;
        b.vx -= fx / b.mass; b.vy -= fy / b.mass; b.vz -= fz / b.mass;
      }
    }
    for (const [i, j] of edgePairs) {
      const a = sim[i], b = sim[j];
      const dx = b.x - a.x, dy = b.y - a.y, dz = b.z - a.z;
      const d = Math.sqrt(dx*dx + dy*dy + dz*dz) + 0.01;
      const f = (d - k) * 0.08;
      const fx = (dx/d) * f, fy = (dy/d) * f, fz = (dz/d) * f;
      a.vx += fx / a.mass; a.vy += fy / a.mass; a.vz += fz / a.mass;
      b.vx -= fx / b.mass; b.vy -= fy / b.mass; b.vz -= fz / b.mass;
    }
    for (const s of sim) {
      s.vx -= s.x * gravity;
      s.vy -= s.y * gravity;
      s.vz -= s.z * gravity;
      s.vx *= damping; s.vy *= damping; s.vz *= damping;
      s.x += s.vx * alpha;
      s.y += s.vy * alpha;
      s.z += s.vz * alpha;
    }
  }
  return Object.fromEntries(sim.map(s => [s.id, { x: s.x, y: s.y, z: s.z }]));
}

function project(p, yaw, pitch, zoom, w, h) {
  const cy = Math.cos(yaw), sy = Math.sin(yaw);
  const cp = Math.cos(pitch), sp = Math.sin(pitch);
  let x = p.x * cy + p.z * sy;
  let z = -p.x * sy + p.z * cy;
  let y = p.y * cp - z * sp;
  z = p.y * sp + z * cp;
  const focal = 360;
  const scale = focal / (focal + z + 240) * zoom;
  const sx = x * scale + w / 2;
  const sy_ = y * scale + h / 2;
  const depth = (z + 200) / 400;
  return { x: sx, y: sy_, scale, depth: Math.max(0, Math.min(1, depth)), z };
}

function GraphCanvas3D({
  data, selected, setSelected, hovered, setHovered,
  edgeKinds, activeContentTypes, search, dof, dark
}) {
  const { NODES, EDGES, CONTENT_TYPES, RELATIONS } = data;
  const wrapRef = use3Ref(null);
  const [size, setSize] = use3State({ w: 1000, h: 700 });
  const [yaw, setYaw] = use3State(0.4);
  const [pitch, setPitch] = use3State(-0.18);
  const [zoom, setZoom] = use3State(1.4);
  const [drag, setDrag] = use3State(null);
  const [spaceDown, setSpaceDown] = use3State(false);
  const [pan, setPan] = use3State({ x: 0, y: 0 });

  use3Effect(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver(([e]) => setSize({ w: e.contentRect.width, h: e.contentRect.height }));
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  use3Effect(() => {
    const dn = (e) => { if (e.code === "Space" && !["INPUT","TEXTAREA"].includes(document.activeElement?.tagName)) { setSpaceDown(true); e.preventDefault(); } };
    const up = (e) => { if (e.code === "Space") setSpaceDown(false); };
    window.addEventListener("keydown", dn);
    window.addEventListener("keyup", up);
    return () => { window.removeEventListener("keydown", dn); window.removeEventListener("keyup", up); };
  }, []);

  const positions = use3Memo(() => simulate3D(NODES, EDGES), [NODES, EDGES]);
  const nodeById = use3Memo(() => Object.fromEntries(NODES.map(n => [n.id, n])), [NODES]);
  const ctById = use3Memo(() => Object.fromEntries(CONTENT_TYPES.map(c => [c.id, c])), [CONTENT_TYPES]);
  const relById = use3Memo(() => Object.fromEntries(RELATIONS.map(r => [r.id, r])), [RELATIONS]);

  use3Effect(() => {
    let raf;
    let last = performance.now();
    const tick = (t) => {
      const dt = (t - last) / 1000; last = t;
      if (!drag && !hovered && !selected) {
        setYaw(y => y + dt * 0.04);
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [drag, hovered, selected]);

  const onWheel = (e) => {
    e.preventDefault();
    setZoom(z => Math.max(0.5, Math.min(3.5, z * (1 - e.deltaY * 0.0015))));
  };
  const onMouseDown = (e) => {
    if (e.target.closest("[data-node]")) return;
    setDrag({ sx: e.clientX, sy: e.clientY, yaw, pitch, panX: pan.x, panY: pan.y, mode: spaceDown ? "pan" : "rotate" });
  };
  use3Effect(() => {
    if (!drag) return;
    const onMove = (e) => {
      const dx = e.clientX - drag.sx;
      const dy = e.clientY - drag.sy;
      if (drag.mode === "rotate") {
        setYaw(drag.yaw + dx * 0.008);
        setPitch(Math.max(-Math.PI/2 + 0.05, Math.min(Math.PI/2 - 0.05, drag.pitch + dy * 0.008)));
      } else {
        setPan({ x: drag.panX + dx, y: drag.panY + dy });
      }
    };
    const onUp = () => setDrag(null);
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => { window.removeEventListener("mousemove", onMove); window.removeEventListener("mouseup", onUp); };
  }, [drag]);

  const projected = use3Memo(() => {
    const out = {};
    for (const n of NODES) {
      const p = positions[n.id];
      if (!p) continue;
      const pr = project(p, yaw, pitch, zoom, size.w + pan.x * 2, size.h + pan.y * 2);
      out[n.id] = { ...pr, x: pr.x + pan.x, y: pr.y + pan.y };
    }
    return out;
  }, [NODES, positions, yaw, pitch, zoom, size, pan]);

  const matchesSearch = (n) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return n.label.toLowerCase().includes(q) || n.en.toLowerCase().includes(q);
  };

  const visibleNodes = use3Memo(() =>
    NODES.filter(n => activeContentTypes.has(n.ct) && matchesSearch(n))
         .sort((a, b) => (projected[b.id]?.depth || 0) - (projected[a.id]?.depth || 0)),
    [NODES, activeContentTypes, search, projected]
  );
  const visibleIds = new Set(visibleNodes.map(n => n.id));

  const focusId = hovered || selected;
  const neighborIds = use3Memo(() => {
    if (!focusId) return null;
    const s = new Set([focusId]);
    for (const [a, b] of EDGES) {
      if (a === focusId) s.add(b);
      if (b === focusId) s.add(a);
    }
    return s;
  }, [focusId, EDGES]);

  const edgeRender = EDGES.map(([a, b, kind], i) => {
    if (!visibleIds.has(a) || !visibleIds.has(b)) return null;
    if (!edgeKinds.has(kind)) return null;
    const A = projected[a], B = projected[b];
    if (!A || !B) return null;
    const rel = relById[kind];
    const isFocused = neighborIds && (a === focusId || b === focusId);
    const isDimmed = neighborIds && !isFocused;
    const meanDepth = (A.depth + B.depth) / 2;
    const baseOp = 0.18 + (1 - meanDepth) * 0.45;
    const op = isDimmed ? 0.05 : isFocused ? Math.min(0.95, baseOp + 0.35) : baseOp;
    return {
      key: i, a, b, kind, rel,
      x1: A.x, y1: A.y, x2: B.x, y2: B.y,
      op, focused: isFocused, depth: meanDepth, dimmed: isDimmed,
    };
  }).filter(Boolean).sort((a, b) => b.depth - a.depth);

  const cursor = drag ? "grabbing" : spaceDown ? "grab" : "default";

  const pal = dark ? {
    canvasBg: "#0d0f1a",
    labelFill: "rgba(255,255,255,0.85)",
    labelStroke: "#0d0f1a",
    hintColor: "rgba(255,255,255,0.45)",
    badgeBg: "rgba(13,15,26,0.82)",
    badgeBorder: "rgba(255,255,255,0.10)",
    badgeText: "rgba(255,255,255,0.62)",
    legendDivider: "rgba(255,255,255,0.10)",
  } : {
    canvasBg: "#f4f6fb",
    labelFill: "rgba(20,28,55,0.92)",
    labelStroke: "#f4f6fb",
    hintColor: "rgba(20,28,55,0.45)",
    badgeBg: "rgba(255,255,255,0.92)",
    badgeBorder: "rgba(15,23,42,0.08)",
    badgeText: "rgba(20,28,55,0.62)",
    legendDivider: "rgba(15,23,42,0.08)",
  };

  return (
    <div ref={wrapRef} className="gc3-wrap" style={{ background: pal.canvasBg, cursor }}
         onWheel={onWheel} onMouseDown={onMouseDown}>
      <svg width="100%" height="100%" style={{ display: "block" }}>
        <defs>
          <radialGradient id="vignette" cx="50%" cy="50%" r="60%">
            <stop offset="0%" stopColor={dark ? "rgba(99,102,241,0.06)" : "rgba(99,102,241,0.04)"} />
            <stop offset="100%" stopColor="transparent" />
          </radialGradient>
        </defs>
        <rect width="100%" height="100%" fill="url(#vignette)" />

        <g>
          {edgeRender.map(e => {
            const stroke = e.rel.color;
            const dash = e.rel.style === "dashed" ? "4 4" : null;
            const w = e.focused ? 2.2 : 0.6 + (1 - e.depth) * 1.4;
            return (
              <g key={e.key} style={{ pointerEvents: "none", opacity: e.op }}>
                <line x1={e.x1} y1={e.y1} x2={e.x2} y2={e.y2}
                  stroke={stroke} strokeWidth={w} strokeDasharray={dash} strokeLinecap="round" />
                {e.focused && (
                  <text x={(e.x1 + e.x2)/2} y={(e.y1 + e.y2)/2 - 4} fontSize="10" textAnchor="middle"
                    fill={stroke} fontFamily="var(--mono)"
                    style={{ paintOrder: "stroke", stroke: pal.canvasBg, strokeWidth: 3 }}>
                    {e.rel.zh} · {e.kind}
                  </text>
                )}
              </g>
            );
          })}
        </g>

        <g>
          {visibleNodes.map(n => {
            const p = projected[n.id];
            if (!p) return null;
            const ct = ctById[n.ct];
            const isFocus = focusId === n.id;
            const isNeighbor = neighborIds && neighborIds.has(n.id);
            const isSelected = selected === n.id;
            const dim = neighborIds && !isNeighbor;
            const trust = n.trust || 0.5;
            const baseR = 4 + trust * 6;
            const r = baseR * p.scale * (isSelected ? 1.4 : isFocus ? 1.25 : 1);
            const color = rgbToCss(ct.rgb, 0.55 + trust * 0.45);
            const labelOpacity = dim ? 0.18 : isFocus || isSelected ? 1 : Math.max(0.25, (1 - p.depth) * 0.95);
            const showLabel = (1 - p.depth) > 0.35 || isFocus || isSelected || trust > 0.7;
            const blur = dof ? Math.max(0, Math.abs(p.depth - 0.5) * 4 - 0.3) : 0;
            return (
              <g key={n.id} data-node transform={`translate(${p.x} ${p.y})`}
                 style={{ cursor: "pointer", opacity: dim ? 0.28 : 1, filter: blur ? `blur(${blur}px)` : null }}
                 onMouseEnter={() => setHovered(n.id)}
                 onMouseLeave={() => setHovered(null)}
                 onClick={() => setSelected(n.id)}>
                {(isFocus || isSelected) && (
                  <circle r={r + 9} fill="none" stroke={color} strokeWidth="1.2" opacity="0.55" />
                )}
                {(isFocus || isSelected) && (
                  <circle r={r + 17} fill="none" stroke={color} strokeWidth="0.6" opacity="0.22" />
                )}
                <circle r={r} fill={color} opacity={0.88} />
                <circle r={r * 0.45} cx={-r * 0.18} cy={-r * 0.18} fill="white" opacity="0.32" />
                {showLabel && (
                  <text y={r + 12} textAnchor="middle"
                    fontSize={Math.max(9, 10 * p.scale)}
                    fontFamily="var(--sans)"
                    fontWeight={isFocus || isSelected ? 600 : 500}
                    fill={pal.labelFill}
                    opacity={labelOpacity}
                    style={{ paintOrder: "stroke", stroke: pal.labelStroke, strokeWidth: 3 }}>
                    {n.label.length > 14 ? n.label.slice(0, 13) + "…" : n.label}
                  </text>
                )}
              </g>
            );
          })}
        </g>
      </svg>

      <div className="gc3-legend" style={{ color: pal.badgeText }}>
        {CONTENT_TYPES.map(ct => (
          <div key={ct.id} className="gc3-legend-row">
            <span className="gc3-legend-dot" style={{ background: rgbToCss(ct.rgb, 1) }} />
            <span>{ct.zh}</span>
            <em>{ct.id}</em>
          </div>
        ))}
        <div style={{ borderTop: `1px solid ${pal.legendDivider}`, marginTop: 8, paddingTop: 8 }}>
          {RELATIONS.map(r => (
            <div key={r.id} className="gc3-legend-row">
              <svg width="22" height="6" style={{ flexShrink: 0 }}>
                <line x1="1" y1="3" x2="21" y2="3" stroke={r.color} strokeWidth="1.6"
                  strokeDasharray={r.style === "dashed" ? "3 3" : null} strokeLinecap="round" />
              </svg>
              <span>{r.zh}</span>
              <em>{r.id}</em>
            </div>
          ))}
        </div>
      </div>

      <div className="gc3-badge" style={{
        background: pal.badgeBg, borderColor: pal.badgeBorder, color: pal.badgeText
      }}>
        <span>{visibleNodes.length} 節點 <em>nodes</em></span>
        <span>{edgeRender.length} 關聯 <em>edges</em></span>
      </div>

      <div className="gc3-hint" style={{ color: pal.hintColor }}>
        左鍵旋轉 · Space+拖曳平移 · 滾輪縮放 · 點擊開啟節點
      </div>
    </div>
  );
}

window.GraphCanvas3D = GraphCanvas3D;
