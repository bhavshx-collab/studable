/**
 * Studable — Authentication API Service
 * 
 * Provides real HTTP communication with the FastAPI backend (/api/v1/auth/*).
 * Stores access tokens strictly in memory (never localStorage).
 * Sends HttpOnly cookies for refresh tokens via credentials: 'include'.
 */

import { UserProfile } from '../types/domain';

// In production on Vercel (or via Vite dev proxy), API routes are served at /api/... on the same origin.
// In SSR/functions with Vercel service bindings, BACKEND_URL is injected.
// VITE_API_URL can still override if set explicitly.
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

// In-memory access token storage
let _accessToken: string | null = null;

export function getAccessToken(): string | null {
  return _accessToken;
}

export function setAccessToken(token: string | null): void {
  _accessToken = token;
}

export interface AuthUserResponse {
  id: string;
  username: string;
  email: string;
  display_name: string;
  category?: string;
  headline?: string | null;
  bio?: string | null;
  avatar_url?: string | null;
  is_verified?: boolean;
  role?: string;
}

export interface RegisterPayload {
  username: string;
  email: string;
  password: string;
  displayName: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export class AuthError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'AuthError';
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Register a new user on the Studable backend.
 */
export async function registerApi(payload: RegisterPayload): Promise<{ user: AuthUserResponse; accessToken: string }> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({
      username: payload.username,
      email: payload.email,
      password: payload.password,
      display_name: payload.displayName,
    }),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const detail = typeof data.detail === 'string' 
      ? data.detail 
      : Array.isArray(data.detail)
      ? data.detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join(' ')
      : 'Registration failed. Please verify your details.';
    throw new AuthError(response.status, detail);
  }

  // Access token returned via header
  const accessToken = response.headers.get('X-Access-Token') || '';
  setAccessToken(accessToken);

  return {
    user: data,
    accessToken,
  };
}

/**
 * Log in with email and password.
 */
export async function loginApi(payload: LoginPayload): Promise<{ accessToken: string }> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({
      email: payload.email,
      password: payload.password,
    }),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const detail = typeof data.detail === 'string' 
      ? data.detail 
      : 'Invalid email or password.';
    throw new AuthError(response.status, detail);
  }

  const accessToken = data.access_token || '';
  setAccessToken(accessToken);

  return { accessToken };
}

/**
 * Rotate refresh token and obtain a new access token.
 */
export async function refreshApi(): Promise<{ accessToken: string }> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
    method: 'POST',
    credentials: 'include',
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    setAccessToken(null);
    throw new AuthError(response.status, data.detail || 'Session expired.');
  }

  const accessToken = data.access_token || '';
  setAccessToken(accessToken);

  return { accessToken };
}

/**
 * Revoke session and remove HttpOnly cookie.
 */
export async function logoutApi(): Promise<void> {
  try {
    await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    });
  } finally {
    setAccessToken(null);
  }
}

/**
 * Fetch current authenticated user from backend.
 */
export async function getMeApi(): Promise<UserProfile> {
  const token = getAccessToken();
  if (!token) {
    throw new AuthError(401, 'No authentication token present.');
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    credentials: 'include',
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new AuthError(response.status, data.detail || 'Failed to retrieve profile.');
  }

  return {
    id: data.id,
    displayName: data.display_name,
    avatarUrl: data.avatar_url || undefined,
    category: data.category || 'Student',
    headline: data.headline || `${data.category || 'Member'} on Studable`,
    bio: data.bio || '',
    skills: [],
    interests: [],
    languages: data.preferred_language ? [data.preferred_language] : ['English'],
    connectionCount: 0,
    isVerified: data.is_verified ?? false,
    role: data.role || 'member',
  };
}
