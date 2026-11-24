/**
 * Studable — Real-Time Matching Service (Phase 5)
 *
 * REST client and WebSocket manager for the real-time matching engine.
 * Connects to FastAPI backend (/api/v1/matching/* and /api/v1/ws/matching).
 */

import { MatchingMode, MatchProposal, UserProfile } from '../types/domain';
import { getAccessToken } from './authApi';

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

// ── REST API Functions ────────────────────────────────────────────────────────

/**
 * Request a short-lived single-use WebSocket ticket.
 */
export async function getWsTicket(): Promise<string | null> {
  const token = getAccessToken();
  if (!token) return null;

  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/ws/ticket`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      credentials: 'include',
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.ticket || null;
  } catch {
    return null;
  }
}

/**
 * Join the matching queue ('random' or 'interest').
 */
export async function joinMatchingQueue(mode: MatchingMode): Promise<{ success: boolean; detail?: string }> {
  const token = getAccessToken();
  if (!token) throw new Error('Not authenticated');

  const res = await fetch(`${API_BASE_URL}/api/v1/matching/join`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    credentials: 'include',
    body: JSON.stringify({ mode }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to join queue' }));
    throw new Error(err.detail || 'Failed to join matching queue');
  }

  const data = await res.json();
  return { success: true, detail: data.message };
}

/**
 * Leave the matching queue.
 */
export async function cancelMatchingQueue(): Promise<boolean> {
  const token = getAccessToken();
  if (!token) return false;

  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/matching/cancel`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      credentials: 'include',
    });
    return res.ok;
  } catch {
    return false;
  }
}

/**
 * Fetch current matching queue / proposal status.
 */
export async function getMatchStatus(): Promise<any> {
  const token = getAccessToken();
  if (!token) return { status: 'IDLE' };

  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/matching/status`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      credentials: 'include',
    });
    if (!res.ok) return { status: 'IDLE' };
    return await res.json();
  } catch {
    return { status: 'IDLE' };
  }
}

/**
 * Accept an active match proposal.
 */
export async function acceptMatchProposal(matchId: string): Promise<any> {
  const token = getAccessToken();
  if (!token) throw new Error('Not authenticated');

  const res = await fetch(`${API_BASE_URL}/api/v1/matching/${matchId}/accept`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    credentials: 'include',
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to accept match' }));
    throw new Error(err.detail || 'Failed to accept match proposal');
  }

  return await res.json();
}

/**
 * Decline an active match proposal.
 */
export async function rejectMatchProposal(matchId: string): Promise<any> {
  const token = getAccessToken();
  if (!token) return false;

  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/matching/${matchId}/reject`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      credentials: 'include',
    });
    return res.ok;
  } catch {
    return false;
  }
}

/**
 * Fetch match history.
 */
export async function getMatchHistory(limit = 20, offset = 0): Promise<any> {
  const token = getAccessToken();
  if (!token) return { items: [], count: 0 };

  try {
    const res = await fetch(
      `${API_BASE_URL}/api/v1/matching/history?limit=${limit}&offset=${offset}`,
      {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        credentials: 'include',
      }
    );
    if (!res.ok) return { items: [], count: 0 };
    return await res.json();
  } catch {
    return { items: [], count: 0 };
  }
}

// ── WebSocket Matching Client ─────────────────────────────────────────────────

export type MatchingEventListener = (event: any) => void;

class MatchingWebSocketManager {
  private ws: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private isExplicitlyClosed = false;
  private listeners: Set<MatchingEventListener> = new Set();

  public async connect(): Promise<void> {
    const token = getAccessToken();
    if (!token) return;

    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.isExplicitlyClosed = false;

    // Prefer short-lived ticket to prevent token exposure in URL
    const ticket = await getWsTicket();
    const wsUrl = ticket
      ? `${WS_BASE_URL}/api/v1/ws/matching?ticket=${encodeURIComponent(ticket)}`
      : `${WS_BASE_URL}/api/v1/ws/matching?token=${encodeURIComponent(token)}`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        // Connected
      };

      this.ws.onmessage = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          this.emit(data);
        } catch {
          // Ignore invalid frames
        }
      };

      this.ws.onclose = () => {
        if (!this.isExplicitlyClosed) {
          this.reconnectTimer = setTimeout(() => this.connect(), 4000);
        }
      };

      this.ws.onerror = () => {
        // Handled via onclose
      };
    } catch {
      // Connect error handled
    }
  }

  public disconnect(): void {
    this.isExplicitlyClosed = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  public onEvent(listener: MatchingEventListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private emit(eventData: any): void {
    this.listeners.forEach((fn) => {
      try {
        fn(eventData);
      } catch {
        // Listener error swallowed
      }
    });
  }
}

export const matchingWs = new MatchingWebSocketManager();
