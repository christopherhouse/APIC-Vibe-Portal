"""Tests for bot detection middleware."""

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from apic_vibe_portal_bff.middleware.bot_detection import BotDetectionMiddleware


def _make_app(
    block_missing_ua: bool = True,
    block_known_bots: bool = True,
    exempt_paths: set[str] | None = None,
) -> Starlette:
    """Create a test Starlette app with bot detection middleware."""

    async def homepage(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "healthy"})

    app = Starlette(
        routes=[
            Route("/", homepage),
            Route("/api/test", homepage),
            Route("/health", health),
        ]
    )
    app.add_middleware(
        BotDetectionMiddleware,
        block_missing_ua=block_missing_ua,
        block_known_bots=block_known_bots,
        exempt_paths=exempt_paths,
    )
    return app


class TestBotDetection:
    """Test the BotDetectionMiddleware."""

    def test_allows_browser_request(self):
        app = _make_app()
        client = TestClient(app)
        browser_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        response = client.get(
            "/",
            headers={"User-Agent": browser_ua},
        )
        assert response.status_code == 200

    def test_blocks_missing_user_agent(self):
        app = _make_app()
        client = TestClient(app)
        response = client.get("/", headers={"User-Agent": ""})
        assert response.status_code == 403
        assert "missing User-Agent" in response.json()["detail"]

    def test_allows_missing_ua_when_disabled(self):
        app = _make_app(block_missing_ua=False)
        client = TestClient(app)
        response = client.get("/", headers={"User-Agent": ""})
        assert response.status_code == 200

    def test_blocks_python_requests(self):
        app = _make_app()
        client = TestClient(app)
        response = client.get("/", headers={"User-Agent": "python-requests/2.31.0"})
        assert response.status_code == 403
        assert "automated client" in response.json()["detail"]

    def test_blocks_curl(self):
        app = _make_app()
        client = TestClient(app)
        response = client.get("/", headers={"User-Agent": "curl/8.1.0"})
        assert response.status_code == 403

    def test_blocks_wget(self):
        app = _make_app()
        client = TestClient(app)
        response = client.get("/", headers={"User-Agent": "Wget/1.21"})
        assert response.status_code == 403

    def test_blocks_scrapy(self):
        app = _make_app()
        client = TestClient(app)
        response = client.get("/", headers={"User-Agent": "Scrapy/2.10"})
        assert response.status_code == 403

    def test_blocks_go_http_client(self):
        app = _make_app()
        client = TestClient(app)
        response = client.get("/", headers={"User-Agent": "Go-http-client/1.1"})
        assert response.status_code == 403

    def test_blocks_httpie(self):
        app = _make_app()
        client = TestClient(app)
        response = client.get("/", headers={"User-Agent": "HTTPie/3.2.2"})
        assert response.status_code == 403

    def test_allows_known_bots_when_disabled(self):
        app = _make_app(block_known_bots=False)
        client = TestClient(app)
        response = client.get("/", headers={"User-Agent": "python-requests/2.31.0"})
        assert response.status_code == 200

    def test_allows_browser_with_bot_substring(self):
        """A User-Agent with both bot and browser patterns should be allowed."""
        app = _make_app()
        client = TestClient(app)
        # Some browser extensions add tool names to UA string
        ua = "Mozilla/5.0 (compatible; curl/8.0; Chrome/120.0.0.0)"
        response = client.get("/", headers={"User-Agent": ua})
        assert response.status_code == 200

    def test_health_endpoint_bypasses_bot_detection(self):
        app = _make_app()
        client = TestClient(app)
        # Even with a bot UA, health endpoint should work
        response = client.get("/health", headers={"User-Agent": "python-requests/2.31.0"})
        assert response.status_code == 200

    def test_health_endpoint_no_ua(self):
        app = _make_app()
        client = TestClient(app)
        response = client.get("/health", headers={"User-Agent": ""})
        assert response.status_code == 200

    def test_custom_exempt_paths(self):
        app = _make_app(exempt_paths={"/api/test"})
        client = TestClient(app)
        response = client.get("/api/test", headers={"User-Agent": "curl/8.0"})
        assert response.status_code == 200

    def test_allows_unknown_user_agent(self):
        """Non-matching UAs that aren't in the blocked list should be allowed."""
        app = _make_app()
        client = TestClient(app)
        response = client.get("/", headers={"User-Agent": "MyCustomApp/1.0"})
        assert response.status_code == 200

    def test_case_insensitive_matching(self):
        app = _make_app()
        client = TestClient(app)
        response = client.get("/", headers={"User-Agent": "Python-Requests/2.31.0"})
        assert response.status_code == 403
