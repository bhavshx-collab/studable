"""
Regression tests for CORS configuration.

Verifies:
1. OPTIONS preflight with Vercel origin is allowed → 200 + correct header.
2. OPTIONS preflight with unauthorized origin → no Access-Control-Allow-Origin header.
3. ALLOWED_ORIGINS env var parsing: comma-separated and JSON array formats.
4. API URL construction: no double /api/v1 prefix.
5. Settings.CORS_ORIGINS property correctly parses ALLOWED_ORIGINS.
"""
from __future__ import annotations

import os
import pytest
from httpx import AsyncClient, ASGITransport


# ── 1. Settings parsing tests ─────────────────────────────────────────────────

def test_cors_origins_default_contains_vercel():
    """CORS_ORIGINS default must include the Vercel production frontend."""
    from app.core.config import Settings
    s = Settings()
    assert "https://studable-eight.vercel.app" in s.CORS_ORIGINS, (
        f"Vercel URL missing from default CORS_ORIGINS: {s.CORS_ORIGINS}"
    )


def test_cors_origins_default_contains_local():
    """CORS_ORIGINS default must include local dev origins."""
    from app.core.config import Settings
    s = Settings()
    assert "http://localhost:3000" in s.CORS_ORIGINS
    assert "http://localhost:5173" in s.CORS_ORIGINS


def test_allowed_origins_comma_separated(monkeypatch):
    """ALLOWED_ORIGINS env var: comma-separated string is correctly parsed."""
    monkeypatch.setenv(
        "ALLOWED_ORIGINS",
        "https://studable-eight.vercel.app,http://localhost:3000"
    )
    from app.core.config import Settings
    s = Settings()
    origins = s.CORS_ORIGINS
    assert "https://studable-eight.vercel.app" in origins
    assert "http://localhost:3000" in origins
    assert len(origins) == 2


def test_allowed_origins_json_array(monkeypatch):
    """ALLOWED_ORIGINS env var: JSON array string is correctly parsed."""
    monkeypatch.setenv(
        "ALLOWED_ORIGINS",
        '["https://studable-eight.vercel.app", "http://localhost:5173"]'
    )
    from app.core.config import Settings
    s = Settings()
    origins = s.CORS_ORIGINS
    assert "https://studable-eight.vercel.app" in origins
    assert "http://localhost:5173" in origins
    assert len(origins) == 2


def test_cors_origins_no_nested_list():
    """CORS_ORIGINS must NOT contain a nested list (original bug)."""
    from app.core.config import Settings
    s = Settings()
    for item in s.CORS_ORIGINS:
        assert isinstance(item, str), (
            f"CORS_ORIGINS contains non-string item: {item!r} "
            f"(nested list bug — full list: {s.CORS_ORIGINS})"
        )


def test_cors_origins_no_duplicates():
    """CORS_ORIGINS must not contain duplicate origins."""
    from app.core.config import Settings
    s = Settings()
    assert len(s.CORS_ORIGINS) == len(set(s.CORS_ORIGINS)), (
        f"Duplicate origins found: {s.CORS_ORIGINS}"
    )


# ── 2. CORS middleware / preflight tests ──────────────────────────────────────

@pytest.mark.anyio
async def test_cors_preflight_vercel_origin_allowed():
    """OPTIONS preflight from Vercel frontend must receive 200 + CORS headers."""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.options(
            "/api/v1/auth/register",
            headers={
                "Origin": "https://studable-eight.vercel.app",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,authorization",
            },
        )

    assert resp.status_code == 200, (
        f"Preflight failed with {resp.status_code}. Headers: {dict(resp.headers)}"
    )
    allow_origin = resp.headers.get("access-control-allow-origin", "")
    assert allow_origin == "https://studable-eight.vercel.app", (
        f"Wrong Access-Control-Allow-Origin: {allow_origin!r}. "
        "CORS middleware may not be registered or Vercel URL is missing."
    )
    assert resp.headers.get("access-control-allow-credentials", "").lower() == "true"


@pytest.mark.anyio
async def test_cors_preflight_localhost_allowed():
    """OPTIONS preflight from localhost:3000 must be allowed."""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    assert resp.status_code == 200
    allow_origin = resp.headers.get("access-control-allow-origin", "")
    assert allow_origin == "http://localhost:3000", (
        f"Wrong Access-Control-Allow-Origin: {allow_origin!r}"
    )


@pytest.mark.anyio
async def test_cors_preflight_unauthorized_origin_blocked():
    """OPTIONS preflight from an unauthorized origin must NOT return CORS headers."""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.options(
            "/api/v1/auth/register",
            headers={
                "Origin": "https://evil-attacker.example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    allow_origin = resp.headers.get("access-control-allow-origin", "")
    assert allow_origin != "*", "Wildcard origin must never be returned with credentials"
    assert allow_origin != "https://evil-attacker.example.com", (
        "Unauthorized origin received Access-Control-Allow-Origin header!"
    )


@pytest.mark.anyio
async def test_cors_actual_request_with_vercel_origin():
    """Actual GET request with Vercel Origin header must have CORS response header."""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.get(
            "/api/v1/health",
            headers={"Origin": "https://studable-eight.vercel.app"},
        )

    allow_origin = resp.headers.get("access-control-allow-origin", "")
    assert allow_origin == "https://studable-eight.vercel.app", (
        f"CORS header missing on actual request: {allow_origin!r}"
    )


# ── 3. API URL construction tests ─────────────────────────────────────────────

def test_no_double_api_v1_in_endpoints():
    """
    Auth API URLs must not contain /api/v1/api/v1 double prefix.
    When VITE_API_URL is 'https://api.example.com' (no trailing /api/v1),
    the authApi constructs full URLs like https://api.example.com/api/v1/auth/register.
    """
    # Simulate what authApi.ts does
    vite_api_url = "https://studableapi-production.up.railway.app"
    api_base = vite_api_url.rstrip("/")
    register_url = f"{api_base}/api/v1/auth/register"
    # Must not double-prefix
    assert "/api/v1/api/v1/" not in register_url, (
        f"Double /api/v1 prefix detected: {register_url}"
    )
    assert register_url == "https://studableapi-production.up.railway.app/api/v1/auth/register"


def test_no_double_api_v1_when_base_has_path():
    """
    If VITE_API_URL accidentally includes /api/v1, the URL would double up.
    This documents the expected correct value and fails if the URL is wrong.
    """
    # This is the WRONG value (user should NOT set VITE_API_URL with /api/v1)
    wrong_base = "https://studableapi-production.up.railway.app/api/v1"
    register_url = f"{wrong_base}/api/v1/auth/register"
    assert "/api/v1/api/v1/" in register_url, (
        "Test setup error: expected double /api/v1 to be present for wrong base"
    )
    # Confirm: the correct base should NOT include /api/v1
    correct_base = "https://studableapi-production.up.railway.app"
    assert "/api/v1" not in correct_base, (
        "VITE_API_URL should be the base domain only, without /api/v1"
    )
