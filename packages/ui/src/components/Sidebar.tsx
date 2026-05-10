import React from 'react';
import { useTranslation } from 'react-i18next';
import {
  Network, PlusCircle, Globe, ChevronDown, ChevronLeft, ChevronRight,
  GitFork, RefreshCw, AlertTriangle, XCircle, BarChart3, Inbox, Users, FileUp
} from 'lucide-react';
import { type Workspace, type WorkspaceCloneJob, workspaces } from '../api';
import { Button } from './ui';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  selectedWs: Workspace | null;
  onSelectWs: (ws: Workspace) => void;
  wsList: Workspace[];
  wsMenuOpen: boolean;
  onSetWsMenuOpen: (open: boolean) => void;
  wsMenuRef: React.RefObject<HTMLDivElement | null>;
  currentView: string;
  onSetView: (view: any) => void;
  user: any;
  cloneJob: WorkspaceCloneJob | null;
  cancellingJob: boolean;
  onSetCancellingJob: (cancelling: boolean) => void;
  onShowCreateWs: () => void;
  onShowForkWs: (ws: Workspace) => void;
  canWrite: boolean;
}

const Sidebar: React.FC<SidebarProps> = ({
  collapsed,
  onToggle,
  selectedWs,
  onSelectWs,
  wsList,
  wsMenuOpen,
  onSetWsMenuOpen,
  wsMenuRef,
  currentView,
  onSetView,
  user,
  cloneJob,
  cancellingJob,
  onSetCancellingJob,
  onShowCreateWs,
  onShowForkWs,
  canWrite,
}) => {
  const { t, i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <Button
        variant="ghost"
        size="sm"
        className="sidebar-toggle"
        onClick={onToggle}
        style={{ position: 'absolute', top: '50%', right: -10, transform: 'translateY(-50%)', width: 20, height: 60, padding: 0 }}
      >
        {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </Button>

      <div className="brand" style={{ justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {!collapsed && <div className="brand-text">MemTrace</div>}
        </div>
      </div>

      {/* Workspace selector */}
      {!collapsed && (
        <div ref={wsMenuRef} style={{ position: 'relative', padding: '0 0 12px' }}>
          <button
            onClick={() => onSetWsMenuOpen(!wsMenuOpen)}
            className="search-bar"
            style={{
              width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '8px 12px', background: 'var(--bg-elevated)',
              border: '1px solid var(--border-default)', borderRadius: 8, cursor: 'pointer',
              color: 'var(--text-primary)', fontSize: 13,
            }}
          >
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {selectedWs ? (zh ? selectedWs.name_zh : selectedWs.name_en) : (zh ? '選擇工作區…' : 'Select workspace…')}
            </span>
            <ChevronDown size={14} />
          </button>
          {wsMenuOpen && (
            <div style={{
              position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 50,
              background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
              borderRadius: 8, overflow: 'hidden', boxShadow: 'var(--shadow-lg)',
            }}>
              {/* My workspaces */}
              {wsList.filter(ws => ws.visibility !== 'public' && ws.visibility !== 'conditional_public').map(ws => (
                <div
                  key={ws.id}
                  onClick={() => { onSelectWs(ws); onSetWsMenuOpen(false); }}
                  style={{
                    padding: '9px 14px', cursor: 'pointer', fontSize: 13,
                    background: selectedWs?.id === ws.id ? 'var(--color-primary-subtle)' : 'transparent',
                    color: selectedWs?.id === ws.id ? 'var(--color-primary)' : 'var(--text-primary)',
                    transition: 'all 0.15s'
                  }}
                >
                  {zh ? ws.name_zh : ws.name_en}
                  <span style={{ fontSize: 10, opacity: 0.6, marginLeft: 6 }}>{ws.kb_type}</span>
                </div>
              ))}
              {/* Public / example workspaces */}
              {wsList.some(ws => ws.visibility === 'public' || ws.visibility === 'conditional_public') && (
                <>
                  <div style={{ padding: '6px 14px 4px', fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: 'var(--text-muted)', borderTop: '1px solid var(--border-subtle)', textTransform: 'uppercase' }}>
                    {zh ? '公開知識庫' : 'Public'}
                  </div>
                  {wsList.filter(ws => ws.visibility === 'public' || ws.visibility === 'conditional_public').map(ws => (
                    <div
                      key={ws.id}
                      style={{
                        padding: '7px 14px', cursor: 'pointer', fontSize: 13,
                        background: selectedWs?.id === ws.id ? 'var(--color-primary-subtle)' : 'transparent',
                        color: selectedWs?.id === ws.id ? 'var(--color-primary)' : 'var(--text-primary)',
                        transition: 'all 0.15s',
                        display: 'flex', alignItems: 'center', gap: 6,
                      }}
                      onClick={() => { onSelectWs(ws); onSetWsMenuOpen(false); }}
                    >
                      <Globe size={11} style={{ opacity: 0.5, flexShrink: 0 }} />
                      <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {zh ? ws.name_zh : ws.name_en}
                      </span>
                      <span style={{ fontSize: 10, opacity: 0.6 }}>{ws.kb_type}</span>
                      {user && ws.owner_id !== user.id && (
                        <Button
                          variant="secondary"
                          size="sm"
                          title={zh ? 'Fork 此知識庫' : 'Fork this KB'}
                          onClick={e => {
                            e.stopPropagation();
                            onSetWsMenuOpen(false);
                            onShowForkWs(ws);
                          }}
                          style={{ padding: '2px 6px', fontSize: 10, height: 20 }}
                          leftIcon={<GitFork size={10} />}
                        >
                          Fork
                        </Button>
                      )}
                    </div>
                  ))}
                </>
              )}
              {/* New workspace button */}
              <div
                onClick={() => { onSetWsMenuOpen(false); onShowCreateWs(); }}
                style={{
                  padding: '9px 14px', cursor: 'pointer', fontSize: 13,
                  borderTop: '1px solid var(--border-default)',
                  color: 'var(--color-primary)',
                  display: 'flex', alignItems: 'center', gap: 6,
                }}
              >
                <PlusCircle size={13} />
                {zh ? '新增工作區…' : 'New workspace…'}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Clone / Fork progress panel */}
      {!collapsed && cloneJob && ['pending', 'running', 'cancelling', 'cancelled', 'failed'].includes(cloneJob.status) && (
        <div style={{ padding: '0 12px 16px' }}>
          <div style={{
            padding: '10px 12px',
            background: cloneJob.status === 'failed' ? 'var(--color-error-subtle)'
                      : cloneJob.status === 'cancelled' ? 'var(--bg-elevated)'
                      : 'var(--bg-elevated)',
            borderRadius: 10,
            border: `1px solid ${
              cloneJob.status === 'failed' ? 'var(--color-error)' : 'var(--border-default)'
            }`,
          }}>
            <div style={{
              fontSize: 11,
              color: cloneJob.status === 'failed' ? 'var(--color-error)' : 'var(--text-muted)',
              marginBottom: 6,
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                {cloneJob.status === 'failed' && <AlertTriangle size={12} />}
                {cloneJob.status === 'cancelled' && <XCircle size={12} />}
                {['pending', 'running', 'cancelling'].includes(cloneJob.status) && (
                  <RefreshCw size={12} className="animate-spin-slow" />
                )}
                {cloneJob.status === 'failed'
                  ? (zh ? `${cloneJob.is_fork ? 'Fork' : '複製'}失敗` : `${cloneJob.is_fork ? 'Fork' : 'Clone'} Failed`)
                  : cloneJob.status === 'cancelled'
                  ? (zh ? '已取消' : 'Cancelled')
                  : cloneJob.status === 'cancelling'
                  ? (zh ? '取消中…' : 'Cancelling…')
                  : zh
                  ? `${cloneJob.is_fork ? 'Fork' : '複製'}進行中…`
                  : `${cloneJob.is_fork ? 'Fork' : 'Clone'} in progress…`}
              </span>
              {['pending', 'running'].includes(cloneJob.status) && cloneJob.total_nodes > 0 && (
                <span>{cloneJob.processed_nodes} / {cloneJob.total_nodes}</span>
              )}
            </div>

            {['pending', 'running'].includes(cloneJob.status) && (
              <div style={{ height: 4, background: 'var(--border-default)', borderRadius: 2, overflow: 'hidden', marginBottom: 8 }}>
                <div style={{
                  height: '100%',
                  background: 'var(--color-primary)',
                  width: `${Math.max(5, (cloneJob.processed_nodes / (cloneJob.total_nodes || 1)) * 100)}%`,
                  transition: 'width 0.3s',
                }} />
              </div>
            )}

            {cloneJob.status === 'failed' && (
              <div style={{ fontSize: 10, color: 'var(--color-error)', opacity: 0.8 }}>{cloneJob.error_msg}</div>
            )}

            {['pending', 'running'].includes(cloneJob.status) && (
              <Button
                variant="secondary"
                size="sm"
                onClick={async () => {
                  if (cancellingJob) return;
                  onSetCancellingJob(true);
                  try {
                    await workspaces.cancelCloneJob(cloneJob.id);
                  } catch {
                    onSetCancellingJob(false);
                  }
                }}
                disabled={cancellingJob}
                style={{ marginTop: 4, fontSize: 11, padding: '2px 8px', height: 24 }}
              >
                {cancellingJob ? (zh ? '取消中…' : 'Cancelling…') : (zh ? '取消' : 'Cancel')}
              </Button>
            )}
          </div>
        </div>
      )}

      <nav style={{ flex: 1 }}>
        <div className={`nav-item ${currentView === 'graph' ? 'active' : ''}`} onClick={() => onSetView('graph')}>
          <Network size={18} />
          {!collapsed && <span className="nav-text">{t('sidebar.graph')}</span>}
        </div>

        {selectedWs && (
          <div
            className={`nav-item ${currentView === 'analytics' ? 'active' : ''}`}
            style={{ marginTop: 4 }}
            title={collapsed ? t('sidebar.analytics') : undefined}
            onClick={() => onSetView('analytics')}
          >
            <BarChart3 size={18} />
            {!collapsed && <span className="nav-text">{t('sidebar.analytics')}</span>}
          </div>
        )}
        {selectedWs && canWrite && (
          <div
            className={`nav-item ${currentView === 'review' ? 'active' : ''}`}
            style={{ marginTop: 4 }}
            title={collapsed ? t('sidebar.review') : undefined}
            onClick={() => onSetView('review')}
          >
            <Inbox size={18} />
            {!collapsed && <span className="nav-text">{t('sidebar.review')}</span>}
          </div>
        )}
        {selectedWs && canWrite && (
          <div
            className={`nav-item ${currentView === 'ws_settings' ? 'active' : ''}`}
            style={{ marginTop: 4 }}
            title={collapsed ? t('sidebar.ws_settings') : undefined}
            onClick={() => onSetView('ws_settings')}
          >
            <Users size={18} />
            {!collapsed && <span className="nav-text">{t('sidebar.ws_settings')}</span>}
          </div>
        )}
        {selectedWs && canWrite && (
          <div
            className={`nav-item ${currentView === 'ingest' ? 'active' : ''}`}
            style={{ marginTop: 4 }}
            title={collapsed ? t('sidebar.ingest') : undefined}
            onClick={() => onSetView('ingest')}
          >
            <FileUp size={18} />
            {!collapsed && <span className="nav-text">{t('sidebar.ingest')}</span>}
          </div>
        )}
      </nav>
    </aside>
  );
};

export default Sidebar;
