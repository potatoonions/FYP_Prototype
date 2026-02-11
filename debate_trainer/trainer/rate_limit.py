"""
Rate limiting for API endpoints.
Implements token bucket rate limiting per IP address.
"""
from __future__ import annotations

import logging
import time
from functools import wraps
from typing import Callable

from django.core.cache import cache
from django.http import HttpRequest, JsonResponse

logger = logging.getLogger("trainer.rate_limit")

# Rate limit constants
DEFAULT_REQUESTS_PER_MINUTE = 30  # Free tier limits
DEBATE_START_LIMIT = 20
DEBATE_RESPONSE_LIMIT = 100


def get_client_ip(request: HttpRequest) -> str:
    """Extract client IP from request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def rate_limit(
    requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE,
    key_func: Callable[[HttpRequest], str] | None = None,
) -> Callable:
    """
    Rate limiting decorator for API endpoints.
    
    Args:
        requests_per_minute: Max requests per minute (default: 30)
        key_func: Optional function to generate cache key
    
    Returns:
        Decorated function with rate limiting
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(request: HttpRequest, *args, **kwargs):
            # Generate unique cache key
            if key_func:
                identifier = key_func(request)
            else:
                identifier = get_client_ip(request)
            
            cache_key = f"rate_limit:{func.__name__}:{identifier}"
            current = cache.get(cache_key, 0)
            
            # Check if rate limit exceeded
            if current >= requests_per_minute:
                logger.warning(f"Rate limit exceeded: {cache_key} ({current}/{requests_per_minute})")
                return JsonResponse(
                    {
                        "error": "Rate limit exceeded",
                        "detail": f"Maximum {requests_per_minute} requests per minute allowed",
                        "retry_after": 60,
                    },
                    status=429,
                )
            
            # Increment and set expiry
            cache.set(cache_key, current + 1, timeout=60)
            
            return func(request, *args, **kwargs)
        
        return wrapper
    return decorator


class RateLimitMixin:
    """Mixin for view classes with built-in rate limiting."""
    
    rate_limit_requests = DEFAULT_REQUESTS_PER_MINUTE
    
    def get_cache_key(self, request: HttpRequest) -> str:
        """Generate rate limit cache key."""
        return f"{self.__class__.__name__}:{get_client_ip(request)}"
    
    def check_rate_limit(self, request: HttpRequest) -> bool:
        """Check if client has exceeded rate limit."""
        cache_key = self.get_cache_key(request)
        current = cache.get(cache_key, 0)
        
        if current >= self.rate_limit_requests:
            return False
        
        cache.set(cache_key, current + 1, timeout=60)
        return True

