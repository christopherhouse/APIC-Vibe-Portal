"""Tests for input validation middleware."""

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from apic_vibe_portal_bff.middleware.input_validation import (
    InputValidationMiddleware,
    sanitize_string,
)


def _make_app(
    max_body_size: int = 1_048_576,
    check_content_type: bool = True,
    check_path_traversal: bool = True,
    check_injection: bool = True,
    exempt_paths: set[str] | None = None,
) -> Starlette:
    """Create a test Starlette app with input validation middleware."""

    async def homepage(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    async def post_endpoint(request: Request) -> JSONResponse:
        return JSONResponse({"status": "created"})

    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "healthy"})

    app = Starlette(
        routes=[
            Route("/", homepage),
            Route("/api/data", post_endpoint, methods=["POST", "PUT", "PATCH", "GET"]),
            Route("/health", health),
        ]
    )
    app.add_middleware(
        InputValidationMiddleware,
        max_body_size=max_body_size,
        check_content_type=check_content_type,
        check_path_traversal=check_path_traversal,
        check_injection=check_injection,
        exempt_paths=exempt_paths,
    )
    return app


class TestSanitizeString:
    """Test the sanitize_string utility function."""

    def test_plain_text_unchanged(self):
        assert sanitize_string("hello world") == "hello world"

    def test_removes_script_tags(self):
        result = sanitize_string('<script>alert("xss")</script>hello')
        assert "<script>" not in result
        assert "hello" in result

    def test_removes_html_tags(self):
        result = sanitize_string("<b>bold</b> and <i>italic</i>")
        assert "<b>" not in result
        assert "bold" in result
        assert "italic" in result

    def test_removes_nested_script(self):
        result = sanitize_string('<script type="text/javascript">document.cookie</script>')
        assert "document.cookie" not in result

    def test_empty_string(self):
        assert sanitize_string("") == ""


class TestInputValidationMiddleware:
    """Test the InputValidationMiddleware."""

    def test_allows_normal_get_request(self):
        app = _make_app()
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200

    def test_allows_post_with_json_content_type(self):
        app = _make_app()
        client = TestClient(app)
        response = client.post(
            "/api/data",
            json={"key": "value"},
        )
        assert response.status_code == 200

    def test_allows_post_with_form_content_type(self):
        app = _make_app()
        client = TestClient(app)
        response = client.post(
            "/api/data",
            data={"key": "value"},
        )
        assert response.status_code == 200

    def test_blocks_post_without_content_type(self):
        app = _make_app()
        client = TestClient(app)
        response = client.post(
            "/api/data",
            content=b"raw data",
            headers={"Content-Type": ""},
        )
        assert response.status_code == 415
        assert "Content-Type header is required" in response.json()["detail"]

    def test_blocks_unsupported_content_type(self):
        app = _make_app()
        client = TestClient(app)
        response = client.post(
            "/api/data",
            content=b"<xml>data</xml>",
            headers={"Content-Type": "application/xml"},
        )
        assert response.status_code == 415
        assert "not supported" in response.json()["detail"]

    def test_allows_content_type_check_disabled(self):
        app = _make_app(check_content_type=False)
        client = TestClient(app)
        response = client.post(
            "/api/data",
            content=b"raw data",
            headers={"Content-Type": ""},
        )
        assert response.status_code == 200

    def test_blocks_oversized_body(self):
        app = _make_app(max_body_size=100)
        client = TestClient(app)
        response = client.post(
            "/api/data",
            content=b"x" * 200,
            headers={"Content-Type": "application/json", "Content-Length": "200"},
        )
        assert response.status_code == 413
        assert "exceeds maximum size" in response.json()["detail"]

    def test_allows_body_within_limit(self):
        app = _make_app(max_body_size=1000)
        client = TestClient(app)
        response = client.post(
            "/api/data",
            json={"key": "value"},
        )
        assert response.status_code == 200

    # --- Path Traversal Tests ---

    def test_blocks_path_traversal(self):
        app = _make_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/data?file=../../etc/passwd")
        assert response.status_code == 400
        assert "Path traversal" in response.json()["detail"]

    def test_blocks_encoded_path_traversal(self):
        app = _make_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/data?file=%2e%2e%2fetc/passwd")
        assert response.status_code == 400
        assert "Path traversal" in response.json()["detail"]

    def test_allows_normal_paths(self):
        app = _make_app()
        client = TestClient(app)
        response = client.get("/api/data?search=hello+world")
        assert response.status_code == 200

    # --- Injection Detection Tests ---

    def test_blocks_script_injection_in_query(self):
        app = _make_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get('/api/data?q=<script>alert("xss")</script>')
        assert response.status_code == 400
        assert "script injection" in response.json()["detail"]

    def test_blocks_sql_injection_in_query(self):
        app = _make_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/data?id=1 UNION SELECT * FROM users")
        assert response.status_code == 400
        assert "SQL injection" in response.json()["detail"]

    def test_allows_normal_query(self):
        app = _make_app()
        client = TestClient(app)
        response = client.get("/api/data?search=api+management&page=1")
        assert response.status_code == 200

    def test_allows_injection_check_disabled(self):
        app = _make_app(check_injection=False)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/data?q=<script>alert(1)</script>")
        # Should pass through (404 from actual router or 200 if matched)
        assert response.status_code != 400

    # --- Exempt Paths ---

    def test_health_endpoint_bypasses_validation(self):
        app = _make_app()
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_custom_exempt_paths(self):
        app = _make_app(exempt_paths={"/api/data"})
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/data?q=<script>alert(1)</script>")
        assert response.status_code != 400

    # --- GET requests don't need Content-Type ---

    def test_get_request_no_content_type_required(self):
        app = _make_app()
        client = TestClient(app)
        response = client.get("/api/data")
        assert response.status_code == 200
