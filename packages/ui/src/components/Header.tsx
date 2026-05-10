import React from 'react';
import { useTranslation } from 'react-i18next';
import { Settings, Network, LogOut } from 'lucide-react';

interface HeaderProps {
  currentView: string;
  pageSubtitle: string;
  user: any;
  userMenuOpen: boolean;
  onSetUserMenuOpen: (open: boolean) => void;
  userMenuRef: React.RefObject<HTMLDivElement | null>;
  onSetView: (view: any) => void;
  onLogout: () => void;
  showMcpStatus: boolean;
  onSetShowMcpStatus: (show: boolean) => void;
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
  showMcpStatus,
  onSetShowMcpStatus,
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
                fontSize: 14, fontWeight: 700
              }}>
                {user.display_name?.[0]?.toUpperCase()}
              </div>
              <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>{user.display_name}</span>
            </div>

            {userMenuOpen && (
              <div style={{ 
                position: 'absolute', top: 'calc(100% + 8px)', right: 0, 
                width: 200, background: 'var(--bg-elevated)', border: '1px solid var(--border-default)',
                borderRadius: 12, boxShadow: 'var(--shadow-lg)', overflow: 'hidden',
                animation: 'fade-in-down 0.2s ease-out', zIndex: 1100
              }}>
                <div 
                  className="nav-item" 
                  onClick={() => { onSetView('settings'); onSetUserMenuOpen(false); }}
                  style={{ borderRadius: 0, padding: '12px 16px', margin: 0, border: 'none' }}
                >
                  <Settings size={16} />
                  <span className="nav-text" style={{ fontSize: 13, whiteSpace: 'nowrap' }}>{t('nav.settings')}</span>
                </div>
                <div 
                  className="nav-item" 
                  onClick={() => { onSetShowMcpStatus(!showMcpStatus); onSetUserMenuOpen(false); }}
                  style={{ borderRadius: 0, padding: '12px 16px', margin: 0, border: 'none' }}
                >
                  <Network size={16} />
                  <span className="nav-text" style={{ fontSize: 13, whiteSpace: 'nowrap' }}>MCP Status</span>
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
