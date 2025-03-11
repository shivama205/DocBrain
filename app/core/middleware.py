from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, List, Callable, Optional

from app.core.permissions import Permission, get_permissions_for_role
from app.db.models.user import UserRole


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