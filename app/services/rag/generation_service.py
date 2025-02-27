from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging
from pydantic import BaseModel, Field
import json
from google import genai
from app.core.config import settings

logger = logging.getLogger(__name__)

class GenerationConfig(BaseModel):
    """Configuration for the generation service."""
    
    # Model name
    model_name: str = Field(
        default="gemini-1.5-pro", 
        description="The model to use for generation"
    )
    
    # Maximum number of tokens to generate
    max_new_tokens: int = Field(
        default=1024, 
        description="Maximum number of tokens to generate"
    )
    
    # Temperature for generation
    temperature: float = Field(
        default=0.7, 
        description="Temperature for generation"
    )
    
    # Top-p for generation
    top_p: float = Field(
        default=0.95, 
        description="Top-p for generation"
    )
    
    # Top-k for generation
    top_k: int = Field(
        default=40, 
        description="Top-k for generation"
    )
    
    # System prompt
    system_prompt: str = Field(
        default="You are a helpful AI assistant that answers questions based on the provided context. "
                "If the answer is not in the context, say so clearly. "
                "Do not make up information or use prior knowledge.",
        description="System prompt for the model"
    )
    
    class Config:
        """Pydantic config"""
        extra = "forbid"  # Forbid extra attributes


class GenerationService(ABC):
    """Interface for generation services."""
    
    @abstractmethod
    async def generate(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate an answer based on the query and retrieved chunks.
        
        Args:
            query: The user query
            chunks: List of relevant chunks
            context: Additional context for generation
            
        Returns:
            Generated answer
        """
        pass


class GeminiGenerationService(GenerationService):
    """Generation service using Google's Gemini API."""
    
    def __init__(self, config: Optional[GenerationConfig] = None):
        """
        Initialize the Gemini generation service.
        
        Args:
            config: Configuration for the generation service
        """
        self.config = config or GenerationConfig()
        logger.info(f"Initializing GeminiGenerationService with config: {self.config}")
        
        try:
            # Initialize Gemini client
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
            self.model = self.client.get_model(self.config.model_name)
            
            logger.info(f"Successfully initialized Gemini model: {self.config.model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}", exc_info=True)
            raise
    
    async def generate(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate an answer using Gemini.
        
        Args:
            query: The user query
            chunks: List of relevant chunks
            context: Additional context for generation
            
        Returns:
            Generated answer
        """
        try:
            logger.info(f"Generating answer for query: '{query}'")
            logger.info(f"Using {len(chunks)} chunks for generation")
            
            if not chunks:
                logger.warning("No chunks provided for answer generation")
                return "I apologize, but I couldn't find any relevant information to answer your question."
            
            # Sort chunks by score and take only the top most relevant ones
            sorted_chunks = sorted(chunks, key=lambda x: x.get('score', 0.0), reverse=True)
            
            # Format chunks into context
            context_text = self._format_chunks_for_context(sorted_chunks)
            
            # Prepare the prompt
            prompt = self._create_prompt(query, context_text, context)
            
            # Generate the answer
            generation_config = {
                "max_output_tokens": self.config.max_new_tokens,
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
                "top_k": self.config.top_k
            }
            
            logger.info(f"Generation config: {generation_config}")
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            answer = response.text
            logger.info(f"Generated answer of length {len(answer)}")
            
            return answer
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}", exc_info=True)
            return "I apologize, but I encountered an error while generating an answer. Please try again later."
    
    def _format_chunks_for_context(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Format chunks into a context string for the model.
        
        Args:
            chunks: List of chunks to format
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            content = chunk.get('content', '')
            metadata = chunk.get('metadata', {})
            title = metadata.get('doc_title', chunk.get('title', 'Untitled'))
            score = chunk.get('score', 0.0)
            
            # Format the chunk with metadata
            chunk_text = f"[Document {i}] {title}\n"
            
            if 'section' in metadata and metadata['section']:
                chunk_text += f"Section: {metadata['section']}\n"
                
            chunk_text += f"Relevance Score: {score:.3f}\n"
            chunk_text += f"Content:\n{content}\n\n"
            
            context_parts.append(chunk_text)
        
        return "\n".join(context_parts)
    
    def _create_prompt(
        self,
        query: str,
        context_text: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a prompt for the model.
        
        Args:
            query: The user query
            context_text: Formatted context text
            additional_context: Additional context for generation
            
        Returns:
            Formatted prompt
        """
        system_prompt = self.config.system_prompt
        
        # Add additional context to system prompt if provided
        if additional_context:
            context_str = json.dumps(additional_context, indent=2)
            system_prompt += f"\n\nAdditional context:\n{context_str}"
        
        prompt = f"{system_prompt}\n\n"
        prompt += f"Context information is below:\n{context_text}\n\n"
        prompt += f"Question: {query}\n\n"
        prompt += "Answer:"
        
        return prompt 