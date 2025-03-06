# DocBrain Enhancement Roadmap

This roadmap outlines the planned enhancements to DocBrain, our self-hosted RAG (Retrieval-Augmented Generation) framework focused on privacy, security, and modularity.

## Phase 1: Core RAG Capabilities

### 1. TAG (Table Augmented Generation)

**Priority: High**

Enable reasoning over tabular data for more accurate responses to queries involving structured information.

**Features:**
- Table detection and extraction from documents
- Specialized embeddings for tabular data
- SQL-like query capability over embedded tables
- LLM prompt engineering for tabular reasoning

**Implementation approach:**
- Implement table structure preservation during ingestion
- Create specialized embedding techniques for tables
- Develop retrieval methods optimized for tabular data
- Design prompting strategies for table-based reasoning

### 2. Advanced Document Ingestors

**Priority: High**

Add support for additional document formats with focus on structured data extraction.

**Document Types:**
- CSV / Excel spreadsheets
- DOCX / Word documents
- HTML with table extraction
- PDF tables and forms
- Markdown with formatted content

**Implementation approach:**
- Create specialized extractors for each format
- Focus on maintaining structural information
- Implement metadata extraction
- Build chunking strategies optimized for each format

### 3. Retrieval Router

**Priority: High**

Implement intelligent routing between different retrieval methods based on query type.

**Components:**
- Query classifier to determine optimal retrieval strategy
- Multiple retrieval pipelines optimized for different query types
- Hybrid retrieval combining vector and keyword search
- Query reformulation for improved retrieval

**Implementation approach:**
- Train/implement query classifier
- Support BM25/keyword search alongside vector search
- Create rules engine for routing decisions
- Implement query-specific reranking strategies

## Phase 2: Provider Integrations

### 4. Multiple LLM Provider Support

**Priority: High**

Expand beyond Google Gemini to support multiple LLM providers.

**Target Implementations:**
- OpenAI (GPT-3.5, GPT-4)
- Anthropic (Claude)
- HuggingFace models
- Mistral AI

**Implementation approach:**
- Create provider-agnostic interface for LLM interactions
- Implement provider-specific adapters
- Add configuration for model selection and parameters
- Support for API key management and usage tracking

### 5. Multiple Vector Database Support

**Priority: Medium**

Extend beyond the current Pinecone implementation to support additional vector databases.

**Target Implementations:**
- Weaviate
- Qdrant
- Chroma

**Implementation approach:**
- Create abstraction layer for vector store operations
- Implement provider-specific adapters
- Add configuration options for each provider
- Provide migration utilities between providers

### 6. RAG Evaluation Framework

**Priority: Medium**

Integrate with RAGAS and custom metrics to measure and improve RAG performance.

**Metrics:**
- Faithfulness (answer accuracy relative to context)
- Answer relevance
- Context relevance
- Context recall
- Groundedness

**Implementation approach:**
- Integrate RAGAS evaluation framework
- Add custom evaluation metrics
- Create evaluation datasets
- Build dashboard for tracking performance
- Implement automated testing using evaluation metrics

### 7. Streaming Responses

**Priority: Low**

Support for streaming LLM responses in real-time.

**Features:**
- Server-sent events (SSE) API
- Progressive chunk loading
- Token-by-token streaming
- Citation generation during streaming

**Implementation approach:**
- Implement streaming-compatible API endpoints
- Create streaming adapter for LLM providers
- Update frontend to handle streaming responses
- Add support for citation tracking during streaming

## Phase 3: Enterprise Features

### 8. Access Control

**Priority: High**

Implement document-level permission system.

**Features:**
- Role-based access control
- Document-level permissions
- Content redaction based on permissions
- Audit logging for access events

**Implementation approach:**
- Design permission model
- Implement authentication integration
- Add permission checking during retrieval
- Create management interface for permissions

### 9. Audit Trails

**Priority: Medium**

Comprehensive query logging and access monitoring.

**Features:**
- Query history tracking
- Document access logging
- User activity monitoring
- Compliance reporting

**Implementation approach:**
- Design audit schema
- Implement logging middleware
- Create retention policies
- Build reporting interface

### 10. Enterprise Deployment Guide

**Priority: Medium**

Comprehensive documentation for production deployments.

**Components:**
- Docker/Kubernetes deployment templates
- Security hardening guidelines
- Scaling recommendations
- High availability configuration
- Monitoring setup

### 11. Neural Reranking with Cross-Encoder

**Priority: High**

Implement a cross-encoder reranking step to improve the relevance of retrieved chunks before answer generation.

**Benefits:**
- Provides immediate quality improvements with minimal architectural changes
- Addresses a common RAG weakness: initial retrieval often brings back marginally relevant content
- Can significantly improve answer quality by ensuring the most relevant chunks are used for generation

**Implementation approach:**
- Add a reranking step after vector retrieval
- Use a cross-encoder model (e.g., `cross-encoder/ms-marco-MiniLM-L-6-v2`)
- Score (query, chunk) pairs and reorder chunks by relevance
- Fall back gracefully if reranking fails

## Phase 4: Advanced Features

### 12. Hypothetical Document Embeddings (HyDE)

**Priority: Medium**

Implement the HyDE technique to improve retrieval for complex or abstract queries.

**Benefits:**
- Particularly effective for complex or abstract queries
- Helps bridge the gap between natural language questions and document content
- Can significantly improve retrieval for questions that require inference

**Implementation approach:**
- Generate hypothetical answers to queries using LLM
- Use these hypothetical answers to enhance retrieval
- Implement as an optional step in the RAG pipeline

### 13. Local LLM Option with Ollama

**Priority: Medium**

Add support for local LLM inference using Ollama.

**Benefits:**
- Provides flexibility for users with privacy concerns or offline requirements
- Reduces API costs for high-volume usage
- Allows for customization of models based on specific needs

**Implementation approach:**
- Create abstraction layer for LLM providers
- Implement Ollama integration
- Provide configuration options for model selection
- Ensure compatibility with existing code

### 14. GraphRAG Implementation

**Priority: Low**

Explore graph-based retrieval to capture relationships between entities in documents.

**Benefits:**
- Captures relationships between entities in documents
- Enables more complex reasoning about document content
- Improves answers for queries requiring understanding of relationships

**Implementation approach:**
- Extract entities and relationships from documents
- Build knowledge graph representation
- Implement graph-based retrieval algorithms
- Integrate with existing retrieval methods

## Success Metrics

For each enhancement, we will measure:

1. **Retrieval Quality**: Precision, recall, and mean reciprocal rank
2. **Answer Quality**: Human evaluation of answer relevance and correctness
3. **Performance Impact**: Latency and resource usage
4. **User Satisfaction**: Feedback from users on answer quality

## Contributing to the Roadmap

We welcome community input on this roadmap. If you have suggestions for features or prioritization, please:

1. Open an issue with the tag `roadmap-suggestion`
2. Include a clear description of the feature
3. Explain the benefit to DocBrain users
4. Suggest an implementation approach if possible

## Revision History

- **v1.2** - Updated priorities based on implementation focus (May 2024)
- **v1.1** - Updated with comprehensive feature list (May 2024)
- **v1.0** - Initial roadmap created (May 2024) 