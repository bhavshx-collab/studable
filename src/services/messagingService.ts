/**
 * Studable — Real-Time Messaging & Safety Service (Phase 6 & 7)
 *
 * REST client and WebSocket manager for:
 * - 1-on-1 conversations & chat messages
 * - Typing indicators & read receipts
 * - User blocking & reporting
 * - Admin moderation API
 */

import { ChatMessage, ModerationReport, PlatformMetrics, UserProfile } from '../types/domain';
import { getAccessToken } from './authApi';
import { getWsTicket } from './matchingService';

const getApiBaseUrl = (): string => {
  if (typeof process !== 'undefined' && process.env?.BACKEND_URL) {
    return process.env.BACKEND_URL.replace(/\/$/, '');
  }
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL.replace(/\/$/, '');
  }
  return '';
};

const API_BASE_URL = getApiBaseUrl();
const WS_BASE_URL = API_BASE_URL
  ? API_BASE_URL.replace(/^http/, 'ws')
  : (typeof window !== 'undefined'
      ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
      : 'ws://localhost:8000');

// ── Types ────────────────────────────────────────────────────────────────────

export interface BackendConversation {
  id: string;
  participant_a?: string | null;
  participant_b?: string | null;
  topic?: string | null;
  matching_mode?: string | null;
  status: 'active' | 'ended';
  created_at: string;
  ended_at?: string | null;
}

export interface BackendMessage {
  id: string;
  conversation_id: string;
  sender_id?: string | null;
  content: string;
  status: 'sent' | 'delivered' | 'read';
  created_at: string;
}

export type MessagingEventHandler = (event: any) => void;

// ── WebSocket Manager ────────────────────────────────────────────────────────

class MessagingWebSocketManager {
  private ws: WebSocket | null = null;
  private isConnecting = false;
  private listeners = new Set<MessagingEventHandler>();
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

  public subscribe(handler: MessagingEventHandler): () => void {
    this.listeners.add(handler);
    return () => {
      this.listeners.delete(handler);
    };
  }

  private emit(event: any): void {
    this.listeners.forEach((listener) => {
      try {
        listener(event);
      } catch (err) {
        console.error('Messaging listener error:', err);
      }
    });
  }

  public async connect(): Promise<void> {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }
    if (this.isConnecting) return;
    this.isConnecting = true;

    try {
      const ticket = await getWsTicket();
      const wsUrl = ticket
        ? `${WS_BASE_URL}/api/v1/ws/messaging?ticket=${encodeURIComponent(ticket)}`
        : null;

      if (!wsUrl) {
        this.isConnecting = false;
        return;
      }

      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.isConnecting = false;
        this.startHeartbeat();
      };

      this.ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          this.emit(data);
        } catch {
          // ignore non-json
        }
      };

      this.ws.onclose = () => {
        this.cleanup();
        this.scheduleReconnect();
      };

      this.ws.onerror = () => {
        this.cleanup();
      };
    } catch {
      this.cleanup();
    }
  }

  public send(data: object): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  public sendMessage(conversationId: string, content: string): void {
    this.send({
      type: 'message.send',
      conversation_id: conversationId,
      content,
    });
  }

  public sendTyping(conversationId: string, isTyping: boolean): void {
    this.send({
      type: isTyping ? 'typing.start' : 'typing.stop',
      conversation_id: conversationId,
    });
  }

  public markRead(conversationId: string): void {
    this.send({
      type: 'message.read',
      conversation_id: conversationId,
    });
  }

  private startHeartbeat(): void {
    if (this.heartbeatInterval) clearInterval(this.heartbeatInterval);
    this.heartbeatInterval = setInterval(() => {
      this.send({ type: 'heartbeat' });
    }, 25000);
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimeout) clearTimeout(this.reconnectTimeout);
    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, 5000);
  }

  private cleanup(): void {
    this.isConnecting = false;
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  public disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    this.cleanup();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

export const messagingWs = new MessagingWebSocketManager();

// ── REST API Functions ────────────────────────────────────────────────────────

export async function getConversationsApi(): Promise<BackendConversation[]> {
  const token = getAccessToken();
  if (!token) return [];
  const res = await fetch(`${API_BASE_URL}/api/v1/conversations`, {
    headers: { Authorization: `Bearer ${token}` },
    credentials: 'include',
  });
  if (!res.ok) return [];
  return res.json();
}

export async function getConversationMessagesApi(
  conversationId: string,
  limit = 50,
  before?: string
): Promise<ChatMessage[]> {
  const token = getAccessToken();
  if (!token) return [];
  const url = new URL(`${API_BASE_URL}/api/v1/conversations/${conversationId}/messages`);
  url.searchParams.set('limit', String(limit));
  if (before) url.searchParams.set('before', before);

  const res = await fetch(url.toString(), {
    headers: { Authorization: `Bearer ${token}` },
    credentials: 'include',
  });
  if (!res.ok) return [];
  const rows: BackendMessage[] = await res.json();
  return rows.map((r) => ({
    id: r.id,
    conversationId: r.conversation_id,
    senderId: r.sender_id || '',
    content: r.content,
    createdAt: r.created_at,
    status: r.status,
  }));
}

export async function sendMessageApi(conversationId: string, content: string): Promise<ChatMessage | null> {
  const token = getAccessToken();
  if (!token) return null;
  const res = await fetch(`${API_BASE_URL}/api/v1/conversations/${conversationId}/messages`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ content }),
    credentials: 'include',
  });
  if (!res.ok) return null;
  const r: BackendMessage = await res.json();
  return {
    id: r.id,
    conversationId: r.conversation_id,
    senderId: r.sender_id || '',
    content: r.content,
    createdAt: r.created_at,
    status: r.status,
  };
}

