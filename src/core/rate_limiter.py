"""Rate limiting middleware for admin endpoints"""
from fastapi import Request, HTTPException, status
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict
import asyncio

# Simple in-memory rate limiter
class RateLimiter:
    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = defaultdict(list)
        self.lock = asyncio.Lock()

    async def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed based on rate limit"""
        async with self.lock:
            now = datetime.utcnow()
            window_start = now - timedelta(seconds=self.window_seconds)

            # Clean old requests
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if req_time > window_start
            ]

            # Check if under limit
            if len(self.requests[identifier]) >= self.max_requests:
                return False

            # Add current request
            self.requests[identifier].append(now)
            return True


# Global rate limiter instances
login_rate_limiter = RateLimiter(max_requests=5, window_seconds=300)  # 5 attempts per 5 minutes
api_rate_limiter = RateLimiter(max_requests=30, window_seconds=60)  # 30 requests per minute


async def check_rate_limit(request: Request, limiter: RateLimiter):
    """Check rate limit for a request"""
    # Use IP address as identifier
    client_ip = request.client.host if request.client else "unknown"

    if not await limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later."
        )
