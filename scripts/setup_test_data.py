import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.db.database import db
from app.models.user import User, UserRole
from app.core.security import get_password_hash

def setup_test_users():
    print("Creating test users...")
    
    # Create admin user
    admin = User(
        email="admin@docbrain.ai",
        hashed_password=get_password_hash("admin123!"),
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_verified=True
    )
    db.create("users", admin)
    print(f"✓ Admin user created: admin@docbrain.ai")

    # Create test user
    user = User(
        email="user@docbrain.ai",
        hashed_password=get_password_hash("user123!"),
        full_name="Test User",
        role=UserRole.USER,
        is_verified=True
    )
    db.create("users", user)
    print(f"✓ Test user created: user@docbrain.ai")

if __name__ == "__main__":
    try:
        setup_test_users()
        print("\n✨ Test users created successfully!")
        print("\nTest Credentials:")
        print("Admin User:")
        print("  Email: admin@docbrain.ai")
        print("  Password: admin123!")
        print("\nRegular User:")
        print("  Email: user@docbrain.ai")
        print("  Password: user123!")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}") 