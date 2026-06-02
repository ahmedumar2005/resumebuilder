import os
import re
import shutil
import tempfile
import socket
from io import BytesIO

import requests
from bs4 import BeautifulSoup
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_file,
    flash,
)
from flask_wtf import CSRFProtect
from markupsafe import Markup, escape
import ipaddress
from urllib.parse import urlparse


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = (
        os.environ.get("SESSION_COOKIE_SECURE", "False").lower() in (
            "1",
            "true",
            "yes",
        )
    )
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PREFERRED_URL_SCHEME = "https"
    WTF_CSRF_TIME_LIMIT = None


app = Flask(__name__, static_folder="static", template_folder="templates")
app.config.from_object(Config)
if not app.config["SECRET_KEY"]:
    raise RuntimeError(
        "SECRET_KEY environment variable not set. "
        "Set SECRET_KEY before starting the app."
    )

# enable CSRF protection for all POST forms
csrf = CSRFProtect(app)


STEPS = 3


try:
    import weasyprint
except (ImportError, OSError):
    weasyprint = None


def get_data():
    return session.get("resume_data", {})


def save_data(data):
    session["resume_data"] = data


def normalize_text(text):
    return "\n".join([line.strip() for line in text.splitlines() if line.strip()])


def is_safe_url(u):
    try:
        parsed = urlparse(u)
        if parsed.scheme not in ("http", "https"):
            return False
        host = parsed.hostname
        if not host:
            return False
        try:
            infos = socket.getaddrinfo(host, None)
        except Exception:
            return False
        for info in infos:
            ip = info[4][0]
            try:
                ip_obj = ipaddress.ip_address(ip)
            except Exception:
                return False
            if (
                ip_obj.is_private
                or ip_obj.is_loopback
                or ip_obj.is_link_local
                or ip_obj.is_reserved
            ):
                return False
        return True
    except Exception:
        return False


def parse_resume_text(text):
    text = normalize_text(text)
    sections = {
        "summary": "",
        "education": "",
        "experience": "",
        "projects": "",
        "skills": "",
    }

    heading_patterns = {
        "summary": re.compile(r"^(professional summary|summary|profile)$", re.I),
        "education": re.compile(
            r"^(education|academic background|qualifications)$", re.I
        ),
        "experience": re.compile(r"^(experience|work experience|employment)$", re.I),
        "projects": re.compile(r"^(projects|achievements|selected projects)$", re.I),
        "skills": re.compile(r"^(skills|technical skills|expertise)$", re.I),
    }

    current = None
    content = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        found = False
        for section, pattern in heading_patterns.items():
            if pattern.match(stripped.lower()):
                if current:
                    sections[current] = normalize_text("\n".join(content))
                current = section
                content = []
                found = True
                break
        if found:
            continue
        if current:
            content.append(stripped)
        elif not sections["summary"]:
            sections["summary"] += stripped + " "
        else:
            sections["experience"] += stripped + "\n"

    if current:
        sections[current] = normalize_text("\n".join(content))

    if not sections["skills"]:
        skills = re.findall(
            r"\b(Python|JavaScript|Java|C\+\+|HTML|CSS|Django|Flask|SQL|Excel|React|"
            r"Node\.js|Docker|Kubernetes|AWS|Azure|Git|Linux)\b",
            text,
            re.I,
        )
        if skills:
            sections["skills"] = ", ".join(dict.fromkeys([s.title() for s in skills]))

    return sections


