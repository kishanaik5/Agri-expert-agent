import time
import threading
from typing import Dict, Any, Tuple, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class RateLimitTier:
    STANDARD = "standard"        # 10 req/min
    AGRONOMIST = "agronomist"    # 60 req/min
    ENTERPRISE = "enterprise"    # 300 req/min

TIER_LIMITS: Dict[str, Dict[str, Any]] = {
    RateLimitTier.STANDARD: {
        "name": "Standard Farmer Tier",
        "requests_per_minute": 10,
        "burst": 3,
        "window_seconds": 60
    },
    RateLimitTier.AGRONOMIST: {
        "name": "KVK Field Agronomist Tier",
        "requests_per_minute": 60,
        "burst": 10,
        "window_seconds": 60
    },
    RateLimitTier.ENTERPRISE: {
        "name": "Enterprise Research Tier",
        "requests_per_minute": 300,
        "burst": 30,
        "window_seconds": 60
    }
}

class TokenBucketRateLimiter:
    """Thread-safe Token Bucket Rate Limiter with Sliding Window and Multi-Tier Support."""
    def __init__(self):
        self._lock = threading.Lock()
        self._buckets: Dict[str, Dict[str, Any]] = {}
        self._client_tiers: Dict[str, str] = {}
        self._default_tier = RateLimitTier.STANDARD

    def set_client_tier(self, client_id: str, tier: str) -> bool:
        if tier not in TIER_LIMITS:
            return False
        with self._lock:
            self._client_tiers[client_id] = tier
            # Reset bucket for new tier
            if client_id in self._buckets:
                del self._buckets[client_id]
        return True

    def get_client_tier(self, client_id: str) -> str:
        with self._lock:
            return self._client_tiers.get(client_id, self._default_tier)

    def check_rate_limit(self, client_id: str, requested_tier: Optional[str] = None) -> Tuple[bool, int, int, int, str]:
        """
        Evaluates rate limit for client.
        Returns: (allowed, remaining, limit, reset_seconds, active_tier)
        """
        now = time.time()
        with self._lock:
            tier = requested_tier if requested_tier in TIER_LIMITS else self._client_tiers.get(client_id, self._default_tier)
            cfg = TIER_LIMITS[tier]
            limit = cfg["requests_per_minute"]
            window = cfg["window_seconds"]
            fill_rate = limit / window

            bucket = self._buckets.get(client_id)
            if not bucket:
                bucket = {
                    "tokens": float(limit),
                    "last_updated": now,
                    "window_start": now
                }
                self._buckets[client_id] = bucket

            # Replenish tokens based on elapsed time
            elapsed = now - bucket["last_updated"]
            bucket["tokens"] = min(float(limit), bucket["tokens"] + (elapsed * fill_rate))
            bucket["last_updated"] = now

            # Reset window calculation
            time_in_window = now - bucket["window_start"]
            if time_in_window >= window:
                bucket["window_start"] = now
                reset_seconds = window
            else:
                reset_seconds = max(1, int(window - time_in_window))

            if bucket["tokens"] >= 1.0:
                bucket["tokens"] -= 1.0
                remaining = int(bucket["tokens"])
                return True, remaining, limit, reset_seconds, tier
            else:
                remaining = 0
                return False, remaining, limit, reset_seconds, tier

    def get_status(self, client_id: str) -> Dict[str, Any]:
        with self._lock:
            tier = self._client_tiers.get(client_id, self._default_tier)
            cfg = TIER_LIMITS[tier]
            limit = cfg["requests_per_minute"]
            bucket = self._buckets.get(client_id)
            remaining = int(bucket["tokens"]) if bucket else limit
            return {
                "client_id": client_id,
                "tier": tier,
                "tier_name": cfg["name"],
                "limit": limit,
                "remaining": remaining,
                "window_seconds": cfg["window_seconds"],
                "available_tiers": TIER_LIMITS
            }

_rate_limiter = TokenBucketRateLimiter()

def get_rate_limiter() -> TokenBucketRateLimiter:
    return _rate_limiter

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Exempt static assets, swagger docs, and favicon
        path = request.url.path
        if (
            path.startswith("/static") or 
            path.startswith("/assets") or 
            path in ("/favicon.ico", "/docs", "/openapi.json", "/api/status", "/api/ratelimit/config", "/api/ratelimit/status")
        ):
            return await call_next(request)

        # Identify client by header or IP
        client_ip = request.headers.get("x-forwarded-for") or request.client.host if request.client else "127.0.0.1"
        client_tier = request.headers.get("x-client-tier")

        limiter = get_rate_limiter()
        allowed, remaining, limit, reset_seconds, tier = limiter.check_rate_limit(client_ip, client_tier)

        if not allowed:
            headers = {
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_seconds),
                "X-RateLimit-Tier": tier,
                "Retry-After": str(reset_seconds)
            }
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests on tier '{tier}'. Please wait {reset_seconds}s before dispatching new queries.",
                    "retry_after_seconds": reset_seconds,
                    "tier": tier,
                    "limit_per_minute": limit
                },
                headers=headers
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_seconds)
        response.headers["X-RateLimit-Tier"] = tier
        return response
