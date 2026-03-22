"""Tests for the RBAC permission system."""
import pytest
from app.core.permissions import (
    Permission,
    ROLE_PERMISSIONS,
    get_permissions_for_role,
)
from app.db.models.user import UserRole


class TestRolePermissions:
    """Verify that each role has the correct permissions."""

    def test_user_role_has_minimal_permissions(self):
        perms = get_permissions_for_role(UserRole.USER)
        assert Permission.VIEW_KNOWLEDGE_BASES in perms
        assert Permission.CONVERSE_WITH_KNOWLEDGE_BASE in perms
        # Users should NOT be able to create/delete
        assert Permission.CREATE_KNOWLEDGE_BASE not in perms
        assert Permission.DELETE_KNOWLEDGE_BASE not in perms
        assert Permission.UPLOAD_DOCUMENT not in perms
        assert Permission.MANAGE_SYSTEM not in perms

    def test_owner_role_has_document_permissions(self):
        perms = get_permissions_for_role(UserRole.OWNER)
        assert Permission.CREATE_KNOWLEDGE_BASE in perms
        assert Permission.UPDATE_KNOWLEDGE_BASE in perms
        assert Permission.DELETE_KNOWLEDGE_BASE in perms
        assert Permission.UPLOAD_DOCUMENT in perms
        assert Permission.DELETE_DOCUMENT in perms
        assert Permission.VIEW_DOCUMENTS in perms
        # Owners should NOT manage system or users
        assert Permission.MANAGE_SYSTEM not in perms
        assert Permission.CREATE_USER not in perms
        assert Permission.DELETE_USER not in perms

    def test_admin_role_has_all_permissions(self):
        perms = get_permissions_for_role(UserRole.ADMIN)
        for permission in Permission:
            assert permission in perms, f"Admin missing {permission}"

    def test_unknown_role_returns_empty(self):
        perms = get_permissions_for_role("nonexistent")
        assert perms == []

    def test_owner_inherits_user_permissions(self):
        user_perms = set(get_permissions_for_role(UserRole.USER))
        owner_perms = set(get_permissions_for_role(UserRole.OWNER))
        assert user_perms.issubset(owner_perms)

    def test_admin_inherits_owner_permissions(self):
        owner_perms = set(get_permissions_for_role(UserRole.OWNER))
        admin_perms = set(get_permissions_for_role(UserRole.ADMIN))
        assert owner_perms.issubset(admin_perms)
