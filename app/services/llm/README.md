# LLM Service Architecture

This document explains DocBrain's LLM service architecture, which provides a centralized approach to managing prompts and interacting with multiple LLM providers.

## Overview

The architecture consists of two main components:

1. **Prompt Registry** - Centralized storage and management of all LLM prompts
2. **LLM Factory** - Provider-agnostic interface for LLM interactions following OpenAI's Chat Completions API

## Prompt Registry

The Prompt Registry (`app/core/prompts.py`) centralizes all LLM prompts used throughout the application. This approach offers several benefits:

- **Single Source of Truth**: All prompts are defined in one place
- **Versioning**: Changes to prompts can be tracked through version control
- **Consistency**: Common patterns can be enforced across all prompts
- **Templating**: Uses Jinja2 for variable substitution in prompts
- **Organization**: Prompts are organized by domain and purpose

### Using the Prompt Registry

```python
from app.core.prompts import get_prompt

# Get a prompt with variables substituted
prompt = get_prompt("query_router", "analyze_query", query="What is the average salary?")

# Register a new prompt (typically only done during initialization)
from app.core.prompts import register_prompt
register_prompt("my_domain", "my_prompt", "This is a template with {{variable}}")
```

## LLM Factory

The LLM Factory (`app/services/llm/factory.py`) provides a consistent interface for interacting with multiple LLM providers, following OpenAI's Chat Completions API pattern.

### Supported Providers

- Google Gemini
- OpenAI (GPT models)
- Anthropic (Claude models)

### Benefits

- **Provider Agnostic**: Consistent interface regardless of the underlying LLM
- **Easy Switching**: Change providers with minimal code changes
- **Configuration Based**: Provider selection through environment variables
- **OpenAI Compatible**: Interface modeled after OpenAI's Chat Completions API
- **Type Safety**: Pydantic models for input/output validation

### Using the LLM Factory

```python
from app.services.llm.factory import LLMFactory, Message, Role, CompletionOptions

# Simple usage with convenience method
from app.services.llm.factory import complete

response = await complete(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"}
    ],
    options=CompletionOptions(temperature=0.7)
)

print(response.content)  # The LLM's response

# More explicit usage with full control
messages = [
    Message(role=Role.SYSTEM, content="You are a helpful assistant."),
    Message(role=Role.USER, content="Hello, how are you?")
]

options = CompletionOptions(
    temperature=0.7,
    max_tokens=500
)

# Create a specific provider instance
llm = LLMFactory.create(provider="openai", model="gpt-4o")
response = await llm.complete(messages, options)

# Or use the factory directly
response = await LLMFactory.complete(
    messages=messages,
    provider="anthropic",
    model="claude-3-sonnet-20240229",
    options=options
)
```

### Text Embeddings

The LLM Factory also supports generating text embeddings:

```python
# Generate an embedding for text
embedding = await LLMFactory.embed_text(
    text="This is the text to embed",
    model="text-embedding-004"  # Optional, defaults to Google's model
)

# Use the embedding with vector databases
similarity = cosine_similarity(embedding, other_embedding)
```

Currently supported embedding models:
- Google's `text-embedding-004` (default, 768-dimension)

## Configuration

Set the following environment variables:

```
# Default provider
LLM_PROVIDER=gemini  # Options: gemini, openai, anthropic

# Provider-specific API keys
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Optional default model (if not specified, provider-specific defaults are used)
DEFAULT_LLM_MODEL=gemini-2.0-flash
```

## Adding a New Provider

To add a new LLM provider:

1. Create a new class that extends `LLMProvider`
2. Implement the required methods
3. Add the provider to the `LLMFactory.create()` method

Example:

```python
class MyNewProvider(LLMProvider):
    def __init__(self, api_key, model):
        # Initialize the provider
        
    async def complete(self, messages, options):
        # Implement completion logic
        
# Add to factory
if provider == "my_new_provider":
    return MyNewProvider(api_key, model)
```

## Best Practices

1. **Always use the Prompt Registry** for prompt management
2. **Prefer the LLM Factory** over direct provider imports
3. **Keep prompts modular** and focused on specific tasks
4. **Use domain organization** for prompts to maintain clarity
5. **Explicitly set temperature** based on the task requirements
6. **Handle errors gracefully** with appropriate fallbacks