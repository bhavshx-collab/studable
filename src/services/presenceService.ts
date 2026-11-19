/**
 * Studable — Real-Time Presence Service (Phase 4)
 *
 * REST client and WebSocket manager for user availability & presence tracking.
 * Connects to FastAPI backend (/api/v1/presence/* and /api/v1/ws/presence).
 */

import { PresenceStatus } from '../types/domain';
import { getAccessToken } from './authApi';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws');

// ── REST API functions ────────────────────────────────────────────────────────

/**
 * Fetch the current number of online (non-OFFLINE) users.
 * Returns null if the backend or Redis is unreachable.
 */
export async function getLiveOnlineCount(): Promise<number | null> {
  const token = getAccessToken();
  if (!token) return null;

  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/presence/online`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      credentials: 'include',
    });

    if (!res.ok) return null;
    const data = await res.json();
    return typeof data.online_count === 'number' ? data.online_count : null;
  } catch {
    return null;
  }
}

/**
 * Fetch the presence status of the currently authenticated user.
 */
export async function getMyPresence(): Promise<PresenceStatus | null> {
  const token = getAccessToken();
  if (!token) return null;

  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/presence/me`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      credentials: 'include',
    });

    if (!res.ok) return null;
    const data = await res.json();
    return data.status as PresenceStatus;
  } catch {
    return null;
  }
}

/**
 * Update the current user's status to AVAILABLE or BUSY.
 */
export async function setMyPresence(
  status: 'AVAILABLE' | 'BUSY'
): Promise<PresenceStatus> {
  const token = getAccessToken();
  if (!token) throw new Error('Not authenticated');

  const res = await fetch(`${API_BASE_URL}/api/v1/presence/me`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    credentials: 'include',
    body: JSON.stringify({ status }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to update presence' }));
    throw new Error(err.detail || 'Failed to update presence');
  }

  const data = await res.json();
  return data.status as PresenceStatus;
}

/**
 * Fetch another user's presence status.
 */
export async function getUserPresence(userId: string): Promise<PresenceStatus | null> {
  const token = getAccessToken();
  if (!token) return null;

  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/presence/users/${userId}`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      credentials: 'include',
    });

    if (!res.ok) return null;
    const data = await res.json();
    return data.status as PresenceStatus;
  } catch {
    return null;
  }
}

/**
 * Fetch user IDs currently in AVAILABLE status.
 */
export async function getAvailableUsers(limit = 50): Promise<string[]> {
  const token = getAccessToken();
  if (!token) return [];

  try {
    const res = await fetch(
      `${API_BASE_URL}/api/v1/presence/available?limit=${limit}`,
      {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        credentials: 'include',
      }
    );

    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data.user_ids) ? data.user_ids : [];
  } catch {
    return [];
  }
}

// ── WebSocket Presence Client ─────────────────────────────────────────────────

export type StatusListener = (status: PresenceStatus) => void;
export type ConnectionListener = (isConnected: boolean) => void;

class PresenceWebSocketManager {
  private ws: WebSocket | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private isExplicitlyClosed = false;
  private statusListeners: Set<StatusListener> = new Set();
  private connectionListeners: Set<ConnectionListener> = new Set();
  private currentStatus: PresenceStatus = 'OFFLINE';

  public connect(): void {
    const token = getAccessToken();
    if (!token) {
      this.updateStatus('OFFLINE');
      return;
    }

    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.isExplicitlyClosed = false;
    const wsUrl = `${WS_BASE_URL}/api/v1/ws/presence?token=${encodeURIComponent(token)}`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.notifyConnection(true);
      };

      this.ws.onmessage = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'presence.connected' || data.type === 'presence.updated') {
            if (data.status) {
              this.updateStatus(data.status as PresenceStatus);
            }
            if (data.heartbeat_interval) {
              this.startHeartbeat(data.heartbeat_interval);
            }
          } else if (data.type === 'heartbeat.ack') {
            if (data.status) {
              this.updateStatus(data.status as PresenceStatus);
            }
          }
        } catch {
          // Ignore invalid JSON
        }
      };

      this.ws.onclose = () => {
        this.stopHeartbeat();
        this.notifyConnection(false);
        this.updateStatus('OFFLINE');
        if (!this.isExplicitlyClosed && this.reconnectAttempts < this.maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 15000);
          this.reconnectAttempts += 1;
          this.reconnectTimer = setTimeout(() => this.connect(), delay);
        }
      };

      this.ws.onerror = () => {
        // Handled via onclose
      };
    } catch {
      this.updateStatus('OFFLINE');
      this.notifyConnection(false);
    }
  }

  public disconnect(): void {
    this.isExplicitlyClosed = true;
    this.stopHeartbeat();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.updateStatus('OFFLINE');
    this.notifyConnection(false);
  }

  public setStatus(newStatus: 'AVAILABLE' | 'BUSY'): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'set_status', status: newStatus }));
    } else {
      // Fallback to REST if WebSocket is not open
      setMyPresence(newStatus)
        .then((s) => this.updateStatus(s))
        .catch(() => {});
    }
  }

  public getStatus(): PresenceStatus {
    return this.currentStatus;
  }

  public onStatusChange(listener: StatusListener): () => void {
    this.statusListeners.add(listener);
    listener(this.currentStatus);
    return () => this.statusListeners.delete(listener);
  }

  public onConnectionChange(listener: ConnectionListener): () => void {
    this.connectionListeners.add(listener);
    return () => this.connectionListeners.delete(listener);
  }

  private startHeartbeat(intervalSeconds: number): void {
    this.stopHeartbeat();
    const intervalMs = Math.max(intervalSeconds * 1000, 10000);
    this.heartbeatTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'heartbeat' }));
      }
    }, intervalMs);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private updateStatus(newStatus: PresenceStatus): void {
    this.currentStatus = newStatus;
    this.statusListeners.forEach((fn) => {
      try {
        fn(newStatus);
      } catch {
        // Listener error swallowed
      }
    });
  }

  private notifyConnection(isConnected: boolean): void {
    this.connectionListeners.forEach((fn) => {
      try {
        fn(isConnected);
      } catch {
        // Listener error swallowed
      }
    });
  }
}

export const presenceWs = new PresenceWebSocketManager();
