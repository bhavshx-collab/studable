export type AccountCategory = 'Student' | 'Working Professional' | 'Entrepreneur' | 'Mentor';

export type InterestTag =
  | 'Technology'
  | 'AI and Machine Learning'
  | 'Programming'
  | 'Startups'
  | 'Business'
  | 'Career Development'
  | 'Design'
  | 'Education'
  | 'Personal Growth'
  | 'Entrepreneurship'
  | 'Other';

export type MatchingMode = 'random' | 'interest';
export type AudiencePreference = 'Students' | 'Professionals' | 'Anyone';

export type PresenceStatus =
  | 'OFFLINE'
  | 'ONLINE'
  | 'AVAILABLE'
  | 'BUSY'
  | 'MATCHING'
  | 'IN_CONVERSATION';

export interface UserProfile {
  id: string;
  displayName: string;
  avatarUrl?: string;
  category: AccountCategory;
  headline: string;
  bio: string;
  skills: string[];
  interests: InterestTag[];
  languages: string[];
  connectionCount: number;
  isVerified?: boolean;
  role?: 'member' | 'admin';
  presenceStatus?: PresenceStatus;
}

export interface OwnAccountSettings {
  email: string;
  preferredAudience: AudiencePreference;
  preferredLanguage: string;
  preferredTopics: string[];
  defaultMatchingMode: MatchingMode;
  allowRandomDiscovery: boolean;
  showOnlineStatus: boolean;
  notifyConnectionRequests: boolean;
  notifyMessages: boolean;
}

export type MatchLifecycleState =
  | 'idle'
  | 'queuing'
  | 'match_found'
  | 'awaiting_peer_acceptance'
  | 'no_match'
  | 'timeout'
  | 'error';

export type MatchRequestStatus =
  | 'IDLE'
  | 'QUEUED'
  | 'MATCH_FOUND'
  | 'ACCEPTED'
  | 'REJECTED'
  | 'CANCELLED'
  | 'EXPIRED'
  | 'COMPLETED';

export interface MatchProposal {
  matchId: string;
  peer: UserProfile;
  topic: string;
  mode: MatchingMode;
  expiresAtIso: string;
  selfAccepted: boolean;
  peerAccepted: boolean;
  score?: number;
  conversationId?: string;
}

export interface ChatMessage {
  id: string;
  conversationId: string;
  senderId: string;
  content: string;
  createdAt: string;
  status?: 'sent' | 'delivered';
}

export interface ConnectionRecord {
  id: string;
  user: UserProfile;
  status: 'accepted' | 'pending_incoming' | 'pending_outgoing';
  connectedAt?: string;
  sharedTopic?: string;
}

export interface AppNotification {
  id: string;
  type: 'connection_request' | 'connection_accepted' | 'new_message' | 'account_update' | 'moderation';
  title: string;
  description: string;
  timestamp: string;
  read: boolean;
  relatedUserId?: string;
}

export interface ModerationReport {
  id: string;
  reportedUserId: string;
  reportedUserName: string;
  reporterId: string;
  reason: string;
  details: string;
  status: 'pending' | 'resolved_warned' | 'resolved_suspended' | 'dismissed';
  createdAt: string;
}

export interface PlatformMetrics {
  totalRegisteredUsers: number | null;
  activeUsers24h: number | null;
  totalMatches: number | null;
  totalConversations: number | null;
}
