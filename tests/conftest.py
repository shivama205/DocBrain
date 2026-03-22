"""
Shared test fixtures for DocBrain test suite.

Environment variables and module mocks are set up before any app imports
to avoid database connection errors during testing.
"""

import os
import sys
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# 1. Set test environment variables BEFORE any app imports
# ---------------------------------------------------------------------------
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests")
os.environ.setdefault("SENDGRID_API_KEY", "test-key")
os.environ.setdefault("FROM_EMAIL", "test@example.com")
os.environ.setdefault("PINECONE_API_KEY", "test-key")
os.environ.setdefault("PINECONE_ENVIRONMENT", "test")
os.environ.setdefault("WHITELISTED_EMAILS", "test@example.com")
os.environ.setdefault("MYSQL_HOST", "localhost")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
# Use SQLite for test to avoid needing MySQL driver
os.environ["DATABASE_URL"] = "sqlite://"

# ---------------------------------------------------------------------------
# 2. Pre-populate sys.modules with a mock for app.db.database so that
#    importing permissions / middleware does NOT trigger create_engine.
# ---------------------------------------------------------------------------
_mock_db_module = MagicMock()
_mock_db_module.get_db = MagicMock()
_mock_db_module.engine = MagicMock()
_mock_db_module.SessionLocal = MagicMock()
sys.modules.setdefault("app.db.database", _mock_db_module)

# ---------------------------------------------------------------------------
# Now safe to import app modules
# ---------------------------------------------------------------------------
import pytest

from app.db.models.user import UserRole
from app.schemas.user import UserResponse


def _make_user(role: UserRole, user_id: str = "user-123") -> UserResponse:
    return UserResponse(
        id=user_id,
        email=f"{role.value}@example.com",
        full_name=f"Test {role.value.title()}",
        role=role,
        is_active=True,
        hashed_password="hashed",
    )


@pytest.fixture
def admin_user():
    return _make_user(UserRole.ADMIN, "admin-001")


@pytest.fixture
def owner_user():
    return _make_user(UserRole.OWNER, "owner-001")


@pytest.fixture
def regular_user():
    return _make_user(UserRole.USER, "user-001")


@pytest.fixture
def mock_db():
    session = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    session.refresh = MagicMock()
    return session
