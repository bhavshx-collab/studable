# Studable — Backend Setup Guide

This guide describes how to configure, run, and test the **Studable API** backend built with FastAPI, SQLAlchemy 2.0, PostgreSQL (psycopg3), and Alembic.

---

## 1. Prerequisites

Before starting, ensure your system has:

- **Python 3.13+**: [Download Python](https://www.python.org/downloads/) (ensure "Add Python to PATH" is checked on Windows)
- **pip**: Bundled with Python (`pip --version`)
- **PostgreSQL 15+** (optional for health check / tests; required for full persistent database operations): [Download PostgreSQL](https://www.postgresql.org/download/)
- **Git**

---

## 2. Directory Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Centralized Pydantic v2 settings
│   │   └── database.py      # SQLAlchemy 2.0 engine & session factory
│   ├── models/              # SQLAlchemy ORM models
│   │   └── __init__.py
│   ├── schemas/             # Pydantic request/response schemas
│   │   └── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/          # API route handlers
│   │       ├── __init__.py
│   │       └── health.py    # Health check endpoints
│   └── services/            # Decoupled business logic services
│       └── __init__.py
├── alembic/
│   ├── env.py               # Alembic migration environment
│   ├── script.py.mako       # Migration template
│   └── versions/            # Migration revisions directory
├── tests/
│   ├── __init__.py
│   └── test_health.py       # Comprehensive pytest suite
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

Create a virtual environment:

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
- `pydantic-settings==2.6.1`: Environment-based application configuration
- `pytest==8.3.4` & `pytest-asyncio==0.24.0`: Automated test runners
- `httpx==0.28.0`: HTTP client for testing endpoints

---

## 5. PostgreSQL Database Setup

1. Start your local PostgreSQL server.
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

# PostgreSQL Connection String
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/studable

# Allowed CORS Origins (JSON array or comma-separated)
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

> [!IMPORTANT]
> Never commit `.env` containing sensitive production credentials into version control. It is already included in `.gitignore`.

---

## 7. Running the Backend Server

Start the development server with live reload:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

## 8. Interactive API Documentation

When the server is running, explore the interactive API documentation at:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema (JSON)**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 9. Health Check Verification

Test the health endpoint directly:

```bash
curl http://localhost:8000/api/v1/health
```

### Response (when PostgreSQL is connected):
```json
{
  "status": "healthy",
  "service": "Studable API",
  "database": "connected"
}
```

### Response (when PostgreSQL is unreachable):
```json
{
  "status": "healthy",
  "service": "Studable API",
  "database": "unavailable"
}
```

> [!NOTE]
> The application remains resilient and reports `healthy` status even if the database is temporarily unreachable, preventing cascading orchestration failures.

---

## 10. Database Migrations (Alembic)

Alembic is configured to read the `DATABASE_URL` dynamically from the environment settings and automatically inspect all models in `app/models/`.

### Generate a new migration:
```bash
alembic revision --autogenerate -m "create initial tables"
```

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

## 11. Running Automated Tests

Run the full pytest suite:

```bash
pytest
```

For verbose output with timing:

```bash
pytest tests/ -v
```

All tests run in isolation using mocked database checks, so **no active PostgreSQL database is required** to pass the automated test suite.
