# IRTC Backend

Production-oriented FastAPI backend for user authentication and account security workflows.

This service provides:
- User signup, login, profile APIs
- JWT access/refresh token lifecycle with server-side token state
- OTP-driven security flows for password change, email verification, and email change
- Reliable asynchronous dispatch pipeline using MySQL outbox + Kafka consumers
- Redis-backed caching and rate limiting

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Core Features](#core-features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Local Development Setup](#local-development-setup)
- [Running the Application](#running-the-application)
- [Running Background Workers](#running-background-workers)
- [Database Migrations](#database-migrations)
- [API Endpoints](#api-endpoints)
- [Request/Response Contract](#requestresponse-contract)
- [Security and Auth Model](#security-and-auth-model)
- [OTP Flow Model](#otp-flow-model)
- [Rate Limiting](#rate-limiting)
- [Caching](#caching)
- [Performance Testing (k6)](#performance-testing-k6)
- [Logging](#logging)
- [Operational Notes](#operational-notes)

## Architecture Overview
The codebase follows a layered architecture:
- `api` layer: route handlers and HTTP contract
- `domains` layer: business logic and use-case orchestration
- `repository` layer: database persistence abstractions and SQLAlchemy implementations
- `infrastructure` layer: DB/Redis/Kafka/provider clients
- `workers` layer: async outbox publishers and Kafka consumers

Key async reliability pattern:
1. API request stores OTP challenge + outbox row in one DB transaction.
2. Outbox worker publishes event to Kafka.
3. Consumer worker sends OTP via provider abstraction and updates challenge/event logs.

## Core Features
- User onboarding and login
- Token issuance with DB-backed token rows (`USER_TOKENS`) and hash-only token storage
- Refresh token rotation with access/refresh pair validation
- Logout with pair integrity checks and revocation
- Password change flow with OTP challenge verification and active-session revocation
- Email verification flow with OTP challenge verification
- Email change flow with encrypted metadata and OTP confirmation
- Unified security event audit trail (`SECURITY_EVENT_LOG`)

## Tech Stack
- Python 3.12 (verified in this workspace)
- FastAPI + Starlette
- SQLAlchemy 2.x (async) + AsyncMy
- Alembic
- Redis (cache + rate limiting)
- Kafka (`aiokafka`)
- SendGrid provider abstraction for email OTP
- Loguru for application logging

## Project Structure
```text
.
├── app/
│   ├── api/v1/                       # HTTP routes
│   ├── common/                       # security, cache, utils, decorators
│   ├── core/                         # settings, config, exceptions, routing helpers
│   ├── dependencies/                 # FastAPI dependency providers
│   ├── domains/
│   │   ├── users/                    # signup/login/profile domain
│   │   ├── auth/                     # token domain
│   │   └── security/                 # OTP + outbox + audit domain
│   ├── infrastructure/
│   │   ├── database/                 # SQLAlchemy base/session/models importer
│   │   ├── redis/                    # Redis client
│   │   ├── kafka/                    # Kafka client builders
│   │   ├── otp/                      # provider factory
│   │   ├── email/                    # SendGrid sender
│   │   └── sms/                      # SMS sender abstraction impl
│   ├── middlewares/                  # global exception middleware
│   ├── workers/                      # outbox publisher + consumer workers
│   └── main.py                       # FastAPI entrypoint
├── alembic/                          # migration env and versions folder
├── perf/                             # k6 performance scripts and reports
├── logs/                             # runtime logs
├── requirements.txt
└── alembic.ini
```

## Prerequisites
- Python 3.11+ (3.12 recommended)
- MySQL 8+
- Redis 6+
- Kafka cluster (local single broker works for dev)
- (Optional) k6 for performance tests

## Configuration
Configuration is loaded from `.env` using `pydantic-settings` (`app/core/settings.py`).

### Required Environment Variables
- App: `APP_NAME`, `APP_ENV`, `APP_DEBUG`
- MySQL: `MYSQL_DB_HOST`, `MYSQL_DB_PORT`, `MYSQL_DB_NAME`, `MYSQL_DB_USER`, `MYSQL_DB_PASSWORD`
- Redis: `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`
- Kafka: `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_CLIENT_ID`
- JWT/Token security: `JWT_SECRET_KEY`, `TOKEN_HASH_SECRET`, `JWT_ALGORITHM`, `JWT_ACCESS_EXPIRE_MINUTES`, `JWT_REFRESH_EXPIRE_DAYS`, `JWT_ISSUER`, `JWT_AUDIENCE`
- SendGrid: `SENDGRID_API_KEY`
- OTP flow config:
  - Password change: `PWDCHANGED_*`
  - Email verification: `EMAILVERIFICATION_*`
  - Email change: `EMAILCHANGED_*`
  - User-level OTP/API limits: `PWDCHANGED_*_RATE_*`, `EMAILVERIFICATION_*_RATE_*`, `EMAILCHANGE_*_RATE_*`

Security note: do not commit real credentials or API keys. Rotate any key that has already been exposed.

## Local Development Setup
```bash
# from project root
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create or update `.env` with your local infra values.

## Running the Application
```bash
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Swagger docs: `http://127.0.0.1:8000/docs`

Health check:
```bash
curl http://127.0.0.1:8000/health
```

## Running Background Workers
Run each worker in a separate terminal/process.

### Password Change OTP Workers
```bash
python3 -m app.workers.pwdchanged_otp_outbox_worker
python3 -m app.workers.pwdchanged_otp_dispatch_consumer_worker
```

### Email Verification OTP Workers
```bash
python3 -m app.workers.emailverification_otp_outbox_worker
python3 -m app.workers.emailverification_otp_dispatch_consumer_worker
```

### Email Change OTP Workers
```bash
python3 -m app.workers.emailchanged_otp_outbox_worker
python3 -m app.workers.emailchanged_otp_dispatch_consumer_worker
```

## Database Migrations
Alembic is configured for async SQLAlchemy (`alembic/env.py`) and imports all domain models via `app.infrastructure.database.models_importer`.

```bash
# create migration
alembic revision --autogenerate -m "init"

# apply migration
alembic upgrade head
```

## API Endpoints
Base prefix: `/api/v1`

### Public
- `POST /api/v1/users/signup`
- `POST /api/v1/users/login`
- `GET /health`

### Authenticated (Bearer access token)
- `GET /api/v1/users/profile_details`
- `POST /api/v1/auth/refresh` (requires refresh-token in body)
- `POST /api/v1/auth/logout` (requires refresh-token in body and access-token in header)
- `POST /api/v1/auth/logout-all-devices` (requires refresh-token in body and access-token is header)
- `POST /api/v1/users/password/change/request-otp`
- `POST /api/v1/users/password/change/confirm`
- `POST /api/v1/users/email/verification/request-otp`
- `POST /api/v1/users/email/verification/confirm`
- `POST /api/v1/users/email/change/request-otp`
- `POST /api/v1/users/email/change/confirm`

## Request/Response Contract
All APIs use a standardized response envelope:

```json
{
  "status_code": 200,
  "messages": ["..."],
  "data": {}
}
```

Validation errors return `422` with normalized message array.

## Security and Auth Model
- JWTs include `sub`, `jti`, token `type`, issuer/audience, and linked token id
- Raw JWTs are never stored in DB; HMAC hash is stored
- Access token validity is checked against Redis (`cache:user:access:jti:{jti}`)
- Login creates access+refresh rows and writes access-token cache/index
- Refresh rotates token pair atomically and updates cache/index
- Logout revokes access-token + refresh-token pair and performs cache cleanup [Current active session devices]
- Logout all devices revokes access-token + refresh-token pair and performs cache cleanup [All active session devices]
- Password change revokes all active user tokens and clears access token cache set

## OTP Flow Model
Primary tables:
- `OTP_CHALLENGES`: challenge lifecycle + encrypted OTP + attempt tracking
- `OUTBOX_EVENTS`: publish queue with retry/backoff metadata
- `SECURITY_EVENT_LOG`: auditable events for OTP/security lifecycle

Common OTP policy:
- OTP TTL: 300 seconds
- Max attempts: 5
- Cooldown between requests: 60 seconds
- Status transitions include: `REQUESTED`, `SENT`, `VERIFIED`, `EXPIRED`, `BLOCKED`, `DISPATCH_FAILED`

## Rate Limiting
Two layers are implemented:
- Route/IP-level limiter in `FeatureAPIRoute` using Redis INCR + EXPIRE
- Additional user-level limits for OTP request/confirm APIs (configurable via env)

Fail-open behavior is used when limiter infrastructure fails.

## Caching
- Profile cache key: `cache:v1.users.profile:{user_id}` (TTL 300s)
- Access token cache key: `cache:user:access:jti:{token_id}`
- User access-token index set: `cache:user:access:index:{user_id}`

Cache is invalidated on:
- logout/refresh token rotation
- password change
- email verify / email change profile updates

## Performance Testing (k6)
Scripts are available under `perf/scripts` for:
- health, signup, login, profile, refresh, logout
- password-change OTP request/confirm
- email-verification OTP request/confirm
- email-change OTP request/confirm

Example run:
```bash
source perf/env.local.sh
k6 run perf/scripts/01_health.js
k6 run perf/scripts/03_login.js
```

## Logging
- Loguru-backed logging
- Console and rotating file logs (`logs/app.log`, 10 MB rotation, 10-day retention, zip compression)
- Feature route logs include worker, API name, IP, method, path, timing, error, status

## Operational Notes
- Run API and workers as separate processes (systemd/supervisor/container orchestrator)
- Scale outbox publishers and consumers horizontally; outbox fetch uses `FOR UPDATE SKIP LOCKED`
- Keep Redis and Kafka highly available for stable throughput
- Add CI checks for linting, type checks, and tests (no test suite is currently committed)
- Add and apply Alembic revisions before production deploy (no migration scripts are currently present in `alembic/versions`)

Current implementation caveat:
- `app/infrastructure/email/sendgrid_otp_sender.py` currently short-circuits `send_otp` with a test return before real SendGrid send logic. Remove the early return for live email dispatch.
