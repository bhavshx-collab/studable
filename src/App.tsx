import { useState, useMemo, useEffect } from 'react';
import { AppShell, AppRoute } from './components/layout/AppShell';
import {
  PROTOTYPE_CONNECTIONS,
  PROTOTYPE_CURRENT_USER,
  PROTOTYPE_MESSAGES_BY_PEER,
  PROTOTYPE_NOTIFICATIONS,
  PROTOTYPE_PEERS,
  PROTOTYPE_REPORTS,
  PROTOTYPE_SETTINGS,
  PROTOTYPE_ADMIN_USER,
} from './data/prototypeMocks';
import {
  AppNotification,
  AudiencePreference,
  ChatMessage,
  ConnectionRecord,
  ModerationReport,
  OwnAccountSettings,
  UserProfile,
} from './types/domain';
import { LandingPage } from './pages/LandingPage';
import { AuthOnboardingPage } from './pages/AuthOnboardingPage';
import { DashboardPage, DashboardRightPanel } from './pages/DashboardPage';
import { ConnectLobbyPage } from './pages/ConnectLobbyPage';
import { ChatPage } from './pages/ChatPage';
import { ProfilePage } from './pages/ProfilePage';
import { ConnectionsPage } from './pages/ConnectionsPage';
import { NotificationsPage } from './pages/NotificationsPage';
import { SettingsPage } from './pages/SettingsPage';
import { AdminDashboardPage } from './pages/AdminDashboardPage';
import { StateView } from './components/ui/StateView';
import { BrowserRouter, useRouter } from './router/Router';
import { AdminGuard } from './router/AdminGuard';
import { getMeApi, logoutApi, refreshApi } from './services/authApi';
import { getLiveOnlineCount, presenceWs } from './services/presenceService';
import { matchingWs } from './services/matchingService';

const VALID_APP_ROUTES: AppRoute[] = [
  'dashboard',
  'discover',
  'connect',
  'connections',
  'messages',
  'notifications',
  'profile',
  'settings',
];