def parse_linkedin_profile(url):
    """Best-effort LinkedIn public profile scraper with SSRF protection.

    Returns a dict with keys matching the resume fields. If the URL is unsafe
    or scraping fails, returns empty values.
    """

    if not is_safe_url(url):
        return {
            "full_name": "",
            "summary": "",
            "education": "",
            "experience": "",
            "skills": "",
            "projects": "",
            "email": "",
            "phone": "",
        }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36"
        )
    }

    result = {
        "full_name": "",
        "summary": "",
        "education": "",
        "experience": "",
        "skills": "",
        "projects": "",
        "email": "",
        "phone": "",
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception:
        return result

    soup = BeautifulSoup(response.text, "html.parser")

    # Name: prefer h1/h2
    name_tag = soup.find(["h1", "h2"])
    if name_tag:
        result["full_name"] = name_tag.get_text(strip=True)

    # Summary/about: find nearby text
    summary_tag = soup.find(string=re.compile(r"summary|about", re.I))
    if summary_tag:
        parent = summary_tag.find_parent()
        if parent:
            result["summary"] = normalize_text(
                parent.get_text(separator=" ", strip=True)
            )

    bullets = soup.find_all(
        ["li", "span"], string=re.compile(r"\bexperience\b|\bcompany\b|\brole\b", re.I)
    )
    if bullets:
        result["experience"] = normalize_text(
            "\n".join(b.get_text(strip=True) for b in bullets[:8])
        )

    edu = soup.find_all(
        string=re.compile(r"\beducation\b|\bdegree\b|\buniversity\b", re.I)
    )
    if edu:
        result["education"] = normalize_text("\n".join(e.strip() for e in edu[:6]))

    skills = soup.find_all(string=re.compile(r"\bskills?\b", re.I))
    if skills:
        result["skills"] = normalize_text("\n".join(s.strip() for s in skills[:1]))

    return result


@app.route("/")
def index():
    return redirect(url_for("step", step=1))


@app.route("/step/<int:step>", methods=["GET", "POST"])
def step(step):
    if step < 1 or step > STEPS:
        return redirect(url_for("step", step=1))

    data = get_data()

    if request.method == "POST":
        errors = []
        if step == 1:
            linkedin_url = request.form.get("linkedin_url", "").strip()
            resume_text = request.form.get("resume_text", "").strip()
            data["linkedin_url"] = linkedin_url
            data["resume_text"] = resume_text

            if linkedin_url:
                if not linkedin_url.lower().startswith(("http://", "https://")):
                    errors.append("LinkedIn URL must start with http:// or https://")
                else:
                    imported = parse_linkedin_profile(linkedin_url)
                    if any(imported.values()):
                        data.update({k: v for k, v in imported.items() if v})
                    else:
                        errors.append(
                            "Could not import data from the LinkedIn URL. "
                            "Please check the link or enter your details manually."
                        )
            elif resume_text:
                imported = parse_resume_text(resume_text)
                if any(imported.values()):
                    data.update({k: v for k, v in imported.items() if v})
                else:
                    errors.append(
                        "Could not parse the pasted resume text. "
                        "Please enter your details manually."
                    )

            data["full_name"] = request.form.get(
                "full_name", data.get("full_name", "")
            ).strip()
            data["email"] = request.form.get("email", data.get("email", "")).strip()
            data["phone"] = request.form.get("phone", data.get("phone", "")).strip()
            data["summary"] = request.form.get(
                "summary", data.get("summary", "")
            ).strip()

            if not data["full_name"]:
                errors.append("Full name is required.")
            if not data["email"]:
                errors.append("Email is required.")

        elif step == 2:
            data["education"] = request.form.get(
                "education", data.get("education", "")
            ).strip()
            data["experience"] = request.form.get(
                "experience", data.get("experience", "")
            ).strip()
            data["projects"] = request.form.get(
                "projects", data.get("projects", "")
            ).strip()
        elif step == 3:
            data["skills"] = request.form.get("skills", data.get("skills", "")).strip()
            data["template"] = request.form.get(
                "template", data.get("template", "classic")
            )

        save_data(data)

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("form_step.html", step=step, data=data)

        if step < STEPS:
            return redirect(url_for("step", step=step + 1))
        else:
            return redirect(url_for("resume"))

    return render_template("form_step.html", step=step, data=data)


@app.route("/resume")
def resume():
    data = dict(get_data())
    if not data:
        return redirect(url_for("step", step=1))

    # Make simple HTML-safe replacements for long textareas
    for key in ("education", "experience", "projects", "summary"):
        if key in data:
            escaped = escape(data[key])
            lines = [line for line in escaped.splitlines() if line.strip()]
            data[key] = (
                Markup("<p>" + "</p><p>".join(lines) + "</p>") if lines else Markup("")
            )

    return render_template("resume.html", data=data)


@app.route("/resume/pdf")
def resume_pdf():
    data = get_data()
    if not data:
        return redirect(url_for("step", step=1))

    html = render_template("resume.html", data=data)
    if weasyprint is None:
        flash(
            "PDF export is unavailable because WeasyPrint system dependencies "
            "are missing. Use the browser Print / Save PDF button instead.",
            "warning",
        )
        return redirect(url_for("resume"))

    pdf = weasyprint.HTML(string=html, base_url=request.url_root).write_pdf()
    return send_file(
        BytesIO(pdf),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="resume.pdf",
    )


@app.route("/reset")
def reset():
    session.pop("resume_data", None)
    return redirect(url_for("step", step=1))


@app.route("/health")
def health():
    # Basic checks: disk free, temp dir writable, optional external probes,
    # weasyprint availability
    issues = []

    # Disk free space (require at least 50MB free)
    try:
        total, used, free = shutil.disk_usage("/")
        if free < 50 * 1024 * 1024:
            issues.append(f"low_disk_space:{free}")
    except Exception as e:
        issues.append(f"disk_check_error:{e}")

    # Temp dir writable
    try:
        fd, path = tempfile.mkstemp()
        os.close(fd)
        os.remove(path)
    except Exception as e:
        issues.append(f"temp_write_error:{e}")

    # Optional external URL probes from env var HEALTH_CHECK_URLS (comma-separated)
    probes = os.environ.get("HEALTH_CHECK_URLS", "")
    if probes:
        for url in probes.split(","):
            url = url.strip()
            if not url:
                continue
            try:
                resp = requests.get(url, timeout=3)
                if resp.status_code >= 400:
                    issues.append(f"probe_failed:{url}:{resp.status_code}")
            except Exception as e:
                issues.append(f"probe_error:{url}:{e}")

    # Check WeasyPrint availability.
    # This is optional: the app still works without server-side PDF export.
    try:
        wp_ok = weasyprint is not None
    except NameError:
        wp_ok = False
    if not wp_ok:
        issues.append("weasyprint_unavailable")

    critical_issues = [i for i in issues if not i.startswith("weasyprint_unavailable")]
    if critical_issues:
        return {"status": "degraded", "issues": issues}, 503
    if issues:
        return {"status": "degraded", "issues": issues}, 200
    return {"status": "ok"}, 200


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=debug_mode)
