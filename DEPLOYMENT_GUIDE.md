# Studable — Production Deployment Guide

This guide outlines the production deployment architecture and step-by-step procedures to deploy Studable to cloud hosting providers.

---

## 1. Architectural Topology

Because Studable relies heavily on **long-running WebSockets** (`/ws/presence`, `/ws/matching`, `/ws/messaging`) and a **background worker process** (`matching_worker`), the deployment is divided into two tiers:

```
[ Users / Browsers ]
       │
       ├─────────────────────────────────┐ (Static SPA Traffic)
       │                                 ▼
       │                    ┌────────────────────────┐
       │                    │     Vercel Edge CDN    │
       │                    │    (Frontend Bundle)   │
       │                    └────────────────────────┘
       │
       ▼ (REST API & Persistent WebSockets)
┌────────────────────────────────────────────────────────┐
│      WebSocket-Compatible Hosting Service               │
│      (Render / Railway / Fly.io / AWS ECS / VPS)       │
│                                                        │
│  ┌────────────────────────┐  ┌──────────────────────┐  │
│  │   FastAPI Web Service  │  │   Matching Worker    │  │
│  │  (Uvicorn, 2 workers)  │  │ (Background asyncio) │  │
│  └───────────┬────────────┘  └──────────┬───────────┘  │
│              │                          │              │
│              ▼                          ▼              │
│  ┌────────────────────────┐  ┌──────────────────────┐  │
│  │  Managed PostgreSQL 16 │  │   Managed Redis 7    │  │
│  │    (Persistent Data)   │  │   (Pub/Sub & Queues) │  │
│  └────────────────────────┘  └──────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

> [!IMPORTANT]
> **Why not deploy backend to Vercel Serverless Functions?**  
> Vercel Functions are stateless serverless lambdas with short execution limits. They do **not** support persistent bidirectional WebSockets or continuous asyncio background queue loops. Deploying the frontend to Vercel and the backend to Render, Railway, or a Docker VPS is the industry standard for real-time applications.

---

## 2. Environment Variables Reference

### Backend (`.env.production`)
| Variable | Description | Example / Default |
|---|---|---|
| `ENVIRONMENT` | Runtime environment mode | `production` |
| `DEBUG` | FastAPI debug mode | `false` |
| `DATABASE_URL` | PostgreSQL 16 connection string (psycopg 3) | `postgresql+psycopg://user:pass@host:5432/studable_prod` |
| `REDIS_URL` | Redis 7 connection string | `redis://:pass@host:6379/0` |
| `SECRET_KEY` | 64-character hex key for access JWTs | `openssl rand -hex 32` |
| `REFRESH_SECRET_KEY` | 64-character hex key for refresh JWTs | `openssl rand -hex 32` |
| `FRONTEND_URL` | Primary URL of the frontend SPA | `https://studable.vercel.app` |
| `ALLOWED_ORIGINS` | JSON array of permitted CORS & WS origins | `["https://studable.vercel.app"]` |
| `COOKIE_SECURE` | Enforce HTTPS on refresh cookies | `true` |
| `WS_MAX_CONNECTIONS_PER_USER` | Maximum simultaneous WS connections per user | `3` |
| `SMTP_HOST` | Transactional email SMTP host | `smtp.sendgrid.net` |
| `SMTP_PORT` | SMTP port | `587` |
| `SMTP_USER` | SMTP username | `apikey` |
| `SMTP_PASSWORD` | SMTP password / API key | `<your-api-key>` |
| `SMTP_TLS` | Enable TLS encryption for email | `true` |
| `EMAILS_FROM_EMAIL` | Sender email address | `noreply@studable.app` |
| `EMAILS_FROM_NAME` | Sender display name | `Studable Team` |

### Frontend (`.env.production`)
| Variable | Description | Example |
|---|---|---|
| `VITE_API_URL` | Backend REST API base URL | `https://studable-api.onrender.com` |
| `VITE_WS_URL` | Backend WebSocket base URL | `wss://studable-api.onrender.com` |

