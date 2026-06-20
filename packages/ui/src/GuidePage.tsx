import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
  BookOpen, Target, Sparkles, Rocket, Boxes, Bot, ArrowRight,
  Clock, AlertTriangle, Database, GitMerge,
  ShieldCheck, HelpCircle, Network, Cpu, KeyRound, Cloud, HardDrive,
} from 'lucide-react';

interface GuidePageProps {
  onOpenSpecKb: () => void;
}

export default function GuidePage({ onOpenSpecKb }: GuidePageProps) {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';

  const scrollRef = useRef<HTMLDivElement>(null);

  const SECTIONS = [
    { id: 'intro', icon: Target, label: zh ? '為什麼' : 'Why' },
    { id: 'living', icon: Sparkles, label: zh ? '為什麼是「活的」' : 'Why "living"' },
    { id: 'start', icon: Rocket, label: zh ? '怎麼開始' : 'Getting started' },
    { id: 'concepts', icon: Boxes, label: zh ? '核心概念' : 'Core concepts' },
    { id: 'providers', icon: Cpu, label: zh ? '模型供應商' : 'LLM providers' },
    { id: 'agents', icon: Bot, label: zh ? '接上 MCP' : 'Connect via MCP' },
    { id: 'spec', icon: BookOpen, label: zh ? '完整規格' : 'Full spec' },
  ];

  const [activeId, setActiveId] = useState(SECTIONS[0].id);

  useEffect(() => {
    const root = scrollRef.current;
    if (!root) return;
    const observer = new IntersectionObserver(
      entries => {
        const visible = entries
          .filter(e => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActiveId(visible[0].target.id);
      },
      { root, rootMargin: '0px 0px -70% 0px', threshold: 0 }
    );
    SECTIONS.forEach(s => {
      const el = document.getElementById(s.id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const goTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  // ── Content data ──────────────────────────────────────────────────────────
  const goldenCircle = [
    {
      ring: 'WHY',
      label: zh ? '為什麼' : 'Why',
      headline: zh ? '知識不該歸零' : 'Knowledge shouldn’t reset',
      text: zh
        ? '我們相信，人與 AI 一起累積的理解，不該隨著每次對話結束就消失。知識值得被保存、被持續檢驗、被一點一滴累積起來。'
        : 'We believe the understanding humans and AI build together shouldn’t vanish at the end of every conversation. Knowledge deserves to be kept, continually questioned, and compounded.',
    },
    {
      ring: 'HOW',
      label: zh ? '怎麼做' : 'How',
      headline: zh ? '讓知識可被驗證、會演化' : 'Make knowledge verifiable & evolving',
      text: zh
        ? '把知識拆成帶來源、帶信任度的節點與關聯，讓它能被驗證、演化、甚至淘汰；由人與 AI 共同維護，並用審核佇列為品質把關。'
        : 'We structure knowledge into nodes and typed edges with provenance and trust — so it can be verified, evolve, or retire — co-maintained by humans and AI, gated by a review queue.',
    },
    {
      ring: 'WHAT',
      label: zh ? '做什麼' : 'What',
      headline: zh ? '一個活的知識圖譜' : 'A living knowledge graph',
      text: zh
        ? '結果就是一個活的知識圖譜：你看到的每個節點、每條關聯、每個信任分數，都是這個信念的具體呈現。'
        : 'The result is a living knowledge graph: every node, edge, and trust score you see is that belief made concrete.',
    },
  ];

  const scenarios = [
    {
      icon: Clock,
      title: zh ? '知識會老化' : 'Knowledge ages',
      see: zh
        ? '每個節點都有信任分數，會隨時間衰減。久未驗證的知識會在健康頁被標記為「待重新驗證」，提醒你它可能已經過時。'
        : 'Every node has a trust score that decays over time. Stale knowledge gets flagged for re-verification on the health page.',
      how: zh ? '機制：信任分數時間衰減' : 'Mechanism: time-based trust decay',
    },
    {
      icon: Bot,
      title: zh ? '人與 AI 共筆' : 'Humans & AI co-author',
      see: zh
        ? 'AI 助手透過 MCP 連進來提案新知識，這些提案會進入審核佇列，由你確認後才正式生效。'
        : 'AI agents connect via MCP and propose new knowledge. Proposals enter a review queue and only go live once you approve.',
      how: zh ? '機制：MCP 提案 → 審核佇列 → 人工把關' : 'Mechanism: MCP proposal → review queue → human gate',
    },
    {
      icon: HelpCircle,
      title: zh ? '問題驅動成長' : 'Question-driven growth',
      see: zh
        ? '搜尋找不到答案時，系統會記下一個 inquiry（待答問題）節點；之後補上答案，會用 answered_by 邊把問題與答案串起來，缺口自動收斂。'
        : 'When a search misses, the system records an inquiry node. Once answered, an answered_by edge links question to answer and the gap closes.',
      how: zh ? '機制：gap/inquiry → answered_by' : 'Mechanism: gap/inquiry → answered_by',
    },
    {
      icon: AlertTriangle,
      title: zh ? '衝突會被偵測' : 'Conflicts get detected',
      see: zh
        ? '當新知識和既有高信任節點矛盾時，系統不會默默覆蓋，而是標記 contradicts 邊，交給你裁決。'
        : 'When new knowledge contradicts a high-trust node, nothing is silently overwritten — a contradicts edge is flagged for you to resolve.',
      how: zh ? '機制：矛盾偵測 + contradicts 邊' : 'Mechanism: contradiction detection + contradicts edge',
    },
    {
      icon: Network,
      title: zh ? '文件變成知識網' : 'Documents become a graph',
      see: zh
        ? '上傳一份文件，AI 會把它拆解成多個知識節點，並用 extracted_from 邊連回原始文件，保留來源可追溯。'
        : 'Upload a document and AI breaks it into knowledge nodes, linked back to the source via extracted_from edges for full traceability.',
      how: zh ? '機制：ingestion 拆解 + extracted_from' : 'Mechanism: ingestion + extracted_from',
    },
  ];

  const steps = [
    {
      title: zh ? '建立知識庫' : 'Create a knowledge base',
      desc: zh
        ? '在左上角工作區選單建立一個新的 KB，選擇語言與可見度。'
        : 'Create a new KB from the workspace selector (top-left), choosing language and visibility.',
    },
    {
      title: zh ? '放入知識' : 'Add knowledge',
      desc: zh
        ? '兩種方式：上傳 .md / .txt 文件讓 AI 自動拆解成節點，或手動建立節點。'
        : 'Two ways: upload .md / .txt files for AI to break into nodes, or create nodes manually.',
    },
    {
      title: zh ? '搜尋與遍歷' : 'Search & traverse',
      desc: zh
        ? '用語意搜尋找到相關節點，再沿著關聯邊（related_to、depends_on…）探索周邊脈絡。'
        : 'Use semantic search to find nodes, then follow typed edges (related_to, depends_on…) to explore surrounding context.',
    },
    {
      title: zh ? '用 AI 對話' : 'Chat with AI',
      desc: zh
        ? '開啟右下角的 AI 面板，直接提問。AI 會基於這個知識庫回答，並可提案補充新知識。'
        : 'Open the AI panel (bottom-right) and ask. It answers grounded in this KB and can propose new knowledge.',
    },
    {
      title: zh ? '讓 AI agent 接入' : 'Connect an AI agent',
      desc: zh
        ? '在設定建立具 kb:write 權限的 API 金鑰，把 MemTrace 當成 Claude Code / Cursor 等工具的長期記憶（見下一節）。'
        : 'Create an API key with kb:write scope, then use MemTrace as long-term memory for Claude Code / Cursor (see next section).',
    },
    {
      title: zh ? '審核佇列把關' : 'Gate via the review queue',
      desc: zh
        ? 'AI 或外部來源的提案會進入審核佇列，你在這裡決定接受、修改或拒絕。'
        : 'Proposals from AI or external sources land in the review queue, where you accept, edit, or reject them.',
    },
  ];

  const concepts = [
    {
      term: zh ? '記憶節點 (Node)' : 'Memory Node',
      def: zh
        ? '知識的原子單位 —— 事實、程序、偏好或情境。'
        : 'The atomic unit of knowledge — factual, procedural, preference, or context.',
    },
    {
      term: zh ? '關聯邊 (Edge)' : 'Typed Edge',
      def: zh
        ? '帶類型的有向連結（related_to / depends_on / contradicts / answered_by…），表達節點之間的關係。'
        : 'A typed directed link (related_to / depends_on / contradicts / answered_by…) expressing how nodes relate.',
    },
    {
      term: zh ? '信任分數 (Trust)' : 'Trust Score',
      def: zh
        ? '多維度評分（正確性、新鮮度、效用、作者信譽），會隨時間衰減、被投票或驗證調整。'
        : 'A multi-dimensional score (accuracy, freshness, utility, author rep) that decays over time and shifts with votes/verifications.',
    },
    {
      term: zh ? 'inquiry 節點' : 'Inquiry Node',
      def: zh
        ? '記錄「目前還沒有答案」的開放問題，是知識缺口的標記，被回答後以 answered_by 收斂。'
        : 'Records an open question with no answer yet — a gap marker, closed by an answered_by edge once resolved.',
    },
    {
      term: zh ? '審核佇列 (Review Queue)' : 'Review Queue',
      def: zh
        ? '非信任來源（AI / MCP）的提案先進這裡，經人工 gate 才進入正式圖譜。'
        : 'Proposals from untrusted sources (AI / MCP) wait here for a human gate before entering the graph.',
    },
    {
      term: 'resolution_status',
      def: zh
        ? 'open / resolved / superseded —— 記錄知識本身的生命週期狀態，與節點是否存在（active）獨立。'
        : 'open / resolved / superseded — the epistemic lifecycle of the knowledge, independent of whether the node is active.',
    },
  ];

  const providers = [
    {
      name: 'OpenAI', cloud: true,
      note: zh ? '填入 sk-... 金鑰，支援對話與向量（embedding）模型。' : 'Paste an sk-... key; supports chat and embedding models.',
    },
    {
      name: 'Anthropic', cloud: true,
      note: zh ? 'Claude 系列對話模型，填入 sk-ant-... 金鑰。' : 'Claude chat models; paste an sk-ant-... key.',
    },
    {
      name: 'Gemini', cloud: true,
      note: zh ? 'Google 模型，支援對話與向量模型，填入 AIza... 金鑰。' : 'Google models for chat and embeddings; paste an AIza... key.',
    },
    {
      name: 'Ollama', cloud: false,
      note: zh ? '本機 / 自架：填 Base URL（如 http://localhost:11434），可選 Bearer Token。模型在你自己的機器上跑，資料不外傳。' : 'Local / self-hosted: enter a Base URL (e.g. http://localhost:11434) with optional Bearer token. Models run on your own machine — nothing leaves it.',
    },
  ];

  const providerSteps = [
    zh ? '選擇供應商（OpenAI / Anthropic / Gemini / Ollama）' : 'Pick a provider (OpenAI / Anthropic / Gemini / Ollama)',
    zh ? '填入 API 金鑰；Ollama 則填 Base URL' : 'Paste the API key; for Ollama enter the Base URL',
    zh ? '點「驗證金鑰並載入模型」' : 'Click "Test & Load Models"',
    zh ? '選擇預設對話模型，然後儲存設定' : 'Choose a default chat model, then save',
  ];

  const mcpSteps = [
    {
      title: zh ? '產生 API 金鑰' : 'Generate an API key',
      desc: zh
        ? '進入「工作區設定 → API Keys」，輸入名稱、選擇權限 scope，建立後複製金鑰（mt_… 開頭，只顯示一次）。'
        : 'Go to Workspace Settings → API Keys, name it, pick a scope, then copy the key (starts with mt_…, shown only once).',
    },
    {
      title: zh ? '在 agent 設定 MCP server' : 'Configure the MCP server in your agent',
      desc: zh
        ? '在 Claude Code / Cursor 等工具加入下方的 MCP server 設定，把金鑰放進 Authorization 標頭。'
        : 'Add the MCP server config below in Claude Code / Cursor, putting the key in the Authorization header.',
    },
    {
      title: zh ? '（選用）開啟 MCP 攝入' : '(Optional) Enable MCP ingestion',
      desc: zh
        ? '若要讓 agent 直接把文件寫入此工作區，在「工作區設定」開啟「MCP 攝入」並設定每日額度。'
        : 'To let agents ingest documents directly, enable "MCP Ingestion" in Workspace Settings and set a daily quota.',
    },
  ];

  const scopes = [
    { scope: 'kb:read', desc: zh ? '唯讀：搜尋、讀取節點' : 'Read-only: search and retrieve nodes' },
    { scope: 'kb:propose', desc: zh ? '可提案：新增節點須經審核佇列' : 'Propose: new nodes go to the review queue' },
    { scope: 'kb:write', desc: zh ? '完整寫入：直接新增 / 修改節點' : 'Full write: create and edit nodes directly' },
  ];

  // ── Styles ──────────────────────────────────────────────────────────────
  const card: React.CSSProperties = {
    background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)',
    borderRadius: 12, padding: 16,
  };
  const h2: React.CSSProperties = {
    fontSize: 22, fontWeight: 700, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 10,
  };
  const lead: React.CSSProperties = {
    color: 'var(--text-muted)', lineHeight: 1.7, marginBottom: 24, maxWidth: 680,
  };
  const sectionGap: React.CSSProperties = { marginBottom: 56, scrollMarginTop: 24 };

  return (
    <div style={{ flex: 1, display: 'flex', minHeight: 0, overflow: 'hidden' }}>
      {/* ── Table of contents ── */}
      <nav
        style={{
          width: 232, flexShrink: 0, borderRight: '1px solid var(--border-subtle)',
          padding: '32px 16px', overflowY: 'auto',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0 12px 16px', color: 'var(--color-primary)' }}>
          <BookOpen size={18} />
          <span style={{ fontWeight: 700, fontSize: 14 }}>{zh ? '使用說明' : 'Guide'}</span>
        </div>
        {SECTIONS.map(s => {
          const active = activeId === s.id;
          return (
            <button
              key={s.id}
              onClick={() => goTo(s.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 10, width: '100%',
                padding: '9px 12px', marginBottom: 2, borderRadius: 8, border: 'none',
                cursor: 'pointer', textAlign: 'left', fontSize: 13,
                background: active ? 'var(--color-primary-subtle)' : 'transparent',
                color: active ? 'var(--color-primary)' : 'var(--text-secondary)',
                fontWeight: active ? 600 : 500, transition: 'all 0.15s',
              }}
            >
              <s.icon size={15} />
              <span>{s.label}</span>
            </button>
          );
        })}
      </nav>

      {/* ── Content ── */}
      <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: '48px 56px' }}>
        <div style={{ maxWidth: 820, margin: '0 auto' }}>

          {/* Intro — start with Why (Golden Circle) */}
          <section id="intro" style={sectionGap}>
            <h2 style={h2}><Target size={22} style={{ color: "var(--color-primary)" }} />{zh ? "先從「為什麼」說起" : "Start with Why"}</h2>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 20 }}>
              {zh ? '（引用 Simon Sinek 的黃金圈：由內而外，Why → How → What）' : "(Framed with Simon Sinek's Golden Circle: from the inside out, Why → How → What)"}
            </div>

            <div style={{ display: "flex", gap: 32, alignItems: "center", flexWrap: "wrap", marginBottom: 8 }}>
              {/* Golden Circle graphic */}
              <div style={{ position: 'relative', width: 188, height: 188, flexShrink: 0, margin: '0 auto' }}>
                <div style={{
                  position: 'absolute', inset: 0, borderRadius: '50%',
                  border: '2px solid var(--border-default)',
                  display: 'flex', alignItems: 'flex-start', justifyContent: 'center', paddingTop: 7,
                }}>
                  <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: 1, color: 'var(--text-muted)' }}>WHAT</span>
                </div>
                <div style={{
                  position: 'absolute', inset: 34, borderRadius: '50%',
                  border: '2px solid var(--color-primary)',
                  display: 'flex', alignItems: 'flex-start', justifyContent: 'center', paddingTop: 6,
                }}>
                  <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: 1, color: 'var(--color-primary)' }}>HOW</span>
                </div>
                <div style={{
                  position: 'absolute', inset: 66, borderRadius: '50%',
                  background: 'var(--color-primary)', color: 'var(--text-on-primary, #fff)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <span style={{ fontSize: 12, fontWeight: 800, letterSpacing: 1 }}>WHY</span>
                </div>
              </div>

              {/* Three layers */}
              <div style={{ flex: 1, minWidth: 280, display: 'flex', flexDirection: 'column', gap: 12 }}>
                {goldenCircle.map(g => (
                  <div key={g.ring} style={{ ...card, display: 'flex', gap: 14, alignItems: 'flex-start' }}>
                    <div style={{
                      flexShrink: 0, minWidth: 52, height: 24, borderRadius: 12, padding: '0 10px',
                      background: g.ring === 'WHY' ? 'var(--color-primary)' : 'var(--color-primary-subtle)',
                      color: g.ring === 'WHY' ? 'var(--text-on-primary, #fff)' : 'var(--color-primary)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 10, fontWeight: 800, letterSpacing: 0.5,
                    }}>
                      {g.ring}
                    </div>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 4 }}>
                        <span style={{ color: 'var(--color-primary)' }}>{g.label}</span>
                        <span style={{ color: 'var(--text-muted)', margin: '0 6px' }}>·</span>
                        {g.headline}
                      </div>
                      <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{g.text}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </section>

          {/* Living */}
          <section id="living" style={sectionGap}>
            <h2 style={h2}><Sparkles size={22} style={{ color: 'var(--color-primary)' }} />{zh ? '為什麼說它是「活的」？' : 'Why is it "living"?'}</h2>
            <p style={lead}>
              {zh
                ? 'MemTrace 和靜態文件最大的差別，是知識會自己變化。以下幾個情境就是「活」的具體展現：'
                : 'The big difference from static docs is that the knowledge changes on its own. These scenarios show what "living" means in practice:'}
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {scenarios.map(s => (
                <div key={s.title} style={{ ...card, display: 'flex', gap: 16, alignItems: 'flex-start' }}>
                  <div style={{
                    flexShrink: 0, width: 40, height: 40, borderRadius: 10,
                    background: 'var(--color-primary-subtle)', color: 'var(--color-primary)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    <s.icon size={20} />
                  </div>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>{s.title}</div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 6 }}>{s.see}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace' }}>{s.how}</div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Getting started */}
          <section id="start" style={sectionGap}>
            <h2 style={h2}><Rocket size={22} style={{ color: 'var(--color-primary)' }} />{zh ? '怎麼開始使用？' : 'How to get started'}</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {steps.map((s, i) => (
                <div key={s.title} style={{ ...card, display: 'flex', gap: 16, alignItems: 'flex-start' }}>
                  <div style={{
                    flexShrink: 0, width: 28, height: 28, borderRadius: '50%',
                    background: 'var(--color-primary)', color: 'var(--text-on-primary, #fff)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontWeight: 700, fontSize: 13,
                  }}>
                    {i + 1}
                  </div>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>{s.title}</div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{s.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Concepts */}
          <section id="concepts" style={sectionGap}>
            <h2 style={h2}><Boxes size={22} style={{ color: 'var(--color-primary)' }} />{zh ? '核心概念' : 'Core concepts'}</h2>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              {concepts.map(c => (
                <div key={c.term} style={card}>
                  <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 8 }}>
                    {c.term === 'Memory Node' || c.term.startsWith('記憶節點') ? <Database size={14} style={{ color: 'var(--color-primary)' }} /> :
                     c.term === 'Typed Edge' || c.term.startsWith('關聯邊') ? <GitMerge size={14} style={{ color: 'var(--color-primary)' }} /> :
                     c.term === 'Trust Score' || c.term.startsWith('信任分數') ? <ShieldCheck size={14} style={{ color: 'var(--color-primary)' }} /> :
                     c.term === 'Review Queue' || c.term.startsWith('審核佇列') ? <ShieldCheck size={14} style={{ color: 'var(--color-primary)' }} /> :
                     <HelpCircle size={14} style={{ color: 'var(--color-primary)' }} />}
                    {c.term}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.55 }}>{c.def}</div>
                </div>
              ))}
            </div>
          </section>

          {/* LLM providers — bring your own model */}
          <section id="providers" style={sectionGap}>
            <h2 style={h2}><Cpu size={22} style={{ color: 'var(--color-primary)' }} />{zh ? '怎麼把大模型加進來？' : 'Adding an LLM'}</h2>
            <p style={lead}>
              {zh
                ? 'MemTrace 的對話、文件拆解與語意向量都需要一個大模型來驅動。你可以接上自己的模型供應商——金鑰只存在本機，不會上傳。'
                : 'MemTrace’s chat, document extraction, and embeddings are all powered by an LLM. Bring your own provider — keys are stored locally and never uploaded.'}
            </p>

            <div style={{
              ...card, display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16,
              background: 'var(--color-primary-subtle)', borderColor: 'var(--color-primary)',
            }}>
              <KeyRound size={16} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
              <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                {zh ? '設定位置：右上角帳號 → 個人設定 →「AI 模型供應商」。' : 'Where: top-right account → Personal Settings → "AI Providers".'}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 20 }}>
              {providers.map(p => (
                <div key={p.name} style={card}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <span style={{ fontWeight: 700, fontSize: 14 }}>{p.name}</span>
                    <span style={{
                      display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 10, fontWeight: 700,
                      padding: '2px 8px', borderRadius: 10,
                      background: p.cloud ? 'var(--bg-base)' : 'var(--color-primary-subtle)',
                      color: p.cloud ? 'var(--text-muted)' : 'var(--color-primary)',
                    }}>
                      {p.cloud ? <Cloud size={11} /> : <HardDrive size={11} />}
                      {p.cloud ? (zh ? '雲端' : 'Cloud') : (zh ? '本機' : 'Local')}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.55 }}>{p.note}</div>
                </div>
              ))}
            </div>

            <div style={card}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>{zh ? '設定步驟' : 'Setup steps'}</div>
              <ol style={{ margin: 0, paddingLeft: 20, fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.9 }}>
                {providerSteps.map((s, i) => <li key={i}>{s}</li>)}
              </ol>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border-subtle)' }}>
                {zh
                  ? '提示：向量（embedding）模型會在建立知識庫時鎖定，建議在建庫前先設定好供應商。'
                  : 'Tip: the embedding model is locked when a KB is created, so set up your provider before creating one.'}
              </div>
            </div>
          </section>

          {/* Connect an agent via MCP */}
          <section id="agents" style={sectionGap}>
            <h2 style={h2}><Bot size={22} style={{ color: 'var(--color-primary)' }} />{zh ? '怎麼把 AI 助手接上 MCP？' : 'Connecting an agent via MCP'}</h2>
            <p style={lead}>
              {zh
                ? '這和上一節相反：上一節是 MemTrace 去呼叫大模型，這一節是讓外部 AI 助手（Claude Code、Cursor…）把 MemTrace 當成共享長期記憶來讀寫。連線後 agent 在握手當下就會收到一段使用指引。'
                : 'This is the reverse of the previous section: there MemTrace calls an LLM; here an external agent (Claude Code, Cursor…) uses MemTrace as shared long-term memory. On connect, the agent receives usage instructions at handshake.'}
            </p>

            {/* Steps */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 16 }}>
              {mcpSteps.map((s, i) => (
                <div key={s.title} style={{ ...card, display: 'flex', gap: 16, alignItems: 'flex-start' }}>
                  <div style={{
                    flexShrink: 0, width: 28, height: 28, borderRadius: '50%',
                    background: 'var(--color-primary)', color: 'var(--text-on-primary, #fff)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontWeight: 700, fontSize: 13,
                  }}>
                    {i + 1}
                  </div>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>{s.title}</div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{s.desc}</div>
                  </div>
                </div>
              ))}
            </div>

            {/* Scopes */}
            <div style={{ ...card, marginBottom: 16 }}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 8 }}>
                <ShieldCheck size={15} style={{ color: 'var(--color-primary)' }} />
                {zh ? '金鑰權限 (scope)' : 'Key scopes'}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {scopes.map(s => (
                  <div key={s.scope} style={{ display: 'flex', gap: 12, alignItems: 'baseline' }}>
                    <code style={{ fontSize: 12, fontWeight: 700, color: 'var(--color-primary)', minWidth: 92 }}>{s.scope}</code>
                    <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{s.desc}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Config */}
            <div style={{ ...card, marginBottom: 16 }}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>{zh ? 'MCP server 設定範例' : 'MCP server config'}</div>
              <pre style={{
                background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', borderRadius: 8,
                padding: 14, fontSize: 12, overflowX: 'auto', margin: 0, lineHeight: 1.5,
              }}>{`{
  "mcpServers": {
    "memtrace": {
      "type": "sse",
      "url": "https://<your-host>/sse",
      "headers": { "Authorization": "Bearer mt_..." }
    }
  }
}`}</pre>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 10 }}>
                {zh
                  ? '較新的 client（如 Cursor、Antigravity）也支援 Streamable HTTP：把 type 設為 http、url 指向 /mcp 即可。'
                  : 'Newer clients (Cursor, Antigravity) also support Streamable HTTP: set type to http and point the url at /mcp.'}
              </div>
            </div>

            {/* Etiquette */}
            <div style={card}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>{zh ? 'Agent 行為準則（連線時自動告知）' : 'Agent etiquette (told automatically on connect)'}</div>
              <ul style={{ margin: 0, paddingLeft: 20, fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.8 }}>
                <li>{zh ? '建立前先 search，避免重複、先看既有脈絡' : 'Search before creating — avoid duplicates, surface context'}</li>
                <li>{zh ? '沿 typed edge 遍歷，建立完整上下文' : 'Traverse typed edges to build full context'}</li>
                <li>{zh ? '提案會進審核佇列（除非持有寫入權限）' : 'Proposals enter the review queue unless write scope is held'}</li>
                <li>{zh ? '開放問題寫成 inquiry 節點，答到後以 answered_by 收斂' : 'Log open questions as inquiry nodes; close with answered_by'}</li>
                <li>{zh ? '附上 tags 與來源，方便人工驗證' : 'Include tags and provenance for human verification'}</li>
              </ul>
            </div>
          </section>

          {/* Full spec CTA */}
          <section id="spec" style={{ ...sectionGap, marginBottom: 24 }}>
            <h2 style={h2}><BookOpen size={22} style={{ color: 'var(--color-primary)' }} />{zh ? '想看完整規格？' : 'Want the full spec?'}</h2>
            <div style={{
              background: 'var(--color-primary-subtle)', border: '1px solid var(--color-primary)',
              borderRadius: 16, padding: 24, display: 'flex', gap: 18, alignItems: 'flex-start',
            }}>
              <Database size={28} style={{ color: 'var(--color-primary)', flexShrink: 0, marginTop: 2 }} />
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--color-primary)', marginBottom: 6 }}>
                  {zh ? 'MemTrace 規格知識庫' : 'MemTrace Spec KB'}
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 14 }}>
                  {zh
                    ? 'MemTrace 把自己的完整規格放在一個公開的知識庫裡——也就是用 MemTrace 本身來記錄 MemTrace。想深入每個欄位、機制與設計決策，直接進去探索這個「活」的文件。'
                    : 'MemTrace keeps its own complete spec inside a public knowledge base — MemTrace documenting MemTrace. To dig into every field, mechanism, and design decision, explore this living documentation directly.'}
                </div>
                <button
                  type="button"
                  onClick={onOpenSpecKb}
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: 8,
                    padding: '9px 18px', borderRadius: 8, border: 'none', cursor: 'pointer',
                    background: 'var(--color-primary)', color: 'var(--text-on-primary, #fff)',
                    fontSize: 13, fontWeight: 600,
                  }}
                >
                  {zh ? '前往規格知識庫' : 'Open the Spec KB'}
                  <ArrowRight size={15} />
                </button>
              </div>
            </div>
          </section>

        </div>
      </div>
    </div>
  );
}
