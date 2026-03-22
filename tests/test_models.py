"""Tests for database models and enums."""

from app.db.models.knowledge_base import DocumentStatus, DocumentType
from app.db.models.user import UserRole


class TestUserRole:
    def test_all_roles_exist(self):
        assert UserRole.ADMIN == "admin"
        assert UserRole.OWNER == "owner"
        assert UserRole.USER == "user"

    def test_role_count(self):
        assert len(UserRole) == 3


class TestDocumentStatus:
    def test_all_statuses_exist(self):
        assert DocumentStatus.PENDING == "PENDING"
        assert DocumentStatus.PROCESSING == "PROCESSING"
        assert DocumentStatus.PROCESSED == "PROCESSED"
        assert DocumentStatus.FAILED == "FAILED"

    def test_status_count(self):
        assert len(DocumentStatus) == 4


class TestDocumentType:
    def test_pdf_type(self):
        assert DocumentType.PDF == "application/pdf"

    def test_csv_type(self):
        assert DocumentType.CSV == "text/csv"

    def test_image_types_exist(self):
        assert DocumentType.JPG == "image/jpeg"
        assert DocumentType.PNG == "image/png"
        assert DocumentType.GIF == "image/gif"
        assert DocumentType.TIFF == "image/tiff"

    def test_text_types_exist(self):
        assert DocumentType.TXT == "text/plain"
        assert DocumentType.MARKDOWN == "text/markdown"
        assert DocumentType.HTML == "text/html"

    def test_all_types_are_strings(self):
        for doc_type in DocumentType:
            assert isinstance(doc_type.value, str)
