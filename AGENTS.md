# AGENTS.md — SpoolBud Helper Guidance

This file provides guiding principles for AI/code agents extending this repository.
Its scope is the entire repo.

## Product intent

SpoolBud is a minimal companion service for Spoolman with a two-scan workflow:
1. **Spool scan** selects a spool (`/scan`), stores selection in a cookie, and redirects to Spoolman.
2. **Bin scan** updates location (`/bin/{location}`) for the selected spool.

Design for low-friction phone use with stable QR labels and simple operational deployment.

## Core architecture concepts

- Backend: a single FastAPI app (`app.py`).
- State: browser cookie (`COOKIE_NAME`) storing selected spool id.
- Integration: Spoolman API update is done server-side via `PATCH /api/v1/spool/{id}`.
- Runtime: containerized Python service (`Dockerfile`) and `docker-compose.yml`.
- Delivery: CI validates tests/build; publish workflow pushes images on merges/pushes to `main`.

## Engineering principles

1. **Keep it minimal**
   - Avoid unnecessary frameworks, databases, or background services.
   - Prefer straightforward functions/endpoints over abstraction layers.

2. **Preserve scan ergonomics**
   - Never break `/scan?value=...` and `/bin/{location}` URL contracts.
   - Maintain support for these spool value forms in `extract_spool_id`:
     - full `/spool/<id>` URL
     - `?spool_id=<id>` query value
     - raw numeric id

3. **Fail clearly for operators**
   - Return actionable HTML/JSON messages for missing spool selection or Spoolman failures.
   - Keep error messages understandable to a non-developer scanning on a phone.

4. **Security and safety defaults**
   - Read credentials only from environment variables.
   - Do not log API tokens or secrets.
   - Escape user-controlled content rendered in HTML responses.

5. **Compatibility first**
   - Do not require users to regenerate all labels immediately.
   - Keep `/select/{spool_id}` fallback available unless replaced by an explicit migration plan.

6. **Operational reliability**
   - Keep `/healthz` stable for health checks.
   - Ensure Docker image remains small and fast to boot.
   - CI must continue to validate unit tests + container build behavior.

## Change guidelines

- If endpoint behavior changes, update:
  - tests in `tests/test_app.py`
  - docs in `README.md`
  - QR examples and workflow notes
- If environment variables change, update:
  - `README.md`
  - `docker-compose.yml`
  - any CI assumptions
- Prefer additive migrations over breaking changes.

## Testing expectations

At minimum, maintain or improve coverage for:
- spool ID parsing variants
- `/scan` redirect + cookie set
- `/bin` behavior when no selected spool exists
- `/status` cookie reflection

When feasible, run locally:
- `pytest -q`
- `docker compose config -q`
- `docker build -t spoolbud:test .`

## Non-goals (unless explicitly requested)

- Full user auth system
- Persistent database state
- Frontend SPA/dashboard replacement
- Complex queueing or async job processing

Keep the service focused on fast, reliable QR-driven spool location updates.
