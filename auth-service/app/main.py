"""
auth-service/app/main.py

FastAPI application entry point for the auth service.
Configures middleware, rate limiting, CORS, and registers all routers.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import settings
from .middleware.rate_limit import limiter
from .routes import auth, users, roles

app = FastAPI(
    title="DocSign Auth Service",
    description="Authentication, MFA, and identity management for the DocSign platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Attach rate limiter to app state — slowapi reads this in its middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — only allow requests from known frontend origins
# Strict whitelist prevents other domains from making credentialed requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,  # Required for httpOnly cookie handling
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-MFA-Token"],
)

# Register routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(roles.router)


@app.get("/health")
async def health_check():
    """Health endpoint for Docker health checks and load balancer probes."""
    return {"status": "healthy", "service": "auth-service"}


@app.get("/auth/public-key")
async def get_public_key():
    """
    Expose the RSA public key so other services can verify JWTs independently.
    This is the standard JWKS-lite approach — public key is not sensitive.
    """
    from .services.jwt import get_public_key_pem
    pem = get_public_key_pem()
    return {"public_key_pem": pem.decode("utf-8")}