export async function endConversationApi(conversationId: string): Promise<boolean> {
  const token = getAccessToken();
  if (!token) return false;
  const res = await fetch(`${API_BASE_URL}/api/v1/conversations/${conversationId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
    credentials: 'include',
  });
  return res.ok;
}

export async function getUnreadCountApi(): Promise<number> {
  const token = getAccessToken();
  if (!token) return 0;
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/conversations/unread-count`, {
      headers: { Authorization: `Bearer ${token}` },
      credentials: 'include',
    });
    if (!res.ok) return 0;
    const data = await res.json();
    return data.unread_count ?? 0;
  } catch {
    return 0;
  }
}

// ── Safety & Moderation API ──────────────────────────────────────────────────

export async function blockUserApi(userId: string): Promise<boolean> {
  const token = getAccessToken();
  if (!token) return false;
  const res = await fetch(`${API_BASE_URL}/api/v1/users/${userId}/block`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    credentials: 'include',
  });
  return res.ok;
}

export async function unblockUserApi(userId: string): Promise<boolean> {
  const token = getAccessToken();
  if (!token) return false;
  const res = await fetch(`${API_BASE_URL}/api/v1/users/${userId}/block`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
    credentials: 'include',
  });
  return res.ok;
}

export async function reportUserApi(
  userId: string,
  reason: string,
  details?: string,
  conversationId?: string
): Promise<boolean> {
  const token = getAccessToken();
  if (!token) return false;
  const res = await fetch(`${API_BASE_URL}/api/v1/users/${userId}/report`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ reason, details, conversation_id: conversationId }),
    credentials: 'include',
  });
  return res.ok;
}

export async function updatePrivacyApi(showOnlineStatus?: boolean, allowRandomDiscovery?: boolean): Promise<boolean> {
  const token = getAccessToken();
  if (!token) return false;
  const res = await fetch(`${API_BASE_URL}/api/v1/users/me/privacy`, {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      show_online_status: showOnlineStatus,
      allow_random_discovery: allowRandomDiscovery,
    }),
    credentials: 'include',
  });
  return res.ok;
}

export async function deleteAccountApi(): Promise<boolean> {
  const token = getAccessToken();
  if (!token) return false;
  const res = await fetch(`${API_BASE_URL}/api/v1/users/me`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
    credentials: 'include',
  });
  return res.ok;
}

// ── Admin API ────────────────────────────────────────────────────────────────

export async function getAdminReportsApi(): Promise<ModerationReport[]> {
  const token = getAccessToken();
  if (!token) return [];
  const res = await fetch(`${API_BASE_URL}/api/v1/admin/reports`, {
    headers: { Authorization: `Bearer ${token}` },
    credentials: 'include',
  });
  if (!res.ok) return [];
  const rows = await res.json();
  return rows.map((r: any) => ({
    id: r.id,
    reportedUserId: r.reported_user_id || '',
    reportedUserName: r.reported_user_id || 'User',
    reporterId: r.reporter_id || '',
    reason: r.reason,
    details: r.details || '',
    status: r.status,
    createdAt: r.created_at,
  }));
}

export async function resolveReportApi(
  reportId: string,
  action: 'resolved_warned' | 'resolved_suspended' | 'dismissed'
): Promise<boolean> {
  const token = getAccessToken();
  if (!token) return false;
  const res = await fetch(`${API_BASE_URL}/api/v1/admin/reports/${reportId}/resolve`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ action }),
    credentials: 'include',
  });
  return res.ok;
}

export async function suspendUserApi(userId: string): Promise<boolean> {
  const token = getAccessToken();
  if (!token) return false;
  const res = await fetch(`${API_BASE_URL}/api/v1/admin/users/${userId}/suspend`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    credentials: 'include',
  });
  return res.ok;
}

export async function unsuspendUserApi(userId: string): Promise<boolean> {
  const token = getAccessToken();
  if (!token) return false;
  const res = await fetch(`${API_BASE_URL}/api/v1/admin/users/${userId}/suspend`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
    credentials: 'include',
  });
  return res.ok;
}

export async function getAdminMetricsApi(): Promise<PlatformMetrics | null> {
  const token = getAccessToken();
  if (!token) return null;
  const res = await fetch(`${API_BASE_URL}/api/v1/admin/metrics`, {
    headers: { Authorization: `Bearer ${token}` },
    credentials: 'include',
  });
  if (!res.ok) return null;
  const m = await res.json();
  return {
    totalRegisteredUsers: m.total_users,
    activeUsers24h: m.total_users,
    totalMatches: m.total_matches,
    totalConversations: m.total_conversations,
  };
}
