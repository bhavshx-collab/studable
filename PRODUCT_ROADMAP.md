# PRODUCT ROADMAP — STUDABLE
> **Status:** Phases 0–8 Completed | Phase 9 Pending  
> **Last updated:** November 2026

---

## OVERVIEW

This roadmap defines the development sequence for Studable from its initial frontend prototype into a production-ready, scalable social connection and networking platform.

---

## PHASE BREAKDOWN

### Phase 0 — Frontend Hardening & Clean Baseline (COMPLETED)
- Complete rebranding from "Valence" to "Studable".
- Robust HTML5 URL-based routing (direct URL, back/forward, refresh).
- Removal of visible prototype testing controls from public views.
- Frontend Admin authorization guard & route isolation.
- Verification and audit sign-off.

### Phase 1 — Backend Foundation (COMPLETED)
- FastAPI application scaffolding and centralized configuration.
- PostgreSQL engine & session lifecycle management.
- Health check endpoints (`/api/v1/health`) with live DB probing.
- Modular architecture with test suite.

### Phase 2 & 3 — Database Models & Authentication (COMPLETED)
- 11 SQLAlchemy 2.0 ORM models covering Users, Auth, Connections, Conversations, Messages, Notifications, Reports, Blocks.
- Alembic database migration scripts.
- Argon2id password hashing and JWT access token issuance.
- Secure HttpOnly refresh token rotation cookies.
- Role-based authorization gates (`member` / `admin`).
- Frontend session restore and login/register integration.

### Phase 4 — User Availability & Presence Engine (COMPLETED)
- Real-time Redis-based presence state machine (`OFFLINE`, `ONLINE`, `AVAILABLE`, `BUSY`, `MATCHING`, `IN_CONVERSATION`).
- Authenticated WebSocket gateway (`/api/v1/ws/presence`) with heartbeats and connection manager.
- REST endpoints for presence query, availability listing, and live online user count.
- Multi-session/device support with sliding TTL.
- Frontend `presenceService.ts` and UI count integration.
- Graceful degradation when external services are unavailable.

### Phase 5 — Real-Time Matching Engine (COMPLETED)
- Redis matching queues (`matching:queue:random` and `matching:queue:interest`).
- Matching background worker service with distributed concurrency protection (`matching:worker:lock`).
- Deterministic compatibility scoring algorithm (interests 3x, languages 2x, audience 1.5x, category 1x, wait time bonus).
- Complete proposal lifecycle: `QUEUED` → `MATCH_FOUND` → `ACCEPTED` / `REJECTED` → `COMPLETED` / `EXPIRED` / `CANCELLED`.
- Expiring session leases and stale session cleanup (`cleanup_stale_sessions`).
- Short-lived single-use WebSocket tickets (`POST /api/v1/ws/ticket`) and Redis Pub/Sub multi-worker event routing.
- Real-time WebSocket matching channel (`/api/v1/ws/matching`) and REST matching endpoints.
- Frontend `matchingService.ts` and interactive lobby UI integration with countdown and mutual handshake.

### Phase 6 — Real-Time 1-on-1 Messaging (COMPLETED)
- Automatic conversation activation upon mutual match acceptance.
- Real-time 1-on-1 messaging WebSocket gateway (`/api/v1/ws/messaging`) with ticket authentication.
- Multi-worker event delivery via Redis Pub/Sub (`message.new`, `message.read`, `typing.start`, `typing.stop`, `conversation.ended`).
- Message persistence in PostgreSQL with status tracking (`sent`, `delivered`, `read`).
- Paginated message history with cursor (`before_id`), unread counter, and conversation termination.
- Bidirectional blocking enforcement at the message delivery layer.
- Frontend `messagingService.ts` integrated with `ChatPage` and `App.tsx`.

### Phase 7 — Safety, Moderation, Privacy & Verification (COMPLETED)
- Bidirectional blocking system with mutual exclusion in matching and messaging.
- User reporting with categorized reasons and conversation context.
- Secure Admin moderation REST endpoints (`/api/v1/admin/reports`, `/api/v1/admin/users`, `/api/v1/admin/metrics`).
- Report resolution workflows and automated/manual user suspensions.
- Rate limiting and input validation for spam prevention.
- Redis-backed password reset tokens (`/api/v1/auth/forgot-password`, `/api/v1/auth/reset-password`).
- Email verification token workflows.
- User privacy settings (`show_online_status`, `allow_random_discovery`) and GDPR-compliant soft-deletion (`DELETE /api/v1/users/me`).
- Comprehensive test coverage: 171/171 backend tests passing.

### Phase 8 — Production Readiness & Deployment (COMPLETED)
- Full-stack security gap remediation:
  - Age gating & COPPA compliance (minimum age 13 enforcement).
  - Message deduplication with Redis idempotency caching and client message ID tracking.
  - Delivery receipt tracking (`message.delivered`) across REST and WebSockets.
  - Origin verification and concurrent connection limits on WebSockets (`WS_MAX_CONNECTIONS_PER_USER=3`).
  - Privacy enforcement for hidden presence and random discovery filters.
  - Global session revocation (`revoke_all_user_sessions`) across PostgreSQL and Redis.
  - Security headers middleware and `slowapi` rate limiting.
- Asynchronous SMTP transactional email service (`aiosmtplib`).
- End-to-end two-user lifecycle automated integration test (`test_two_user_e2e.py`).
- 184/184 backend tests passing (100% pass rate).
- Production deployment configurations: `Dockerfile`, `docker-compose.prod.yml`, `render.yaml`, `railway.json`, `.github/workflows/ci.yml`, and `vercel.json`.
- Legal and compliance policies: `PRIVACY_POLICY.md`, `TERMS_OF_SERVICE.md`, and `COMMUNITY_GUIDELINES.md`.
- Comprehensive `DEPLOYMENT_GUIDE.md` and `PHASE_8_REPORT.md`.

### Phase 9 — Discovery, Recommendations & Post-Launch Growth (PENDING)
- Shared interest graph recommendations.
- Trending discussion topics aggregation.
- Mobile push notifications (Web Push / FCM).
- Audio/video networking rooms (WebRTC).

---

## IMPLEMENTATION DEPENDENCY GRAPH

```
Phase 0 (Hardening) [COMPLETED]
       │
       ▼
Phase 1 (Auth & DB Foundation) [COMPLETED]
       │
       ▼
Phase 2 & 3 (Profiles & Auth) [COMPLETED]
      / \
     /   \
    ▼     ▼
Phase 4 (Presence Engine) [COMPLETED]
    │
    ▼
Phase 5 (Matching Engine) [COMPLETED]
    │
    ▼
Phase 6 (Real-time Chat) [COMPLETED]
    │
    ▼
Phase 7 (Safety & Moderation) [COMPLETED]
    │
    ▼
Phase 8 (Production Readiness & Deployment) [COMPLETED]
    │
    ▼
Phase 9 (Discovery & Recommendations) [PENDING]
```
