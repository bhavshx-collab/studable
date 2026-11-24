# Studable — Backend Setup Guide

This guide describes how to configure, run, and test the **Studable API** backend built with FastAPI, SQLAlchemy 2.0, PostgreSQL (psycopg3), and Alembic.

---

## 1. Prerequisites

Before starting, ensure your system has:

- **Python 3.13+**: [Download Python](https://www.python.org/downloads/) (ensure "Add Python to PATH" is checked on Windows)
- **pip**: Bundled with Python (`pip --version`)
- **PostgreSQL 15+** or **Docker**: [Download Docker](https://www.docker.com/) to run PostgreSQL 16 and Redis 7 with zero installation
- **Redis 7+** (or Docker)
- **Git**

---

## 1.1 Local Development with Docker Compose (Recommended)

To spin up local PostgreSQL and Redis services in seconds:

```bash
docker compose up -d
```

This starts:
- `postgres:16-alpine` on `localhost:5432` (`user=postgres`, `password=postgres`, `database=studable`)
- `redis:7-alpine` on `localhost:6379`

To stop:
```bash
docker compose down
```

---

## 2. Directory Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point with CORS & routes
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Centralized Pydantic v2 settings (JWT, CORS, DB)
│   │   ├── database.py      # SQLAlchemy 2.0 engine, Base, & session management
│   │   ├── security.py      # Argon2id hashing, JWT creation & decoding, cookie helpers
│   │   └── dependencies.py  # get_db, get_current_user, require_admin dependencies
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── user.py          # User, UserInterest, UserSkill, UserLanguage
│   │   ├── auth.py          # RefreshToken (hashed token storage)
│   │   ├── connection.py    # Connection (peer requests)
│   │   ├── conversation.py  # Conversation (1-on-1 chat room)
│   │   ├── message.py       # Message (chat messages with indexing)
│   │   ├── notification.py  # Notification (in-app alerts)
│   │   ├── report.py        # Report (moderation reports)
│   │   └── block.py         # Block (composite key blocks)
│   ├── schemas/             # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   └── auth.py          # Register, Login, Token, UserMe schemas
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/          # API route handlers
│   │       ├── __init__.py
│   │       ├── health.py    # GET /api/v1/health endpoint
│   │       └── auth.py      # /api/v1/auth/* endpoints (register, login, refresh, logout, me)
│   └── services/            # Decoupled business logic services
│       ├── __init__.py
│       └── auth_service.py  # Registration, credential check, token rotation
├── alembic/
│   ├── env.py               # Alembic migration environment
│   ├── script.py.mako       # Migration template
│   └── versions/            # Migration revisions directory
│       └── 20261119_0001_initial_schema.py # Initial full database schema migration
├── tests/
│   ├── __init__.py
│   ├── test_health.py       # Application metadata & health tests
│   └── test_phase2_phase3.py# 36 comprehensive tests for models, auth, JWT, & security
├── alembic.ini              # Alembic config
├── pyproject.toml           # Pytest & project tool settings
├── requirements.txt         # Production & development dependencies
├── .env.example             # Template for local environment variables
└── .gitignore               # Git ignore patterns for Python
```

---

## 3. Python Environment Setup

Navigate to the `backend/` directory:

```bash
cd backend
```

Create and activate a virtual environment:

### On Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### On macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 4. Dependency Installation

With the virtual environment active, install dependencies:

```bash
pip install -r requirements.txt
```

### Key Libraries Installed:
- `fastapi==0.115.5`: Modern asynchronous web framework
- `uvicorn[standard]==0.32.1`: Production ASGI server
- `sqlalchemy==2.0.36`: Modern ORM with connection pooling
- `psycopg[binary]==3.2.3`: High-performance PostgreSQL driver (psycopg3)
- `alembic==1.14.0`: Schema migration tool
- `passlib[argon2]==1.7.4` & `argon2-cffi==23.1.0`: Industry-standard Argon2id password hashing
- `python-jose[cryptography]==3.3.0`: Cryptographically signed JWT tokens
- `pydantic-settings==2.6.1`: Environment-based application configuration
- `pytest==8.3.4` & `pytest-asyncio==0.24.0`: Automated test runners
- `httpx==0.28.0`: HTTP client for testing endpoints

---

## 5. PostgreSQL Database Setup

1. Start your local PostgreSQL server:
   - On Windows: Start the PostgreSQL service in Services (`services.msc`) or via pgAdmin.
   - On Linux/macOS: `sudo systemctl start postgresql` or `brew services start postgresql`.
2. Create a dedicated database for Studable:
   ```sql
   CREATE DATABASE studable;
   CREATE USER postgres WITH ENCRYPTED PASSWORD 'postgres';
   GRANT ALL PRIVILEGES ON DATABASE studable TO postgres;
   ```

---

## 6. Environment Configuration

Copy the example environment file to `.env`:

```bash
cp .env.example .env
```
*(On Windows PowerShell: `Copy-Item .env.example .env`)*

Configure `.env` as appropriate:

```ini
APP_NAME=Studable API
APP_VERSION=1.0.0
DEBUG=false
ENVIRONMENT=development

# PostgreSQL Connection String (psycopg3)
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/studable

# Allowed CORS Origins (JSON array or comma-separated)
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# JWT Authentication
JWT_SECRET_KEY=replace_with_a_secure_32_byte_hex_string_in_production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# Cookie Security (set to true in production HTTPS)
REFRESH_COOKIE_NAME=studable_refresh
REFRESH_COOKIE_SECURE=false
REFRESH_COOKIE_SAMESITE=strict
```

> [!IMPORTANT]
> Never commit `.env` containing sensitive production credentials into version control. It is already included in `.gitignore`.

---

## 7. Database Migrations (Alembic)

Alembic is configured to read `DATABASE_URL` dynamically from the environment settings and inspect all models in `app/models/`.

### Apply migrations:
```bash
alembic upgrade head
```

### Inspect SQL without applying (Offline Mode):
```bash
alembic upgrade head --sql
```

### Revert the latest migration:
```bash
alembic downgrade -1
```

---

## 8. Running the Backend Server

Start the development server with live reload:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## 9. Interactive API Documentation

When the server is running, explore the interactive API documentation at:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema (JSON)**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 10. Running Automated Tests

Run the full pytest suite (53 tests covering metadata, health, models, and authentication):

```bash
pytest tests/ -v
```

All tests run in isolation using SQLite in-memory databases with mocked checks, so **no active PostgreSQL database is required** to pass the automated test suite.
