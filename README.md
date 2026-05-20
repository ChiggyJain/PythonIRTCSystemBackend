# 🚆 IRTC System Backend

A Python FastAPI backend for an IRCTC-style train ticketing system with event-driven flows, search, and background workers.

This repository includes:
- `app/` — FastAPI application, domain logic, API routes, middleware, services, and workers
- `Dockerfile` — backend container build definition
- `docker-compose.yml` — full local infrastructure stack: MySQL, Redis, Kafka, Elasticsearch, Kibana, phpMyAdmin, backend, and workers
- `start.sh` — startup wrapper for dependency checks, Alembic migration, and Uvicorn launch
- `requirements.txt` — Python dependencies
- `.env` — environment configuration for local development and Docker Compose

## 📋 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Port Reference](#-port-reference)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Running the Application](#running-the-application)
- [Services](#-services)
- [Kafka Topics](#-kafka-topics)
- [API Documentation](#-api-documentation)
- [Environment Variables](#-environment-variables)
- [Project Structure](#-project-structure)
- [Notes](#-notes)

---

## 🎯 Overview

This project implements a backend for an IRCTC-like booking system using a single FastAPI application plus background workers and asynchronous integration with Kafka, Redis, MySQL, and Elasticsearch.

The repository architecture is designed to demonstrate:
- REST API with FastAPI
- asynchronous event-driven processing using Kafka topics
- database migrations with Alembic
- caching and rate-limiting support via Redis
- search and discovery using Elasticsearch
- containerized local development with Docker Compose

## 🏗️ Architecture

The backend serves API requests and also relies on asynchronous worker processes for outbox dispatch and Kafka-based integration.

Key architectural components:
- **FastAPI backend** — main HTTP API exposed on `/api/v1`
- **Database layer** — MySQL for application persistence
- **Redis** — fast read cache, rate limiting, frequently accessed data, and distributed seat lock management for booking operations
- **Kafka** — event streaming and topic-driven workers for asynchronous decoupling
- **Elasticsearch** — search index for station/route discovery
- **Outbox workers** — asynchronous dispatch of domain events to Kafka
- **Saga-style booking coordination** — booking workflows coordinate inventory locks, payment orders, and eventual confirmation or rollback

The app combines synchronous request handling with asynchronous event flows to support features such as OTP email handling, booking inventory coordination, distributed locks, and search indexing.

## 🧩 Event-driven Outbox + Dispatcher Pattern

This project uses the Outbox pattern to keep Kafka event publishing reliable and decoupled from HTTP request handling.

### Why this pattern?
- Writes domain events to the database as part of the same transaction as business changes.
- Prevents lost events when Kafka is temporarily unavailable.
- Moves Kafka publish logic out of user-facing request handlers.
- Supports retries and eventual consistency.

### How the flow works
1. Domain code creates an event record in the `outbox_events` table.
2. An outbox worker reads pending rows and marks them processing.
3. The worker publishes event payloads to Kafka topics.
4. The worker marks each event published, or retries/fails if publishing fails.
5. A dispatcher process consumes the Kafka topic and applies side effects.

### Producers, topics, and consumers
| Kafka topic | Outbox worker | Dispatcher / consumer | Container name | Consumer group |
|---|---|---|---|---|
| `pwdchanged-otp` | `pwdchanged-otp-outbox-worker` | `pwdchanged-otp-outbox-dispatcher` | `irtc-pwdchanged-otp-outbox-dispatcher` | `pwdchanged-otp-consumer-group` |
| `emailverification-otp` | `emailverification-otp-outbox-worker` | `emailverification-otp-outbox-dispatcher` | `irtc-emailverification-otp-outbox-dispatcher` | `emailverification-otp-consumer-group` |
| `emailchanged-otp` | `emailchanged-otp-outbox-worker` | `emailchanged-otp-outbox-dispatcher` | `irtc-emailchanged-otp-outbox-dispatcher` | `emailchanged-otp-consumer-group` |
| `station` | `stations-outbox-worker` | `stations-outbox-dispatcher` | `irtc-stations-outbox-dispatcher` | `station-consumer-group` |
| `route` | `routes-outbox-worker` | `routes-outbox-dispatcher` | `irtc-routes-outbox-dispatcher` | `route-consumer-group` |
| `schedule` | `schedules-outbox-worker` | `schedules-outbox-dispatcher` | `irtc-schedules-outbox-dispatcher` | `schedule-consumer-group` |
| `schedule-inventory-seat-availability-updated` | `schedule-inventory-seat-availability-updated-outbox-worker` | `schedule-inventory-seat-availability-updated-outbox-dispatcher` | `irtc-schedule-inventory-seat-availability-updated-outbox-dispatcher` | `schedule-inventory-seat-availability-updated-consumer-group` |
| `payment-updated-status` | `payment-updated-status-outbox-worker` | `payment-updated-status-outbox-dispatcher` | `irtc-payment-updated-status-outbox-dispatcher` | `payment-updated-status-consumer-group` |
| `booking-updated-status` | `booking-updated-status-outbox-worker` | `booking-updated-status-send-email-outbox-dispatcher` | `irtc-booking-updated-status-send-email-outbox-dispatcher` | `booking-updated-status-email-consumer-group` |

### Internal architecture pattern
The project follows a layered domain architecture:
- `app/api/v1/` — HTTP adapters and route definitions.
- `app/domains/` — business logic and consumer services.
- `app/infrastructure/` — DB, Kafka, Elasticsearch, Redis, email, and outbox plumbing.
- `app/workers/` — background workers that publish to Kafka or consume Kafka topics.
- `app/core/`, `app/common/`, and `app/dependencies/` — shared configuration, middleware, and FastAPI integration.

This structure keeps domain logic separated from infrastructure code and makes the event-driven flows clear and maintainable.

### Booking Saga Flow

Booking in this project is implemented as a Saga-style workflow rather than a single monolithic transaction.

- A booking request starts in the backend and writes a local booking state to MySQL.
- Redis is used for fast access data, rate limiting, and to coordinate distributed seat locks during booking.
- The booking service creates outbox events for inventory lock, payment order, and booking status updates.
- Kafka topics carry each step as an event, so the system can resume and retry independently.
- A successful payment result triggers a confirm flow that locks the seat permanently and marks the booking confirmed.
- A failure or timeout triggers compensating actions, such as unlocking seat reservations and canceling the booking.

This Saga-style pattern helps the application maintain consistency across services without requiring distributed transactions.

## 🔌 Port Reference

| Component | Local URL | Container port | Notes |
|---|---|---|---|
| Backend API | http://localhost:8000 | 8000 | FastAPI app /docs available |
| phpMyAdmin | http://localhost:8080 | 80 | MySQL UI |
| MySQL | localhost:3307 | 3306 | Database for app |
| Redis | localhost:6380 | 6379 | Cache and rate limiting |
| Kafka | localhost:9092 | 9092 | Event broker |
| Elasticsearch | http://localhost:9200 | 9200 | Search index |
| Kibana | http://localhost:5601 | 5601 | Elasticsearch UI |

## 🛠️ Tech Stack

### Backend
- Python 3.12
- FastAPI
- Uvicorn
- SQLAlchemy + asyncmy
- Alembic migrations
- Pydantic / Pydantic Settings
- SendGrid mail integration

### Infrastructure
- Docker Compose
- MySQL 8.4
- Redis 7.2
- Apache Kafka 3.9.0 (KRaft mode)
- Elasticsearch 8.15.1
- Kibana 8.15.1
- phpMyAdmin

### Messaging and Search
- Kafka topics for event-driven asynchronous workflows
- Elasticsearch for station/route search and discovery

## 🚀 Getting Started

### Prerequisites

- Docker
- Docker Compose
- Python 3.12+ (optional for local non-container execution)
- Git

### Installation

Clone the repository:

```bash
git clone https://github.com/your-user/PythonIRTCSystemBackend.git
cd PythonIRTCSystemBackend
```

### Quick Start

If you just pulled the code and want to launch the full stack immediately, run:

```bash
docker compose down -v && docker compose build --no-cache && docker compose up -d --force-recreate
```

Install Python dependencies locally (optional):

```bash
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Running with Docker Compose

Start the full stack:

```bash
docker compose up -d
```

Verify services:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f
```

Stop and remove containers:

```bash
docker compose down -v
```

### Running Locally Without Docker

The backend can be run directly if dependencies are installed, but it still requires the supporting services from Docker Compose.

```bash
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Elasticsearch-Only Compose

To run Elasticsearch and Kibana alone:

```bash
docker compose -f docker-compose.elastic.yml up -d
```

## 📦 Services

### `backend`
- Builds from `Dockerfile`
- Serves FastAPI app on port `8000`
- Uses `start.sh` to wait for MySQL, Redis, Kafka, Elasticsearch, then run Alembic and start Uvicorn

### `mysql`
- MySQL 8.4 database
- Exposes port `3307` locally
- Uses `.env` values for credentials

### `phpmyadmin`
- Web UI for MySQL
- Access at `http://localhost:8080`

### `redis`
- Redis cache exposed on `6380` locally

### `kafka`
- Kafka broker on `9092`

### `kafka-init`
- Creates required Kafka topics automatically

### `elasticsearch`
- Elasticsearch single-node cluster on `9200`

### `kibana`
- Kibana UI on `http://localhost:5601`

### Worker services
- `pwdchanged-otp-outbox-worker`
- `pwdchanged-otp-outbox-dispatcher`
- `emailchanged-otp-outbox-worker`
- `emailchanged-otp-outbox-dispatcher`
- `emailverification-otp-outbox-worker`
- `emailverification-otp-outbox-dispatcher`
- `stations-outbox-worker`
- `stations-outbox-dispatcher`
- `routes-outbox-worker`
- `routes-outbox-dispatcher`
- `schedules-outbox-worker`
- `schedules-outbox-dispatcher`
- and other workers defined in `docker-compose.yml`

## 📡 Kafka Topics

The compose stack creates these Kafka topics:

- `pwdchanged-otp`
- `emailverification-otp`
- `emailchanged-otp`
- `station`
- `route`
- `schedule`
- `schedule-inventory-seat-availability-updated`
- `payment-updated-status`
- `booking-updated-status`

## 🧪 API Documentation

The backend exposes the FastAPI docs at:

- `http://localhost:8000/docs`
- `http://localhost:8000/openapi.json`

### Health and readiness

- `GET /health` — service health
- `GET /routes_es_client_ready` — Elasticsearch services health

### API route groups

All API routes are mounted under `/api/v1`.

- `POST /api/v1/auth/...` — authentication, OTP, login, refresh
- `GET/POST /api/v1/users/...` — user operations
- `GET/POST /api/v1/admin/master-data/...` — admin/master-data CRUD
- `GET /api/v1/search_discovery/...` — search and discovery
- `GET/POST /api/v1/inventory/...` — inventory endpoints
- `GET/POST /api/v1/bookings/...` — booking operations
- `GET/POST /api/v1/payments/...` — payments and refunds

### Example requests

Send OTP:

```http
POST http://localhost:8000/api/v1/auth/send-otp
Content-Type: application/json

{
  "email": "user@example.com"
}
```

User signup example:

```http
POST http://127.0.0.1:8000/api/v1/users/signup
Content-Type: application/json

{
  "first_name": "Chirag",
  "last_name": "Jain",
  "mobile": "9975967186",
  "email": "cjain9975@gmail.com",
  "gender": "Male",
  "password": "Test1@123456",
  "confirm_password": "Test1@123456",
  "profile": "User/Admin"
}
```

Verify OTP:

```http
POST http://localhost:8000/api/v1/auth/verify-otp
Content-Type: application/json

{
  "email": "user@example.com",
  "otp": "123456"
}
```

Create booking:

```http
POST http://localhost:8000/api/v1/bookings
Content-Type: application/json
Authorization: Bearer <access_token>
```

## 🔐 Environment Variables

Configuration is loaded from `.env` using Pydantic Settings.

Important variables:

- `APP_NAME`, `APP_ENV`, `APP_DEBUG`
- `JWT_SECRET_KEY`, `TOKEN_HASH_SECRET`, `JWT_ALGORITHM`
- `MYSQL_DB_HOST`, `MYSQL_DB_PORT`, `MYSQL_DB_NAME`, `MYSQL_DB_USER`, `MYSQL_DB_PASSWORD`, `MYSQL_ROOT_PASSWORD`
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`
- `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_CLIENT_ID`
- `ELASTICSEARCH_URL`, `ELASTICSEARCH_USERNAME`, `ELASTICSEARCH_PASSWORD`, `ELASTICSEARCH_VERIFY_CERTS`
- `SENDGRID_API_KEY`, `SENDGRID_DRY_RUN`
- `INVENTORY_SERVICE_BASE_URL`, `PAYMENT_SERVICE_BASE_URL`

> Do not commit secrets or the `.env` file to version control.

## 📁 Project Structure

The repository uses a layered domain architecture that separates API adapters, domain logic, infrastructure adapters, and background workers.

```
PythonIRTCSystemBackend/
├── .env
├── Dockerfile
├── docker-compose.yml
├── docker-compose.elastic.yml
├── README.md
├── requirements.txt
├── start.sh
├── app/
│   ├── api/
│   │   └── v1/           # API routers by domain
│   ├── common/           # shared helpers, security, cache
│   ├── core/             # application settings, exception handlers, response wrapper
│   ├── dependencies/     # FastAPI dependencies
│   ├── domains/          # business logic and service classes
│   ├── infrastructure/   # database, kafka, email, redis, outbox integrations
│   ├── middlewares/      # middleware definitions
│   ├── services/         # saga and background service orchestration
│   └── workers/          # background worker entrypoints
├── alembic/              # migration configuration and versions
└── project_details.txt   # notes and helper commands
```

## 💡 Notes

- `Dockerfile` installs dependencies, copies source code, and runs `start.sh`.
- `start.sh` waits for MySQL, Redis, Kafka, and Elasticsearch, then runs Alembic migrations before launching Uvicorn.
- The API is primarily served at `http://localhost:8000` and the docs are available at `http://localhost:8000/docs`.
- `docker-compose.elastic.yml` is available for Elasticsearch + Kibana only.

