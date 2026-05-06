import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Search, ChevronLeft, ChevronRight, Edit, Archive, Trash2, 
  ArrowUpDown, ArrowUp, ArrowDown, CheckSquare, Square, X
} from 'lucide-react';
import { workspaces, nodes as nodesApi, type Node as ApiNode } from './api';
import { useModal } from './components/ModalContext';

interface Props {
  wsId: string;
  onEditNode: (node: ApiNode) => void;
  isAdmin?: boolean;
  initialFilter?: string;
}

type SortField = 'title' | 'content_type' | 'trust_score' | 'created_at';
type SortOrder = 'asc' | 'desc';

export default function TableView({ wsId, onEditNode, isAdmin, initialFilter }: Props) {
  const { t, i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const { confirm, toast } = useModal();

  const [nodes, setNodes] = useState<ApiNode[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Params
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);
  const [sortBy, setSortBy] = useState<SortField>('created_at');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [filter, setFilter] = useState<string | undefined>(initialFilter);

  // Selection
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), 300);
    return () => clearTimeout(timer);
  }, [query]);

  const load = useCallback(async () => {
    if (!wsId) return;
    setLoading(true);
    setError('');
    try {
      const res = await workspaces.tableView(wsId, {
        q: debouncedQuery,
        filter,
        limit,
        offset,
        sort_by: sortBy,
        order: sortOrder,
      });
      // Filter out source_document as requested
      const filteredNodes = res.nodes.filter(n => n.content_type !== 'source_document');
      setNodes(filteredNodes);
      setTotalCount(res.total_count);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [wsId, debouncedQuery, limit, offset, sortBy, sortOrder]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (initialFilter) {
      setFilter(initialFilter);
      setOffset(0);
    }
  }, [initialFilter]);

  const toggleSort = (field: SortField) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('asc');
    }
  };

  const handleArchive = async (node: ApiNode) => {
    const ok = await confirm({
      title: zh ? '歸檔節點' : 'Archive Node',
      message: zh ? `確定要歸檔「${zh ? node.title_zh : node.title_en}」嗎？` : `Archive "${zh ? node.title_zh : node.title_en}"?`,
      confirmLabel: zh ? '歸檔' : 'Archive',
    });
    if (!ok) return;
    try {
      await nodesApi.archive(wsId, node.id);
      toast({ message: zh ? '已歸檔' : 'Archived', variant: 'success' });
      load();
    } catch (e: any) {
      toast({ message: e.message, variant: 'error' });
    }
  };

  const handleBulkArchive = async () => {
    if (selectedIds.size === 0) return;
    const ok = await confirm({
      title: zh ? '批量歸檔' : 'Bulk Archive',
      message: zh ? `確定要歸檔選中的 ${selectedIds.size} 個節點嗎？` : `Archive ${selectedIds.size} selected nodes?`,
      confirmLabel: zh ? '歸檔' : 'Archive',
    });
    if (!ok) return;
    try {
      await nodesApi.bulkArchive(wsId, Array.from(selectedIds));
      toast({ message: zh ? '已歸檔' : 'Archived', variant: 'success' });
      setSelectedIds(new Set());
      load();
    } catch (e: any) {
      toast({ message: e.message, variant: 'error' });
    }
  };

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return;
    const ok = await confirm({
      title: zh ? '批量刪除' : 'Bulk Delete',
      message: zh ? `確定要刪除選中的 ${selectedIds.size} 個節點嗎？此操作無法還原。` : `Delete ${selectedIds.size} selected nodes? This cannot be undone.`,
      variant: 'danger',
      confirmLabel: zh ? '刪除' : 'Delete',
    });
    if (!ok) return;
    try {
      await nodesApi.bulkDelete(wsId, Array.from(selectedIds));
      toast({ message: zh ? '已刪除' : 'Deleted', variant: 'success' });
      setSelectedIds(new Set());
      load();
    } catch (e: any) {
      toast({ message: e.message, variant: 'error' });
    }
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === nodes.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(nodes.map(n => n.id)));
    }
  };

  const toggleSelect = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedIds(next);
  };

  const renderSortIcon = (field: SortField) => {
    if (sortBy !== field) return <ArrowUpDown size={14} style={{ opacity: 0.3 }} />;
    return sortOrder === 'asc' ? <ArrowUp size={14} /> : <ArrowDown size={14} />;
  };

  return (
    <div className="table-view-container animate-fade-in" style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, padding: '0 40px 40px' }}>
      
      {/* Toolbar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, gap: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div className="search-bar" style={{ width: 320 }}>
            <Search size={16} style={{ color: 'var(--text-muted)', marginLeft: 4 }} />
            <input 
              className="search-input" 
              placeholder={t('table.search_ph')} 
              value={query}
              onChange={e => { setQuery(e.target.value); setOffset(0); }}
            />
          </div>
          {filter && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 12px', background: 'var(--color-primary-subtle)', border: '1px solid var(--color-primary)', borderRadius: 8, fontSize: 13, color: 'var(--color-primary)' }}>
              <span>{t('table.filter')}: {filter}</span>
              <button className="btn-ghost" onClick={() => setFilter(undefined)} style={{ padding: 0, color: 'var(--color-primary)' }}>
                <X size={14} />
              </button>
            </div>
          )}
          {selectedIds.size > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 12px', background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: 8, fontSize: 13 }}>
              <span style={{ color: 'var(--text-muted)' }}>{t('table.items_selected', { count: selectedIds.size })}</span>
              <button className="btn-ghost" onClick={handleBulkArchive} style={{ padding: '4px 8px', color: 'var(--color-primary)' }}>
                <Archive size={14} style={{ marginRight: 4 }} />
                {t('table.archive')}
              </button>
              {isAdmin && (
                <button className="btn-ghost" onClick={handleBulkDelete} style={{ padding: '4px 8px', color: 'var(--color-error)' }}>
                  <Trash2 size={14} style={{ marginRight: 4 }} />
                  {t('common.delete')}
                </button>
              )}
            </div>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-muted)' }}>
            <span>{t('table.show')}</span>
            <select 
              className="mt-input" 
              style={{ padding: '4px 8px', height: 'auto' }}
              value={limit}
              onChange={e => { setLimit(Number(e.target.value)); setOffset(0); }}
            >
              {[25, 50, 100].map(v => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <button 
              className="btn-secondary" 
              style={{ padding: 6 }} 
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - limit))}
            >
              <ChevronLeft size={18} />
            </button>
            <span style={{ fontSize: 13, minWidth: 80, textAlign: 'center' }}>
              {t('table.page', { page: Math.floor(offset / limit) + 1 })}
            </span>
            <button 
              className="btn-secondary" 
              style={{ padding: 6 }}
              disabled={offset + limit >= totalCount}
              onClick={() => setOffset(offset + limit)}
            >
              <ChevronRight size={18} />
            </button>
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            {t('table.total', { count: totalCount })}
          </div>
        </div>
      </div>

      {/* Table */}
      <div style={{ flex: 1, overflow: 'auto', background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: 12, boxShadow: 'var(--shadow-sm)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 14 }}>
          <thead style={{ position: 'sticky', top: 0, background: 'var(--bg-surface)', zIndex: 1, borderBottom: '1px solid var(--border-default)' }}>
            <tr>
              <th style={{ padding: '12px 16px', width: 40 }}>
                <button onClick={toggleSelectAll} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-primary)', display: 'flex', alignItems: 'center' }}>
                  {selectedIds.size === nodes.length && nodes.length > 0 ? <CheckSquare size={18} /> : <Square size={18} />}
                </button>
              </th>
              <th onClick={() => toggleSort('title')} style={{ padding: '12px 16px', cursor: 'pointer', userSelect: 'none' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  {t('table.title')}
                  {renderSortIcon('title')}
                </div>
              </th>
              <th onClick={() => toggleSort('content_type')} style={{ padding: '12px 16px', cursor: 'pointer', userSelect: 'none', width: 140 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  {t('table.type')}
                  {renderSortIcon('content_type')}
                </div>
              </th>
              <th style={{ padding: '12px 16px', width: 200 }}>{t('table.tags')}</th>
              <th onClick={() => toggleSort('trust_score')} style={{ padding: '12px 16px', cursor: 'pointer', userSelect: 'none', width: 150 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  {t('table.trust')}
                  {renderSortIcon('trust_score')}
                </div>
              </th>
              <th onClick={() => toggleSort('created_at')} style={{ padding: '12px 16px', cursor: 'pointer', userSelect: 'none', width: 160 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  {t('table.created')}
                  {renderSortIcon('created_at')}
                </div>
              </th>
              <th style={{ padding: '12px 16px', width: 100, textAlign: 'right' }}>{t('table.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
                  {zh ? '載入中…' : 'Loading…'}
                </td>
              </tr>
            ) : nodes.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
                  {error ? `Error: ${error}` : (zh ? '尚無節點' : 'No nodes found')}
                </td>
              </tr>
            ) : nodes.map(node => (
              <tr key={node.id} style={{ borderBottom: '1px solid var(--border-subtle)', transition: 'background 0.15s' }} className="table-row-hover">
                <td style={{ padding: '12px 16px' }}>
                  <button onClick={() => toggleSelect(node.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: selectedIds.has(node.id) ? 'var(--color-primary)' : 'var(--text-muted)' }}>
                    {selectedIds.has(node.id) ? <CheckSquare size={18} /> : <Square size={18} />}
                  </button>
                </td>
                <td style={{ padding: '12px 16px', maxWidth: 300 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <div style={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={zh ? node.title_zh : node.title_en}>
                      {zh ? node.title_zh : node.title_en}
                    </div>
                    {!node.body_zh && !node.body_en && (
                      <span title={t('node.empty_body_desc')} style={{ flexShrink: 0, fontSize: 11, padding: '1px 5px', borderRadius: 4, background: 'var(--color-warning-subtle, #fef3c7)', color: 'var(--color-warning, #d97706)', lineHeight: 1.4 }}>
                        {t('node.empty_body_badge')}
                      </span>
                    )}
                  </div>
                </td>
                <td style={{ padding: '12px 16px' }}>
                  <span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 12, background: 'var(--bg-muted)', color: 'var(--text-secondary)' }}>
                    {node.content_type}
                  </span>
                </td>
                <td style={{ padding: '12px 16px' }}>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {node.tags.slice(0, 3).map(t => (
                      <span key={t} style={{ fontSize: 11, color: 'var(--color-primary)', background: 'var(--color-primary-subtle)', padding: '1px 6px', borderRadius: 4 }}>
                        #{t}
                      </span>
                    ))}
                    {node.tags.length > 3 && <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>+{node.tags.length - 3}</span>}
                  </div>
                </td>
                <td style={{ padding: '12px 16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ flex: 1, height: 6, background: 'var(--border-default)', borderRadius: 3, overflow: 'hidden' }}>
                      <div style={{ 
                        height: '100%', 
                        width: `${node.trust_score * 100}%`, 
                        background: node.trust_score > 0.8 ? 'var(--color-success)' : node.trust_score > 0.5 ? 'var(--color-primary)' : 'var(--color-warning)'
                      }} />
                    </div>
                    <span style={{ fontSize: 12, width: 32, textAlign: 'right' }}>{Math.round(node.trust_score * 100)}%</span>
                  </div>
                </td>
                <td style={{ padding: '12px 16px', fontSize: 12, color: 'var(--text-muted)' }}>
                  {new Date(node.created_at).toLocaleDateString()}
                </td>
                <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 4 }}>
                    <button className="btn-ghost" style={{ padding: 6 }} onClick={() => onEditNode(node)} title={t('common.save')}>
                      <Edit size={16} />
                    </button>
                    <button className="btn-ghost" style={{ padding: 6 }} onClick={() => handleArchive(node)} title={t('table.archive')}>
                      <Archive size={16} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
