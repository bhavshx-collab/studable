# BACKEND ARCHITECTURE — STUDABLE
> **Status:** Planned — not yet implemented  
> **Last updated:** November 2026  
> **Tech stack:** Python · FastAPI · PostgreSQL · SQLAlchemy · WebSockets · Redis

---

## 1. HIGH-LEVEL ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT (Browser)                      │
│   React 19 · TypeScript · Vite · Tailwind CSS               │
│                                                              │
│   REST calls (axios)       WebSocket connections             │
└────────────────┬───────────────────┬────────────────────────┘
                 │                   │
                 ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Application                     │
│                                                              │
│   REST Router           WebSocket Gateway                   │
│   /api/v1/*             /ws/*                               │
│                                                              │
│   Auth Middleware · Rate Limiting · CORS · CSP              │
└────────────────┬───────────────────┬────────────────────────┘
                 │                   │
        ┌────────┘       ┌───────────┘
        ▼                ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐
│  PostgreSQL  │   │    Redis     │   │   File Storage (S3)  │
│              │   │              │   │                      │
│ Users        │   │ Match queues │   │ Avatar images        │
│ Connections  │   │ Presence     │   │ (dev: local disk)    │
│ Messages     │   │ WS sessions  │   │ (prod: S3-compat.)   │
│ Reports      │   │ Rate limits  │   └──────────────────────┘
│ Notifications│   │ JWT blocklist│
└──────────────┘   └──────────────┘
```

---

## 2. PROPOSED BACKEND FOLDER STRUCTURE

```
backend/
├── main.py                        # FastAPI app factory + router mounting
├── requirements.txt
├── .env.example
├── alembic/                       # Database migrations
│   ├── env.py
│   └── versions/
├── app/
│   ├── core/
│   │   ├── config.py              # Settings from environment variables (pydantic-settings)
│   │   ├── security.py            # JWT creation, verification, bcrypt hashing
│   │   ├── database.py            # SQLAlchemy engine + session factory
│   │   ├── redis.py               # Redis connection pool
│   │   └── dependencies.py        # FastAPI dependency injectors (get_db, get_current_user)
│   ├── models/                    # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── connection.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── notification.py
│   │   ├── report.py
│   │   └── block.py
│   ├── schemas/                   # Pydantic request/response schemas
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── connection.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── notification.py
│   │   ├── matching.py
│   │   └── moderation.py
│   ├── routers/                   # FastAPI APIRouter modules
│   │   ├── auth.py                # /api/v1/auth/*
│   │   ├── users.py               # /api/v1/users/*
│   │   ├── connections.py         # /api/v1/connections/*
│   │   ├── conversations.py       # /api/v1/conversations/*
│   │   ├── notifications.py       # /api/v1/notifications/*
│   │   ├── matching.py            # /api/v1/matching/*
│   │   ├── moderation.py          # /api/v1/moderation/*
│   │   └── admin.py               # /api/v1/admin/*
│   ├── websockets/
│   │   ├── manager.py             # WebSocket connection manager (room-based pub/sub)
│   │   ├── matching_ws.py         # /ws/matching — match proposals
│   │   └── conversation_ws.py     # /ws/conversations/{convId} — real-time chat
│   ├── services/                  # Business logic layer
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── connection_service.py
│   │   ├── matching_service.py    # Queue management, match scoring
│   │   ├── conversation_service.py
│   │   ├── notification_service.py
│   │   └── moderation_service.py
│   └── workers/
│       └── matching_worker.py     # Background task: pull queue, pair users, emit proposals
```

---

## 3. DATABASE ENTITIES & SCHEMA

### 3.1 `users`

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        VARCHAR(32) UNIQUE NOT NULL,        -- URL-safe slug
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    display_name    VARCHAR(80) NOT NULL,
    category        VARCHAR(32) NOT NULL,               -- Student | Working Professional | Entrepreneur | Mentor
    headline        VARCHAR(160),
    bio             TEXT,
    avatar_url      VARCHAR(500),
    is_verified     BOOLEAN DEFAULT FALSE,
    is_suspended    BOOLEAN DEFAULT FALSE,
    role            VARCHAR(16) DEFAULT 'member',       -- member | admin
    show_online_status      BOOLEAN DEFAULT TRUE,
    allow_random_discovery  BOOLEAN DEFAULT TRUE,
    preferred_audience      VARCHAR(16) DEFAULT 'Anyone',
    preferred_language      VARCHAR(32) DEFAULT 'English',
    default_matching_mode   VARCHAR(16) DEFAULT 'interest',
    notify_connection_requests  BOOLEAN DEFAULT TRUE,
    notify_messages             BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ                         -- soft delete
);
```

### 3.2 `user_interests`

```sql
CREATE TABLE user_interests (
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    interest    VARCHAR(64) NOT NULL,
    PRIMARY KEY (user_id, interest)
);
```

### 3.3 `user_skills`

```sql
CREATE TABLE user_skills (
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    skill       VARCHAR(64) NOT NULL,
    PRIMARY KEY (user_id, skill)
);
```

### 3.4 `user_languages`

```sql
CREATE TABLE user_languages (
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    language    VARCHAR(32) NOT NULL,
    PRIMARY KEY (user_id, language)
);
```

### 3.5 `connections`

```sql
CREATE TABLE connections (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requester_id    UUID REFERENCES users(id) ON DELETE CASCADE,
    recipient_id    UUID REFERENCES users(id) ON DELETE CASCADE,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending | accepted | rejected
    shared_topic    VARCHAR(255),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (requester_id, recipient_id),
    CHECK (requester_id <> recipient_id)
);
```

### 3.6 `conversations`

```sql
CREATE TABLE conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_a   UUID REFERENCES users(id) ON DELETE SET NULL,
    participant_b   UUID REFERENCES users(id) ON DELETE SET NULL,
    topic           VARCHAR(255),
    matching_mode   VARCHAR(16),                            -- random | interest
    status          VARCHAR(16) DEFAULT 'active',           -- active | ended
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    ended_at        TIMESTAMPTZ
);
```

### 3.7 `messages`

```sql
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    sender_id       UUID REFERENCES users(id) ON DELETE SET NULL,
    content         TEXT NOT NULL,
    status          VARCHAR(16) DEFAULT 'sent',             -- sent | delivered | read
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation_created ON messages(conversation_id, created_at);
```

### 3.8 `notifications`

```sql
CREATE TABLE notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    type            VARCHAR(32) NOT NULL,     -- connection_request | connection_accepted | new_message | account_update | moderation
    title           VARCHAR(160) NOT NULL,
    description     TEXT,
    related_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    related_entity_id UUID,                  -- generic: conversation_id, connection_id, etc.
    is_read         BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_notifications_user_read ON notifications(user_id, is_read, created_at DESC);
```

### 3.9 `reports`

```sql
CREATE TABLE reports (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    reported_user_id    UUID REFERENCES users(id) ON DELETE SET NULL,
    conversation_id     UUID REFERENCES conversations(id) ON DELETE SET NULL,
    reason              VARCHAR(128) NOT NULL,
    details             TEXT,
    status              VARCHAR(32) DEFAULT 'pending',    -- pending | resolved_warned | resolved_suspended | dismissed
    moderator_id        UUID REFERENCES users(id) ON DELETE SET NULL,
    resolved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.10 `blocks`

```sql
CREATE TABLE blocks (
    blocker_id  UUID REFERENCES users(id) ON DELETE CASCADE,
    blocked_id  UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (blocker_id, blocked_id),
    CHECK (blocker_id <> blocked_id)
);
```

### 3.11 `refresh_tokens`

```sql
CREATE TABLE refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    token_hash  VARCHAR(255) UNIQUE NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked     BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 4. ENTITY RELATIONSHIPS

```
users ──< user_interests
users ──< user_skills
users ──< user_languages
users ──< connections (as requester OR recipient)
users ──< conversations (as participant_a OR participant_b)
users ──< messages (as sender)
users ──< notifications
users ──< reports (as reporter OR reported)
users ──< blocks (as blocker OR blocked)
users ──< refresh_tokens
conversations ──< messages
```

---

## 5. REST API ENDPOINTS

### Authentication — `/api/v1/auth`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | No | Create account |
| POST | `/auth/login` | No | Login, returns JWT pair |
| POST | `/auth/refresh` | Refresh token | Issue new access token |
| POST | `/auth/logout` | Access token | Revoke refresh token |
| POST | `/auth/change-password` | Access token | Change password |

### Users — `/api/v1/users`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/users/me` | Required | Get own full profile + settings |
| PUT | `/users/me` | Required | Update own profile |
| PUT | `/users/me/settings` | Required | Update privacy/notification settings |
| POST | `/users/me/avatar` | Required | Upload avatar image |
| DELETE | `/users/me` | Required | Soft-delete own account |
| GET | `/users/{userId}` | Required | Get public profile of any user |
| GET | `/users/suggestions` | Required | Interest-based suggested connections |
| POST | `/users/{userId}/block` | Required | Block a user |
| DELETE | `/users/{userId}/block` | Required | Unblock a user |
| GET | `/users/me/blocked` | Required | List blocked users |

### Connections — `/api/v1/connections`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/connections` | Required | List own connections (filter: status) |
| POST | `/connections` | Required | Send connection request |
| POST | `/connections/{connId}/accept` | Required | Accept incoming request |
| DELETE | `/connections/{connId}` | Required | Reject / cancel / remove connection |

### Matching — `/api/v1/matching`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/matching/enqueue` | Required | Enter matching queue |
| DELETE | `/matching/queue/{ticketId}` | Required | Leave matching queue |
| POST | `/matching/proposals/{matchId}/respond` | Required | Accept or decline a match proposal |

### Conversations — `/api/v1/conversations`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/conversations` | Required | List own conversations |
| GET | `/conversations/{convId}` | Required | Get conversation detail |
| GET | `/conversations/{convId}/messages` | Required | Paginated message history |
| POST | `/conversations/{convId}/end` | Required | End active conversation |

### Notifications — `/api/v1/notifications`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/notifications` | Required | Paginated notification list |
| POST | `/notifications/{notifId}/read` | Required | Mark single notification read |
| POST | `/notifications/read-all` | Required | Mark all notifications read |

### Moderation — `/api/v1/moderation`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/moderation/reports` | Required | Submit a report |

### Admin — `/api/v1/admin` (role: admin)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/admin/metrics` | Admin | Platform metrics |
| GET | `/admin/reports` | Admin | All reports with filters |
| POST | `/admin/reports/{reportId}/action` | Admin | Warn / dismiss / suspend |
| GET | `/admin/users` | Admin | Search users |
| POST | `/admin/users/{userId}/suspend` | Admin | Suspend user |
| POST | `/admin/users/{userId}/unsuspend` | Admin | Unsuspend user |

### Topics — `/api/v1/topics`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/topics/popular` | Required | Trending conversation topics |

---

## 6. WEBSOCKET ENDPOINTS

### 6.1 Matching WebSocket — `/ws/matching`

**Purpose:** Real-time delivery of match proposals and peer acceptance state.

**Authentication:** JWT passed as query parameter `?token=<access_token>`

**Message types (server → client):**

```json
{ "type": "queue_joined", "ticketId": "..." }
{ "type": "match_proposal", "matchId": "...", "peer": {...}, "topic": "...", "expiresAtIso": "..." }
{ "type": "peer_accepted", "matchId": "..." }
{ "type": "peer_declined", "matchId": "..." }
{ "type": "match_expired", "matchId": "..." }
{ "type": "conversation_ready", "conversationId": "..." }
{ "type": "online_count", "count": 42 }
```

**Message types (client → server):**

```json
{ "type": "accept_match", "matchId": "..." }
{ "type": "decline_match", "matchId": "..." }
{ "type": "ping" }
```

### 6.2 Conversation WebSocket — `/ws/conversations/{convId}`

**Purpose:** Real-time 1-on-1 text chat within an active conversation.

**Authentication:** JWT passed as query parameter `?token=<access_token>`

**Message types (server → client):**

```json
{ "type": "message", "id": "...", "senderId": "...", "content": "...", "createdAt": "...", "status": "delivered" }
{ "type": "typing", "senderId": "..." }
{ "type": "stop_typing", "senderId": "..." }
{ "type": "message_status", "messageId": "...", "status": "delivered" }
{ "type": "conversation_ended", "endedBy": "..." }
{ "type": "peer_disconnected" }
{ "type": "peer_reconnected" }
```

**Message types (client → server):**

```json
{ "type": "send_message", "content": "..." }
{ "type": "typing" }
{ "type": "stop_typing" }
{ "type": "ping" }
```

---

## 7. AUTHENTICATION STRATEGY

### 7.1 Mechanism

| Concern | Decision |
|---|---|
| Token type | JWT (JSON Web Tokens) |
| Access token TTL | 15 minutes |
| Refresh token TTL | 30 days |
| Refresh token storage | PostgreSQL `refresh_tokens` table (hashed) |
| Access token storage | Memory only (not in `localStorage`) — delivered via JSON response body |
| Refresh token storage (browser) | `httpOnly`, `Secure`, `SameSite=Strict` cookie |
| Password hashing | bcrypt (cost factor 12) |

### 7.2 Token Flow

```
1. POST /auth/login
   ← 200: { accessToken, user }
   ← Set-Cookie: refresh_token=<token>; HttpOnly; Secure; SameSite=Strict

2. Frontend stores accessToken in memory (React state or Zustand).

3. All API requests: Authorization: Bearer <accessToken>

4. When accessToken expires (401 response):
   POST /auth/refresh (cookie is sent automatically)
   ← 200: { accessToken }
   Frontend updates stored token and retries original request.

5. POST /auth/logout
   ← Revokes refresh token in database
   ← Clears cookie
```

### 7.3 Admin Role

- `users.role = 'admin'` column.
- JWT payload includes `"role": "admin"`.
- FastAPI dependency `require_admin_role` checks this claim on all `/admin/*` routes.
- Admin users are created via CLI seed script — no self-registration for admin.

---

## 8. MATCHING ENGINE DESIGN

### 8.1 Queue Data Structure (Redis)

```
Key: matching:queue:random:{audience}:{language}
Key: matching:queue:interest:{language}:{sorted_interest_hash}
Type: Sorted Set — score = enqueue timestamp (UNIX ms)
Value: { userId, ticketId, interests[], topic, enqueueTime }
TTL: 5 minutes (auto-expire stale tickets)
```

### 8.2 Matching Worker

The worker runs as a FastAPI background task (or a separate process):

```python
Every 500ms:
1. For each active queue:
   a. Pull top 2 users (by enqueue time)
   b. Check compatibility:
      - Neither has blocked the other
      - Neither is already in a pending match proposal
      - Language preference compatible
      - Audience category compatible
   c. If compatible:
      - Create MatchProposal (store in Redis with 30s TTL)
      - Push "match_proposal" event to both users' WebSocket connections
      - Remove both from queue
```

### 8.3 Match Proposal (Redis)

```
Key: matching:proposal:{matchId}
Type: Hash
Fields: userId_a, userId_b, accepted_a, accepted_b, topic, mode, expiresAt
TTL: 35 seconds (5s grace after the 30s proposal expiry shown to users)
```

### 8.4 Mutual Acceptance Flow

```
User accepts → POST /matching/proposals/{matchId}/respond { accept: true }
  → Service sets accepted_a or accepted_b = true in Redis
  → If both accepted:
      - Create Conversation in PostgreSQL
      - Push "conversation_ready" to both WebSocket connections
      - Frontend navigates to ChatPage with the conversationId
  → If one declines:
      - Push "peer_declined" to the accepting user
      - Delete proposal from Redis
  → If proposal expires (30s TTL):
      - Redis key auto-deletes
      - Worker notifies both users with "match_expired"
      - Both users are returned to idle state
```

---

## 9. PRESENCE & ONLINE COUNT

```
Key: presence:online              — Redis Set of active userIds
Key: presence:user:{userId}       — String, TTL = 60s, refreshed by WebSocket heartbeat
```

- When a user opens the matching WebSocket: `SADD presence:online {userId}`
- WebSocket client sends a `ping` every 30s; server refreshes the TTL key
- When WebSocket closes: `SREM presence:online {userId}`
- `GET /api/v1/matching` returns `SCARD presence:online` as `liveOnlineCount`

---

## 10. FILE STORAGE

| Environment | Strategy |
|---|---|
| Development | Local disk at `/uploads/avatars/` served via FastAPI StaticFiles |
| Production | AWS S3 or Cloudflare R2 (S3-compatible) |
| Upload flow | Client → `POST /users/me/avatar` (multipart) → Backend validates (type, size ≤ 5MB) → Stores → Returns `avatarUrl` |
| Security | Reject non-image MIME types, strip EXIF metadata, enforce max dimensions |

---

## 11. RATE LIMITING

| Endpoint | Limit |
|---|---|
| `POST /auth/register` | 5 per IP per hour |
| `POST /auth/login` | 10 per IP per 15 minutes |
| `POST /matching/enqueue` | 20 per user per hour |
| `POST /moderation/reports` | 10 per user per day |
| All other endpoints | 200 per user per minute |
| WebSocket messages | 1 per 500ms per connection (server-side throttle) |

Implementation: `slowapi` (Python) for REST endpoints; custom counter in Redis for WebSocket.

---

## 12. ENVIRONMENT VARIABLES

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/studable

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=<32-byte random hex string>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# File Storage
STORAGE_BACKEND=local                    # local | s3
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_S3_BUCKET=studable-avatars
AWS_S3_REGION=ap-south-1

# App
ENVIRONMENT=development                  # development | staging | production
CORS_ORIGINS=http://localhost:3000
ADMIN_EMAIL=admin@studable.app           # Seed admin account email

# Optional future
SENTRY_DSN=
GEMINI_API_KEY=                          # For future AI-powered matching or moderation
```

---

## 13. SECURITY CHECKLIST

| Concern | Implementation |
|---|---|
| Password hashing | bcrypt (cost 12) via `passlib` |
| JWT signing | HS256 with 32-byte secret from env |
| Refresh token rotation | Old token revoked on each refresh |
| SQL injection | SQLAlchemy ORM (parameterised queries) — no raw SQL |
| XSS | React escapes by default; CSP header configured |
| CSRF | `SameSite=Strict` cookie + CORS origin whitelist |
| Input validation | Pydantic v2 schemas on all request bodies |
| File upload | MIME type check, 5MB limit, EXIF strip |
| Rate limiting | slowapi + Redis counters |
| Admin access | JWT role claim + FastAPI dependency guard |
| Sensitive env vars | Never committed; loaded from environment only |
| Logging | No PII in logs (no passwords, emails in log lines) |
| Blocked user enforcement | Block table checked before queue pairing AND before connection request |
| Suspended user enforcement | `is_suspended` check in JWT middleware — 403 on all requests |

---

## 14. FRONTEND INTEGRATION CHECKLIST

This is what the frontend (`App.tsx`, pages, `apiContracts.ts`) must do to consume the backend:

| Task | File to modify |
|---|---|
| Implement `ValenceServiceContract` as `LiveBackendAdapter` using axios | `src/services/api.ts` (new) |
| Replace all `PROTOTYPE_*` mock imports with API calls | All pages |
| Add `@tanstack/react-query` for caching and loading states | App-wide |
| Add `react-router-dom` for URL routing | `App.tsx`, `src/router.tsx` (new) |
| Add `AuthGuard` and `AdminGuard` route wrappers | `src/components/guards/` (new) |
| Connect matching WebSocket in `ConnectLobbyPage` | `ConnectLobbyPage.tsx` |
| Connect conversation WebSocket in `ChatPage` | `ChatPage.tsx` |
| Handle WebSocket reconnection (exponential backoff) | `src/services/ws.ts` (new) |
| Handle API 401 → trigger token refresh → retry | `src/services/api.ts` |
| Show loading states for all data-fetching components | All pages |
| Show error states when API calls fail | All pages |
| Remove hardcoded `senderId: 'usr_self'` | `ChatPage.tsx` |
| Remove "Prototype Flow" state switcher | `ConnectLobbyPage.tsx` |
