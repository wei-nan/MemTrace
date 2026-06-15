import { useState, useEffect, useMemo } from 'react';
import { Search, Globe, Lock, BookOpen, ArrowRight } from 'lucide-react';
import { workspaces as wsApi, type ExploreWorkspace, type Workspace } from './api';
import { useTranslation } from 'react-i18next';

interface Props {
  authenticated: boolean;
  onSelectWs: (ws: Workspace) => void;
  onSignIn: () => void;
}

export default function ExplorePage({ authenticated, onSelectWs, onSignIn }: Props) {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';

  const [items, setItems] = useState<ExploreWorkspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState('');
  const [lang, setLang] = useState<'all' | 'zh-TW' | 'en'>('all');
  const [sort, setSort] = useState<'newest' | 'nodes'>('newest');

  useEffect(() => {
    setLoading(true);
    wsApi.explore({ sort })
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [sort]);

  const filtered = useMemo(() => {
    let list = items;
    if (q.trim()) {
      const lower = q.toLowerCase();
      list = list.filter(w =>
        w.name.toLowerCase().includes(lower) ||
        (w.description || '').toLowerCase().includes(lower)
      );
    }
    if (lang !== 'all') {
      list = list.filter(w => w.language === lang);
    }
    return list;
  }, [items, q, lang]);

  const myKBs = filtered.filter(w => w.my_role !== null);
  const publicKBs = filtered.filter(w => w.my_role === null);

  const visIcon = (v: string) =>
    v === 'public' || v === 'conditional_public'
      ? <Globe size={12} style={{ color: 'var(--color-primary)' }} />
      : <Lock size={12} style={{ color: 'var(--text-muted)' }} />;

  const langLabel = (l: string) =>
    l === 'zh-TW' ? '繁中' : 'EN';

  const handleSelect = (item: ExploreWorkspace) => {
    onSelectWs(item as unknown as Workspace);
  };

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '40px 48px', maxWidth: 1100, margin: '0 auto', width: '100%' }}>

      {/* Hero */}
      <div style={{ marginBottom: 40 }}>
        <h1 style={{ fontSize: 28, fontWeight: 800, color: 'var(--text-primary)', marginBottom: 8 }}>
          {zh ? '探索知識庫' : 'Explore Knowledge Bases'}
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: 15 }}>
          {zh
            ? '瀏覽公開與個人知識庫，點擊即可切換'
            : 'Browse public and personal knowledge bases — click to switch'}
        </p>
      </div>

      {/* Search + Filters */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 36, flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: '1 1 280px', minWidth: 200 }}>
          <Search size={15} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }} />
          <input
            className="mt-input"
            style={{ paddingLeft: 38, width: '100%', boxSizing: 'border-box' }}
            placeholder={zh ? '搜尋名稱或描述…' : 'Search name or description…'}
            value={q}
            onChange={e => setQ(e.target.value)}
          />
        </div>

        <div style={{ display: 'flex', gap: 6 }}>
          {(['all', 'zh-TW', 'en'] as const).map(l => (
            <button
              key={l}
              onClick={() => setLang(l)}
              style={{
                padding: '0 14px', height: 38, borderRadius: 8, border: '1px solid var(--border-default)',
                background: lang === l ? 'var(--color-primary)' : 'var(--bg-elevated)',
                color: lang === l ? 'var(--text-on-primary)' : 'var(--text-secondary)',
                fontSize: 13, fontWeight: 500, cursor: 'pointer',
              }}
            >
              {l === 'all' ? (zh ? '全部' : 'All') : l === 'zh-TW' ? '繁中' : 'EN'}
            </button>
          ))}
        </div>

        <select
          className="mt-input"
          style={{ width: 'auto', minWidth: 130 }}
          value={sort}
          onChange={e => setSort(e.target.value as 'newest' | 'nodes')}
        >
          <option value="newest">{zh ? '最新建立' : 'Newest'}</option>
          <option value="nodes">{zh ? '節點數量' : 'Most nodes'}</option>
        </select>

        {!authenticated && (
          <button
            onClick={onSignIn}
            style={{
              padding: '0 20px', height: 38, borderRadius: 8,
              background: 'var(--color-primary)', color: 'var(--text-on-primary)',
              fontSize: 13, fontWeight: 600, cursor: 'pointer', border: 'none',
            }}
          >
            {zh ? '登入' : 'Sign In'}
          </button>
        )}
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 80, color: 'var(--text-muted)' }}>
          {zh ? '載入中…' : 'Loading…'}
        </div>
      ) : (
        <>
          {/* My KBs */}
          {authenticated && myKBs.length > 0 && (
            <Section title={zh ? '我的知識庫' : 'My Knowledge Bases'} count={myKBs.length}>
              {myKBs.map(item => (
                <KBCard key={item.id} item={item} visIcon={visIcon} langLabel={langLabel} zh={zh} onSelect={handleSelect} />
              ))}
            </Section>
          )}

          {/* Public KBs */}
          <Section
            title={zh ? '公開知識庫' : 'Public Knowledge Bases'}
            count={publicKBs.length}
            style={{ marginTop: authenticated && myKBs.length > 0 ? 40 : 0 }}
          >
            {publicKBs.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: 14, padding: '20px 0' }}>
                {q ? (zh ? '找不到符合的知識庫' : 'No results found') : (zh ? '目前沒有公開知識庫' : 'No public knowledge bases yet')}
              </div>
            ) : (
              publicKBs.map(item => (
                <KBCard key={item.id} item={item} visIcon={visIcon} langLabel={langLabel} zh={zh} onSelect={handleSelect} />
              ))
            )}
          </Section>
        </>
      )}
    </div>
  );
}

function Section({ title, count, children, style }: { title: string; count: number; children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={style}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <h2 style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>{title}</h2>
        <span style={{ fontSize: 12, color: 'var(--text-muted)', background: 'var(--bg-subtle)', padding: '2px 8px', borderRadius: 20 }}>{count}</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
        {children}
      </div>
    </div>
  );
}

function KBCard({ item, visIcon, langLabel, zh, onSelect }: {
  item: ExploreWorkspace;
  visIcon: (v: string) => React.ReactNode;
  langLabel: (l: string) => string;
  zh: boolean;
  onSelect: (item: ExploreWorkspace) => void;
}) {
  return (
    <div
      onClick={() => onSelect(item)}
      className="kb-card"
      style={{
        background: 'var(--bg-elevated)', border: '1px solid var(--border-default)',
        borderRadius: 12, padding: 20, cursor: 'pointer',
        transition: 'all 0.15s',
        display: 'flex', flexDirection: 'column', gap: 10,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
        <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1.3 }}>{item.name}</span>
        <ArrowRight size={16} style={{ color: 'var(--text-muted)', flexShrink: 0, marginTop: 2 }} />
      </div>

      {item.description && (
        <p style={{
          fontSize: 13, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5,
          display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
        }}>
          {item.description}
        </p>
      )}

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginTop: 'auto' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: 'var(--text-muted)' }}>
          {visIcon(item.visibility)}
          {item.visibility === 'public' ? (zh ? '公開' : 'Public') : item.visibility === 'private' ? (zh ? '私人' : 'Private') : item.visibility}
        </span>
        <span style={{ fontSize: 12, color: 'var(--text-muted)', background: 'var(--bg-subtle)', padding: '2px 8px', borderRadius: 20 }}>
          {langLabel(item.language)}
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: 'var(--text-muted)' }}>
          <BookOpen size={12} />
          {item.node_count}
        </span>
        <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 'auto' }}>
          {item.owner_display_name}
        </span>
      </div>
    </div>
  );
}
