import React, { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { RefreshCw } from 'lucide-react';
import AuthPage from './AuthPage';
import PublicWorkspaceView from './PublicWorkspaceView';
import MagicLinkVerifyPage from './MagicLinkVerifyPage';
import JoinInvitationPage from './JoinInvitationPage';
import ResetPasswordPage from './ResetPasswordPage';
import ExplorePage from './ExplorePage';
import { ErrorBoundary } from './components/ErrorBoundary';

// Lazy Loaded Components
const AnalyticsDashboard = lazy(() => import('./AnalyticsDashboard'));
const NodeHealthManager = lazy(() => import('./NodeHealthManager'));
const ReviewQueue = lazy(() => import('./ReviewQueue'));
const WorkspaceSettings = lazy(() => import('./WorkspaceSettings'));
const IngestPage = lazy(() => import('./IngestPage'));
const DocumentsPage = lazy(() => import('./DocumentsPage'));
const SettingsPanel = lazy(() => import('./components/SettingsPanel'));
const GraphContainer = lazy(() => import('./GraphContainer'));
const SystemAISettings = lazy(() => import('./SystemAISettings'));
const AiChatPanel = lazy(() => import('./components/AiChatPanel'));
const JobRunsPage = lazy(() => import('./JobRunsPage'));
const SystemMonitorPage = lazy(() => import('./SystemMonitorPage'));
const GuidePage = lazy(() => import('./GuidePage'));
const NotificationsPage = lazy(() => import('./NotificationsPage'));

interface AppRouterProps {
  authenticated: boolean;
  setAuthenticated: (v: boolean) => void;
  user: any;
  selectedWs: any;
  setSelectedWs: (ws: any) => void;
  currentView: string;
  setCurrentView: (v: any) => void;
  graphVersion: number;
  setEditingNode: (n: any) => void;
  theme: string;
  toggleTheme: () => void;
  language: string;
  switchLanguage: (l: string) => void;
  onOpenSpecKb: () => void;
  onNavigateNotification?: (n: any) => void;
}

const AppRouter: React.FC<AppRouterProps> = ({
  authenticated,
  setAuthenticated,
  user,
  selectedWs,
  setSelectedWs,
  currentView,
  setCurrentView,
  graphVersion,
  setEditingNode,
  theme,
  toggleTheme,
  language,
  switchLanguage,
  onOpenSpecKb,
  onNavigateNotification,
}) => {
  return (
    <Routes>
      <Route path="/public/:wsId" element={<PublicWorkspaceView />} />
      <Route path="/verify" element={<MagicLinkVerifyPage onAuthenticated={() => setAuthenticated(true)} />} />
      <Route path="/invite/:token" element={<JoinInvitationPage />} />
      <Route path="/signin" element={
        authenticated ? <Navigate to="/" /> : <AuthPage />
      } />
      <Route path="/reset-password" element={
        <ResetPasswordPage 
          token={new URLSearchParams(window.location.search).get('token') || ''} 
          onSuccess={() => window.location.href = '/'} 
        />
      } />
      <Route path="/" element={
        !authenticated ? <Navigate to="/signin" /> : (
          <div style={{ flex: 1, minHeight: 0, position: 'relative', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <ErrorBoundary>
              <Suspense fallback={<div className="loading-overlay"><RefreshCw className="animate-spin" /></div>}>
                {currentView === 'guide' && (
                  <GuidePage onOpenSpecKb={onOpenSpecKb} />
                )}
                {currentView === 'explore' && (
                  <ExplorePage
                    authenticated={authenticated}
                    onSelectWs={ws => { setSelectedWs(ws); setCurrentView('graph'); }}
                    onSignIn={() => window.location.href = '/signin'}
                  />
                )}
                {currentView === 'graph' && (
                  <GraphContainer
                    wsId={selectedWs?.id}
                    userId={user?.id}
                    reloadKey={graphVersion}
                    onEditNode={node => setEditingNode(node)}
                    onNewNode={() => setEditingNode(null)}
                    onSwitchView={setCurrentView}
                  />
                )}
                {currentView === 'analytics' && selectedWs && (
                  <div style={{ flex: 1, padding: 40, overflowY: 'auto' }}>
                    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
                      <AnalyticsDashboard wsId={selectedWs.id} onOpenHealthManager={() => setCurrentView('node_health')} />
                    </div>
                  </div>
                )}
                {currentView === 'node_health' && selectedWs && (
                  <div style={{ flex: 1, padding: 40, overflowY: 'auto' }}>
                    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
                      <NodeHealthManager wsId={selectedWs.id} onEditNode={(node: any) => setEditingNode(node)} />
                    </div>
                  </div>
                )}
                {currentView === 'settings' && (
                  <div style={{ flex: 1, overflowY: 'auto' }}>
                    <SettingsPanel 
                      user={user}
                      theme={theme} 
                      toggleTheme={toggleTheme} 
                      language={language} 
                      switchLanguage={switchLanguage} 
                    />
                  </div>
                )}
                {currentView === 'review' && selectedWs && (
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                    <ReviewQueue
                      wsId={selectedWs.id}
                      onClose={() => setCurrentView('graph')}
                      onOpenNode={(node) => {
                        setEditingNode(node);
                        setCurrentView('graph');
                      }}
                    />
                  </div>
                )}
                {currentView === 'notifications' && (
                  <div style={{ flex: 1, overflowY: 'auto', padding: '32px 24px' }}>
                    <NotificationsPage onNavigate={onNavigateNotification} />
                  </div>
                )}
                {currentView === 'ws_settings' && selectedWs && (
                  <div style={{ flex: 1, padding: 40, overflowY: 'auto' }}>
                    <div style={{ maxWidth: 800, margin: '0 auto' }}>
                      <WorkspaceSettings wsId={selectedWs.id} userId={user?.id} />
                    </div>
                  </div>
                )}
                {currentView === 'ingest' && selectedWs && (
                  <div style={{ flex: 1, overflowY: 'auto' }}>
                    <IngestPage
                      wsId={selectedWs.id}
                      onGoToReview={() => setCurrentView('review')}
                    />
                  </div>
                )}
                {currentView === 'documents' && selectedWs && (
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                    <DocumentsPage
                      wsId={selectedWs.id}
                      onEditNode={(nodeId: string) => setEditingNode({ id: nodeId } as any)}
                    />
                  </div>
                )}
                {currentView === 'job_runs' && selectedWs && (
                  <div style={{ flex: 1, padding: 40, overflowY: 'auto' }}>
                    <JobRunsPage wsId={selectedWs.id} />
                  </div>
                )}
                {currentView === 'system_ai' && user?.is_platform_admin && (
                  <div style={{ flex: 1, overflowY: 'auto' }}>
                    <SystemAISettings />
                  </div>
                )}
                {currentView === 'system_monitor' && user?.is_platform_admin && (
                  <div style={{ flex: 1, overflowY: 'auto' }}>
                    <SystemMonitorPage />
                  </div>
                )}
                {currentView === 'ai_chat' && selectedWs && (
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                    <AiChatPanel wsId={selectedWs.id} zh={language === 'zh-TW'} fullPage />
                  </div>
                )}
              </Suspense>
            </ErrorBoundary>
          </div>
        )
      } />
    </Routes>
  );
};

export default AppRouter;