---

## 3. Deployment Option A: Render (Recommended for 1-Click Setup)

Render natively supports WebSockets, background workers, and managed PostgreSQL and Redis using the included `render.yaml` blueprint.

### Steps:
1. Push your repository to GitHub.
2. Sign in to [Render](https://render.com).
3. Navigate to **Blueprints** → **New Blueprint Instance**.
4. Select your `studable` repository.
5. Render reads `render.yaml` and provisions:
   - `studable-db` (Managed PostgreSQL 16)
   - `studable-redis` (Managed Redis 7)
   - `studable-api` (Web service running FastAPI + Uvicorn)
   - `studable-matching-worker` (Background worker running matching engine)
6. Set the `FRONTEND_URL` to your Vercel domain.
7. Click **Apply**.
8. Run database migrations:
   - In the Render dashboard for `studable-api`, open the **Shell** tab and run:
     ```bash
     alembic upgrade head
     ```

---

## 4. Deployment Option B: Railway

Railway provides high-performance container deployment with automatic WebSocket support.

### Steps:
1. Install Railway CLI or connect via [Railway.app](https://railway.app).
2. Create a new project and add:
   - **PostgreSQL plugin** (Railway will inject `DATABASE_URL`).
   - **Redis plugin** (Railway will inject `REDIS_URL`).
3. Deploy the backend service from GitHub using `backend/Dockerfile`.
4. Deploy a second service pointing to the same repo with custom start command:
   ```bash
   python -m app.workers.matching_worker
   ```
5. In the backend service settings, add the required environment variables from Section 2.
6. Set health check path to `/health`.

---

## 5. Deployment Option C: Self-Hosted Docker VPS (Ubuntu / Debian)

Using the included `docker-compose.prod.yml`:

```bash
# 1. Clone repository on VPS
git clone https://github.com/bhavshx-collab/studable.git
cd studable/studable-main

# 2. Configure production environment
cp backend/.env.production.example backend/.env.production
nano backend/.env.production  # Edit secrets, passwords, and domains

# 3. Launch production containers
docker compose -f docker-compose.prod.yml up -d --build

# 4. Verify running services
docker compose -f docker-compose.prod.yml ps

# 5. Check health check status
curl -i http://localhost:8000/health
```

---

## 6. Frontend Deployment on Vercel

1. Sign in to [Vercel](https://vercel.com) and click **Add New** → **Project**.
2. Select your `studable` repository.
3. Configure the project:
   - **Framework Preset:** `Vite`
   - **Root Directory:** `studable-main`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
4. Add Environment Variables:
   - `VITE_API_URL`: Your backend URL (e.g., `https://studable-api.onrender.com`)
   - `VITE_WS_URL`: Your WebSocket URL (e.g., `wss://studable-api.onrender.com`)
5. Click **Deploy**.
6. Note the generated URL (e.g., `https://studable.vercel.app`) and update `ALLOWED_ORIGINS` and `FRONTEND_URL` on the backend.

---

## 7. Post-Deployment Verification Checklist

- [ ] **Health Endpoint:** `GET https://your-backend.com/health` returns `{"status": "healthy", "database": "connected", "redis": "connected"}`.
- [ ] **CORS Verification:** Preflight `OPTIONS` requests from frontend domain return 200 with appropriate `Access-Control-Allow-Origin`.
- [ ] **WebSocket Connectivity:**
  - Presence: connects to `/api/v1/ws/presence?ticket=...` with 101 Switching Protocols.
  - Matching: connects to `/api/v1/ws/matching?ticket=...`.
  - Messaging: connects to `/api/v1/ws/messaging?ticket=...`.
- [ ] **Two-User Flow:** Register User A and User B, enter lobby, complete match, exchange messages, and test block/report.
- [ ] **Admin Console:** Log in with admin credentials and verify `/admin` dashboard loads live reports and metrics.
- [ ] **Email Delivery:** Trigger password reset email and verify inbox receipt via configured SMTP provider.
