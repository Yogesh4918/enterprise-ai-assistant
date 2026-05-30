"""Simple in-memory sliding-window rate limiter middleware."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class _TokenBucket:
    """Per-client token-bucket state."""

    __slots__ = ("tokens", "last_refill", "capacity", "refill_rate")

    def __init__(self, capacity: float, refill_rate: float) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.tokens = capacity
        self.last_refill = time.monotonic()

    def consume(self) -> bool:
        """Try to consume one token. Returns True if allowed."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """IP-based rate limiter using a token-bucket algorithm.

    Parameters
    ----------
    app : FastAPI
        The ASGI application.
    requests_per_minute : int
        Maximum sustained request rate per client IP.
    burst : int
        Maximum burst size (bucket capacity).
    """

    def __init__(
        self,
        app: FastAPI,
        requests_per_minute: int = 60,
        burst: int = 20,
    ) -> None:
        super().__init__(app)
        self._buckets: dict[str, _TokenBucket] = defaultdict(
            lambda: _TokenBucket(
                capacity=float(burst),
                refill_rate=requests_per_minute / 60.0,
            )
        )
        self._requests_per_minute = requests_per_minute
        self._burst = burst
        self._last_cleanup = time.monotonic()

    def _client_key(self, request: Request) -> str:
        """Derive a rate-limit key from the request."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        client = request.client
        return client.host if client else "unknown"

    def _cleanup_stale_buckets(self) -> None:
        """Remove buckets that have been idle for more than 5 minutes."""
        now = time.monotonic()
        if now - self._last_cleanup < 60.0:
            return
        self._last_cleanup = now
        stale_threshold = now - 300.0
        stale_keys = [
            k for k, b in self._buckets.items() if b.last_refill < stale_threshold
        ]
        for k in stale_keys:
            del self._buckets[k]

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Skip rate limiting for health checks
        if request.url.path == "/api/health":
            return await call_next(request)

        self._cleanup_stale_buckets()

        key = self._client_key(request)
        bucket = self._buckets[key]

        if not bucket.consume():
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please slow down.",
                    "retry_after_seconds": int(60 / self._requests_per_minute) + 1,
                },
                headers={
                    "Retry-After": str(int(60 / self._requests_per_minute) + 1),
                },
            )

        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = (time.monotonic() - start) * 1000.0
        response.headers["X-Process-Time"] = f"{elapsed_ms:.1f}ms"
        return response


def setup_rate_limit(app: FastAPI, requests_per_minute: int = 120, burst: int = 30) -> None:
    """Attach the rate-limit middleware to the application."""
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=requests_per_minute,
        burst=burst,
    )
