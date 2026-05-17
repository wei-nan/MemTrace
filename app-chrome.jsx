// app-chrome.jsx — Sidebar, header, toolbar, detail panel for MemTrace

const T = (lang, zh, en) => lang === "en" ? en : zh;
function rgbCss([r, g, b], f = 1) {
  return `rgb(${Math.round(r*f)}, ${Math.round(g*f)}, ${Math.round(b*f)})`;
}

function Sidebar({ lang, data, search, setSearch, activeContentTypes, setActiveContentTypes,
                   activeClusters, setActiveClusters, edgeKinds, setEdgeKinds, counts, ctCounts }) {
  const NAV = [
    { id: "graph",  zh: "知識圖譜",   en: "Knowledge Graph", icon: "graph", active: true },
    { id: "stats",  zh: "數據統計",   en: "Statistics",      icon: "stats" },
    { id: "review", zh: "審核佇列",   en: "Review Queue",    icon: "inbox", badge: 7 },
    { id: "ws",     zh: "工作區管理", en: "Workspaces",      icon: "users" },
    { id: "ingest", zh: "文件攝入",   en: "Document Ingest", icon: "upload" },
  ];

  return (
    <aside className="side">
      <div className="side-brand">
        <div className="side-logo">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none">
            <circle cx="7" cy="8" r="2.4" stroke="currentColor" strokeWidth="1.6" />
            <circle cx="17" cy="8" r="2.4" stroke="currentColor" strokeWidth="1.6" />
            <circle cx="12" cy="17" r="2.4" stroke="currentColor" strokeWidth="1.6" />
            <path d="M9 9 L15 9 M8 10 L11 15 M16 10 L13 15" stroke="currentColor" strokeWidth="1.4" />
          </svg>
        </div>
        <div className="side-brand-text">
          <b>MemTrace</b>
          <span>v2.4 · stable</span>
        </div>
      </div>

      <div className="side-workspace">
        <div className="side-workspace-label">{T(lang, "當前工作區", "Current Workspace")}</div>
        <button className="side-workspace-btn">
          <span>{T(lang, "MemTrace 規格知識庫", "MemTrace Spec KB")}</span>
          <svg width="12" height="12" viewBox="0 0 12 12"><path d="M3 5 L6 8 L9 5" stroke="currentColor" strokeWidth="1.4" fill="none" /></svg>
        </button>
      </div>

      <div className="side-search">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.4"><circle cx="6" cy="6" r="3.5"/><path d="M9 9 L12 12"/></svg>
        <input
          placeholder={T(lang, "搜尋節點…", "Search nodes…")}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        {search && <button onClick={() => setSearch("")}>×</button>}
      </div>

      <nav className="side-nav">
        {NAV.map(n => (
          <button key={n.id} className={`side-nav-item ${n.active ? "is-active" : ""}`}>
            <NavIcon name={n.icon} />
            <div className="side-nav-text">
              <span className="label">{T(lang, n.zh, n.en)}</span>
            </div>
            {n.badge && <span className="side-nav-badge">{n.badge}</span>}
          </button>
        ))}
      </nav>

      <div className="side-section">
        <div className="side-section-h">
          <span>{T(lang, "內容類型", "Content Type")}</span>
        </div>
        <div className="side-clusters">
          {data.CONTENT_TYPES.map(ct => {
            const on = activeContentTypes.has(ct.id);
            return (
              <button key={ct.id} className={`side-cluster ${on ? "is-on" : ""}`}
                onClick={() => {
                  const s = new Set(activeContentTypes);
                  on ? s.delete(ct.id) : s.add(ct.id);
                  setActiveContentTypes(s);
                }}>
                <span className="side-cluster-dot" style={{ background: rgbCss(ct.rgb) }} />
                <span className="side-cluster-label">
                  <b>{T(lang, ct.zh, ct.id)}</b>
                </span>
                <span className="side-cluster-count">{ctCounts[ct.id] || 0}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="side-section">
        <div className="side-section-h">
          <span>{T(lang, "節點分群", "Clusters")}</span>
        </div>
        <div className="side-clusters side-clusters-compact">
          {data.CLUSTERS.map(cl => {
            const on = activeClusters.has(cl.id);
            return (
              <button key={cl.id} className={`side-cluster ${on ? "is-on" : ""}`}
                onClick={() => {
                  const s = new Set(activeClusters);
                  on ? s.delete(cl.id) : s.add(cl.id);
                  setActiveClusters(s);
                }}>
                <span className="side-cluster-dot" style={{ background: `var(--c-${cl.color})` }} />
                <span className="side-cluster-label">
                  <b>{T(lang, cl.label, cl.en)}</b>
                </span>
                <span className="side-cluster-count">{counts[cl.id] || 0}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="side-section">
        <div className="side-section-h">
          <span>{T(lang, "關係類型", "Relations")}</span>
        </div>
        <div className="side-edges">
          {data.RELATIONS.map(k => {
            const on = edgeKinds.has(k.id);
            return (
              <label key={k.id} className={`side-edge ${on ? "is-on" : ""}`}>
                <input type="checkbox" checked={on} onChange={() => {
                  const s = new Set(edgeKinds);
                  on ? s.delete(k.id) : s.add(k.id);
                  setEdgeKinds(s);
                }} />
                <svg width="28" height="6" style={{ flexShrink: 0 }}>
                  <line x1="2" y1="3" x2="26" y2="3" stroke={k.color} strokeWidth="1.6"
                    strokeDasharray={k.style === "dashed" ? "3 3" : null} strokeLinecap="round" />
                </svg>
                <span className="side-edge-zh">{T(lang, k.zh, k.id.replace(/_/g, " "))}</span>
              </label>
            );
          })}
        </div>
      </div>

      <div className="side-foot">
        <div className="side-foot-row">
          <span>W</span>
          <div>
            <b>William</b>
            <em>{T(lang, "工作區擁有者", "Workspace Owner")}</em>
          </div>
          <svg width="12" height="12" viewBox="0 0 12 12"><circle cx="6" cy="3" r="1" fill="currentColor"/><circle cx="6" cy="6" r="1" fill="currentColor"/><circle cx="6" cy="9" r="1" fill="currentColor"/></svg>
        </div>
      </div>
    </aside>
  );
}

function NavIcon({ name }) {
  const common = { width: 16, height: 16, viewBox: "0 0 16 16", fill: "none", stroke: "currentColor", strokeWidth: 1.4, strokeLinecap: "round", strokeLinejoin: "round" };
  switch (name) {
    case "graph": return <svg {...common}><circle cx="4" cy="4" r="1.6"/><circle cx="12" cy="4" r="1.6"/><circle cx="8" cy="12" r="1.6"/><path d="M5 5 L11 5 M5 6 L7 11 M11 6 L9 11"/></svg>;
    case "stats": return <svg {...common}><path d="M3 13 L3 9 M7 13 L7 5 M11 13 L11 8 M13 13 L1 13"/></svg>;
    case "inbox": return <svg {...common}><path d="M2 9 L4 4 L12 4 L14 9 L14 13 L2 13 Z M2 9 L6 9 L7 10.5 L9 10.5 L10 9 L14 9"/></svg>;
    case "users": return <svg {...common}><circle cx="6" cy="6" r="2"/><path d="M3 13 C3 11 4.5 10 6 10 C7.5 10 9 11 9 13"/><circle cx="11" cy="6" r="1.6"/><path d="M9.5 11 C10 10.4 10.7 10 11.5 10 C12.7 10 13.5 10.9 13.5 12.5"/></svg>;
    case "upload": return <svg {...common}><path d="M8 11 L8 3 M5 6 L8 3 L11 6 M3 13 L13 13"/></svg>;
    default: return null;
  }
}

function HeaderBar({ lang, counts }) {
  return (
    <header className="head">
      <div className="head-l">
        <h1>{T(lang, "知識圖譜", "Knowledge Graph")}</h1>
        <div className="head-meta">
          <span className="head-meta-num">{counts.shown} {T(lang, "節點", "nodes")}</span>
          <span className="head-dot" />
          <span>{counts.edges} {T(lang, "連結", "edges")}</span>
        </div>
      </div>
      <div className="head-r">
        <div className="head-user">
          <span className="head-avatar">W</span>
          <span>William</span>
        </div>
      </div>
    </header>
  );
}

function Toolbar({ lang, isolated, limit, setLimit, viewMode, setViewMode, dof, setDof, onAction }) {
  return (
    <div className="tool">
      <div className="tool-l">
        {isolated > 0 && (
          <div className="tool-warn">
            <svg width="13" height="13" viewBox="0 0 14 14" fill="none">
              <path d="M7 2 L13 12 L1 12 Z" stroke="currentColor" strokeWidth="1.2" />
              <path d="M7 6 L7 8.4 M7 10 L7 10.1" stroke="currentColor" strokeWidth="1.2" />
            </svg>
            <span>{isolated} {T(lang, "個孤立節點", "isolated nodes")}</span>
          </div>
        )}
        <div className="tool-limit">
          <span className="tool-limit-label">{T(lang, "顯示上限", "Limit")}</span>
          <select value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
            <option value={100}>100</option>
            <option value={200}>200</option>
            <option value={500}>500</option>
            <option value={1000}>1000</option>
          </select>
        </div>
      </div>

      <div className="tool-c">
        <div className="tool-view">
          {[
            { id: "2D", label: "2D", icon: "two" },
            { id: "3D", label: "3D", icon: "three" },
            { id: "table", label: T(lang, "表格", "TABLE"), icon: "table" },
            { id: "explore", label: T(lang, "探索", "EXPLORE"), icon: "explore" },
          ].map(v => (
            <button key={v.id} className={viewMode === v.id ? "is-on" : ""} onClick={() => setViewMode(v.id)}>
              <ViewIcon name={v.icon} />
              <span>{v.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="tool-r">
        <button className="tool-btn" onClick={() => onAction("archive")}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.4">
            <rect x="1.5" y="2" width="11" height="3" rx="0.5"/><path d="M2.5 5 L2.5 12 L11.5 12 L11.5 5 M5.5 7.5 L8.5 7.5"/>
          </svg>
          <span className="tool-btn-label"><span className="tool-btn-zh">{T(lang, "歸檔", "Archive")}</span></span>
        </button>
        <button className={`tool-btn ${dof && viewMode === "3D" ? "is-on" : ""}`}
                onClick={() => setDof(!dof)} disabled={viewMode !== "3D"}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.4">
            <path d="M2.5 7 L4 3.5 L4.8 5.6 L6.6 1.5 L7.6 5.2 L9.4 3 L10.4 6 L11.5 4 L11.5 7" fill="currentColor" fillOpacity="0.15" />
            <path d="M2.5 7 L4 3.5 L4.8 5.6 L6.6 1.5 L7.6 5.2 L9.4 3 L10.4 6 L11.5 4 L11.5 7" />
          </svg>
          <span className="tool-btn-label"><span className="tool-btn-zh">{T(lang, "景深", "DOF")}</span></span>
        </button>
        <button className="tool-btn" onClick={() => onAction("connect")}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.4">
            <circle cx="3.5" cy="3.5" r="1.5"/><circle cx="10.5" cy="10.5" r="1.5"/><path d="M4.6 4.6 L9.4 9.4"/>
          </svg>
          <span className="tool-btn-label"><span className="tool-btn-zh">{T(lang, "補邊", "Connect")}</span></span>
        </button>
        <button className="tool-btn" onClick={() => onAction("relayout")}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.4">
            <path d="M2 7 A5 5 0 1 1 7 12 M2 7 L4 5 M2 7 L0.5 5"/>
          </svg>
          <span className="tool-btn-label"><span className="tool-btn-zh">{T(lang, "重新整理", "Re-layout")}</span></span>
        </button>
        <button className="tool-btn is-primary" onClick={() => onAction("add")}>
          <span className="tool-btn-plus">＋</span>
          <span className="tool-btn-label"><span className="tool-btn-zh">{T(lang, "新增節點", "New Node")}</span></span>
        </button>
      </div>
    </div>
  );
}

function ViewIcon({ name }) {
  const c = { width: 14, height: 14, viewBox: "0 0 14 14", fill: "none", stroke: "currentColor", strokeWidth: 1.3, strokeLinecap: "round", strokeLinejoin: "round" };
  switch (name) {
    case "two":   return <svg {...c}><circle cx="3" cy="4" r="1.3"/><circle cx="11" cy="4" r="1.3"/><circle cx="7" cy="11" r="1.3"/><path d="M4 4.5 L10 4.5 M4 5 L6 10 M10 5 L8 10"/></svg>;
    case "three": return <svg {...c}><path d="M2 4 L7 1.5 L12 4 L12 10 L7 12.5 L2 10 Z"/><path d="M7 1.5 L7 12.5 M2 4 L12 4 M2 10 L12 10" opacity="0.5"/></svg>;
    case "table": return <svg {...c}><rect x="1.5" y="2.5" width="11" height="9" rx="0.5"/><path d="M1.5 5.5 L12.5 5.5 M1.5 8.5 L12.5 8.5 M5 5.5 L5 11.5 M9 5.5 L9 11.5" opacity="0.5"/></svg>;
    case "explore": return <svg {...c}><circle cx="7" cy="7" r="5"/><path d="M5 7 L7 5 L9 7 L7 9 Z"/></svg>;
    default: return null;
  }
}

function DetailPanel({ lang, node, contentType, neighbors, onClose, onJump }) {
  if (!node) return null;
  return (
    <aside className="detail">
      <div className="detail-hd">
        <div className="detail-hd-l">
          <div className="detail-cluster">
            <span className="detail-cluster-dot" style={{ background: rgbCss(contentType.rgb) }} />
            <span>{T(lang, contentType.zh, contentType.id)}</span>
          </div>
          <h2>{T(lang, node.label, node.en)}</h2>
        </div>
        <button className="detail-x" onClick={onClose}>✕</button>
      </div>

      <div className="detail-meta">
        <div>
          <span className="detail-meta-k">ID</span>
          <code>{node.id}</code>
        </div>
        <div>
          <span className="detail-meta-k">{T(lang, "信任", "Trust")}</span>
          <div className="detail-meta-bar">
            <div style={{ width: `${node.trust * 100}%`, background: rgbCss(contentType.rgb) }} />
          </div>
          <em>{node.trust.toFixed(2)}</em>
        </div>
        <div>
          <span className="detail-meta-k">{T(lang, "分群", "Cluster")}</span>
          <span className="detail-meta-v">{node.cluster}</span>
        </div>
      </div>

      <div className="detail-section">
        <div className="detail-section-h">
          <span>{T(lang, "摘要", "Summary")}</span>
        </div>
        <p className="detail-summary">
          {T(lang,
            SUMMARIES_ZH[node.id] || `本節點記錄了與「${node.label}」相關的規格與決策。`,
            SUMMARIES_EN[node.id] || `Node ${node.id} captures specification notes for this concept.`)}
        </p>
      </div>

      <div className="detail-section">
        <div className="detail-section-h">
          <span>{T(lang, "相關節點", "Related Nodes")}</span>
          <em>· {neighbors.length}</em>
        </div>
        <div className="detail-neighbors">
          {neighbors.length === 0 && <div className="detail-empty">{T(lang, "尚無相關節點", "No neighbors")}</div>}
          {neighbors.map(({ n, kind, ct, rel }) => (
            <button key={n.id + kind} className="detail-neighbor" onClick={() => onJump(n.id)}>
              <span className="detail-neighbor-dot" style={{ background: rgbCss(ct.rgb) }} />
              <div className="detail-neighbor-text">
                <b>{T(lang, n.label, n.en)}</b>
              </div>
              <code className="detail-neighbor-kind" style={{ color: rel.color }}>
                {T(lang, rel.zh, rel.id.replace(/_/g, " "))}
              </code>
            </button>
          ))}
        </div>
      </div>

      <div className="detail-foot">
        <button className="detail-act">{T(lang, "編輯", "Edit")}</button>
        <button className="detail-act">{T(lang, "補邊", "Connect")}</button>
        <button className="detail-act">{T(lang, "歸檔", "Archive")}</button>
      </div>
    </aside>
  );
}

const SUMMARIES_ZH = {
  n_core: "MemTrace 平台的總覽節點，連結所有主要規格區塊：API、知識圖譜、AI 代理與文件來源。",
  n_api: "API 金鑰與 Session 的核心定義，描述了金鑰簽發、權限範圍與會話生命週期。",
  n_graph: "知識圖譜的計量規範：節點權重、連結方向、孤立節點清理策略。",
  n_ai: "AI 代理的工作流程，從讀取知識庫、生成回應、到寫回新節點的完整循環。",
  n_auth: "管理角色與其能力詳情。角色繼承自工作區所有者，可委派或自訂能力。",
  n_doc: "來源文件節點的驗證規範與儲存方法，包含多種類型（檔案、URL、片段）。",
};
const SUMMARIES_EN = {
  n_core: "Top-level platform spec connecting API, graph, agent, and source clusters.",
  n_api: "Definition of API keys and sessions: issuance, scope, lifecycle.",
  n_graph: "Knowledge-graph metrics: node weight, edge direction, isolation cleanup.",
  n_ai: "End-to-end agent workflow from KB read to new-node write-back.",
  n_auth: "Role admin: capabilities inherited from workspace owner, delegable.",
  n_doc: "Source-node validation + storage across file / URL / snippet kinds.",
};

window.Sidebar = Sidebar;
window.HeaderBar = HeaderBar;
window.Toolbar = Toolbar;
window.DetailPanel = DetailPanel;
window.MT_T = T;
