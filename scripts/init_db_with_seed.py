import sys
import os
import uuid
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mysql.connector
from passlib.context import CryptContext
from app.core.config import settings
from app.models.sql import User, KnowledgeBase, Document, Conversation, Message
from app.db.database import Base, engine, SessionLocal

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_database():
    """Create the database if it doesn't exist"""
    try:
        # Connect to MySQL server without database
        conn = mysql.connector.connect(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD
        )
        cursor = conn.cursor()

        # Create database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {settings.MYSQL_DATABASE}")
        print(f"Database '{settings.MYSQL_DATABASE}' created successfully")

        # Close connection
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error creating database: {e}")
        sys.exit(1)

def create_tables():
    """Create all tables"""
    try:
        Base.metadata.create_all(bind=engine)
        print("All tables created successfully")
    except Exception as e:
        print(f"Error creating tables: {e}")
        sys.exit(1)

def add_seed_data():
    """Add seed data to the database"""
    try:
        db = SessionLocal()

        # Create admin user
        admin_id = str(uuid.uuid4())
        admin = User(
            id=admin_id,
            email="admin@docbrain.ai",
            hashed_password=pwd_context.hash("admin123"),
            full_name="Admin User",
            role="admin",
            is_verified=True,
            api_keys=["test_api_key_1"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(admin)

        # Create test user
        user_id = str(uuid.uuid4())
        test_user = User(
            id=user_id,
            email="test@docbrain.ai",
            hashed_password=pwd_context.hash("test123"),
            full_name="Test User",
            role="user",
            is_verified=True,
            api_keys=["test_api_key_2"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(test_user)

        # Create knowledge bases
        kb1_id = str(uuid.uuid4())
        kb1 = KnowledgeBase(
            id=kb1_id,
            name="Technical Documentation",
            description="Repository for technical documentation and guides",
            owner_id=admin_id,
            shared_with=[user_id],
            document_count=0,
            total_size_bytes=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(kb1)

        kb2_id = str(uuid.uuid4())
        kb2 = KnowledgeBase(
            id=kb2_id,
            name="Product Documentation",
            description="Product manuals and specifications",
            owner_id=user_id,
            shared_with=[admin_id],
            document_count=0,
            total_size_bytes=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(kb2)

        # Create sample documents
        doc1_id = str(uuid.uuid4())
        doc1 = Document(
            id=doc1_id,
            title="Getting Started Guide",
            knowledge_base_id=kb1_id,
            file_name="getting_started.pdf",
            content_type="application/pdf",
            content="Sample content for getting started guide",
            size_bytes=1024,
            status="completed",
            vector_ids=["vec_1", "vec_2"],
            processed_chunks=2,
            uploaded_by=admin_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(doc1)

        doc2_id = str(uuid.uuid4())
        doc2 = Document(
            id=doc2_id,
            title="API Documentation",
            knowledge_base_id=kb2_id,
            file_name="api_docs.md",
            content_type="text/markdown",
            content="Sample content for API documentation",
            size_bytes=2048,
            status="completed",
            vector_ids=["vec_3", "vec_4"],
            processed_chunks=2,
            uploaded_by=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(doc2)

        # Create sample conversations
        conv1_id = str(uuid.uuid4())
        conv1 = Conversation(
            id=conv1_id,
            title="Technical Support Chat",
            knowledge_base_id=kb1_id,
            owner_id=admin_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(conv1)

        conv2_id = str(uuid.uuid4())
        conv2 = Conversation(
            id=conv2_id,
            title="Product Inquiry",
            knowledge_base_id=kb2_id,
            owner_id=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(conv2)

        # Create sample messages
        msg1 = Message(
            id=str(uuid.uuid4()),
            conversation_id=conv1_id,
            content="How do I get started with the API?",
            type="user",
            status="completed",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(msg1)

        msg2 = Message(
            id=str(uuid.uuid4()),
            conversation_id=conv1_id,
            content="Here's the API documentation guide...",
            type="assistant",
            sources={"document_id": doc2_id, "chunk_index": 1},
            status="completed",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(msg2)

        # Commit all changes
        db.commit()
        print("Seed data added successfully")

    except Exception as e:
        print(f"Error adding seed data: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

def init_database():
    """Initialize database with tables and seed data"""
    print("Starting database initialization...")
    create_database()
    create_tables()
    add_seed_data()
    print("Database initialization completed successfully")

if __name__ == "__main__":
    init_database() 