// graph-canvas.jsx
// SVG-based clustered knowledge-graph renderer for MemTrace.

const { useState, useEffect, useRef, useMemo, useCallback } = React;

const TYPE_COLORS = {
  primary: "var(--c-primary)",
  blue:    "var(--c-blue)",
  teal:    "var(--c-teal)",
  violet:  "var(--c-violet)",
  amber:   "var(--c-amber)",
  rose:    "var(--c-rose)",
};

function GraphCanvas({
  data, search, activeClusters, edgeKinds,
  selected, setSelected, hovered, setHovered, density, showHalos, showEdgeLabels
}) {
  const { CLUSTERS, NODES, EDGES } = data;
  const svgRef = useRef(null);
  const wrapRef = useRef(null);
  const [view, setView] = useState({ x: 0, y: 0, k: 1 });
  const [size, setSize] = useState({ w: 1200, h: 720 });
  const [drag, setDrag] = useState(null);

  useEffect(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver(([e]) => {
      const r = e.contentRect;
      setSize({ w: r.width, h: r.height });
    });
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  const VW = 1600, VH = 1000;
  const toX = useCallback((nx) => nx * VW, []);
  const toY = useCallback((ny) => ny * VH, []);

  const clusterById = useMemo(() => Object.fromEntries(CLUSTERS.map(c => [c.id, c])), [CLUSTERS]);

  const matchesSearch = useCallback((n) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return n.label.toLowerCase().includes(q) || n.en.toLowerCase().includes(q) || n.id.includes(q);
  }, [search]);

  const visibleNodes = useMemo(() =>
    NODES.filter(n => activeClusters.has(n.cluster) && matchesSearch(n)),
    [NODES, activeClusters, matchesSearch]
  );
  const visibleIds = useMemo(() => new Set(visibleNodes.map(n => n.id)), [visibleNodes]);
  const nodeById = useMemo(() => Object.fromEntries(NODES.map(n => [n.id, n])), [NODES]);

  const focusId = hovered || selected;
  const neighborIds = useMemo(() => {
    if (!focusId) return null;
    const s = new Set([focusId]);
    for (const [a, b] of EDGES) {
      if (a === focusId) s.add(b);
      if (b === focusId) s.add(a);
    }
    return s;
  }, [focusId, EDGES]);

  const onWheel = (e) => {
    e.preventDefault();
    const rect = svgRef.current.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const delta = -e.deltaY * 0.0015;
    const newK = Math.max(0.5, Math.min(3.5, view.k * (1 + delta)));
    const wx = (mx - view.x) / view.k;
    const wy = (my - view.y) / view.k;
    setView({ k: newK, x: mx - wx * newK, y: my - wy * newK });
  };
  const onMouseDown = (e) => {
    if (e.target.closest("[data-node]")) return;
    setDrag({ sx: e.clientX, sy: e.clientY, vx: view.x, vy: view.y });
  };
  useEffect(() => {
    if (!drag) return;
    const onMove = (e) => {
      setView(v => ({ ...v, x: drag.vx + (e.clientX - drag.sx), y: drag.vy + (e.clientY - drag.sy) }));
    };
    const onUp = () => setDrag(null);
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [drag]);

  useEffect(() => {
    if (size.w < 10) return;
    const sx = size.w / VW;
    const sy = size.h / VH;
    const k = Math.min(sx, sy) * 0.96;
    setView({
      k,
      x: (size.w - VW * k) / 2,
      y: (size.h - VH * k) / 2,
    });
  }, [size.w, size.h]);

  const renderEdge = (e, i) => {
    const [a, b, kind] = e;
    if (!visibleIds.has(a) || !visibleIds.has(b)) return null;
    if (!edgeKinds.has(kind)) return null;
    const A = nodeById[a], B = nodeById[b];
    if (!A || !B) return null;
    const x1 = toX(A.x), y1 = toY(A.y);
    const x2 = toX(B.x), y2 = toY(B.y);
    const mx = (x1 + x2) / 2;
    const my = (y1 + y2) / 2;
    const dx = x2 - x1, dy = y2 - y1;
    const len = Math.hypot(dx, dy) || 1;
    const off = Math.min(60, len * 0.12);
    const cx = mx - (dy / len) * off;
    const cy = my + (dx / len) * off;
    const isFocused = neighborIds && (neighborIds.has(a) && neighborIds.has(b) && (a === focusId || b === focusId));
    const isDimmed = neighborIds && !isFocused;
    const dashed = kind !== "extends";
    return (
      <g key={i} style={{ opacity: isDimmed ? 0.08 : (neighborIds ? 0.9 : 0.42) }}>
        <path
          d={`M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`}
          fill="none"
          stroke={isFocused ? "var(--ink-strong)" : "var(--edge)"}
          strokeWidth={isFocused ? 1.6 : 0.9}
          strokeDasharray={dashed ? "3 4" : null}
        />
        {showEdgeLabels && isFocused && (
          <text x={cx} y={cy - 3} fontSize="10" fill="var(--ink-mute)" textAnchor="middle"
                style={{ paintOrder: "stroke", stroke: "var(--bg)", strokeWidth: 3 }}>
            {kind}
          </text>
        )}
      </g>
    );
  };

  // Use trust (not imp) for node sizing
  const sizeFor = (n) => 6 + (n.trust || 0.5) * 7;
  const labelFor = (n, scale) => {
    if (scale < 0.7 && (n.trust || 0.5) < 0.65) return null;
    return n.label;
  };

  return (
    <div ref={wrapRef} className="gc-wrap">
      <svg
        ref={svgRef}
        className="gc-svg"
        width="100%" height="100%"
        onWheel={onWheel}
        onMouseDown={onMouseDown}
        style={{ cursor: drag ? "grabbing" : "grab" }}
      >
        <defs>
          <pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse">
            <circle cx="1" cy="1" r="0.8" fill="var(--dot)" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#dots)" />

        <g transform={`translate(${view.x} ${view.y}) scale(${view.k})`}>
          {/* Cluster halos */}
          {showHalos && CLUSTERS.map(cl => {
            const active = activeClusters.has(cl.id);
            return (
              <g key={cl.id} style={{ opacity: active ? (focusId ? 0.35 : 0.75) : 0.18 }}>
                <ellipse
                  cx={toX(cl.cx)} cy={toY(cl.cy)}
                  rx={cl.r * VW * 0.95}
                  ry={cl.r * VH * 0.85}
                  fill={`color-mix(in oklab, ${TYPE_COLORS[cl.color]} 9%, transparent)`}
                  stroke={`color-mix(in oklab, ${TYPE_COLORS[cl.color]} 35%, transparent)`}
                  strokeWidth="1"
                  strokeDasharray="2 5"
                />
                <text
                  x={toX(cl.cx)}
                  y={toY(cl.cy - cl.r * 0.95)}
                  textAnchor="middle"
                  fontSize="13"
                  fontWeight="600"
                  letterSpacing="0.04em"
                  fill={TYPE_COLORS[cl.color]}
                  style={{ paintOrder: "stroke", stroke: "var(--bg)", strokeWidth: 4 }}
                >
                  {cl.label}
                </text>
                <text
                  x={toX(cl.cx)}
                  y={toY(cl.cy - cl.r * 0.95) + 14}
                  textAnchor="middle"
                  fontSize="9.5"
                  fontFamily="var(--mono)"
                  letterSpacing="0.12em"
                  fill="var(--ink-mute)"
                  style={{ paintOrder: "stroke", stroke: "var(--bg)", strokeWidth: 4 }}
                >
                  {cl.en}
                </text>
              </g>
            );
          })}

          {/* Edges */}
          <g>{EDGES.map(renderEdge)}</g>

          {/* Nodes */}
          <g>
            {visibleNodes.map(n => {
              const cl = clusterById[n.cluster];
              const color = TYPE_COLORS[cl.color];
              const x = toX(n.x), y = toY(n.y);
              const r = sizeFor(n);
              const isFocus = focusId === n.id;
              const isNeighbor = neighborIds && neighborIds.has(n.id);
              const dim = neighborIds && !isNeighbor;
              const isSelected = selected === n.id;
              const label = labelFor(n, view.k);
              return (
                <g
                  key={n.id}
                  data-node
                  transform={`translate(${x} ${y})`}
                  style={{ cursor: "pointer", opacity: dim ? 0.22 : 1, transition: "opacity .18s" }}
                  onMouseEnter={() => setHovered(n.id)}
                  onMouseLeave={() => setHovered(null)}
                  onClick={() => setSelected(n.id)}
                >
                  {(isFocus || isSelected) && (
                    <circle r={r + 8} fill="none"
                      stroke={color} strokeWidth="1" opacity="0.6" />
                  )}
                  {(isFocus || isSelected) && (
                    <circle r={r + 14} fill="none"
                      stroke={color} strokeWidth="0.6" opacity="0.25" />
                  )}
                  <circle
                    r={r}
                    fill={isSelected ? color : "var(--bg)"}
                    stroke={color}
                    strokeWidth={isSelected || isFocus ? 2 : 1.3}
                  />
                  <circle r={r * 0.36} fill={color} opacity={isSelected ? 0.0 : 0.85} />

                  {label && (
                    <g transform={`translate(0 ${r + 10})`}>
                      <rect
                        x={-Math.min(80, label.length * 4 + 8)}
                        y={-1}
                        width={Math.min(160, label.length * 8 + 16)}
                        height={20}
                        rx={10}
                        fill="var(--bg)"
                        stroke={isFocus || isSelected ? color : "var(--line)"}
                        strokeWidth={isFocus || isSelected ? 1 : 0.8}
                      />
                      <text
                        y={13}
                        textAnchor="middle"
                        fontSize="10.5"
                        fill={isFocus || isSelected ? "var(--ink-strong)" : "var(--ink)"}
                        fontWeight={isFocus || isSelected ? 600 : 500}
                      >
                        {label.length > 16 ? label.slice(0, 15) + "…" : label}
                      </text>
                    </g>
                  )}
                </g>
              );
            })}
          </g>
        </g>
      </svg>

      <div className="gc-hint">
        <span><kbd>滾輪</kbd> 縮放</span>
        <span><kbd>拖曳</kbd> 平移</span>
        <span><kbd>點擊</kbd> 開啟節點</span>
        <span className="gc-hint-en">scroll · drag · click</span>
      </div>

      <div className="gc-zoom">
        <button onClick={() => setView(v => {
          const k = Math.min(3.5, v.k * 1.2);
          return { ...v, k, x: size.w/2 - (size.w/2 - v.x) * (k / v.k), y: size.h/2 - (size.h/2 - v.y) * (k / v.k) };
        })}>＋</button>
        <div className="gc-zoom-pct">{Math.round(view.k * 100)}%</div>
        <button onClick={() => setView(v => {
          const k = Math.max(0.5, v.k / 1.2);
          return { ...v, k, x: size.w/2 - (size.w/2 - v.x) * (k / v.k), y: size.h/2 - (size.h/2 - v.y) * (k / v.k) };
        })}>−</button>
        <button title="重設視圖 / Reset" onClick={() => {
          const k = Math.min(size.w / VW, size.h / VH) * 0.96;
          setView({ k, x: (size.w - VW*k)/2, y: (size.h - VH*k)/2 });
        }}>⊙</button>
      </div>

      <Minimap
        nodes={NODES} clusters={CLUSTERS}
        visibleIds={visibleIds}
        view={view} size={size}
        VW={VW} VH={VH}
        onMove={(nx, ny) => setView(v => ({ ...v, x: nx, y: ny }))}
      />
    </div>
  );
}

function Minimap({ nodes, clusters, visibleIds, view, size, VW, VH, onMove }) {
  const MW = 220, MH = 138;
  const scale = Math.min(MW / VW, MH / VH);
  const vx = -view.x / view.k;
  const vy = -view.y / view.k;
  const vw = size.w / view.k;
  const vh = size.h / view.k;
  return (
    <div className="gc-mini">
      <svg width={MW} height={MH}>
        <rect width={MW} height={MH} fill="var(--bg)" stroke="var(--line)" />
        <g transform={`translate(${(MW - VW*scale)/2} ${(MH - VH*scale)/2}) scale(${scale})`}>
          {clusters.map(cl => (
            <ellipse key={cl.id}
              cx={cl.cx * VW} cy={cl.cy * VH}
              rx={cl.r * VW * 0.95} ry={cl.r * VH * 0.85}
              fill={`color-mix(in oklab, var(--c-${cl.color}) 14%, transparent)`} />
          ))}
          {nodes.map(n => visibleIds.has(n.id) && (
            <circle key={n.id} cx={n.x*VW} cy={n.y*VH} r={6 + (n.trust||0.5)*8}
              fill={`var(--c-${clusters.find(c=>c.id===n.cluster).color})`}
              opacity="0.6" />
          ))}
          <rect
            x={vx} y={vy} width={vw} height={vh}
            fill="none" stroke="var(--c-primary)" strokeWidth={3 / scale}
          />
        </g>
        <text x="8" y="14" fontSize="10" fontWeight="600" fill="var(--ink-mute)" fontFamily="var(--mono)" letterSpacing="0.1em">MINIMAP</text>
      </svg>
    </div>
  );
}

window.GraphCanvas = GraphCanvas;
