"""
Centralized prompt management system for DocBrain.

This module provides a registry for all LLM prompts used throughout the application.
Prompts are organized by domain and purpose, and can be parameterized with variables.
"""

from typing import Dict, Any, Optional
import jinja2
import logging

logger = logging.getLogger(__name__)

# Configure Jinja2 environment for template rendering
_template_env = jinja2.Environment(
    autoescape=False,  # We don't need HTML escaping for prompts
    trim_blocks=True,
    lstrip_blocks=True
)

class PromptRegistry:
    """Registry for managing and accessing prompts throughout the application."""
    
    # Organized by domain/module and then by purpose
    PROMPTS = {
        "query_router": {
            "analyze_query": """
            You are a query router for a hybrid retrieval system. Your job is to determine whether to route a user query to:
            
            1. TAG (Table Augmented Generation) - for queries that need access to structured data and would be best answered with SQL 
            2. RAG (Retrieval Augmented Generation) - for queries about unstructured text/content
            
            Routes to TAG when:
            - The query asks about statistical information (averages, counts, sums)
            - The query explicitly asks for database information
            - The query requests tabular data, spreadsheets, or data analysis
            - The query involves filtering, sorting, or comparing quantitative data
            - The query is clearly asking for information that would be stored in a structured format
            
            Routes to RAG when:
            - The query asks about concepts, explanations, or general information
            - The query is looking for specific text content
            - The query seems to be related to documents, reports, or unstructured content
            - The query is asking about procedures, policies, or general knowledge
            
            For the following query, determine the appropriate service (tag or rag), provide a confidence score (0-1),
            and explain your reasoning. Return your answer as a JSON object with the keys: service, confidence, reasoning.
            
            User Query: {{ query }}
            """
        },
        "tag_service": {
            "generate_sql": """
            You are an AI assistant that converts natural language questions into SQL queries.
            
            I have the following database tables:
            {{ schema_text }}
            
            Given this schema, please generate a SQL query that answers the following question:
            "{{ query }}"
            
            Return ONLY a valid SQL query without any explanations or markdown formatting.
            Make sure the query is compatible with common SQL dialects.
            Do not use features specific to one SQL dialect unless necessary.
            """
        },
        "rag_service": {
            "generate_answer": """
            You are an assistant that provides accurate, helpful answers based on the given context.
            
            CONTEXT:
            {{ context }}
            
            USER QUERY: {{ query }}
            
            Based only on the context provided, answer the user query.
            If the context doesn't contain enough information to provide a complete answer, say so.
            Cite relevant parts of the context as part of your answer using [Document: Title] format.
            """
        },
        "ingestor": {
            "generate_table_schema": """
            Generate a SQL database create table query for the given table name and headers. 
            Make sure to use headers as column names and rows as sample data.
            Rows contain sample data for the table. 

            Use your understanding to extrapolate scenario where datatype is not obvious, or might be different from the sample data.
            
            Example: CREATE TABLE IF NOT EXISTS {{ table_name }} (
                {{ headers[0] }} VARCHAR(255) NOT NULL,
                {{ headers[1] }} VARCHAR(255) NULL,
                {{ headers[2] }} INTEGER DEFAULT 0
            );

            Table name: {{ table_name }}
            Headers: {{ headers }}
            Rows: {{ rows }}
            """
        }
        # Add more domains and prompts as needed
    }
    
    @classmethod
    def get_prompt(cls, domain: str, prompt_name: str, **kwargs) -> str:
        """
        Get a prompt by domain and name, with optional variable substitution.
        
        Args:
            domain: The domain or module the prompt belongs to
            prompt_name: The specific prompt identifier
            **kwargs: Variables to substitute in the prompt template
            
        Returns:
            The rendered prompt as a string
        """
        try:
            # Get the raw prompt template
            if domain not in cls.PROMPTS:
                logger.warning(f"Domain '{domain}' not found in prompt registry")
                return ""
                
            if prompt_name not in cls.PROMPTS[domain]:
                logger.warning(f"Prompt '{prompt_name}' not found in domain '{domain}'")
                return ""
                
            raw_prompt = cls.PROMPTS[domain][prompt_name]
            
            # If no variables to substitute, return the raw prompt
            if not kwargs:
                return raw_prompt
                
            # Render the template with the provided variables
            template = _template_env.from_string(raw_prompt)
            return template.render(**kwargs)
            
        except Exception as e:
            logger.error(f"Error rendering prompt '{domain}.{prompt_name}': {e}")
            # Return an empty string or the raw template in case of error
            return cls.PROMPTS.get(domain, {}).get(prompt_name, "")

    @classmethod
    def register_prompt(cls, domain: str, prompt_name: str, prompt_template: str) -> None:
        """
        Register a new prompt or update an existing one.
        
        Args:
            domain: The domain or module the prompt belongs to
            prompt_name: The specific prompt identifier
            prompt_template: The prompt template to register
        """
        # Create domain if it doesn't exist
        if domain not in cls.PROMPTS:
            cls.PROMPTS[domain] = {}
            
        # Register or update the prompt
        cls.PROMPTS[domain][prompt_name] = prompt_template
        logger.info(f"Registered prompt '{domain}.{prompt_name}'")

# Simple alias for brevity in imports
get_prompt = PromptRegistry.get_prompt
register_prompt = PromptRegistry.register_prompt 