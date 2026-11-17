import {
  AudiencePreference,
  ChatMessage,
  ConnectionRecord,
  InterestTag,
  MatchProposal,
  MatchingMode,
  UserProfile,
} from '../types/domain';

export interface EnqueueMatchPayload {
  mode: MatchingMode;
  audience: AudiencePreference;
  language: string;
  interests?: InterestTag[];
  topic?: string;
}

/**
 * Contract designed for FastAPI REST + Redis Matching Queue + WebSocket gateway.
 * Swap PrototypeAdapter with LiveBackendAdapter once backend endpoints are live.
 */
export interface ValenceServiceContract {
  getLiveOnlineCount(): Promise<number | null>;
  enqueueForMatch(payload: EnqueueMatchPayload): Promise<{ queueTicketId: string }>;
  cancelMatchQueue(queueTicketId: string): Promise<void>;
  respondToMatchProposal(matchId: string, accept: boolean): Promise<MatchProposal>;
  sendMessage(conversationId: string, content: string): Promise<ChatMessage>;
  endConversation(conversationId: string): Promise<void>;
  requestConnection(targetUserId: string): Promise<void>;
  respondConnection(connectionId: string, accept: boolean): Promise<ConnectionRecord>;
  removeConnection(connectionId: string): Promise<void>;
  reportUser(targetUserId: string, reason: string, details: string): Promise<void>;
  blockUser(targetUserId: string): Promise<void>;
  getProfile(userId: string): Promise<UserProfile>;
}
