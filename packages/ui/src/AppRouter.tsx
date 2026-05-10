import React, { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { RefreshCw } from 'lucide-react';
import AuthPage from './AuthPage';
import PublicWorkspaceView from './PublicWorkspaceView';
import MagicLinkVerifyPage from './MagicLinkVerifyPage';
import JoinInvitationPage from './JoinInvitationPage';
import ResetPasswordPage from './ResetPasswordPage';
import { ErrorBoundary } from './components/ErrorBoundary';

// Lazy Loaded Components
const AnalyticsDashboard = lazy(() => import('./AnalyticsDashboard'));
const NodeHealthManager = lazy(() => import('./NodeHealthManager'));
const ReviewQueue = lazy(() => import('./ReviewQueue'));
const WorkspaceSettings = lazy(() => import('./WorkspaceSettings'));
const IngestPage = lazy(() => import('./IngestPage'));
const SettingsPanel = lazy(() => import('./components/SettingsPanel'));
const GraphContainer = lazy(() => import('./GraphContainer'));

interface AppRouterProps {
  authenticated: boolean;
  setAuthenticated: (v: boolean) => void;
  user: any;
  selectedWs: any;
  currentView: string;
  setCurrentView: (v: any) => void;
  graphVersion: number;
  setEditingNode: (n: any) => void;
  theme: string;
  toggleTheme: () => void;
  language: string;
  switchLanguage: (l: string) => void;
}

const AppRouter: React.FC<AppRouterProps> = ({
  authenticated,
  setAuthenticated,
  user,
  selectedWs,
  currentView,
  setCurrentView,
  graphVersion,
  setEditingNode,
  theme,
  toggleTheme,
  language,
  switchLanguage,
}) => {
  return (
    <Routes>
      <Route path="/public/:wsId" element={<PublicWorkspaceView />} />
      <Route path="/verify" element={<MagicLinkVerifyPage onAuthenticated={() => setAuthenticated(true)} />} />
      <Route path="/invite/:token" element={<JoinInvitationPage />} />
      <Route path="/signin" element={
        authenticated ? <Navigate to="/" /> : <AuthPage onAuthenticated={() => setAuthenticated(true)} />
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
                    <ReviewQueue wsId={selectedWs.id} onClose={() => setCurrentView('graph')} />
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
              </Suspense>
            </ErrorBoundary>
          </div>
        )
      } />
    </Routes>
  );
};

export default AppRouter;
