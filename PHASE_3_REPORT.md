# Studable — Phase 3: Authentication & Authorization Report

**Status:** Completed & Verified  
**Date:** November 19, 2026  
**Author:** Senior Backend Engineer & Application Security Engineer  

---

## 1. Executive Summary

Phase 3 implements an enterprise-grade authentication and authorization subsystem for Studable. The architecture enforces password hashing via **Argon2id**, short-lived cryptographically signed **JWT access tokens** (15-minute TTL with `jti` anti-replay entropy), and **HttpOnly, Secure, SameSite=Strict refresh cookies** with server-side rotation and revocation in PostgreSQL.

Mock authentication has been cleanly replaced in the frontend with real asynchronous calls to the backend via `src/services/authApi.ts`, supporting real login, registration, automatic token injection, session refresh persistence on page reload, and secure logout.

---

## 2. Authentication Architecture

```
Client (React 19)                    FastAPI Backend                      PostgreSQL
     │                                      │                                  │
     │── POST /api/v1/auth/register ───────>│ (Validate username, email, pw)   │
     │                                      │── Hash with Argon2id ───────────>│ (INSERT user)
     │                                      │── Generate Refresh Token ───────>│ (INSERT refresh_token)
     │<── Set-Cookie: studable_refresh ─────│
     │<── Header: X-Access-Token ───────────│
     │                                      │
     │ (Memory-only token storage)          │
     │                                      │
     │── GET /api/v1/auth/me ──────────────>│ (Verify JWT signature & expiry)  │
     │   Authorization: Bearer <token>      │── Fetch user profile ───────────>│
     │<── 200 OK: UserMeResponse ───────────│
     │                                      │
     │── POST /api/v1/auth/refresh ────────>│ (Verify HttpOnly cookie)         │
     │   Cookie: studable_refresh=...       │── Revoke old token in DB ───────>│ (UPDATE revoked=true)
     │                                      │── Issue new token pair ─────────>│ (INSERT new token)
     │<── Set-Cookie: studable_refresh ─────│
     │<── 200 OK: { access_token } ─────────│
     │                                      │
     │── POST /api/v1/auth/logout ─────────>│ (Revoke token in DB) ───────────>│
     │<── Clear-Cookie: studable_refresh ───│
```

---

## 3. Endpoints Implemented

| Method | Path | Security / Access | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Public | Validates password complexity, checks duplicates, creates user, issues JWT access token + refresh cookie. |
| `POST` | `/api/v1/auth/login` | Public | Verifies credentials with Argon2id; constant-time dummy verify on nonexistent users defends against timing attacks. |
| `POST` | `/api/v1/auth/refresh` | Cookie (`HttpOnly`) | Validates refresh token, executes rotation (revoking previous token), issues new access token. |
| `POST` | `/api/v1/auth/logout` | Cookie (`HttpOnly`) | Revokes refresh token in database, clears cookie (idempotent 204). |
| `GET` | `/api/v1/auth/me` | Bearer JWT | Returns current authenticated user profile; rejects expired or invalid tokens. |
| `POST` | `/api/v1/auth/change-password` | Bearer JWT | Verifies current password before updating to new Argon2id hash (204). |
| `POST` | `/api/v1/auth/verify-email` | Public (Stub) | Returns structured response indicating email service is queued for future phase. |
| `POST` | `/api/v1/auth/resend-verification` | Public (Stub) | Safe stub response without leaking existence of email. |
| `POST` | `/api/v1/auth/forgot-password` | Public (Stub) | Returns generic confirmation preventing email enumeration. |
| `POST` | `/api/v1/auth/reset-password` | Public (Stub) | Safe stub response. |

---

## 4. Security Hardening Measures

1. **Argon2id Password Hashing**:
   - Salted with high memory and time cost parameters via `argon2-cffi`.
   - Never stored in plaintext anywhere in code or database.
   - Response models (`RegisterResponse`, `UserMeResponse`, `TokenResponse`) explicitly omit all password fields.
2. **Timing Attack Protection**:
   - `login_user()` executes a genuine Argon2id verification against a pre-computed dummy hash when an email is not found, ensuring uniform response times regardless of user existence.
3. **Token Security**:
   - JWT Access tokens carry 15-minute expiration, `jti` entropy against replay attacks, and `role` claims (`member`/`admin`).
   - Stored strictly in JavaScript memory on the client (never in `localStorage` or `sessionStorage` where they are vulnerable to XSS).
   - Refresh tokens are 64-byte random URL-safe strings; only their SHA-256 digest is stored in the database.
4. **Backend Authorization Guard**:
   - `require_admin` dependency checks the `role == 'admin'` claim on the database user record, not trusting client-side claims.
   - Suspended accounts (`is_suspended == True`) are rejected with HTTP 403 on all authenticated routes.

---

## 5. Frontend Integration

- **API Service**: Built `src/services/authApi.ts` managing token lifecycle, in-memory tokens, credentials inclusion, and structured `AuthError` exception handling.
- **Login & Registration Flow**: [AuthOnboardingPage.tsx](file:///c:/Users/bhavesh%20kumar/Downloads/studable-main/studable-main/src/pages/AuthOnboardingPage.tsx) calls real backend endpoints with visual loading spinners (`Loader2`), validation feedback, and duplicate detection.
- **Session Persistence**: [App.tsx](file:///c:/Users/bhavesh%20kumar/Downloads/studable-main/studable-main/src/App.tsx) automatically attempts a silent session restoration on mount via `refreshApi()` -> `getMeApi()`.
- **Logout**: Seamlessly integrated into `SettingsPage.tsx` via `logoutApi()`.
- **UI Integrity**: 100% of existing visual design, layouts, colors, and typography preserved.

---

## 6. Automated Test Results

Ran complete pytest suite:
- Total tests: **53 tests**
- Pass rate: **100% (53 passed in 7.87s)**
- Coverage includes: password complexity rejection, duplicate username/email, token tampered rejection, refresh token rotation, logout revocation, authenticated /me access, unauthenticated rejection, timing attack defense, and password leak prevention.
