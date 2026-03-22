"""Tests for factory classes (chunker, retriever, reranker, ingestor).

Ingestor and reranker factories depend on heavy ML libraries (PyPDF2, torch,
sentence-transformers). These tests mock those dependencies so they run in
any environment, including CI without GPU or ML packages.
"""

import sys
from unittest.mock import MagicMock

import pytest

from app.db.models.knowledge_base import DocumentType


# ---------------------------------------------------------------------------
# ChunkerFactory — no heavy deps, tests directly
# ---------------------------------------------------------------------------
class TestChunkerFactory:
    def test_create_chunker_returns_multi_level(self):
        from app.services.rag.chunker.chunker import MultiLevelChunker
        from app.services.rag.chunker.chunker_factory import ChunkerFactory

        chunker = ChunkerFactory.create_chunker(DocumentType.PDF)
        assert isinstance(chunker, MultiLevelChunker)

    def test_create_from_metadata_uses_document_type(self):
        from app.services.rag.chunker.chunker import MultiLevelChunker
        from app.services.rag.chunker.chunker_factory import ChunkerFactory

        metadata = {"document_type": DocumentType.CSV}
        chunker = ChunkerFactory.create_chunker_from_metadata(metadata)
        assert isinstance(chunker, MultiLevelChunker)

    def test_create_from_metadata_defaults_to_txt(self):
        from app.services.rag.chunker.chunker import MultiLevelChunker
        from app.services.rag.chunker.chunker_factory import ChunkerFactory

        chunker = ChunkerFactory.create_chunker_from_metadata({})
        assert isinstance(chunker, MultiLevelChunker)


# ---------------------------------------------------------------------------
# IngestorFactory — needs PyPDF2, pandas etc. We mock the ingestor module.
# ---------------------------------------------------------------------------
class TestIngestorFactory:
    @pytest.fixture(autouse=True)
    def _mock_ingestors(self):
        """Mock the ingestor classes so we don't need ML deps."""
        mock_module = MagicMock()
        # Create distinct mock classes so isinstance checks work via identity
        mock_module.PDFIngestor = type("PDFIngestor", (), {})
        mock_module.CSVIngestor = type("CSVIngestor", (), {})
        mock_module.MarkdownIngestor = type("MarkdownIngestor", (), {})
        mock_module.ImageIngestor = type("ImageIngestor", (), {})
        mock_module.TextIngestor = type("TextIngestor", (), {})
        mock_module.Ingestor = type("Ingestor", (), {})

        # Patch sys.modules so the factory import resolves
        orig = sys.modules.get("app.services.rag.ingestor.ingestor")
        sys.modules["app.services.rag.ingestor.ingestor"] = mock_module

        # Force reimport of factory
        if "app.services.rag.ingestor.ingestor_factory" in sys.modules:
            del sys.modules["app.services.rag.ingestor.ingestor_factory"]

        yield mock_module

        # Restore
        if orig is not None:
            sys.modules["app.services.rag.ingestor.ingestor"] = orig
        elif "app.services.rag.ingestor.ingestor" in sys.modules:
            del sys.modules["app.services.rag.ingestor.ingestor"]
        if "app.services.rag.ingestor.ingestor_factory" in sys.modules:
            del sys.modules["app.services.rag.ingestor.ingestor_factory"]

    def test_pdf_type(self, _mock_ingestors):
        from app.services.rag.ingestor.ingestor_factory import IngestorFactory

        IngestorFactory._pdf_ingestor = None
        ingestor = IngestorFactory.create_ingestor(DocumentType.PDF)
        assert type(ingestor).__name__ == "PDFIngestor"

    def test_csv_type(self, _mock_ingestors):
        from app.services.rag.ingestor.ingestor_factory import IngestorFactory

        IngestorFactory._csv_ingestor = None
        ingestor = IngestorFactory.create_ingestor(DocumentType.CSV)
        assert type(ingestor).__name__ == "CSVIngestor"

    def test_txt_type(self, _mock_ingestors):
        from app.services.rag.ingestor.ingestor_factory import IngestorFactory

        IngestorFactory._text_ingestor = None
        ingestor = IngestorFactory.create_ingestor(DocumentType.TXT)
        assert type(ingestor).__name__ == "TextIngestor"

    def test_singleton_returns_same_instance(self, _mock_ingestors):
        from app.services.rag.ingestor.ingestor_factory import IngestorFactory

        IngestorFactory._pdf_ingestor = None
        first = IngestorFactory.create_ingestor(DocumentType.PDF)
        second = IngestorFactory.create_ingestor(DocumentType.PDF)
        assert first is second


# ---------------------------------------------------------------------------
# RetrieverFactory — needs pinecone. Mock PineconeRetriever.
# ---------------------------------------------------------------------------
class TestRetrieverFactory:
    @pytest.fixture(autouse=True)
    def _mock_retriever(self):
        mock_pinecone_retriever = MagicMock()
        mock_retriever_mod = MagicMock()
        mock_retriever_mod.PineconeRetriever = mock_pinecone_retriever

        orig = sys.modules.get("app.services.rag.retriever.pinecone_retriever")
        sys.modules["app.services.rag.retriever.pinecone_retriever"] = (
            mock_retriever_mod
        )

        if "app.services.rag.retriever.retriever_factory" in sys.modules:
            del sys.modules["app.services.rag.retriever.retriever_factory"]

        yield mock_pinecone_retriever

        if orig is not None:
            sys.modules["app.services.rag.retriever.pinecone_retriever"] = orig
        elif "app.services.rag.retriever.pinecone_retriever" in sys.modules:
            del sys.modules["app.services.rag.retriever.pinecone_retriever"]
        if "app.services.rag.retriever.retriever_factory" in sys.modules:
            del sys.modules["app.services.rag.retriever.retriever_factory"]

    def test_default_creates_pinecone(self, _mock_retriever):
        from app.services.rag.retriever.retriever_factory import RetrieverFactory

        RetrieverFactory.create_retriever("kb-123")
        _mock_retriever.assert_called_with("kb-123")

    def test_unknown_type_falls_back(self, _mock_retriever):
        from app.services.rag.retriever.retriever_factory import RetrieverFactory

        RetrieverFactory.create_retriever("kb-789", retriever_type="unknown")
        _mock_retriever.assert_called_with("kb-789")
