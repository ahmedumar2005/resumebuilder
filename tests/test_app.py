import os
import sys

import pytest

# Ensure project root on path and SECRET_KEY set before importing app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("SECRET_KEY", "test-secret-123")

from app import app, parse_resume_text  # noqa: E402


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    # Ensure SECRET_KEY is set for tests
    monkeypatch.setenv("SECRET_KEY", "test-secret-123")
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    yield


def test_parse_resume_text_basic():
    text = """
    Summary
    Experienced developer.

    Experience
    Company A - Engineer

    Education
    BS Computer Science

    Skills
    Python, Flask
    """
    sections = parse_resume_text(text)
    assert "Experienced developer" in sections["summary"]
    assert "Company A" in sections["experience"]
    assert "BS Computer Science" in sections["education"]
    assert "Python" in sections["skills"]


def test_health_endpoint():
    client = app.test_client()
    resp = client.get("/health")
    assert resp.status_code in (200, 503)
    data = resp.get_json()
    assert "status" in data


def test_is_safe_url_checks():
    # Localhost/private addresses should be rejected.
    from app import parse_linkedin_profile

    unsafe = parse_linkedin_profile("http://127.0.0.1:5000")
    assert isinstance(unsafe, dict)
    assert unsafe.get("full_name", "") == ""


def test_parse_linkedin_profile_rejects_invalid_schemes():
    from app import parse_linkedin_profile

    unsafe = parse_linkedin_profile("ftp://example.com/profile")
    assert unsafe == {
        "full_name": "",
        "summary": "",
        "education": "",
        "experience": "",
        "skills": "",
        "projects": "",
        "email": "",
        "phone": "",
    }


def test_step_flow_and_resume_generation():
    client = app.test_client()

    # Step 1 post
    r = client.post(
        "/step/1",
        data={
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "phone": "123",
            "summary": "Dev",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    # Now post step2
    r = client.post(
        "/step/2",
        data={"education": "BS CS", "experience": "X", "projects": "Y"},
        follow_redirects=True,
    )
    assert r.status_code == 200
    # Step3
    r = client.post(
        "/step/3",
        data={"skills": "Python, Flask", "template": "minimal"},
        follow_redirects=True,
    )
    assert r.status_code == 200

    # Visit resume page
    r = client.get("/resume")
    assert r.status_code == 200
    assert b"Jane Doe" in r.data
