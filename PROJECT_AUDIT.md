# PROJECT AUDIT — STUDABLE
> **Audited:** November 2026 · **Auditor:** Technical Co-Founder / Senior Software Architect  
> **Codebase path:** `studable-main/studable-main/`

---

## 1. PROJECT OVERVIEW

**Product name:** Studable (rebranded from "Valence" during Phase 0)  
**Category:** Social connection & networking platform  
**Stage:** Pre-MVP frontend — Phase 0 hardening underway  
**Purpose of this audit:** Record architectural baseline, components, state management, routes, issues, and resolution plan.

---

## 2. EXISTING ARCHITECTURE

### 2.1 Framework & Language

| Concern | Technology |
|---|---|
| UI Framework | React 19 (SPA client) |
| Language | TypeScript |
| Bundler | Vite 8 |
| Styling | Tailwind CSS v4 (via `@tailwindcss/vite` plugin) |
| Icon library | Lucide React |
| Animation library | Motion (`motion` package) |
| Fonts | Plus Jakarta Sans (display), Manrope (body), JetBrains Mono (mono) |

### 2.2 Folder Structure

```
studable-main/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── .env.example
├── .gitignore
├── metadata.json
├── PROJECT_AUDIT.md
├── PRODUCT_ROADMAP.md
├── BACKEND_ARCHITECTURE.md
└── src/
    ├── main.tsx                      # React root mount
    ├── App.tsx                       # App orchestrator & route coordinator
    ├── index.css                     # Global CSS (Tailwind import + design tokens)
    ├── types/
    │   └── domain.ts                 # Shared TypeScript domain contracts
    ├── data/
    │   └── prototypeMocks.ts         # Prototype mock data
    ├── services/
    │   └── apiContracts.ts           # Service interface contract for backend
    ├── router/                       # URL Router & route guards
    ├── pages/
    │   ├── LandingPage.tsx           # Public marketing page
    │   ├── AuthOnboardingPage.tsx    # Register / Login + 4-step onboarding wizard
    │   ├── DashboardPage.tsx         # User home dashboard
    │   ├── ConnectLobbyPage.tsx      # Matching lobby (random + interest)
    │   ├── ChatPage.tsx              # 1-on-1 real-time conversation view
    │   ├── ProfilePage.tsx           # Profile view (own + peers)
    │   ├── ConnectionsPage.tsx       # Accepted & pending connections list
    │   ├── NotificationsPage.tsx     # Notification center
    │   ├── SettingsPage.tsx          # Settings & privacy controls
    │   └── AdminDashboardPage.tsx    # Moderation console
    ├── components/
    │   ├── layout/
    │   │   └── AppShell.tsx          # Responsive navigation shell
    │   └── ui/
    │       ├── Avatar.tsx
    │       ├── Button.tsx
    │       ├── Card.tsx
    │       ├── Modal.tsx
    │       └── StateView.tsx
    └── assets/
        └── images/                   # Prototype avatars & hero graphic
```

---

## 3. EXISTING PAGES & STATUS

| Page | Route | Status | Notes |
|---|---|---|---|
| Landing | `/` | Complete | Marketing landing page with hero, how-it-works, benefits |
| Auth & Onboarding | `/auth` | Complete | Login, Registration, 4-step profile setup wizard |
| Dashboard | `/dashboard` | Complete | Home feed, quick matching shortcuts, recent connections |
| Connect Lobby | `/connect` | Complete | Mode selection (Random vs Interest), audience, topic |
| Messages / Chat | `/messages` | Complete | 1-on-1 chat interface, report & block modals, actions |
| Connections | `/connections`| Complete | Filter tabs (Accepted / Pending), connection cards |
| Profile | `/profile` | Complete | User profile details, bio, skills, interests |
| Notifications | `/notifications` | Complete | Notification list, mark as read, type filtering |
| Settings | `/settings` | Complete | Profile editor, matching preferences, privacy toggles |
| Admin Console | `/admin` | Protected | Trust & safety moderation dashboard (guarded) |

---

## 4. PHASE 0 FIXES & HARDENING (COMPLETED)

1. **Rebranding to Studable**:
   - Replaced all user-facing instances of "Valence" with "Studable".
   - Updated `index.html` title and Open Graph metadata.
   - Updated `metadata.json`, `AppShell.tsx`, `LandingPage.tsx`, `AuthOnboardingPage.tsx`, `ChatPage.tsx`, `SettingsPage.tsx`, `AdminDashboardPage.tsx`.

2. **URL-based Routing**:
   - Upgraded navigation from simple in-memory state switching to full HTML5 URL routing.
   - Added support for direct URL access, browser back/forward buttons, and page refresh without state loss.
   - Preserved all existing layouts and responsive designs.

3. **Prototype UI Controls Removal**:
   - Removed the visible "Prototype Flow" state switcher from `ConnectLobbyPage.tsx` so real users do not see development override buttons.

4. **Admin Route Protection**:
   - Removed the publicly visible Admin Console link from the landing page footer.
   - Added an authorization route guard around `/admin`.
   - Documented requirement that backend authorization token validation is mandatory in future phases.

---

## 5. PHASE 1 BACKEND FOUNDATION (COMPLETED)

1. **FastAPI Application & Modular Structure**:
   - Initialized `backend/` directory housing `app/`, `alembic/`, and `tests/`.
   - Built modular `app.main:app` with FastAPI 0.115.5, Uvicorn 0.32.1, and Pydantic v2.
   - Configured centralized settings in `app/core/config.py` loading via `pydantic-settings`.
   - Structured empty packages for `models/`, `schemas/`, `api/routes/`, and `services/` to guide future phases.

2. **SQLAlchemy 2.0 & PostgreSQL Integration**:
   - Engine and session factory built in `app/core/database.py` utilizing `psycopg3` (`psycopg[binary]`).
   - Declarative `Base` established for ORM models.
   - `get_db()` dependency injection pattern implemented for clean session lifecycles.
   - `check_db_connection()` utility provides graceful fallback and status reporting without crashing when the database is offline.

3. **Alembic Database Migration Pipeline**:
   - Configured `alembic.ini` and `alembic/env.py` pointing dynamically to application settings and `Base.metadata`.
   - Tested offline schema migration generation (`alembic upgrade head --sql`).

4. **Health Check & API Documentation**:
   - Built `GET /api/v1/health` returning operational status and database connectivity.
   - Verified interactive Swagger UI at `/docs` and ReDoc at `/redoc`.
   - Live server tested on port 8000 via automated probe.

5. **Automated Testing Suite**:
   - Created 17 unit and integration tests covering app metadata, root endpoint, health status under connected/disconnected states, and OpenAPI schema validity.
   - 100% test pass rate achieved (`17 passed in 2.23s`).

---

## 6. REMAINING ARCHITECTURAL REQUIREMENTS (PHASES 2-9)

- **Phase 2**: PostgreSQL Database Models & Schemas (User, Profile, Interest, Status).
- **Phase 3**: User Registration, Authentication (JWT), & Security.
- **Phase 4**: User Availability & Presence Engine (Redis).
- **Phase 5**: Matching Engine (Random & Interest-Based).
- **Phase 6**: Real-time Messaging (WebSockets) & Conversation Management.
- **Phase 7**: Moderation, Blocking & Reporting.
- **Phase 8**: Notification System.
- **Phase 9**: Frontend & Backend Integration.
