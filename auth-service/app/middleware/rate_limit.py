"""
auth-service/app/middleware/rate_limit.py

Rate limiting using slowapi (Starlette/FastAPI wrapper for limits library).
Applied at the route level so different endpoints can have different limits.

Stricter limits on auth endpoints prevent:
- Brute force password attacks (/auth/login)
- TOTP code enumeration (/auth/verify-mfa)
- MFA secret scraping (/auth/mfa/setup)
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Use client IP as the rate limit key.
# In production behind Nginx, this gets the real IP from X-Forwarded-For.
# slowapi automatically reads X-Forwarded-For when behind a trusted proxy.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"]  # Default limit — auth routes override with stricter limits
)