function AppRoutes() {
  const { pathname, searchParams, navigate } = useRouter();

  const [currentUser, setCurrentUser] = useState<UserProfile>(
    PROTOTYPE_CURRENT_USER
  );
  const [accountSettings, setAccountSettings] =
    useState<OwnAccountSettings>(PROTOTYPE_SETTINGS);
  const [connections, setConnections] = useState<ConnectionRecord[]>(
    PROTOTYPE_CONNECTIONS
  );
  const [notifications, setNotifications] = useState<AppNotification[]>(
    PROTOTYPE_NOTIFICATIONS
  );
  const [messagesByPeer, setMessagesByPeer] = useState<
    Record<string, ChatMessage[]>
  >(PROTOTYPE_MESSAGES_BY_PEER);
  const [blockedUsers, setBlockedUsers] = useState<UserProfile[]>([]);
  const [reports, setReports] = useState<ModerationReport[]>(PROTOTYPE_REPORTS);

  // Contextual navigation states
  const [lobbyAudience, setLobbyAudience] =
    useState<AudiencePreference>('Anyone');
  const [lobbyTopic, setLobbyTopic] = useState(
    'Building reliable real-world AI products'
  );
  const [activeChatPeer, setActiveChatPeer] = useState<UserProfile | null>(
    PROTOTYPE_PEERS[0]
  );
  const [activeChatTopic, setActiveChatTopic] = useState(
    'Design systems at scale'
  );
  const [inspectedPeer, setInspectedPeer] = useState<UserProfile | null>(null);

  // Live online user count from Redis presence engine
  const [liveOnlineCount, setLiveOnlineCount] = useState<number | null>(null);

  // Restore authenticated session after refresh if refresh cookie is present
  useEffect(() => {
    let isMounted = true;
    refreshApi()
      .then(() => getMeApi())
      .then((profile) => {
        if (isMounted && profile) {
          setCurrentUser(profile);
          presenceWs.connect();
          matchingWs.connect();
          getLiveOnlineCount().then((count) => {
            if (isMounted && count !== null) {
              setLiveOnlineCount(count);
            }
          });
        }
      })
      .catch(() => {
        // No active session — stays as default/guest
      });

    const pollInterval = setInterval(() => {
      getLiveOnlineCount().then((count) => {
        if (isMounted && count !== null) {
          setLiveOnlineCount(count);
        }
      });
    }, 30000);

    return () => {
      isMounted = false;
      clearInterval(pollInterval);
      presenceWs.disconnect();
      matchingWs.disconnect();
    };
  }, []);

  const currentRouteName = useMemo<AppRoute | null>(() => {
    const segment = pathname.replace(/^\//, '').toLowerCase();
    if (VALID_APP_ROUTES.includes(segment as AppRoute)) {
      return segment as AppRoute;
    }
    return null;
  }, [pathname]);

  const openLobbyWith = (audience: AudiencePreference, topic?: string) => {
    setLobbyAudience(audience);
    if (topic) setLobbyTopic(topic);
    navigate('/connect');
  };

  const viewPeerProfile = (peer: UserProfile) => {
    setInspectedPeer(peer);
    navigate('/profile');
  };

  const handleRequestConnection = (peer: UserProfile) => {
    setConnections((prev) => {
      if (prev.some((c) => c.user.id === peer.id)) return prev;
      return [
        {
          id: `conn_${Date.now()}`,
          user: peer,
          status: 'pending_outgoing',
          sharedTopic: activeChatTopic,
        },
        ...prev,
      ];
    });
  };

  const handleBlockUser = (peer: UserProfile) => {
    setBlockedUsers((prev) =>
      prev.some((u) => u.id === peer.id) ? prev : [...prev, peer]
    );
    setConnections((prev) => prev.filter((c) => c.user.id !== peer.id));
    if (activeChatPeer?.id === peer.id) {
      setActiveChatPeer(null);
      navigate('/connect');
    }
  };

  const handleReportUser = (
    peer: UserProfile,
    reason: string,
    details = ''
  ) => {
    const newReport: ModerationReport = {
      id: `rep_${Date.now()}`,
      reportedUserId: peer.id,
      reportedUserName: peer.displayName,
      reporterId: currentUser.id,
      reason,
      details: details || 'Reported from conversation or profile view.',
      status: 'pending',
      createdAt: 'Just now',
    };
    setReports((prev) => [newReport, ...prev]);
  };

  const handleSendMessage = (peerId: string, content: string) => {
    const msg: ChatMessage = {
      id: `msg_${Date.now()}`,
      conversationId: `conv_${peerId}`,
      senderId: currentUser.id,
      content,
      createdAt: new Date().toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
      }),
      status: 'sent',
    };
    setMessagesByPeer((prev) => ({
      ...prev,
      [peerId]: [...(prev[peerId] ?? []), msg],
    }));
  };

  const availablePeers = PROTOTYPE_PEERS.filter(
    (p) => !blockedUsers.some((b) => b.id === p.id)
  );

  const unreadCount = notifications.filter((n) => !n.read).length;

  // 1. Landing Page Route
  if (pathname === '/' || pathname === '/home') {
    return (
      <LandingPage
        onStartConnecting={() => navigate('/register')}
        onLogin={() => navigate('/login')}
      />
    );
  }

  // 2. Auth & Onboarding Route
  if (pathname === '/auth' || pathname === '/login' || pathname === '/register') {
    const isLogin =
      pathname === '/login' || searchParams.get('mode') === 'login';
    return (
      <AuthOnboardingPage
        initialMode={isLogin ? 'login' : 'register'}
        onBackToLanding={() => navigate('/')}
        onComplete={(profile, email) => {
          setCurrentUser(profile);
          setAccountSettings((prev) => ({ ...prev, email }));
          presenceWs.connect();
          getLiveOnlineCount().then((count) => {
            if (count !== null) setLiveOnlineCount(count);
          });
          navigate('/dashboard');
        }}
      />
    );
  }

  // 3. Admin Route with Route Guard
  if (pathname === '/admin') {
    return (
      <AdminGuard
        currentUser={currentUser}
        onNavigateHome={() => navigate('/')}
        onSimulateAdminAccess={() => setCurrentUser(PROTOTYPE_ADMIN_USER)}
      >
        <AdminDashboardPage
          reports={reports}
          users={PROTOTYPE_PEERS}
          onUpdateReportStatus={(reportId, status) =>
            setReports((prev) =>
              prev.map((r) => (r.id === reportId ? { ...r, status } : r))
            )
          }
          onExitAdmin={() => navigate('/')}
        />
      </AdminGuard>
    );
  }

  // 4. In-App Routes inside AppShell
  if (currentRouteName) {
    return (
      <AppShell
        activeRoute={currentRouteName}
        onNavigate={(next) => {
          if (next === 'profile') setInspectedPeer(null);
          navigate(`/${next}`);
        }}
        currentUser={currentUser}
        unreadNotifications={unreadCount}
        rightPanel={
          currentRouteName === 'dashboard' ? (
            <DashboardRightPanel
              suggestedPeers={availablePeers}
              onViewProfile={viewPeerProfile}
            />
          ) : undefined
        }
      >
        {currentRouteName === 'dashboard' && (
          <DashboardPage
            currentUser={currentUser}
            liveOnlineCount={liveOnlineCount}
            suggestedPeers={availablePeers}
            recentConnections={connections}
            onStartRandomConnect={() => openLobbyWith('Anyone')}
            onExploreInterests={(topic) => openLobbyWith('Anyone', topic)}
            onFindProfessionals={() => openLobbyWith('Professionals')}
            onViewProfile={viewPeerProfile}
          />
        )}

        {(currentRouteName === 'connect' || currentRouteName === 'discover') && (
          <ConnectLobbyPage
            defaultAudience={lobbyAudience}
            defaultTopic={lobbyTopic}
            liveOnlineCount={liveOnlineCount}
            prototypePeers={
              availablePeers.length > 0 ? availablePeers : PROTOTYPE_PEERS
            }
            onEnterChat={(peer, topic) => {
              setActiveChatPeer(peer);
              setActiveChatTopic(topic);
              navigate('/messages');
            }}
          />
        )}

        {currentRouteName === 'messages' &&
          (activeChatPeer ? (
            <ChatPage
              peer={activeChatPeer}
              topic={activeChatTopic}
              initialMessages={messagesByPeer[activeChatPeer.id] ?? []}
              isConnected={connections.some(
                (c) =>
                  c.user.id === activeChatPeer.id && c.status === 'accepted'
              )}
              isConnectionPending={connections.some(
                (c) =>
                  c.user.id === activeChatPeer.id && c.status !== 'accepted'
              )}
              onSendMessage={handleSendMessage}
              onRequestConnection={handleRequestConnection}
              onBlockUser={handleBlockUser}
              onReportUser={handleReportUser}
              onViewPeerProfile={viewPeerProfile}
              onSkipToLobby={() => navigate('/connect')}
            />
          ) : (
            <StateView
              kind="empty"
              title="No active conversation"
              description="Enter the connection lobby to match with someone and start a 1-on-1 text chat."
              actionLabel="Go to Connect Lobby"
              onAction={() => navigate('/connect')}
            />
          ))}

        {currentRouteName === 'connections' && (
          <ConnectionsPage
            connections={connections}
            onAccept={(id) =>
              setConnections((prev) =>
                prev.map((c) =>
                  c.id === id
                    ? { ...c, status: 'accepted', connectedAt: 'Just now' }
                    : c
                )
              )
            }
            onRejectOrRemove={(id) =>
              setConnections((prev) => prev.filter((c) => c.id !== id))
            }
            onOpenProfile={viewPeerProfile}
            onOpenChat={(peer) => {
              setActiveChatPeer(peer);
              setActiveChatTopic('Direct Connection');
              navigate('/messages');
            }}
            onExploreMatches={() => navigate('/connect')}
          />
        )}

        {currentRouteName === 'notifications' && (
          <NotificationsPage
            notifications={notifications}
            onMarkAllRead={() =>
              setNotifications((prev) =>
                prev.map((n) => ({ ...n, read: true }))
              )
            }
            onOpenNotification={(notif) => {
              setNotifications((prev) =>
                prev.map((n) => (n.id === notif.id ? { ...n, read: true } : n))
              );
              if (notif.type === 'connection_request') {
                navigate('/connections');
              } else if (notif.type === 'new_message' && notif.relatedUserId) {
                const peer = PROTOTYPE_PEERS.find(
                  (p) => p.id === notif.relatedUserId
                );
                if (peer) {
                  setActiveChatPeer(peer);
                  navigate('/messages');
                }
              }
            }}
          />
        )}

        {currentRouteName === 'profile' && (
          <ProfilePage
            profile={inspectedPeer ?? currentUser}
            isOwnProfile={!inspectedPeer || inspectedPeer.id === currentUser.id}
            isConnected={
              inspectedPeer
                ? connections.some(
                    (c) =>
                      c.user.id === inspectedPeer.id && c.status === 'accepted'
                  )
                : false
            }
            isPending={
              inspectedPeer
                ? connections.some(
                    (c) =>
                      c.user.id === inspectedPeer.id && c.status !== 'accepted'
                  )
                : false
            }
            onEditProfile={() => navigate('/settings')}
            onConnect={() =>
              inspectedPeer && handleRequestConnection(inspectedPeer)
            }
            onBlock={handleBlockUser}
            onReport={(peer, reason) => handleReportUser(peer, reason)}
            onMessage={() => {
              if (inspectedPeer) {
                setActiveChatPeer(inspectedPeer);
                setActiveChatTopic('Direct Connection');
                navigate('/messages');
              }
            }}
          />
        )}

        {currentRouteName === 'settings' && (
          <SettingsPage
            profile={currentUser}
            settings={accountSettings}
            blockedUsers={blockedUsers}
            onSaveProfileAndSettings={(updatedProfile, updatedSettings) => {
              setCurrentUser(updatedProfile);
              setAccountSettings(updatedSettings);
            }}
            onUnblockUser={(userId) =>
              setBlockedUsers((prev) => prev.filter((u) => u.id !== userId))
            }
            onLogout={async () => {
              presenceWs.disconnect();
              await logoutApi();
              setLiveOnlineCount(null);
              navigate('/');
            }}
          />
        )}
      </AppShell>
    );
  }

  // 5. Fallback 404 Route
  return (
    <div className="min-h-screen bg-[#0B0D14] flex flex-col justify-center items-center px-4 py-12 text-[#F5F6FA]">
      <StateView
        kind="empty"
        title="Page Not Found"
        description={`The route "${pathname}" does not exist on Studable.`}
        actionLabel="Go to Home"
        onAction={() => navigate('/')}
      />
    </div>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}

export default App;
