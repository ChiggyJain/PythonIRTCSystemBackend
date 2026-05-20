# IRTC System Backend

A Python FastAPI backend for the IRTC booking and notification system. This repository contains the backend service, infrastructure configuration, and Docker Compose setup to run the full stack locally.

## Project Overview

The backend is built with:
- FastAPI
- SQLAlchemy + Alembic for MySQL database migrations
- Redis for caching and rate limiting
- Kafka (KRaft) for event-driven outbox and asynchronous processing
- Elasticsearch for search indices and discovery
- SendGrid for email integration (configured via environment variables)

The repository includes:
- `app/` — FastAPI app code, API routes, domain logic, repositories, middlewares, workers, and infrastructure integration
- `Dockerfile` — application container build
- `docker-compose.yml` — full local stack including MySQL, Redis, Kafka, Elasticsearch, Kibana, phpMyAdmin, backend, and background workers
- `start.sh` — container entrypoint script that waits for external services, runs Alembic migrations, and starts Uvicorn
- `requirements.txt` — Python dependencies
- `alembic/` — migration configuration and versions
- `.env` — environment variables used by the app and Docker Compose

## Requirements

- Docker Engine
- Docker Compose
- Python 3.12+ (if running locally without Docker)
- Git

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-repo/your-project.git
cd PythonIRTCSystemBackend
```

### 2. Review environment variables

The repository contains a `.env` file with required settings for:
- JWT configuration
- MySQL connection
- Redis connection
- Kafka bootstrap servers
- Elasticsearch connection
- SendGrid API key
- Internal service URLs
- Kafka topics and outbox retry settings

Important values in `.env`:
- `MYSQL_DB_HOST=mysql`
- `MYSQL_DB_PORT=3306`
- `MYSQL_DB_NAME=IRTC`
- `MYSQL_DB_USER=c`
- `MYSQL_DB_PASSWORD=...`
- `MYSQL_ROOT_PASSWORD=...`
- `REDIS_HOST=redis`
- `REDIS_PORT=6379`
- `KAFKA_BOOTSTRAP_SERVERS=kafka:9092`
- `ELASTICSEARCH_URL=http://elasticsearch:9200`
- `INVENTORY_SERVICE_BASE_URL=http://backend:8000`
- `PAYMENT_SERVICE_BASE_URL=http://backend:8000`

> If you need a custom configuration, copy `.env` to another file or update values locally before starting Docker.

### 3. Install Python dependencies (optional, for local development)

If you want to run the backend directly outside Docker:

```bash
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Docker Compose Setup

This project is designed to run with the full stack defined in `docker-compose.yml`.

### 4. Start the full stack

```bash
docker compose up -d
```

This command starts the following services:

- `mysql` — MySQL 8.4 database
- `phpmyadmin` — MySQL UI at port `8080`
- `redis` — Redis cache at port `6380`
- `kafka` — Apache Kafka broker at port `9092`
- `kafka-init` — topic creation helper for required topics
- `elasticsearch` — Elasticsearch cluster at port `9200`
- `kibana` — Kibana UI at port `5601`
- `backend` — backend API server on port `8000`
- `backend-dummy` — dummy dependency service for compose dependency topology
- background worker services for OTP, station, route, schedule and outbox processing

### 5. Check service status

```bash
docker compose ps
```

### 6. View logs

```bash
docker compose logs -f
```

### 7. Stop the stack

```bash
docker compose down -v
```

## Application Startup Behavior

The backend container uses `start.sh` as its entrypoint. It:

1. Waits for MySQL, Redis, Kafka, and Elasticsearch to become available
2. Generates/creates Alembic migration via `alembic revision --autogenerate`
3. Applies migrations with `alembic upgrade head`
4. Starts Uvicorn on port `8000`

## Local Development

If you prefer to run the backend without Docker after installing dependencies:

```bash
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> Note: The backend still requires MySQL, Redis, Kafka, and Elasticsearch. It is easiest to run those dependencies with Docker Compose.

## Database Migrations

Use Alembic for schema management:

```bash
alembic revision --autogenerate -m "create tables"
alembic upgrade head
```

## Available Endpoints

- Backend base URL: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Health check: `http://localhost:8000/health`
- Elasticsearch readiness: `http://localhost:8000/routes_es_client_ready`
- API prefix: `/api/v1`

## UI and Monitoring URLs

- phpMyAdmin: `http://localhost:8080`
- Kibana: `http://localhost:5601`

## Kafka Topic Initialization

`docker-compose.yml` includes a `kafka-init` service that creates the following topics automatically after Kafka becomes healthy:

- `pwdchanged-otp`
- `emailverification-otp`
- `emailchanged-otp`
- `station`
- `route`
- `schedule`
- `schedule-inventory-seat-availability-updated`
- `payment-updated-status`
- `booking-updated-status`

If you need to manually recreate topics, use Kafka commands from the repository notes.

## Worker Services

Background worker containers are defined in `docker-compose.yml` for:

- password-changed OTP outbox and dispatcher
- email-changed OTP outbox and dispatcher
- email-verification OTP outbox and dispatcher
- station outbox and dispatcher
- route outbox and dispatcher
- schedule outbox and dispatcher

These workers are built from the same `Dockerfile` and run Python modules under `app.workers` and `app.infrastructure.outbox.dispatchers`.

## Useful Commands

From `project_details.txt` and repository scripts:

```bash
# Run backend locally
uvicorn app.main:app --reload

# Run Alembic migrations
alembic revision --autogenerate -m "create tables"
alembic upgrade head

# Redis cleanup
redis-cli flushdb
redis-cli get <key>

# Kafka topic management (if running Kafka locally)
./kafka/bin/kafka-topics.sh --bootstrap-server 127.0.0.1:9092 --create --topic pwdchanged-otp --partitions 6 --replication-factor 1
```

## Notes

- The environment variables in `.env` are loaded by `app.core.settings.Settings` using Pydantic Settings.
- `backend` container health checks the docs page: `http://localhost:8000/docs`.
- Elasticsearch is configured for single-node mode and security is disabled in Docker Compose.

## Alternative Compose for Elasticsearch Only

A separate `docker-compose.elastic.yml` is included for starting just Elasticsearch and Kibana when needed.

```bash
docker compose -f docker-compose.elastic.yml up -d
```

## Final Notes

This README documents the full local development and Docker-based environment for `PythonIRTCSystemBackend`. If you want to add new features, follow the existing app structure and keep environment variables in `.env`.
