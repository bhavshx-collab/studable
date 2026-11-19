# PRODUCT ROADMAP — STUDABLE
> **Status:** Pre-development planning & Phase 0 execution  
> **Last updated:** November 2026

---

## OVERVIEW

This roadmap defines the development sequence for Studable from its initial frontend prototype into a production-ready, scalable social connection and networking platform.

---

## PHASE BREAKDOWN

### Phase 0 — Frontend Hardening & Clean Baseline (Current)
- Complete rebranding from "Valence" to "Studable".
- Robust HTML5 URL-based routing (direct URL, back/forward, refresh).
- Removal of visible prototype testing controls from public views.
- Frontend Admin authorization guard & route isolation.
- Verification and audit sign-off.

### Phase 1 — Backend Foundation & Authentication
- FastAPI application scaffolding.
- PostgreSQL database setup and SQLAlchemy ORM models.
- JWT authentication with secure cookies, bcrypt password hashing.
- Register, login, token refresh, and logout endpoints.
- Frontend auth form wiring and session management.

### Phase 2 — User Profiles & Account Settings
- Profile management APIs (read, update).
- Avatar upload pipeline (multipart form, storage abstraction).
- Settings persistence (preferences, languages, topics).
- Real connection count calculation.

### Phase 3 — Connections System
- Connection request lifecycle (send, accept, reject, remove).
- Pending and accepted connection lists.
- Notifications trigger on connection updates.

### Phase 4 — Real-time Matching Engine
- Redis matching queues (Random and Interest-based).
- Matching worker service and compatibility filtering.
- WebSocket match proposal distribution.
- Mutual handshake acceptance protocol.

### Phase 5 — Real-time 1-on-1 Messaging
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
