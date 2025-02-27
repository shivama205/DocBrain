from typing import List, Dict, Any
import logging
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Gemini
try:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')
except Exception as e:
    logger.error(f"Failed to initialize Gemini model: {e}")
    raise

class LLMUtils:
    """Utility class for LLM operations"""

    @staticmethod
    async def generate_response(
        prompt: str,
        system_prompt: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        Generate response from Gemini LLM
        
        Args:
            prompt: The main prompt/question
            system_prompt: Optional system prompt for context
            temperature: Controls randomness (0.0 to 1.0)
            max_tokens: Maximum tokens in response
            
        Returns:
            str: Generated response text
            
        Raises:
            Exception: If LLM generation fails
        """
        try:
            # Combine system prompt and user prompt if provided
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            
            # Generate response
            response = model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    top_p=0.8,
                    top_k=40
                )
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Failed to generate LLM response: {e}")
            raise

    @staticmethod
    def create_rag_prompt(query: str, context_chunks: List[Dict[str, Any]], query_context: Dict = None) -> str:
        """
        Create prompt for RAG response generation
        
        Args:
            query: The user's question
            context_chunks: List of relevant document chunks with metadata
            query_context: Additional context about the query (type, sub-questions, etc.)
            
        Returns:
            str: Formatted RAG prompt
        """
        # Format context chunks
        formatted_chunks = []
        for i, chunk in enumerate(context_chunks, 1):
            chunk_text = (
                f"[Document {i}]\n"
                f"Title: {chunk['title']}\n"
                f"Content: {chunk['content']}\n"
            )
            formatted_chunks.append(chunk_text)
            
        context = "\n\n".join(formatted_chunks)
        
        # Add query context if available
        query_analysis = ""
        if query_context:
            query_type = query_context.get('query_type', 'UNKNOWN')
            sub_questions = query_context.get('sub_questions', [])
            
            query_analysis = f"\nQuery Type: {query_type}\n"
            
            if sub_questions:
                query_analysis += "\nTo answer this question comprehensively, consider these aspects:\n"
                for i, sq in enumerate(sub_questions, 1):
                    query_analysis += f"{i}. {sq['question']}\n   Reasoning: {sq['reasoning']}\n"
        
        # Create the full prompt
        prompt = f"""You are a knowledgeable AI assistant tasked with answering questions based on provided context.
{query_analysis}
Please help answer the following question using the provided context.
If the answer cannot be fully derived from the context, acknowledge what is known and what is not.
Please cite specific documents when providing information.

Context:
{context}

Question: {query}

Guidelines for your response:
1. Focus on answering the main question while addressing any sub-aspects identified
2. Use information only from the provided context
3. Cite sources using [Document X] format
4. Be clear about any information gaps
5. Structure your response logically
6. Maintain a professional and helpful tone

Answer:"""

        return prompt

    @staticmethod
    def create_system_prompt() -> str:
        """
        Create system prompt for RAG responses
        
        Returns:
            str: System prompt for RAG
        """
        return """You are a knowledgeable AI assistant that helps users understand their documents.
Your responses should be:
1. Accurate and based solely on the provided context
2. Clear and well-structured
3. Professional in tone
4. Include relevant citations to source documents
5. Transparent about any information gaps

When answering:
- If the context fully answers the question, provide a comprehensive response
- If the context partially answers the question, explain what is known and what is missing
- If the context doesn't contain relevant information, clearly state that
- Use "Document X" citations when referencing specific information
- Maintain a helpful and professional tone throughout""" 