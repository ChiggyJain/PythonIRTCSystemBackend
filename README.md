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
- **Redis** — caching, rate limiting, and short-term storage
- **Kafka** — event streaming and topic-driven workers
- **Elasticsearch** — search index for station/route discovery
- **Outbox workers** — asynchronous dispatch of OTP and master-data events

The app combines synchronous requests with asynchronous event flows to support features such as OTP email handling, booking inventory coordination, and search indexing.

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
- `GET /routes_es_client_ready` — Elasticsearch readiness for route search

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

