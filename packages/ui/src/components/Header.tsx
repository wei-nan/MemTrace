import React from 'react';
import { useTranslation } from 'react-i18next';
import { Settings, LogOut, BookOpen } from 'lucide-react';
import NotificationBell from './NotificationBell';

interface HeaderProps {
  currentView: string;
  pageSubtitle: string;
  user: any;
  userMenuOpen: boolean;
  onSetUserMenuOpen: (open: boolean) => void;
  userMenuRef: React.RefObject<HTMLDivElement | null>;
  onSetView: (view: any) => void;
  onLogout: () => void;
  onNavigateNotification?: (n: any) => void;
  onViewAllNotifications?: () => void;
}

const Header: React.FC<HeaderProps> = ({
  currentView,
  pageSubtitle,
  user,
  userMenuOpen,
  onSetUserMenuOpen,
  userMenuRef,
  onSetView,
  onLogout,
  onNavigateNotification,
  onViewAllNotifications,
}) => {
  const { t, i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';

  const getTitle = () => {
    switch (currentView) {
      case 'graph': return zh ? '知識圖譜' : 'Knowledge Graph';
      case 'analytics': return t('analytics.title');
      case 'node_health': return t('sidebar.health');
      case 'review': return t('review.title');
      case 'ws_settings': return zh ? '工作區設定' : 'Workspace Settings';
      case 'ingest': return t('ingest.title');
      case 'settings': return zh ? '個人設定' : 'Personal Settings';
      case 'explore': return zh ? '探索知識庫' : 'Explore';
      case 'guide': return zh ? '使用說明' : 'Guide';
      case 'notifications': return zh ? '通知中心' : 'Notifications';
      default: return 'MemTrace';
    }
  };

  const getSubtitle = () => {
    switch (currentView) {
      case 'graph': return pageSubtitle;
      case 'review': return t('review.subtitle');
      case 'analytics': return zh ? '系統數據與健康狀態' : 'System metrics & Health';
      case 'ingest': return t('ingest.desc');
      case 'ws_settings': return zh ? '管理成員與權限' : 'Manage members & permissions';
      default: return '';
    }
  };

  const subtitle = getSubtitle();

  return (
    <header className="main-header">
      <div className="header-left">
        <h1 className="header-title">{getTitle()}</h1>
        {subtitle && (
          <span className="header-subtitle">{subtitle}</span>
        )}
      </div>
      
      <div className="header-right">
        <div id="header-actions"></div>
        {user && (
          <NotificationBell
            onNavigate={onNavigateNotification}
            onViewAll={onViewAllNotifications}
          />
        )}
        {user && (
          <div 
            ref={userMenuRef}
            style={{ position: 'relative' }}
          >
            <div 
              onClick={() => onSetUserMenuOpen(!userMenuOpen)}
              style={{ 
                background: 'transparent', border: 'none',
                borderRadius: 8, padding: '0 4px', height: 38, display: 'flex', alignItems: 'center', gap: 10,
                cursor: 'pointer', boxShadow: 'none', transition: 'all 0.2s',
                userSelect: 'none'
              }}
              className="user-menu-trigger"
            >
              <div style={{ 
                width: 28, height: 28, borderRadius: '50%', background: 'var(--color-primary-subtle)',
                color: 'var(--color-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 12, fontWeight: 700
              }}>
                {user.display_name?.[0]?.toUpperCase()}
              </div>
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>{user.display_name}</span>
            </div>

            {userMenuOpen && (
              <div style={{
                position: 'absolute', top: 'calc(100% + 8px)', right: 0,
                width: 200, background: 'var(--bg-elevated)', border: '1px solid var(--border-default)',
                borderRadius: 10, boxShadow: 'var(--shadow-lg)', overflow: 'hidden',
                animation: 'fade-in-down 0.2s ease-out', zIndex: 1100
              }}>
                <div style={{ padding: '10px 16px 8px', borderBottom: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {user.display_name}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {user.email}
                  </div>
                </div>
                <div
                  className="nav-item"
                  onClick={() => { onSetView('guide'); onSetUserMenuOpen(false); }}
                  style={{ borderRadius: 0, padding: '12px 16px', margin: 0, border: 'none' }}
                >
                  <BookOpen size={16} />
                  <span className="nav-text" style={{ fontSize: 13, whiteSpace: 'nowrap' }}>{zh ? '使用說明' : 'Guide'}</span>
                </div>
                <div style={{ borderTop: '1px solid var(--border-subtle)' }} />
                <div
                  className="nav-item"
                  onClick={() => { onSetView('settings'); onSetUserMenuOpen(false); }}
                  style={{ borderRadius: 0, padding: '12px 16px', margin: 0, border: 'none' }}
                >
                  <Settings size={16} />
                  <span className="nav-text" style={{ fontSize: 13, whiteSpace: 'nowrap' }}>{t('nav.settings')}</span>
                </div>
                <div style={{ borderTop: '1px solid var(--border-subtle)' }} />
                <div
                  className="nav-item logout-item"
                  onClick={() => { onLogout(); onSetUserMenuOpen(false); }}
                  style={{ borderRadius: 0, padding: '12px 16px', margin: 0, border: 'none' }}
                >
                  <LogOut size={16} />
                  <span className="nav-text" style={{ fontSize: 13, whiteSpace: 'nowrap' }}>{t('nav.logout')}</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
};

export default Header;
