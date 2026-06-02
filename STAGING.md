# Staging Deployment & Pre-deploy Checklist

This document collects staging-specific steps and a concise pre-deploy checklist.

## Goal
Prepare a staging instance (Render or similar) and validate the service with automated smoke tests.

## Environment variables (minimum)
- `SECRET_KEY` — required
- `FLASK_ENV=production`
- `SESSION_COOKIE_SECURE=true`
- Optional: `HEALTH_CHECK_URLS` for optional dependency probes

## Render setup (summary)
1. Create a Web Service and connect your repo.
2. Use `runtime.txt` and `render.yaml` already in repo.
3. Build command: `pip install -r requirements.txt`.
4. Start command: `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2`
5. Add environment variables in the Render dashboard (do NOT commit secrets).
6. Set the health check path to `/health`.

## Pre-deploy manual checklist
- [ ] Ensure `SECRET_KEY` is set in Render or staging environment.
- [ ] Confirm `FLASK_ENV=production` and `SESSION_COOKIE_SECURE=true`.
- [ ] Confirm `render.yaml` and `Procfile` are present in repo.
- [ ] Confirm static assets load locally (`python -m http.server` or run app locally).
- [ ] Run unit tests: `python -m pytest -q`.
- [ ] Run `./scripts/smoke_test.sh` against the staging URL once deployed.
- [ ] Perform an end-to-end manual test of the multi-step form and resume generation.

## Running the smoke test locally

```bash
# Make script executable once
chmod +x ./scripts/smoke_test.sh
# Run against a deployed staging URL
./scripts/smoke_test.sh https://your-staging-service.onrender.com
```

## Running the smoke test via GitHub Actions
- Add a repository secret named `SMOKE_URL` (staging URL) OR provide the URL when running the workflow manually.
- See `.github/workflows/smoke-test.yml` (workflow is manual `workflow_dispatch`).

## Troubleshooting
- If `/health` returns `503`, check logs for optional dependency failures (WeasyPrint, external APIs).
- If static assets 404, ensure `templates` use `url_for('static', filename=...)` and `static/` is included in the repo.

***

Once staging is healthy, run the smoke test workflow and perform manual E2E verification.
