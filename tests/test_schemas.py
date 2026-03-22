"""Tests for Pydantic schemas validation."""

import pytest
from pydantic import ValidationError

from app.db.models.user import UserRole
from app.schemas.user import UserCreate, UserResponse, UserUpdate


class TestUserCreate:
    def test_valid_user(self):
        user = UserCreate(
            email="test@example.com",
            full_name="Test User",
            password="securepassword123",
        )
        assert user.email == "test@example.com"
        assert user.role == UserRole.USER  # default

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            UserCreate(
                email="not-an-email",
                full_name="Test",
                password="password",
            )

    def test_missing_password_raises(self):
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                full_name="Test",
            )

    def test_custom_role(self):
        user = UserCreate(
            email="admin@example.com",
            full_name="Admin",
            password="password",
            role=UserRole.ADMIN,
        )
        assert user.role == UserRole.ADMIN


class TestUserUpdate:
    def test_all_fields_optional(self):
        update = UserUpdate()
        assert update.email is None
        assert update.full_name is None
        assert update.password is None

    def test_partial_update(self):
        update = UserUpdate(full_name="New Name")
        assert update.full_name == "New Name"
        assert update.email is None


class TestUserResponse:
    def test_from_attributes(self):
        resp = UserResponse(
            id="user-123",
            email="test@example.com",
            full_name="Test User",
            role=UserRole.USER,
            is_active=True,
            hashed_password="hashed_secret",
        )
        assert resp.id == "user-123"
        assert resp.is_active is True
