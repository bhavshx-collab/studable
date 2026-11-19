# PRODUCT ROADMAP — STUDABLE
> **Status:** Phases 0, 1, 2, 3, 4 Completed | Phase 5 Pending Approval  
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

### Phase 5 — Real-time Matching Engine (NEXT)
- Redis matching queues (Random and Interest-based).
- Matching worker service and compatibility filtering.
- WebSocket match proposal distribution.
- Mutual handshake acceptance protocol.

### Phase 6 — Real-time 1-on-1 Messaging
- WebSocket conversation gateway.
- Real-time message exchange, delivery status, typing indicators.
- Persistent conversation history in PostgreSQL.

### Phase 6 — Notification System
- Notification center API and models.
- Push/WebSocket real-time notification delivery.
- Unread badge counter synchronization.

### Phase 7 — Trust & Safety
- Reporting system with categorized reasons and notes.
- User blocking and mutual exclusion in matching queues.
- Admin moderation dashboard with real database backing.

### Phase 8 — Discovery & Recommendations
- Shared interest graph recommendations.
- Trending discussion topics aggregation.

### Phase 9 — Production Launch Readiness
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
