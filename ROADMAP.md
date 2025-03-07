# DocBrain Enhancement Roadmap

This roadmap outlines the planned enhancements to DocBrain, our self-hosted RAG (Retrieval-Augmented Generation) framework focused on privacy, security, and modularity.

## Phase 1: Core RAG Capabilities

### 1. ✅ TAG (Table Augmented Generation)

**Priority: High** | **Status: Completed**

Enable reasoning over tabular data for more accurate responses to queries involving structured information.

**Features:**
- ✅ Table detection and extraction from documents
- ✅ SQL-like query capability over embedded tables
- ✅ LLM prompt engineering for tabular reasoning
- ✅ CSV document ingestors with table structure preservation

**Implementation Details:**
- Implemented specialized CSV ingestor with structure preservation
- Created TAG service for SQL generation from natural language queries
- Built schema analysis system for effective SQL generation
- Added table storage in dedicated database for query execution
- Integrated with query router for intelligent service selection

### 2. Advanced Document Ingestors

**Priority: High**

Add support for additional document formats with focus on structured data extraction.

**Document Types:**
- ✅ CSV spreadsheets
- DOCX / Word documents
- HTML with table extraction
- PDF tables and forms
- Markdown with formatted content

**Implementation approach:**
- Create specialized extractors for each format
- Focus on maintaining structural information
- Implement metadata extraction
- Build chunking strategies optimized for each format

### 3. ✅ Retrieval Router

**Priority: High** | **Status: Completed**

Implement intelligent routing between different retrieval methods based on query type.

**Components:**
- ✅ Query classifier to determine optimal retrieval strategy
- ✅ Multiple retrieval pipelines optimized for different query types
- ✅ Hybrid retrieval combining different search methods
- ✅ Query-specific processing paths

**Implementation Details:**
- Created QueryRouter class with LLM-based query analysis
- Implemented routing between RAG and TAG services
- Added confidence scoring for routing decisions
- Built fallback mechanisms for uncertain classifications
- Integrated routing information into response metadata

## Phase 2: Provider Integrations

### 4. Multiple LLM Provider Support

**Priority: High** | **Status: Completed**

Expand beyond Google Gemini to support multiple LLM providers.

**Target Implementations:**
- ✅ OpenAI (GPT-3.5, GPT-4)
- ✅ Anthropic (Claude)
- ✅ HuggingFace models
- Mistral AI

**Implementation Details:**
- ✅ Created LLM Factory pattern for provider-agnostic interface
- ✅ Implemented provider-specific adapters for major LLM providers
- ✅ Added configuration for model selection and parameters
- ✅ Added support for API key management
- Future work: Implement usage tracking and cost optimization

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

## Current Architectural Constraints

These constraints represent current limitations that may be addressed in future roadmap items:

### Vector Store Dependency

**Status: Active Constraint**

- Current tight coupling with Pinecone for vector storage
- Limited ability to switch providers without significant refactoring
- Reliance on external API availability and rate limits

**Mitigation Strategy:**
- Implement the vector store abstraction layer (Roadmap item 5)
- Develop local fallback options for development and testing
- Create data migration utilities between providers

### Table Query Limitations

**Status: Active Constraint**

- SQL generation limited to explicitly ingested tables
- No support for cross-table joins or complex relationships
- Limited schema inference capabilities

**Mitigation Strategy:**
- Enhance table schema extraction capabilities
- Implement relationship detection between tables
- Build safety mechanisms for SQL injection prevention
- Explore GraphRAG for relationship modeling (Roadmap item 14)

### Scalability Considerations

**Status: Active Constraint**

- No evident batch processing capability for high-volume ingestion
- Limited control over chunking strategies
- Potential bottlenecks in database operations for table-heavy workloads

**Mitigation Strategy:**
- Implement configurable chunking strategies
- Develop batch processing capabilities for large document sets
- Add worker scaling recommendations to deployment guide

## Open Questions and Implementation Challenges

These questions represent areas where design decisions are still in progress or require further research:

### Vector-Table Integration

**Priority: Medium**

How should vector search results integrate with table data when both are relevant to a query?

**Possible Approaches:**
- Implement a unified ranking algorithm that scores both vector and table results
- Use LLM to dynamically determine which source is more authoritative for a given query
- Develop specialized prompting strategies for hybrid result sets
- Explore structured metadata embeddings that incorporate table relationships

### Caching Strategy

**Priority: Medium**

What caching approach provides the optimal balance of performance and freshness?

**Areas to Explore:**
- Which components benefit most from caching (embeddings, query results, LLM responses)
- How to implement effective cache invalidation for updated documents
- Appropriate time-to-live settings for different cache types
- Potential for pre-computation of common queries

### Confidence Scoring Calibration

**Priority: High**

How can we ensure routing confidence scores are well-calibrated and reliable?

**Research Directions:**
- Evaluation metrics for routing decision quality
- Methods for continuous improvement of router accuracy
- Threshold tuning methodology for different query types
- Implementation of feedback loops from user interactions

### Response Validation

**Priority: High**

What mechanisms can ensure factual accuracy and prevent hallucination?

**Potential Solutions:**
- Implement grounding techniques to verify generated content against retrieved context
- Develop confidence scoring for answer components
- Create explicit citation mechanisms linking assertions to source material
- Explore multi-step generation with self-verification

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

- **v1.4** - Added architectural constraints and open questions sections (May 2024)
- **v1.3** - Updated to mark completion of TAG and Query Router features (May 2024)
- **v1.2** - Updated priorities based on implementation focus (May 2024)
- **v1.1** - Updated with comprehensive feature list (May 2024)
- **v1.0** - Initial roadmap created (May 2024)

## Roadmap Summary

DocBrain has an ambitious development roadmap focused on enhancing capabilities while maintaining our commitment to privacy and security.

We've recently completed implementation of:
- ✅ **Table Augmented Generation (TAG)** - SQL-based tabular data querying
- ✅ **Query Router** - Intelligent routing between retrieval methods
- ✅ **Multiple LLM Provider Support** - Factory pattern for integrating various LLM providers

Some planned future features include:
- **Multiple Vector Database Support** - Alternatives to Pinecone
- **RAG Evaluation Framework** - Integration with RAGAS for measuring performance
- **Access Control** - Document-level permission system 