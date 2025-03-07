"""
LLM Factory for DocBrain.

This module provides a factory for creating LLM clients that follow the OpenAI Chat Completions API pattern.
It abstracts away the specific LLM provider implementations to allow easy switching between providers.
"""

from typing import Dict, List, Any, Optional, Union, Literal
import logging
import os
import json
from enum import Enum
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)

# ----- Type Definitions -----

class Role(str, Enum):
    """Message roles in the OpenAI Chat API format."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"

class Message(BaseModel):
    """Message in the OpenAI Chat API format."""
    role: Role
    content: str
    name: Optional[str] = None
    
class CompletionOptions(BaseModel):
    """Common options for completion requests across providers."""
    temperature: float = Field(default=0.7, ge=0, le=1)
    max_tokens: Optional[int] = None
    top_p: float = Field(default=1.0, ge=0, le=1)
    stream: bool = False
    stop: Optional[Union[str, List[str]]] = None
    
class CompletionResult(BaseModel):
    """Standardized result from any LLM provider."""
    content: str
    role: str = "assistant"
    finish_reason: Optional[str] = None
    model: str
    usage: Dict[str, int] = Field(default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
    raw_response: Optional[Any] = None  # Provider-specific raw response

# ----- LLM Provider Interfaces -----

class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""
    
    @abstractmethod
    async def complete(
        self, 
        messages: List[Message],
        options: Optional[CompletionOptions] = None
    ) -> CompletionResult:
        """
        Send a completion request to the LLM provider.
        
        Args:
            messages: List of messages in the conversation
            options: Completion options
            
        Returns:
            CompletionResult with the LLM's response
        """
        pass

# ----- Provider Implementations -----

class GeminiProvider(LLMProvider):
    """Google Gemini implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash"):
        """
        Initialize the Gemini provider.
        
        Args:
            api_key: Gemini API key (defaults to settings)
            model: Gemini model to use
        """
        import google.generativeai as genai
        
        self.api_key = api_key or settings.GEMINI_API_KEY
        genai.configure(api_key=self.api_key)
        self.model_name = model
        self.model = genai.GenerativeModel(model)
        logger.info(f"Initialized GeminiProvider with model: {model}")
    
    async def complete(
        self, 
        messages: List[Message],
        options: Optional[CompletionOptions] = None
    ) -> CompletionResult:
        """
        Send a completion request to Gemini.
        
        Args:
            messages: List of messages in the conversation
            options: Completion options
            
        Returns:
            CompletionResult with the LLM's response
        """
        if options is None:
            options = CompletionOptions()
            
        try:
            # Convert OpenAI-style messages to Gemini format
            gemini_messages = []
            
            for msg in messages:
                # Gemini only supports user and model roles directly
                # System messages need to be injected into the first user message
                if msg.role == Role.SYSTEM:
                    # Skip for now, we'll handle system message specially
                    continue
                elif msg.role == Role.USER:
                    gemini_messages.append({"role": "user", "parts": [msg.content]})
                elif msg.role == Role.ASSISTANT:
                    gemini_messages.append({"role": "model", "parts": [msg.content]})
                # Function messages aren't directly supported, could be converted to text
            
            # Handle system message by prepending to the first user message if present
            system_messages = [msg for msg in messages if msg.role == Role.SYSTEM]
            if system_messages and gemini_messages and gemini_messages[0]["role"] == "user":
                system_content = "\n".join([msg.content for msg in system_messages])
                gemini_messages[0]["parts"][0] = f"{system_content}\n\n{gemini_messages[0]['parts'][0]}"
            
            # Set up generation config from options
            generation_config = {
                "temperature": options.temperature,
                "top_p": options.top_p,
                "max_output_tokens": options.max_tokens,
                "stop_sequences": options.stop if isinstance(options.stop, list) else [options.stop] if options.stop else None
            }
            
            # Remove None values
            generation_config = {k: v for k, v in generation_config.items() if v is not None}
            
            # For empty conversations or just system message, create a simple content generation
            if not gemini_messages or (len(gemini_messages) == 1 and "role" in gemini_messages[0] and gemini_messages[0]["role"] == "model"):
                # Get the system message if any
                prompt = system_messages[0].content if system_messages else ""
                response = self.model.generate_content(
                    prompt,
                    generation_config=generation_config
                )
            else:
                # For chat-style conversations
                chat = self.model.start_chat(history=gemini_messages[:-1] if gemini_messages else [])
                response = chat.send_message(
                    gemini_messages[-1]["parts"][0] if gemini_messages else "",
                    generation_config=generation_config
                )
            
            return CompletionResult(
                content=response.text,
                model=self.model_name,
                finish_reason="stop",  # Gemini doesn't provide this explicitly
                raw_response=response
            )
            
        except Exception as e:
            logger.error(f"Error completing with Gemini: {e}", exc_info=True)
            raise

