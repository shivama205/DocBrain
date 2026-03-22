import logging
import time
from collections import defaultdict
from typing import Callable, Dict, List, Optional

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.permissions import Permission, get_permissions_for_role

logger = logging.getLogger(__name__)


class PermissionsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to check permissions for endpoints
    This middleware is automatically applied to all routes and checks if the user
    has the required permissions based on path and method.
    """

    def __init__(
        self,
        app,
        path_permissions: Dict[str, Dict[str, List[Permission]]] = None,
        public_paths: List[str] = None,
    ):
        """
        Initialize the middleware

        Args:
            app: The FastAPI application
            path_permissions: Dict mapping paths to methods to required permissions
                Format: {"/path": {"GET": [Permission.SOME_PERMISSION]}}
            public_paths: List of paths that don't require authentication
        """
        super().__init__(app)
        self.path_permissions = path_permissions or {}
        self.public_paths = public_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth/login",
            "/auth/register",
            "/auth/password-reset",
            "/auth/password-reset-confirm",
        ]

    async def dispatch(self, request: Request, call_next: Callable):
        """
        Process the request and check permissions

        Args:
            request: The FastAPI request
            call_next: The next middleware or endpoint to call
        """
        # Skip permission check for public paths
        if any(request.url.path.startswith(path) for path in self.public_paths):
            return await call_next(request)

        # Get user from request state (set by authentication middleware)
        user = getattr(request.state, "user", None)

        # If no user is authenticated and path is not public, return 401
        if not user:
            return await call_next(request)  # Let the endpoint handle authentication

        # Check if path has permission requirements
        path_match = None
        for path in self.path_permissions:
            if request.url.path.startswith(path):
                path_match = path
                break

        if not path_match:
            # No permissions defined for this path, allow access
            return await call_next(request)

        # Get method-specific permissions
        method_permissions = self.path_permissions[path_match].get(request.method, [])

        if not method_permissions:
            # No permissions defined for this method, allow access
            return await call_next(request)

        # Get user permissions based on role
        user_permissions = get_permissions_for_role(user.role)

        # Check if user has all required permissions
        if not all(perm in user_permissions for perm in method_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this resource",
            )

        # User has permissions, proceed with request
        return await call_next(request)


# Define default path permissions for the application
DEFAULT_PATH_PERMISSIONS: Dict[str, Dict[str, List[Permission]]] = {
    # Knowledge Base routes
    "/api/knowledge-bases": {
        "GET": [Permission.VIEW_KNOWLEDGE_BASES],
        "POST": [Permission.CREATE_KNOWLEDGE_BASE],
    },
    "/api/knowledge-bases/": {
        "GET": [Permission.VIEW_KNOWLEDGE_BASES],
        "PUT": [Permission.UPDATE_KNOWLEDGE_BASE],
        "DELETE": [Permission.DELETE_KNOWLEDGE_BASE],
    },
    # Document routes
    "/api/documents": {
        "GET": [Permission.VIEW_DOCUMENTS],
        "POST": [Permission.UPLOAD_DOCUMENT],
    },
    "/api/documents/": {
        "GET": [Permission.VIEW_DOCUMENTS],
        "DELETE": [Permission.DELETE_DOCUMENT],
    },
    # Conversation routes
    "/api/conversations": {
        "GET": [Permission.CONVERSE_WITH_KNOWLEDGE_BASE],
        "POST": [Permission.CONVERSE_WITH_KNOWLEDGE_BASE],
    },
    "/api/conversations/": {
        "GET": [Permission.CONVERSE_WITH_KNOWLEDGE_BASE],
    },
    # User management routes
    "/api/users": {
        "GET": [Permission.VIEW_USERS],
        "POST": [Permission.CREATE_USER],
    },
    "/api/users/me": {
        "GET": [],  # No specific permission required - any authenticated user can access their own info
    },
    "/api/users/": {
        "GET": [Permission.VIEW_USERS],
        "PUT": [Permission.UPDATE_USER],
        "DELETE": [Permission.DELETE_USER],
    },
    # System routes
    "/api/system": {
        "GET": [Permission.MANAGE_SYSTEM],
        "POST": [Permission.MANAGE_SYSTEM],
        "PUT": [Permission.MANAGE_SYSTEM],
        "DELETE": [Permission.MANAGE_SYSTEM],
    },
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.

    Limits requests per client IP using a sliding window approach.
    For production deployments with multiple workers, consider using
    a Redis-backed solution instead.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        exempt_paths: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.exempt_paths = exempt_paths or [
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
        ]
        # {client_ip: [timestamp, ...]}
        self._requests: Dict[str, List[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _cleanup(self, timestamps: List[float], now: float) -> List[float]:
        """Remove timestamps older than 60 seconds."""
        cutoff = now - 60.0
        return [t for t in timestamps if t > cutoff]

    async def dispatch(self, request: Request, call_next: Callable):
        if any(request.url.path.startswith(p) for p in self.exempt_paths):
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        now = time.time()

        # Clean old entries and record this request
        self._requests[client_ip] = self._cleanup(self._requests[client_ip], now)

        if len(self._requests[client_ip]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": "60"},
            )

        self._requests[client_ip].append(now)
        return await call_next(request)
