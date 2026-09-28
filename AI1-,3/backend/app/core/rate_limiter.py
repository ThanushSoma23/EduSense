import time
from typing import Dict, Tuple
from fastapi import HTTPException, Request, status

class RateLimiter:
    """
    In-memory IP token bucket rate limiter for auth endpoints.
    """
    def __init__(self, requests_per_minute: int = 5):
        self.requests_per_minute = requests_per_minute
        self.history: Dict[str, list] = {}


    def check(self, request: Request):
        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()

        if client_ip not in self.history:
            self.history[client_ip] = []

        # Keep requests within last 60 seconds
        self.history[client_ip] = [t for t in self.history[client_ip] if now - t < 60]

        if len(self.history[client_ip]) >= self.requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please wait a minute before retrying."
            )

        self.history[client_ip].append(now)

    check_rate_limit = check

auth_rate_limiter = RateLimiter(requests_per_minute=5)

