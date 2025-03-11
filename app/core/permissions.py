from enum import Enum, auto
from typing import Dict, List, Set
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models.user import UserRole
from app.schemas.user import UserResponse


class Permission(str, Enum):
    # Knowledge Base permissions
    VIEW_KNOWLEDGE_BASES = "view_knowledge_bases"
    CREATE_KNOWLEDGE_BASE = "create_knowledge_base"
    UPDATE_KNOWLEDGE_BASE = "update_knowledge_base"
    DELETE_KNOWLEDGE_BASE = "delete_knowledge_base"
    
    # Document permissions
    VIEW_DOCUMENTS = "view_documents"
    UPLOAD_DOCUMENT = "upload_document"
    DELETE_DOCUMENT = "delete_document"
    
    # Conversation permissions
    CONVERSE_WITH_KNOWLEDGE_BASE = "converse_with_knowledge_base"
    
    # User management permissions
    VIEW_USERS = "view_users"
    CREATE_USER = "create_user"
    UPDATE_USER = "update_user"
    DELETE_USER = "delete_user"
    
    # System management permissions
    MANAGE_SYSTEM = "manage_system"


# Define which permissions are granted to each role
ROLE_PERMISSIONS: Dict[UserRole, List[Permission]] = {
    UserRole.USER: [
        Permission.VIEW_KNOWLEDGE_BASES,
        Permission.CONVERSE_WITH_KNOWLEDGE_BASE,
    ],
    UserRole.OWNER: [
        Permission.VIEW_KNOWLEDGE_BASES,
        Permission.CREATE_KNOWLEDGE_BASE,
        Permission.UPDATE_KNOWLEDGE_BASE,
        Permission.DELETE_KNOWLEDGE_BASE,
        Permission.VIEW_DOCUMENTS,
        Permission.UPLOAD_DOCUMENT,
        Permission.DELETE_DOCUMENT,
        Permission.CONVERSE_WITH_KNOWLEDGE_BASE,
        Permission.VIEW_USERS,
    ],
    UserRole.ADMIN: [
        Permission.VIEW_KNOWLEDGE_BASES,
        Permission.CREATE_KNOWLEDGE_BASE,
        Permission.UPDATE_KNOWLEDGE_BASE,
        Permission.DELETE_KNOWLEDGE_BASE,
        Permission.VIEW_DOCUMENTS,
        Permission.UPLOAD_DOCUMENT,
        Permission.DELETE_DOCUMENT,
        Permission.CONVERSE_WITH_KNOWLEDGE_BASE,
        Permission.VIEW_USERS,
        Permission.CREATE_USER,
        Permission.UPDATE_USER,
        Permission.DELETE_USER,
        Permission.MANAGE_SYSTEM,
    ],
}


def get_permissions_for_role(role: UserRole) -> List[Permission]:
    """Get all permissions for a specific role"""
    return ROLE_PERMISSIONS.get(role, [])


def check_permission(required_permission: Permission):
    """
    Dependency function to check if a user has the required permission
    Usage in routes:
        @router.get("/endpoint")
        def endpoint(_, permission=Depends(check_permission(Permission.SOME_PERMISSION))):
            # This will only execute if the user has the required permission
            pass
    """
    async def permission_dependency(current_user: UserResponse = Depends(get_current_user)):
        if current_user.role not in ROLE_PERMISSIONS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {current_user.role} has no defined permissions",
            )
            
        # Get permissions for the user's role
        user_permissions = get_permissions_for_role(current_user.role)
        
        # Check if the user has the required permission
        if required_permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {required_permission} required",
            )
        
        # User has the permission, return the current user
        return current_user
    
    return permission_dependency


def require_permissions(required_permissions: List[Permission]):
    """
    Dependency function to check if a user has multiple required permissions
    Usage in routes:
        @router.get("/endpoint")
        def endpoint(_, permission=Depends(require_permissions([Permission.PERM1, Permission.PERM2]))):
            # This will only execute if the user has ALL the required permissions
            pass
    """
    async def permissions_dependency(current_user: UserResponse = Depends(get_current_user)):
        if current_user.role not in ROLE_PERMISSIONS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {current_user.role} has no defined permissions",
            )
            
        # Get permissions for the user's role
        user_permissions = get_permissions_for_role(current_user.role)
        
        # Check if the user has all required permissions
        missing_permissions = [
            perm for perm in required_permissions if perm not in user_permissions
        ]
        
        if missing_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: missing {', '.join(missing_permissions)}",
            )
        
        # User has all permissions, return the current user
        return current_user
    
    return permissions_dependency 