# Implementation Checklist

This document is the single source of truth for implementing code in this repository.
It is normative for all future changes.

## 1) Architecture and Layering

- Follow this flow: `api -> dependencies -> domains(service/repository) -> infrastructure`.
- Keep business logic in domain services, not in API routers.
- Use repository interfaces in `base.py` and concrete implementations (for example SQLAlchemy repos) separately.
- Keep infra concerns (DB session, Redis client, external providers) inside `app/infrastructure`.

## 2) Async Standards

- Use async endpoints, async services, and async repositories.
- Use `AsyncSession` from `get_db` for DB access.
- Use async Redis client from `app/infrastructure/redis/client.py`.
- Do not introduce blocking I/O in request path.

## 3) API Contract and Exceptions

- Return standard response envelope:
- `status_code` (int)
- `messages` (list[str])
- `data` (any | null)
- Use response helpers from `app/core/response.py`.
- Use `BaseAppException` (or subclasses) for controlled errors.
- Let global middleware/handlers manage final error formatting.

## 4) Routing and Feature Controls

- Use `@feature_control({...})` metadata for endpoint behavior flags.
- Register endpoints with `FeatureAPIRoute` (for example `route_class_override=FeatureAPIRoute`).
- Keep rate limit and logging config in feature metadata, not hardcoded inside route logic.

## 5) Database Conventions

- Table names must be `CAPS` (for example `USERS`, `USER_TOKENS`).
- Every new table must have primary key:
- `ID INT AUTO_INCREMENT PRIMARY KEY`
- No DB foreign-key constraints; enforce relations at application/service layer.
- Keep model and migration naming consistent with existing project patterns.

## 6) Time and Configuration Standards

- Use IST time utilities from `app/common/utils/datetime.py` (`now_ist`, `today_ist`).
- Keep raw environment variables in `app/core/settings.py` via `.env`.
- Keep computed/runtime config values in `app/core/config.py`.
- Do not hardcode secrets, credentials, or environment-specific values.

## 7) Migrations and Model Discovery

- All schema changes must go through Alembic migrations.
- Ensure new ORM models are imported in `app/infrastructure/database/models_importer.py`.
- Keep models Alembic-autogenerate friendly and SQLAlchemy 2 style.

## 8) Logging and Security Standards

- Never log secrets or sensitive values:
- passwords
- raw OTP values
- JWT secrets
- API keys
- Keep logging through centralized logger utilities.
- OTP/email/SMS sending must use provider-agnostic interfaces (strategy pattern), not vendor-coupled domain logic.
- External provider choice (SendGrid/Twilio/etc.) must be swappable without domain-service refactor.

## 9) Before PR Checklist

- [ ] Layering respected (`api -> dependencies -> domains -> infrastructure`).
- [ ] Async flow preserved (no blocking I/O on request path).
- [ ] Response envelope and exception patterns are unchanged and consistent.
- [ ] Feature controls and `FeatureAPIRoute` used for new/updated endpoints.
- [ ] DB conventions followed (`CAPS` table names, `ID` PK, no FK constraints).
- [ ] Alembic migration added (if schema changed) and models importer updated.
- [ ] IST datetime and settings/config patterns followed.
- [ ] Sensitive data is not logged; provider integration remains abstracted.
- [ ] Changes remain documentation-safe and backward compatible unless explicitly planned.
