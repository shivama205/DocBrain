from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)

class LLM(ABC):
    """
    Abstract base class for language models that generate answers.
    """
    
    @abstractmethod
    async def generate_answer(
        self,
        query: str,
        context: List[Dict[str, Any]],
        **kwargs
    ) -> str:
        """
        Generate an answer based on the query and context.
        
        Args:
            query: The user's query
            context: List of context chunks to use for answering
            **kwargs: Additional parameters for the model
            
        Returns:
            Generated answer as a string
        """
        pass

class GeminiLLM(LLM):
    """
    LLM implementation that uses Google's Gemini API.
    """
    
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        """
        Initialize the GeminiLLM with a model.
        
        Args:
            model_name: Name of the Gemini model to use
        """
        try:
            logger.info(f"Initializing GeminiLLM with model {model_name}")
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(model_name)
            logger.info(f"GeminiLLM initialized with model {model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize GeminiLLM: {e}", exc_info=True)
            raise
    
    async def generate_answer(
        self,
        query: str,
        context: List[Dict[str, Any]],
        **kwargs
    ) -> str:
        """
        Generate an answer using Gemini.
        
        Args:
            query: The user's query
            context: List of context chunks to use for answering
            **kwargs: Additional parameters for the model
            
        Returns:
            Generated answer as a string
        """
        try:
            logger.info(f"Generating answer for query: {query}")
            logger.info(f"Using {len(context)} context chunks")
            
            # Format context chunks
            formatted_context = self._format_context(context)
            
            # Create prompt
            prompt = self._create_prompt(query, formatted_context)
            
            # Generate response
            response = self.model.generate_content(prompt)
            
            logger.info(f"Generated answer with {len(response.text)} characters")
            
            return response.text
            
        except Exception as e:
            logger.error(f"Failed to generate answer: {e}", exc_info=True)
            return f"I apologize, but I encountered an error while generating an answer: {str(e)}"
    
    def _format_context(self, context: List[Dict[str, Any]]) -> str:
        """
        Format context chunks for the prompt.
        
        Args:
            context: List of context chunks
            
        Returns:
            Formatted context as a string
        """
        formatted_chunks = []
        
        for i, chunk in enumerate(context, 1):
            # Extract metadata
            document_id = chunk.get('document_id', 'unknown')
            title = chunk.get('title', 'Untitled')
            content = chunk.get('content', '')
            score = chunk.get('score', 0.0)
            
            # Format chunk
            formatted_chunk = (
                f"[Source {i}]\n"
                f"Document: {title} (ID: {document_id})\n"
                f"Relevance: {score:.3f}\n"
                f"Content: {content}\n"
            )
            
            formatted_chunks.append(formatted_chunk)
        
        return "\n\n".join(formatted_chunks)
    
    def _create_prompt(self, query: str, context: str) -> str:
        """
        Create a prompt for the model.
        
        Args:
            query: The user's query
            context: Formatted context
            
        Returns:
            Complete prompt as a string
        """
        return f"""
        Based on the given sources, please answer the question.
        If you cannot find a relevant answer in the sources, please say so.

        Sources:
        {context}

        Question: {query}

        Please provide a clear, direct answer that:
        1. Directly addresses the question
        2. Uses [Source X] notation to cite the sources
        3. Only uses information from the provided sources
        4. Maintains a professional and helpful tone""" 