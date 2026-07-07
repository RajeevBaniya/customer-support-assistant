import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.middleware.secureHeadersMiddleware import SecureHeadersMiddleware


def _make_app(app_env: str = "development") -> FastAPI:
    from fastapi import HTTPException
    from fastapi.responses import JSONResponse
    from starlette.middleware.base import BaseHTTPMiddleware

    app = FastAPI()

    class _FakeSettings:
        def __init__(self, env: str) -> None:
            self.app_env = env

    app.state.settings = _FakeSettings(app_env)

    # Register DummyAuthMiddleware first (innermost)
    class DummyAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            if request.url.path == "/early-401":
                return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
            return await call_next(request)

    app.add_middleware(DummyAuthMiddleware)

    # Register SecureHeadersMiddleware last (outermost)
    app.add_middleware(SecureHeadersMiddleware)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    @app.get("/403")
    def get_403():
        raise HTTPException(status_code=403, detail="Forbidden")

    @app.get("/404")
    def get_404():
        raise HTTPException(status_code=404, detail="Not Found")

    @app.get("/error")
    def get_error():
        raise ValueError("Simulated unexpected error")

    @app.get("/docs")
    def fake_docs():
        return {"docs": "html"}

    @app.get("/redoc")
    def fake_redoc():
        return {"redoc": "html"}

    @app.get("/openapi.json")
    def fake_openapi():
        return {"openapi": "json"}

    return app


def test_secure_headers_always_present():
    client = TestClient(_make_app("development"))
    response = client.get("/ping")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "Permissions-Policy" in response.headers
    assert "Content-Security-Policy" in response.headers


def test_hsts_absent_in_development():
    client = TestClient(_make_app("development"))
    response = client.get("/ping")
    assert "Strict-Transport-Security" not in response.headers


def test_hsts_present_in_production():
    client = TestClient(_make_app("production"))
    response = client.get("/ping")
    assert "Strict-Transport-Security" in response.headers
    assert "max-age=63072000" in response.headers["Strict-Transport-Security"]


def test_hsts_present_in_staging():
    client = TestClient(_make_app("staging"))
    response = client.get("/ping")
    assert "Strict-Transport-Security" in response.headers


def test_csp_value():
    client = TestClient(_make_app())
    response = client.get("/ping")
    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp


def test_csp_relaxed_for_docs():
    client = TestClient(_make_app())
    for path in ["/docs", "/redoc", "/openapi.json"]:
        response = client.get(path)
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "https://cdn.jsdelivr.net" in csp
        assert "unsafe-inline" in csp
        assert response.status_code == 200


def test_headers_present_on_all_status_codes():
    client = TestClient(_make_app())

    # 401 early middleware exit
    resp_401 = client.get("/early-401")
    assert resp_401.status_code == 401
    assert resp_401.headers["X-Frame-Options"] == "DENY"

    # 403 HTTP exception
    resp_403 = client.get("/403")
    assert resp_403.status_code == 403
    assert resp_403.headers["X-Frame-Options"] == "DENY"

    # 404 HTTP exception
    resp_404 = client.get("/404")
    assert resp_404.status_code == 404
    assert resp_404.headers["X-Frame-Options"] == "DENY"

    # 500 Unhandled Exception
    # FastAPI test client raises unhandled exceptions by default. We disable raise_server_exceptions:
    client_no_raise = TestClient(_make_app(), raise_server_exceptions=False)
    resp_500 = client_no_raise.get("/error")
    assert resp_500.status_code == 500
    assert resp_500.headers["X-Frame-Options"] == "DENY"
