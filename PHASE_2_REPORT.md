# Studable — Phase 2: Database Models & Migrations Report

**Status:** Completed & Verified  
**Date:** November 19, 2026  
**Author:** Senior Backend Engineer & Database Architect  

---

## 1. Executive Summary

Phase 2 (Database Models and Migrations) establishes the core database architecture for the Studable social connection and networking platform. Using SQLAlchemy 2.0 and PostgreSQL (psycopg3), 11 relational entities have been designed, implemented, and indexed with foreign key constraints, uniqueness constraints, cascading deletion policies, and soft-delete capabilities matching the approved `BACKEND_ARCHITECTURE.md` specification.

An Alembic migration script (`20261119_0001_initial_schema.py`) has been configured, generating clean transactional DDL for all 11 tables.

---

## 2. Models Created

All models reside under `backend/app/models/` and are registered with `app.models.__init__.py` for Alembic discovery:

| Model | Table | File | Description |
|---|---|---|---|
| `User` | `users` | `app/models/user.py` | Primary account entity with authentication credentials, profile data, settings, role (`member`/`admin`), and soft-delete (`deleted_at`). |
| `UserInterest` | `user_interests` | `app/models/user.py` | User-selected topic interests (composite PK: `user_id`, `interest`). Cascades on user deletion. |
| `UserSkill` | `user_skills` | `app/models/user.py` | Professional and technical skills (composite PK: `user_id`, `skill`). Cascades on user deletion. |
| `UserLanguage` | `user_languages` | `app/models/user.py` | Preferred spoken/written languages (composite PK: `user_id`, `language`). Cascades on user deletion. |
| `RefreshToken` | `refresh_tokens` | `app/models/auth.py` | Secure hashed refresh token store for session rotation and revocation (`token_hash` unique SHA-256). |
| `Connection` | `connections` | `app/models/connection.py` | Peer networking relationship (`pending`, `accepted`, `rejected`) with non-self check constraint. |
| `Conversation` | `conversations` | `app/models/conversation.py` | 1-on-1 chat session between two participants with `active`/`ended` status lifecycle. |
| `Message` | `messages` | `app/models/message.py` | Chat message records with composite index on (`conversation_id`, `created_at`). |
| `Notification` | `notifications` | `app/models/notification.py` | In-app alerts with hot-path composite index on (`user_id`, `is_read`, `created_at`). |
| `Report` | `reports` | `app/models/report.py` | User safety moderation reports with audit persistence (`SET NULL` on user deletion). |
| `Block` | `blocks` | `app/models/block.py` | Mutual isolation blocks with composite PK (`blocker_id`, `blocked_id`) and non-self constraint. |

---

## 3. Database Constraints & Indexes

### Integrity Constraints:
- **Unique Constraints**: `users(email)`, `users(username)`, `refresh_tokens(token_hash)`, `connections(requester_id, recipient_id)`.
- **Check Constraints**:
  - `ck_users_role`: `role IN ('member', 'admin')`
  - `ck_users_category`: `category IN ('Student', 'Working Professional', 'Entrepreneur', 'Mentor')`
  - `ck_connections_no_self`: `requester_id <> recipient_id`
  - `ck_connections_status`: `status IN ('pending', 'accepted', 'rejected')`
  - `ck_conversations_status`: `status IN ('active', 'ended')`
  - `ck_messages_status`: `status IN ('sent', 'delivered', 'read')`
  - `ck_reports_status`: `status IN ('pending', 'resolved_warned', 'resolved_suspended', 'dismissed')`
  - `ck_blocks_no_self`: `blocker_id <> blocked_id`
- **Cascading Policies**:
  - `CASCADE`: `user_interests`, `user_skills`, `user_languages`, `refresh_tokens`, `connections`, `blocks`, `messages`.
  - `SET NULL`: `conversations` (participants), `reports` (reporter, reported, moderator) — ensures audit integrity is preserved even if user accounts are removed.

---

## 4. Alembic Migration Details

- Migration file: `backend/alembic/versions/20261119_0001_initial_schema.py`
- Revision ID: `0001_initial_schema`
- Verified via `alembic upgrade head --sql` (offline transactional DDL generation).

---

## 5. PostgreSQL Connection Status & Honest Reporting

- **Host connection check**: Attempted connection to `postgresql+psycopg://postgres:postgres@localhost:5432/studable`.
- **Current status**: Local PostgreSQL service is currently **offline / not running** on the host (`Socket is not connected (0x00002749/10057)`).
- **Graceful degradation**:
  - The application accurately reports `"database": "unavailable"` at `/api/v1/health` without crashing.
  - All unit, relationship, constraint, and integration tests execute successfully against isolated SQLite in-memory databases with foreign keys enabled (`PRAGMA foreign_keys=ON`).
- **Prerequisite for live persistence**: Start PostgreSQL service and create the `studable` database as detailed in `BACKEND_SETUP.md`.
