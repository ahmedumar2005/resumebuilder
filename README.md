# Automatic Resume Builder

Small Flask app that collects user information in a 3-step sequence and renders an HTML resume. The generated resume can be printed to PDF from the browser.

Quickstart

1. Create a venv and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Note: WeasyPrint (for server-side PDF generation) requires system libraries. On macOS, you can skip it and use the browser's print-to-PDF feature instead.

2. Run the app:

```bash
python app.py
# then open http://localhost:5000
```

3. Follow the steps in the web UI to enter your details and generate the resume. You can also import resume content from a LinkedIn public profile URL or paste existing resume text in step 1.

Features

- Multi-step resume data collection
- Optional LinkedIn / resume text import and parsing
- Four resume templates: Classic, Modern, Professional, Minimal
- Print or download your resume as PDF

 Files
 
 - `app.py`: Flask application
 - `templates/`: Jinja2 templates
 - `static/`: CSS files

 **Deployment (one-page quickstart)**

 Environment setup

 1. Create virtualenv and install deps (WeasyPrint is optional):

 ```bash
 python3 -m venv .venv
 source .venv/bin/activate
 pip install -r requirements.txt
 ```

 For development and tests:

 ```bash
 pip install -r requirements-dev.txt
 ```

 2. Set environment variables (example):

 ```bash
 export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
 export FLASK_ENV=production
 export SESSION_COOKIE_SECURE=true
 ```

 Run with a WSGI server

 1. Install and run `gunicorn` (example):

 ```bash
 pip install gunicorn
 gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app
 ```

 2. Use `nginx` as a reverse proxy and enable TLS. Keep `gunicorn` behind the proxy.

 Render deployment

 Render can deploy this app as a Python web service using the provided `Procfile`, `render.yaml`, and `runtime.txt`.
 `runtime.txt` pins the runtime to Python 3.12.18 for stable deployment.

 1. Push this repo to GitHub and connect it to Render.
 2. Set the service type to `Web Service` and use the `python` environment.
 3. Use the default build command from `render.yaml`:

 ```bash
 pip install -r requirements.txt
 ```

 4. Use the default start command from `render.yaml` or `Procfile`:

 ```bash
 gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 --access-logfile - --log-file -
 ```

 5. Configure environment variables on Render:

 - `SECRET_KEY`: secure random secret string (store as a Render secret or dashboard variable; do not commit it)
 - `FLASK_ENV`: `production`
 - `SESSION_COOKIE_SECURE`: `true`
 - Optional: `HEALTH_CHECK_URLS` to probe external dependencies

 6. Set the health check path to `/health`.

 7. If using `render.yaml`, override the placeholder `SECRET_KEY` value in the Render dashboard with a real secret.

 8. See `DEPLOYMENT.md` for the final Render deployment checklist and runtime confirmation.

 7. Enable auto-deploy if you want branch pushes to deploy automatically.

 Notes and best-practices

 - Secret management: never commit `SECRET_KEY` to the repo; use environment variables or a secrets manager.
 - CSRF: Add `Flask-WTF` / `CSRFProtect` before exposing the app publicly.
 - Sessions: set `SESSION_COOKIE_SECURE=True`, `SESSION_COOKIE_HTTPONLY=True`, and `SESSION_COOKIE_SAMESITE='Lax'` in production config.
 - PDF export: server-side PDF requires WeasyPrint plus native system libraries (see WeasyPrint docs). If not installed, rely on browser Print → Save as PDF.
 - LinkedIn import: external fetches are best-effort; consider allow-listing domains or queueing imports in background jobs for production.

 Health & monitoring

 - Add a `/health` endpoint for load balancer checks.
 - Configure logging and an error-monitoring service (Sentry) for production error visibility.

 Pre-deploy checklist

 1. Rotate `SECRET_KEY` and disable debug.
 2. Add CSRF protection and session hardening.
 3. Run the manual pre-deploy test checklist from the README (E2E, imports, validation, XSS checks, mobile).
 4. Deploy to staging and run smoke tests, then promote to production.
