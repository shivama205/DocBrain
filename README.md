![DocBrain-Banner-3](https://github.com/user-attachments/assets/6c882743-a60e-4efd-b1b7-13f83167e38e)

# DocBrain - Self-Hosted RAG Framework

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Security](https://img.shields.io/badge/security-self--hosted-brightgreen)

A privacy-focused, modular Retrieval-Augmented Generation framework for enterprises requiring full control over their sensitive data. Built for developers who need an alternative to third-party RAG services. Now with enhanced query routing and table data support.

## Why DocBrain?

- 🔒 **Data Sovereignty** - Keep sensitive documents fully within your infrastructure
- 🧩 **Framework Agnostic** - Purpose-built without LangChain/LlamaIndex dependencies
- ⚡ **Modular Architecture** - Start with managed services, transition to in-house solutions
- 🛡️ **Enterprise-Ready** - Designed for internal security and compliance needs
- 🌱 **Open Core** - Community-driven improvements with commercial extension potential

## Key Features

| Component          | Description                                                                 |
|--------------------|-----------------------------------------------------------------------------|
| **Secure Ingestion** | Process documents without external API dependencies                        |
| **Vector Storage** | Currently using Pinecone for development, with plans to support custom vector DBs in the future |
| **Privacy First**    | No data leaves your environment - self-contained processing pipeline       |
| **Multiple LLM Provider Support** | Factory pattern implementation supporting Google Gemini, OpenAI, and other providers |
| **Query Router** | Intelligent routing between different retrieval methods based on query type |
| **Table Augmented Generation (TAG)** | Enhanced reasoning over tabular data (CSV, Excel) with automatic SQL generation |

## Project Philosophy

DocBrain was created to address common challenges in enterprise RAG implementations:

- Maintaining control over sensitive internal documents
- Avoiding dependency on specific ML frameworks
- Creating clear paths from prototype to production

DocBrain enables organizations to:
- Start quickly with managed services
- Gradually replace components with internal solutions
- Maintain full visibility into data flows
- Meet strict compliance requirements

## Getting Started

DocBrain is a project to be set up, not a Python library to be installed.

```bash
# Clone the repository
git clone https://github.com/shivama205/DocBrain.git
cd DocBrain

# Install dependencies
pip install -r requirements.txt

# Configure your environment
cp .env.example .env
# Edit .env with your specific configuration settings before proceeding
```

### Running the Services

DocBrain requires running two separate components:

1. **API Server**: Handles requests and serves responses to clients
2. **Worker**: Processes background tasks like document ingestion

You need to start each component separately in different terminal sessions:

```bash
# Terminal 1: Start the API server
make run-dev

# Terminal 2: Start the Celery worker
make worker
# or 
# celery -A app.workers worker --loglevel=info
```

> **Note**: Keep both terminals running while using DocBrain. The API server won't function correctly without the worker process.

### Configuration

DocBrain is configured through the `.env` file. Essential configuration includes:

```
# Database settings
DATABASE_URL=mysql+pymysql://username:password@localhost/docbrain

# Vector storage settings (Pinecone is currently the only supported option)
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_environment

# LLM settings
LLM_PROVIDER=gemini  # Options: gemini, openai, anthropic, etc.
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key
# Add other provider API keys as needed

# Document storage
DOCUMENT_STORAGE_PATH=./storage/documents
```

Make sure to set these values before starting the services.

## User Interface

This framework has a companion frontend project available at [DocBrain-UI](https://github.com/shivama205/DocBrain-UI). The UI provides:

- Document upload and management
- Interactive query interface
- Visualization of retrieval results
- User-friendly settings configuration

To use the complete system, set up both this backend and the frontend repository.

## Advanced Features

### Query Router

The Query Router intelligently analyzes incoming queries and routes them to the most appropriate service for processing:

- **Intelligent Query Analysis**: Uses LLM-based classification to determine whether a query requires structured data retrieval (TAG) or traditional document retrieval (RAG)
- **Query Type Detection**: Automatically identifies queries about statistical information, database content, or tabular data
- **Confidence Scoring**: Provides confidence scores with each routing decision
- **Fallback Mechanisms**: Defaults to RAG for unclear queries, ensuring consistent responses

### Table Augmented Generation (TAG)

TAG enhances DocBrain's ability to reason over tabular data:

- **SQL Generation**: Automatically converts natural language queries into SQL
- **Table Schema Analysis**: Maintains and analyzes the structure of ingested tables
- **CSV Support**: Specialized ingestors for tabular data formats
- **Query Execution**: Runs generated SQL against stored tables and formats results
- **Explanation Generation**: Provides natural language explanations of results alongside the data

## Roadmap

DocBrain has an ambitious development roadmap focused on enhancing capabilities while maintaining our commitment to privacy and security.

We've recently completed implementation of:
- ✅ **Table Augmented Generation (TAG)** - SQL-based tabular data querying
- ✅ **Query Router** - Intelligent routing between retrieval methods
- ✅ **Multiple LLM Provider Support** - Factory pattern for integrating various LLM providers

Some planned future features include:
- **Multiple Vector Database Support** - Alternatives to Pinecone
- **RAG Evaluation Framework** - Integration with RAGAS for measuring performance
- **Access Control** - Document-level permission system

For the full development roadmap with implementation details and planned features, see our [ROADMAP.md](ROADMAP.md) file.

## Contributing

**We Need Your Help!** DocBrain is built by developers who understand enterprise security needs.

If you:
- Work with sensitive internal documents
- Need a RAG solution free from third-party dependencies
- Have experience building secure enterprise applications
- Want to shape the future of private, self-hosted AI

...then we'd love your contributions!

Here's how to get involved:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Areas where contributions are especially welcome:
- Document processors for specialized formats
- Vector database connectors
- Security and compliance enhancements
- Performance optimizations
- Documentation and examples

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
