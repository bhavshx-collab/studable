import { useState } from 'react';
import { AppShell, AppRoute } from './components/layout/AppShell';
import {
  PROTOTYPE_CONNECTIONS,
  PROTOTYPE_CURRENT_USER,
  PROTOTYPE_MESSAGES_BY_PEER,
  PROTOTYPE_NOTIFICATIONS,
  PROTOTYPE_PEERS,
  PROTOTYPE_REPORTS,
  PROTOTYPE_SETTINGS,
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

type Surface = 'landing' | 'auth' | 'app' | 'admin';

export function App() {
  const [surface, setSurface] = useState<Surface>('landing');
  const [authInitialMode, setAuthInitialMode] = useState<'register' | 'login'>(
    'register'
  );
  const [route, setRoute] = useState<AppRoute>('dashboard');

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

  // Strictly null until live WebSocket presence is connected
  const liveOnlineCount: number | null = null;

  if (surface === 'landing') {
    return (
      <LandingPage
        onStartConnecting={() => {
          setAuthInitialMode('register');
          setSurface('auth');
        }}
        onLogin={() => {
          setAuthInitialMode('login');
          setSurface('auth');
        }}
        onOpenAdminPreview={() => setSurface('admin')}
      />
    );
  }

  if (surface === 'auth') {
    return (
      <AuthOnboardingPage
        initialMode={authInitialMode}
        onBackToLanding={() => setSurface('landing')}
        onComplete={(profile, email) => {
          setCurrentUser(profile);
          setAccountSettings((prev) => ({ ...prev, email }));
          setSurface('app');
          setRoute('dashboard');
        }}
      />
    );
  }

  if (surface === 'admin') {
    return (
      <AdminDashboardPage
        reports={reports}
        users={PROTOTYPE_PEERS}
        onUpdateReportStatus={(reportId, status) =>
          setReports((prev) =>
            prev.map((r) => (r.id === reportId ? { ...r, status } : r))
          )
        }
        onExitAdmin={() => setSurface('landing')}
      />
    );
  }

  const unreadCount = notifications.filter((n) => !n.read).length;

  const openLobbyWith = (audience: AudiencePreference, topic?: string) => {
    setLobbyAudience(audience);
    if (topic) setLobbyTopic(topic);
    setRoute('connect');
  };

  const viewPeerProfile = (peer: UserProfile) => {
    setInspectedPeer(peer);
    setRoute('profile');
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
      setRoute('connect');
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
      senderId: 'usr_self',
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

  return (
    <AppShell
      activeRoute={route}
      onNavigate={(next) => {
        if (next === 'profile') setInspectedPeer(null);
        setRoute(next);
      }}
      currentUser={currentUser}
      unreadNotifications={unreadCount}
      rightPanel={
        route === 'dashboard' ? (
          <DashboardRightPanel
            suggestedPeers={availablePeers}
            onViewProfile={viewPeerProfile}
          />
        ) : undefined
      }
    >
      {route === 'dashboard' && (
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

      {(route === 'connect' || route === 'discover') && (
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
            setRoute('messages');
          }}
        />
      )}

      {route === 'messages' &&
        (activeChatPeer ? (
          <ChatPage
            peer={activeChatPeer}
            topic={activeChatTopic}
            initialMessages={messagesByPeer[activeChatPeer.id] ?? []}
            isConnected={connections.some(
              (c) => c.user.id === activeChatPeer.id && c.status === 'accepted'
            )}
            isConnectionPending={connections.some(
              (c) => c.user.id === activeChatPeer.id && c.status !== 'accepted'
            )}
            onSendMessage={handleSendMessage}
            onRequestConnection={handleRequestConnection}
            onBlockUser={handleBlockUser}
            onReportUser={handleReportUser}
            onViewPeerProfile={viewPeerProfile}
            onSkipToLobby={() => setRoute('connect')}
          />
        ) : (
          <StateView
            kind="empty"
            title="No active conversation"
            description="Enter the connection lobby to match with someone and start a 1-on-1 text chat."
            actionLabel="Go to Connect Lobby"
            onAction={() => setRoute('connect')}
          />
        ))}

      {route === 'connections' && (
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
            setRoute('messages');
          }}
          onExploreMatches={() => setRoute('connect')}
        />
      )}

      {route === 'notifications' && (
        <NotificationsPage
          notifications={notifications}
          onMarkAllRead={() =>
            setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
          }
          onOpenNotification={(notif) => {
            setNotifications((prev) =>
              prev.map((n) => (n.id === notif.id ? { ...n, read: true } : n))
            );
            if (notif.type === 'connection_request') {
              setRoute('connections');
            } else if (notif.type === 'new_message' && notif.relatedUserId) {
              const peer = PROTOTYPE_PEERS.find(
                (p) => p.id === notif.relatedUserId
              );
              if (peer) {
                setActiveChatPeer(peer);
                setRoute('messages');
              }
            }
          }}
        />
      )}

      {route === 'profile' && (
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
          onEditProfile={() => setRoute('settings')}
          onConnect={() => inspectedPeer && handleRequestConnection(inspectedPeer)}
          onBlock={handleBlockUser}
          onReport={(peer, reason) => handleReportUser(peer, reason)}
          onMessage={() => {
            if (inspectedPeer) {
              setActiveChatPeer(inspectedPeer);
              setActiveChatTopic('Direct Connection');
              setRoute('messages');
            }
          }}
        />
      )}

      {route === 'settings' && (
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
          onLogout={() => setSurface('landing')}
        />
      )}
    </AppShell>
  );
}

export default App;
