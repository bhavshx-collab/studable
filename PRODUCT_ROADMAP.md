# PRODUCT ROADMAP — STUDABLE
> **Status:** Phases 0, 1, 2, 3, 4, 5, 6, 7 Completed | Phase 8 Pending Approval  
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

### Phase 8 — Discovery & Recommendations (PENDING)
- Shared interest graph recommendations.
- Trending discussion topics aggregation.

### Phase 9 — Production Launch Readiness (PENDING)
- End-to-end integration testing.
- Rate limiting, CSRF protection, and Content Security Policy.
- Docker containers and production deployment.

---

## IMPLEMENTATION DEPENDENCY GRAPH

```
Phase 0 (Hardening) [ACTIVE]
       │
       ▼
Phase 1 (Auth & DB Foundation)
       │
       ▼
Phase 2 (Profiles & Settings)
      / \
     /   \
    ▼     ▼
Phase 3  Phase 4 (Matching Engine)
(Conns)   │
    │     ▼
    │    Phase 5 (Real-time Chat)
    │     │
    ▼     ▼
Phase 6 (Notifications)
    │
    ▼
Phase 7 (Safety & Moderation)
    │
    ▼
Phase 8 (Discovery)
    │
    ▼
Phase 9 (Production Hardening)
```
