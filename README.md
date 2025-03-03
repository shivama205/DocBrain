# RAG Framework

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A flexible and extensible Retrieval-Augmented Generation (RAG) framework for building powerful AI applications with context-aware responses.

## Features

- **Document Processing**: Ingest, chunk, and process documents from various sources
- **Vector Storage**: Store and retrieve document embeddings efficiently
- **Semantic Search**: Find the most relevant context for user queries
- **LLM Integration**: Generate accurate, context-aware responses using language models
- **Customizable Pipeline**: Adapt each component to your specific use case

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/rag-framework.git
cd rag-framework

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and configuration
```

## Quick Start

```python
from src.core import RAGPipeline
from src.utils import load_document

# Initialize the RAG pipeline
pipeline = RAGPipeline()

# Load and process a document
document = load_document("path/to/document.pdf")
pipeline.add_document(document)

# Ask a question
response = pipeline.query("What is the main topic of the document?")
print(response)
```

See the [examples](./examples) directory for more detailed usage examples.

## Future Work

- **Retriever Router**: Intelligent routing between different retrieval methods based on query type
- **CSV/Excel Data Handling**: Support for structured data sources and tabular information
- **LLM Factory**: Abstraction layer for multiple LLM providers (OpenAI, Anthropic, HuggingFace, etc.)
- **Evaluation Framework**: Tools to measure and improve RAG performance
- **Web UI**: Simple interface for document management and querying
- **Streaming Responses**: Support for streaming LLM responses in real-time

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.