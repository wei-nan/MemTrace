/**
 * Localized labels for notification categories/severities.
 * The DB stores a baked title for API consumers; the UI renders a localized
 * title from the structured (source_type/category/severity) fields instead.
 */
import type { NotificationItem } from '../api';

const CATEGORY_LABELS: Record<string, { zh: string; en: string }> = {
  // integrity_auditor
  null_updated_at: { zh: '節點缺少更新時間', en: 'Node missing updated_at' },
  null_created_at: { zh: '節點缺少建立時間', en: 'Node missing created_at' },
  missing_embedding: { zh: '節點缺少向量', en: 'Node missing embedding' },
  missing_provenance: { zh: '節點缺少來源/簽章', en: 'Node missing provenance' },
  // secret_scanner
  leaked_secret: { zh: '疑似密鑰/憑證外洩', en: 'Possible secret leak' },
  // safety_queue
  async_safety: { zh: '安全審查標記', en: 'Safety review flag' },
  safety_undetermined: { zh: '安全檢查未完成（已收錄未驗證）', en: 'Safety check undetermined' },
  // contradiction_detector
  contradiction: { zh: '與既有知識矛盾', en: 'Contradicts existing node' },
  // deduper
  duplicate: { zh: '重複節點', en: 'Duplicate node' },
  // tag_normalizer
  tag_too_long: { zh: '標籤過長', en: 'Tag too long' },
  tag_orphan: { zh: '孤兒標籤', en: 'Orphan tag' },
  // edge_auditor
  dangling_edge: { zh: '懸空連結', en: 'Dangling edge' },
  duplicate_edge: { zh: '重複連結', en: 'Duplicate edge' },
  reversed_answered_by: { zh: 'answered_by 方向疑似寫反', en: 'Reversed answered_by edge' },
  resolution_drift: { zh: '結案狀態未同步', en: 'Resolution status drift' },
  // embedding_consistency
  embedding_drift: { zh: '向量可能已過期', en: 'Embedding may be stale' },
  // trust_calibrator
  trust_overrated: { zh: '信任分數偏高', en: 'Trust score overrated' },
  trust_underrated: { zh: '信任分數偏低', en: 'Trust score underrated' },
  // coverage_gap_detector
  stale_gap: { zh: '長期未補的缺口', en: 'Stale knowledge gap' },
  // source_decay_monitor
  stale_url: { zh: '來源連結可能失效', en: 'Stale source URL' },
  // safety_sweep
  historical_safety: { zh: '歷史安全掃描標記', en: 'Historical safety flag' },
  // realtime safety (create_node path)
  realtime_safety: { zh: '即時安全審查', en: 'Realtime safety review' },
  // consult escalation
  consult_escalation: { zh: '診斷提案待審', en: 'Consult proposal pending review' },
  // review_queue change_types
  create: { zh: '新增節點提案待審', en: 'New node proposal' },
  update: { zh: '更新提案待審', en: 'Update proposal' },
  delete: { zh: '刪除提案待審', en: 'Delete proposal' },
  create_edge: { zh: '連結提案待審', en: 'Edge proposal' },
  split_suggestion: { zh: '節點拆分建議待審', en: 'Split suggestion' },
};

const SEVERITY_LABELS: Record<string, { zh: string; en: string }> = {
  high: { zh: '高', en: 'High' },
  mid: { zh: '中', en: 'Mid' },
  low: { zh: '低', en: 'Low' },
  review: { zh: '待審', en: 'Review' },
};

/**
 * Static body templates for categories whose reasoning is a fixed string.
 * Categories with dynamic runtime values (classification names, node titles, etc.)
 * are omitted — the caller falls back to the stored n.body in those cases.
 */
const BODY_TEMPLATES: Record<string, { zh: string; en: string }> = {
  realtime_safety: {
    zh: 'AI/MCP 非程序性節點非同步安全審查，請確認內容符合安全規範。',
    en: 'Async safety review for ai/mcp non-procedural node.',
  },
  safety_undetermined: {
    zh: '安全檢查無法執行（AI 提供者不可用），節點已收錄但未完成安全驗證。',
    en: 'Safety check could not run (provider unavailable); node admitted WITHOUT a safety verdict.',
  },
  consult_escalation: {
    zh: '故障診斷已產生新提案，等待人工審核。',
    en: 'Troubleshooting consult generated a new recommendation pending review.',
  },
};

/** Localized human title for a notification, derived from its category. */
export function notificationTitle(n: NotificationItem, zh: boolean): string {
  const entry = n.category ? CATEGORY_LABELS[n.category] : undefined;
  if (entry) return zh ? entry.zh : entry.en;
  return n.category ?? n.title;
}

export function severityLabel(severity: string | null, zh: boolean): string {
  if (!severity) return '';
  const entry = SEVERITY_LABELS[severity];
  return entry ? (zh ? entry.zh : entry.en) : severity;
}

/**
 * Localized body text for a notification.
 * Uses a static template when available (for deterministic reasoning strings);
 * falls back to the stored body for categories with dynamic runtime values
 * (e.g. async_safety, historical_safety, contradiction — contain node names / classifications).
 */
export function notificationBody(n: NotificationItem, zh: boolean): string | null {
  if (n.category) {
    const tpl = BODY_TEMPLATES[n.category];
    if (tpl) return zh ? tpl.zh : tpl.en;
  }
  return n.body ?? null;
}

export function severityColor(severity: string | null): string {
  switch (severity) {
    case 'high': return '#ef4444';
    case 'mid': return '#f59e0b';
    case 'review': return '#3b82f6';
    default: return 'var(--text-muted)';
  }
}