class OpenAIProvider(LLMProvider):
    """OpenAI ChatGPT implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        """
        Initialize the OpenAI provider.
        
        Args:
            api_key: OpenAI API key (defaults to settings)
            model: OpenAI model to use
        """
        from openai import AsyncOpenAI
        
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model_name = model
        self.client = AsyncOpenAI(api_key=self.api_key)
        logger.info(f"Initialized OpenAIProvider with model: {model}")
    
    async def complete(
        self, 
        messages: List[Message],
        options: Optional[CompletionOptions] = None
    ) -> CompletionResult:
        """
        Send a completion request to OpenAI.
        
        Args:
            messages: List of messages in the conversation
            options: Completion options
            
        Returns:
            CompletionResult with the LLM's response
        """
        if options is None:
            options = CompletionOptions()
            
        try:
            # Convert to OpenAI format (already mostly compatible)
            openai_messages = [{"role": msg.role.value, "content": msg.content} for msg in messages]
            
            # Create completion
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=openai_messages,
                temperature=options.temperature,
                max_tokens=options.max_tokens,
                top_p=options.top_p,
                stream=options.stream,
                stop=options.stop
            )
            
            # Handle the response
            choice = response.choices[0]
            
            return CompletionResult(
                content=choice.message.content,
                model=self.model_name,
                finish_reason=choice.finish_reason,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                raw_response=response
            )
            
        except Exception as e:
            logger.error(f"Error completing with OpenAI: {e}", exc_info=True)
            raise

class AnthropicProvider(LLMProvider):
    """Anthropic Claude implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-sonnet-20240229"):
        """
        Initialize the Anthropic provider.
        
        Args:
            api_key: Anthropic API key (defaults to settings)
            model: Anthropic model to use
        """
        import anthropic
        
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model_name = model
        self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
        logger.info(f"Initialized AnthropicProvider with model: {model}")
    
    async def complete(
        self, 
        messages: List[Message],
        options: Optional[CompletionOptions] = None
    ) -> CompletionResult:
        """
        Send a completion request to Anthropic.
        
        Args:
            messages: List of messages in the conversation
            options: Completion options
            
        Returns:
            CompletionResult with the LLM's response
        """
        if options is None:
            options = CompletionOptions()
            
        try:
            # Convert to Anthropic format
            anthropic_messages = []
            
            for msg in messages:
                if msg.role == Role.SYSTEM:
                    # Anthropic has a separate system parameter
                    system_content = msg.content
                elif msg.role == Role.USER:
                    anthropic_messages.append({"role": "user", "content": msg.content})
                elif msg.role == Role.ASSISTANT:
                    anthropic_messages.append({"role": "assistant", "content": msg.content})
                # Function messages aren't directly supported
            
            # Make the completion request
            response = await self.client.messages.create(
                model=self.model_name,
                messages=anthropic_messages,
                system=system_content if 'system_content' in locals() else None,
                temperature=options.temperature,
                max_tokens=options.max_tokens or 1024,
                top_p=options.top_p,
                stream=options.stream
                # Anthropic doesn't support stop sequences directly in the same way
            )
            
            # Create the completion result
            return CompletionResult(
                content=response.content[0].text,
                model=self.model_name,
                usage={},  # Anthropic doesn't provide token usage in the same format
                raw_response=response
            )
            
        except Exception as e:
            logger.error(f"Error completing with Anthropic: {e}", exc_info=True)
            raise

