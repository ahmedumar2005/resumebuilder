# Deployment Checklist for Render

This file explains the minimal Render deployment setup for the resume builder.

## Included files

- `render.yaml` — Render service definition
- `Procfile` — Gunicorn startup command
- `runtime.txt` — Fixed Python runtime for Render
- `requirements.txt` — Production dependencies, including `gunicorn`
- `app.py` / `wsgi.py` — Flask application and WSGI entrypoint
- `README.md` — general usage and deployment notes

## Required Render settings

1. Connect your GitHub repository to Render and create a `Web Service`.
2. Ensure the service uses the `python` environment.
3. Render should detect `runtime.txt` and install Python 3.12.18.
4. Ensure `render.yaml` is enabled in your service configuration.
5. Set the health check path to `/health`.

## Required environment variables

- `SECRET_KEY`
  - Must be a secure random string.
  - Use a Render secret or environment variable.
  - The app refuses to start without this.
  - If `render.yaml` includes a placeholder, override it in the Render dashboard.

- `FLASK_ENV`
  - Set to `production`.

- `SESSION_COOKIE_SECURE`
  - Set to `true` in production.

Optional:

- `HEALTH_CHECK_URLS`
  - Comma-separated URLs for optional dependency probes.

## Build and start commands

Render will use `render.yaml` by default.

- Build command:

```bash
pip install -r requirements.txt
```

- Start command:

```bash
gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 --access-logfile - --log-file -
```

## Health check compatibility

- The app exposes `/health`.
- `/health` returns `200` when the service is healthy.
- If checks fail, it returns `503`.
- This is compatible with Render load balancer health checks.

## Production blockers to resolve before deploy

- `SECRET_KEY` must be configured in Render.
- `SESSION_COOKIE_SECURE=true` should be enabled.
- If you need PDF export server-side, install WeasyPrint and its native dependencies separately.
- Do not enable Flask debug mode in production.

## Quick deploy checklist

1. Push code to your repository.
2. Confirm `render.yaml`, `Procfile`, and `runtime.txt` are present.
3. Create or update the Render service.
4. Set environment variables: `SECRET_KEY`, `FLASK_ENV=production`, `SESSION_COOKIE_SECURE=true`.
5. Confirm health check path `/health`.
6. Deploy and verify the app loads.
7. Test the form flow and resume generation.

## Smoke test (quick)

- A minimal smoke-test script is provided at `scripts/smoke_test.sh`.
- Usage:

```bash
./scripts/smoke_test.sh https://your-service-name.onrender.com
```

- The script checks `/health`, `/`, `/resume`, and a static asset. It exits non-zero on failures.

Notes:

- For staging, also perform a manual end-to-end test of the multi-step form to validate CSRF tokens and session behaviour.

