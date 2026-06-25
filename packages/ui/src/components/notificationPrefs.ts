/**
 * Notification preferences — group toggles persisted to the database (users.notification_preferences).
 * localStorage is used as a synchronous cache so the UI renders immediately on mount
 * before the async API response arrives.
 *
 * DB schema: { disabled_groups: string[] }
 * Default (empty or missing key) = all groups enabled.
 */
import type { NotificationItem } from '../api';
import { auth as authApi } from '../api';

export interface NotifGroup {
  key: string;
  label: { zh: string; en: string };
  description: { zh: string; en: string };
  categories: string[];
}

export const NOTIF_GROUPS: NotifGroup[] = [
  {
    key: 'review',
    label: { zh: '審核提案', en: 'Review proposals' },
    description: { zh: '節點新增／更新／刪除／連結的人工審核提案', en: 'Create / update / delete / edge proposals awaiting review' },
    categories: ['create', 'update', 'delete', 'create_edge', 'split_suggestion'],
  },
  {
    key: 'security',
    label: { zh: '安全警告', en: 'Security alerts' },
    description: { zh: '密鑰外洩、安全審查標記', en: 'Secret leaks and safety review flags' },
    categories: ['leaked_secret', 'async_safety', 'safety_undetermined', 'historical_safety'],
  },
  {
    key: 'integrity',
    label: { zh: '資料完整性', en: 'Data integrity' },
    description: { zh: '節點缺少時間戳、向量、來源簽章', en: 'Nodes missing timestamps, embeddings, or provenance' },
    categories: ['null_updated_at', 'null_created_at', 'missing_embedding', 'missing_provenance'],
  },
  {
    key: 'contradiction',
    label: { zh: '矛盾與重複', en: 'Contradictions & duplicates' },
    description: { zh: '內容與既有知識矛盾，或發現重複節點', en: 'Content contradicts existing nodes or duplicates found' },
    categories: ['contradiction', 'duplicate'],
  },
  {
    key: 'graph',
    label: { zh: '圖結構', en: 'Graph structure' },
    description: { zh: '懸空連結、重複邊、方向錯誤、結案狀態漂移', en: 'Dangling edges, duplicates, reversed relations, resolution drift' },
    categories: ['dangling_edge', 'duplicate_edge', 'reversed_answered_by', 'resolution_drift'],
  },
  {
    key: 'trust',
    label: { zh: '信任與向量', en: 'Trust & embeddings' },
    description: { zh: '信任分數偏高／偏低、向量可能已過期', en: 'Trust score drift or stale embeddings' },
    categories: ['trust_overrated', 'trust_underrated', 'embedding_drift'],
  },
  {
    key: 'meta',
    label: { zh: '標籤與來源', en: 'Tags & URLs' },
    description: { zh: '標籤過長／孤兒標籤、來源連結失效', en: 'Tag issues or stale source URLs' },
    categories: ['tag_too_long', 'tag_orphan', 'stale_url'],
  },
  {
    key: 'gap',
    label: { zh: '知識缺口', en: 'Knowledge gaps' },
    description: { zh: '長期未補充的知識缺口', en: 'Long-standing uncovered knowledge gaps' },
    categories: ['stale_gap'],
  },
];

// ── localStorage cache (synchronous, used as initial render state) ────────────
const CACHE_KEY = 'mt_notif_prefs_cache';

function readCache(): Set<string> {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return new Set();
    const parsed = JSON.parse(raw);
    return new Set(Array.isArray(parsed) ? parsed : []);
  } catch {
    return new Set();
  }
}

function writeCache(disabled: Set<string>): void {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify([...disabled]));
  } catch {
    // ignore quota errors
  }
}

// ── API-backed load / save ────────────────────────────────────────────────────

/** Load from DB. Returns the disabled group Set. Falls back to empty on error. */
export async function loadPrefsFromDB(): Promise<Set<string>> {
  try {
    const data = await authApi.getNotificationPreferences();
    const disabled = new Set<string>(Array.isArray(data.disabled_groups) ? data.disabled_groups : []);
    writeCache(disabled);
    return disabled;
  } catch {
    return readCache();
  }
}

/** Save to DB and update cache. Optimistic — fire-and-forget is fine here. */
export async function savePrefsToDb(disabled: Set<string>): Promise<void> {
  writeCache(disabled);
  await authApi.updateNotificationPreferences({ disabled_groups: [...disabled] });
}

/** Synchronous initial value from cache — prevents flash on mount. */
export function loadCachedDisabledGroups(): Set<string> {
  return readCache();
}

// ── Filter helper ─────────────────────────────────────────────────────────────

export function isNotifVisible(n: NotificationItem, disabled: Set<string>): boolean {
  if (disabled.size === 0) return true;
  if (!n.category) return true;
  for (const g of NOTIF_GROUPS) {
    if (g.categories.includes(n.category) && disabled.has(g.key)) return false;
  }
  return true;
}
