import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { BarChart2, MessageSquare, Zap, Database, Brain } from 'lucide-react';
import { ai } from './api/ai';

function fmtTokens(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K';
  return String(n);
}

function fmtDate(s: string): string {
  return new Date(s).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

const FEATURE_LABEL: Record<string, { zh: string; en: string; icon: typeof Zap }> = {
  chat:        { zh: 'AI 對話', en: 'Chat', icon: MessageSquare },
  extraction:  { zh: '節點萃取', en: 'Extraction', icon: Brain },
  embedding:   { zh: '向量嵌入', en: 'Embedding', icon: Database },
  restructure: { zh: '重構', en: 'Restructure', icon: BarChart2 },
};

const CARD_STYLE: React.CSSProperties = {
  background: 'var(--bg-elevated)',
  border: '1px solid var(--border-default)',
  borderRadius: 12,
  padding: '20px 24px',
};

export default function UsagePage() {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';

  const [ledger, setLedger] = useState<Array<{ year_month: string; feature: string; provider: string; token_count: number }>>([]);
  const [sessions, setSessions] = useState<Array<{ id: string; title: string; tokens_total: number; message_count: number; last_active_at: string }>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    ai.getMyUsage().then(data => {
      setLedger(data.ledger);
      setSessions(data.sessions);
    }).finally(() => setLoading(false));
  }, []);

  // Monthly totals (last 6 months)
  const byMonth: Record<string, number> = {};
  for (const row of ledger) {
    byMonth[row.year_month] = (byMonth[row.year_month] ?? 0) + row.token_count;
  }
  const months = Object.keys(byMonth).sort().reverse().slice(0, 6);
  const maxMonthTokens = Math.max(...months.map(m => byMonth[m]), 1);

  // Feature totals (all time)
  const byFeature: Record<string, number> = {};
  for (const row of ledger) {
    byFeature[row.feature] = (byFeature[row.feature] ?? 0) + row.token_count;
  }
  const totalAll = Object.values(byFeature).reduce((a, b) => a + b, 0);

  const thisMonth = months[0] ? byMonth[months[0]] : 0;
  const lastMonth = months[1] ? byMonth[months[1]] : 0;
  const delta = lastMonth > 0 ? Math.round(((thisMonth - lastMonth) / lastMonth) * 100) : null;

  if (loading) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ color: 'var(--text-muted)', fontSize: 14 }}>{zh ? '載入中…' : 'Loading…'}</span>
      </div>
    );
  }

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '40px 24px' }}>
      <div style={{ maxWidth: 860, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 24 }}>

        {/* Title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <BarChart2 size={22} color="var(--color-primary)" />
          <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>
            {zh ? '使用量統計' : 'Usage Statistics'}
          </h2>
        </div>

        {/* Top summary cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 }}>
          <div style={CARD_STYLE}>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>
              {zh ? '本月 Token' : 'This Month'}
            </div>
            <div style={{ fontSize: 28, fontWeight: 700 }}>{fmtTokens(thisMonth)}</div>
            {delta !== null && (
              <div style={{ fontSize: 12, marginTop: 4, color: delta >= 0 ? 'var(--color-warning)' : 'var(--color-success)' }}>
                {delta >= 0 ? '▲' : '▼'} {Math.abs(delta)}% {zh ? '較上月' : 'vs last month'}
              </div>
            )}
          </div>
          <div style={CARD_STYLE}>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>
              {zh ? '累計 Token' : 'All Time'}
            </div>
            <div style={{ fontSize: 28, fontWeight: 700 }}>{fmtTokens(totalAll)}</div>
          </div>
          <div style={CARD_STYLE}>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>
              {zh ? '對話次數（近期）' : 'Recent Sessions'}
            </div>
            <div style={{ fontSize: 28, fontWeight: 700 }}>{sessions.length}</div>
          </div>
        </div>

        {/* Monthly bar chart */}
        {months.length > 0 && (
          <div style={CARD_STYLE}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16 }}>
              {zh ? '每月用量（近 6 個月）' : 'Monthly Usage (Last 6 Months)'}
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12, height: 120 }}>
              {[...months].reverse().map(m => {
                const pct = (byMonth[m] / maxMonthTokens) * 100;
                return (
                  <div key={m} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{fmtTokens(byMonth[m])}</div>
                    <div style={{
                      width: '100%', height: `${Math.max(pct, 4)}%`,
                      background: 'var(--color-primary)', borderRadius: 4, minHeight: 4, transition: 'height 0.3s',
                    }} />
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{m.slice(5)}</div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Feature breakdown */}
        {Object.keys(byFeature).length > 0 && (
          <div style={CARD_STYLE}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16 }}>
              {zh ? '功能分布' : 'By Feature'}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {Object.entries(byFeature).sort((a, b) => b[1] - a[1]).map(([feat, count]) => {
                const meta = FEATURE_LABEL[feat];
                const Icon = meta?.icon ?? Zap;
                const pct = totalAll > 0 ? Math.round((count / totalAll) * 100) : 0;
                return (
                  <div key={feat} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <Icon size={15} color="var(--color-primary)" style={{ flexShrink: 0 }} />
                    <div style={{ width: 90, fontSize: 13, color: 'var(--text-secondary)', flexShrink: 0 }}>
                      {meta ? (zh ? meta.zh : meta.en) : feat}
                    </div>
                    <div style={{ flex: 1, height: 8, background: 'var(--bg-subtle)', borderRadius: 4, overflow: 'hidden' }}>
                      <div style={{ width: `${pct}%`, height: '100%', background: 'var(--color-primary)', borderRadius: 4, transition: 'width 0.3s' }} />
                    </div>
                    <div style={{ width: 60, textAlign: 'right', fontSize: 13, fontWeight: 600 }}>{fmtTokens(count)}</div>
                    <div style={{ width: 34, textAlign: 'right', fontSize: 12, color: 'var(--text-muted)' }}>{pct}%</div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Recent sessions */}
        {sessions.length > 0 && (
          <div style={CARD_STYLE}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16 }}>
              {zh ? '最近對話（依 Token 排序）' : 'Recent Chat Sessions'}
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <th style={{ textAlign: 'left', padding: '6px 0', fontWeight: 600, color: 'var(--text-muted)' }}>
                    {zh ? '標題' : 'Title'}
                  </th>
                  <th style={{ textAlign: 'right', padding: '6px 0', fontWeight: 600, color: 'var(--text-muted)', width: 80 }}>
                    {zh ? '訊息' : 'Msgs'}
                  </th>
                  <th style={{ textAlign: 'right', padding: '6px 0', fontWeight: 600, color: 'var(--text-muted)', width: 80 }}>
                    Token
                  </th>
                  <th style={{ textAlign: 'right', padding: '6px 8px', fontWeight: 600, color: 'var(--text-muted)', width: 130 }}>
                    {zh ? '最後活躍' : 'Last Active'}
                  </th>
                </tr>
              </thead>
              <tbody>
                {[...sessions].sort((a, b) => b.tokens_total - a.tokens_total).map(s => (
                  <tr key={s.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '8px 0', color: 'var(--text-primary)', maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {s.title || (zh ? '（無標題）' : '(Untitled)')}
                    </td>
                    <td style={{ padding: '8px 0', textAlign: 'right', color: 'var(--text-muted)' }}>{s.message_count}</td>
                    <td style={{ padding: '8px 0', textAlign: 'right', fontWeight: 600 }}>{fmtTokens(s.tokens_total)}</td>
                    <td style={{ padding: '8px 8px', textAlign: 'right', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{fmtDate(s.last_active_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {totalAll === 0 && sessions.length === 0 && (
          <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)', fontSize: 14 }}>
            {zh ? '尚無使用紀錄' : 'No usage recorded yet'}
          </div>
        )}
      </div>
    </div>
  );
}