# ----- Factory Implementation -----

class LLMFactory:
    """Factory for creating LLM provider instances."""
    
    @staticmethod
    def create(
        provider: Literal["openai", "gemini", "anthropic"] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> LLMProvider:
        """
        Create an LLM provider instance.
        
        Args:
            provider: The LLM provider to use (defaults to settings.LLM_PROVIDER)
            model: The specific model to use (defaults to provider-specific default)
            api_key: API key for the provider (defaults to settings)
            
        Returns:
            An instance of the requested LLM provider
        """
        # Default to configuration
        provider = provider or settings.LLM_PROVIDER
        
        if provider == "openai":
            return OpenAIProvider(api_key=api_key, model=model or "gpt-3.5-turbo")
        elif provider == "gemini":
            return GeminiProvider(api_key=api_key, model=model or "gemini-2.0-flash")
        elif provider == "anthropic":
            return AnthropicProvider(api_key=api_key, model=model or "claude-3-sonnet-20240229")
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    @staticmethod
    async def complete(
        messages: List[Union[Dict[str, str], Message]],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        options: Optional[CompletionOptions] = None
    ) -> CompletionResult:
        """
        Convenience method to create a provider and complete in one step.
        
        Args:
            messages: List of messages in the conversation
            provider: The LLM provider to use (defaults to settings.LLM_PROVIDER)
            model: The specific model to use (defaults to provider-specific default)
            options: Completion options
            
        Returns:
            CompletionResult with the LLM's response
        """
        # Convert dict messages to Message objects if needed
        processed_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                processed_messages.append(Message(
                    role=msg.get("role", "user"),
                    content=msg.get("content", ""),
                    name=msg.get("name")
                ))
            else:
                processed_messages.append(msg)
        
        # Create provider and complete
        llm = LLMFactory.create(provider=provider, model=model)
        return await llm.complete(processed_messages, options=options)
        
    @staticmethod
    async def embed_text(
        text: str,
        provider: Optional[str] = None,
        model: Optional[str] = None  # Default will come from settings
    ) -> List[float]:
        """
        Generate an embedding for the provided text.
        
        Args:
            text: The text to embed
            provider: The provider to use for embeddings (defaults to Google)
            model: The embedding model to use (defaults to settings.EMBEDDING_MODEL)
            
        Returns:
            List of floats representing the embedding
        """
        try:
            # Use the model specified in settings if not provided
            embedding_model = model or settings.EMBEDDING_MODEL
            logger.info(f"Generating embedding using model: {embedding_model}")
            
            # Currently only Google's text-embedding-004 is supported
            # In the future, we can extend this to support other providers
            
            # Use Google's embedding API directly for now
            from google import genai
            from google.genai.types import ContentEmbedding
            
            # Initialize client with API key
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
            # Get embedding
            result: ContentEmbedding = client.models.embed_content(
                model=embedding_model,
                contents=text
            )
            
            # Return the embedding values
            return result.embeddings[0].values
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}", exc_info=True)
            # If embedding fails, return a zero vector of default dimension
            # This allows the system to continue operating, but will produce low-quality results
            # Consider adding appropriate error handling in the calling code
            return [0.0] * 768

# Convenience function
async def complete(
    messages: List[Union[Dict[str, str], Message]],
    provider: Optional[str] = None,
    model: Optional[str] = None,
    options: Optional[CompletionOptions] = None
) -> CompletionResult:
    """
    Complete a conversation with the configured LLM provider.
    
    Args:
        messages: List of messages in the conversation
        provider: The LLM provider to use (defaults to settings.LLM_PROVIDER)
        model: The specific model to use (defaults to provider-specific default)
        options: Completion options
        
    Returns:
        CompletionResult with the LLM's response
    """
    return await LLMFactory.complete(messages, provider, model, options) 