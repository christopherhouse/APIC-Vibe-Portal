"""Tests for rate limiting middleware."""

import time

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from apic_vibe_portal_bff.middleware.rate_limit import RateLimitMiddleware, _TokenBucket

# --- Token Bucket Unit Tests ---


class TestTokenBucket:
    """Test the _TokenBucket implementation."""

    def test_initial_tokens(self):
        bucket = _TokenBucket(capacity=10.0, refill_rate=1.0)
        assert bucket.tokens == 10.0

    def test_consume_success(self):
        bucket = _TokenBucket(capacity=10.0, refill_rate=1.0)
        assert bucket.consume() is True
        assert bucket.tokens < 10.0

    def test_consume_until_empty(self):
        bucket = _TokenBucket(capacity=3.0, refill_rate=0.1)
        assert bucket.consume() is True
        assert bucket.consume() is True
        assert bucket.consume() is True
        assert bucket.consume() is False

    def test_refill_over_time(self):
        bucket = _TokenBucket(capacity=2.0, refill_rate=100.0)  # 100 tokens/sec
        bucket.consume()
        bucket.consume()
        assert bucket.consume() is False

        time.sleep(0.05)  # Wait for refill
        assert bucket.consume() is True

    def test_capacity_limit(self):
        bucket = _TokenBucket(capacity=5.0, refill_rate=1000.0)
        time.sleep(0.1)  # Would add way more than capacity
        bucket.consume()  # triggers refill
        assert bucket.tokens <= 5.0

    def test_retry_after_when_empty(self):
        bucket = _TokenBucket(capacity=1.0, refill_rate=1.0)
        bucket.consume()
        retry = bucket.retry_after()
        assert retry >= 1

    def test_retry_after_when_full(self):
        bucket = _TokenBucket(capacity=10.0, refill_rate=1.0)
        assert bucket.retry_after() == 0


# --- Middleware Integration Tests ---


def _make_app(user_rpm: int = 100, ip_rpm: int = 1000) -> Starlette:
    """Create a test Starlette app with rate limiting middleware."""

    async def homepage(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    app = Starlette(routes=[Route("/", homepage)])
    app.add_middleware(RateLimitMiddleware, user_requests_per_minute=user_rpm, ip_requests_per_minute=ip_rpm)
    return app


class TestRateLimitMiddleware:
    """Test the RateLimitMiddleware integration."""

    def test_allows_normal_requests(self):
        app = _make_app(ip_rpm=100)
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_ip_rate_limit_exceeded(self):
        app = _make_app(ip_rpm=3)
        client = TestClient(app)

        # First 3 requests should succeed
        for _ in range(3):
            response = client.get("/")
            assert response.status_code == 200

        # 4th request should be rate limited
        response = client.get("/")
        assert response.status_code == 429
        data = response.json()
        assert data["error"] == "Too Many Requests"
        assert "IP rate limit" in data["detail"]
        assert "Retry-After" in response.headers

    def test_429_includes_retry_after_header(self):
        app = _make_app(ip_rpm=1)
        client = TestClient(app)
        client.get("/")
        response = client.get("/")
        assert response.status_code == 429
        retry_after = int(response.headers["Retry-After"])
        assert retry_after >= 1

    def test_user_rate_limit(self):
        app = _make_app(user_rpm=2, ip_rpm=1000)
        client = TestClient(app)

        # Without auth middleware setting user_id, only IP limiting applies
        for _ in range(3):
            response = client.get("/")
            assert response.status_code == 200

    def test_x_forwarded_for_header(self):
        app = _make_app(ip_rpm=2)
        client = TestClient(app)

        # Different IPs should have separate rate limits
        for _ in range(2):
            response = client.get("/", headers={"X-Forwarded-For": "10.0.0.1"})
            assert response.status_code == 200

        for _ in range(2):
            response = client.get("/", headers={"X-Forwarded-For": "10.0.0.2"})
            assert response.status_code == 200

        # Now 10.0.0.1 should be rate limited
        response = client.get("/", headers={"X-Forwarded-For": "10.0.0.1"})
        assert response.status_code == 429

    def test_multiple_ips_in_x_forwarded_for(self):
        app = _make_app(ip_rpm=2)
        client = TestClient(app)

        response = client.get("/", headers={"X-Forwarded-For": "10.0.0.1, 10.0.0.2, 10.0.0.3"})
        assert response.status_code == 200

        response = client.get("/", headers={"X-Forwarded-For": "10.0.0.1, 10.0.0.99"})
        assert response.status_code == 200

        # Both have the same first IP, so this should be limited
        response = client.get("/", headers={"X-Forwarded-For": "10.0.0.1"})
        assert response.status_code == 429
