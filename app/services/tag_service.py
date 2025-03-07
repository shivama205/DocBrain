from typing import Dict, Any, List, Optional
import logging
import json
from app.core.config import settings
from app.db.database import get_db
from functools import lru_cache
import re
from app.db.models.knowledge_base import DocumentType
from app.db.storage import get_storage_db
from app.repositories.storage_repository import StorageRepository
from app.db.models.knowledge_base import Document
from app.services.llm.factory import LLMFactory, Message, Role, CompletionOptions
from app.core.prompts import get_prompt, register_prompt


logger = logging.getLogger(__name__)

# Register prompts used by the TAG service
register_prompt("tag_service", "generate_sql", """
You are an AI assistant that converts natural language questions into SQL queries.

I have the following database tables:
{{ schema_text }}

Given this schema, please generate a SQL query that answers the following question:
"{{ query }}"

Return ONLY a valid SQL query without any explanations or markdown formatting.
Make sure the query is compatible with common SQL dialects.
Do not use features specific to one SQL dialect unless necessary.
""")

register_prompt("tag_service", "generate_answer", """
You are an AI assistant that explains SQL query results.

Original question: "{{ query }}"

SQL query executed:
```sql
{{ sql }}
```

Query results:
{{ results }}

Please provide a clear, concise answer to the original question based on these results.
Your answer should:
1. Directly address the user's question
2. Summarize the key findings from the data
3. Be easy to understand for someone without technical SQL knowledge
4. Include specific numbers/values from the results when relevant
""")

class TagService:
    """
    Text-to-SQL service for handling structured data formats like CSV, Excel, etc.
    This service converts natural language queries to SQL and executes them against
    structured data stored in a database.
    """
    
    def __init__(self):
        """Initialize the Tag Service"""
        logger.info("Initializing TagService")
    
    async def retrieve(
        self,
        knowledge_base_id: str,
        query: str,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a natural language query against structured data using text-to-SQL.
        
        Args:
            knowledge_base_id: The ID of the knowledge base to search
            query: The natural language query to process
            metadata_filter: Additional filtering criteria
            
        Returns:
            Dictionary containing:
                - query: The original query
                - answer: The response to the query
                - sql: The generated SQL query
                - results: The results of the SQL query
                - sources: The data sources used
                - service: Always "tag"
        """
        try:
            logger.info(f"TagService processing query: '{query}'")
            
            # Get all table schemas from the database
            table_schemas = await self._get_all_table_schemas()
            
            if not table_schemas:
                logger.warning(f"No table schemas found to process query: {query}")
                return {
                    "query": query,
                    "answer": "I couldn't find any table schemas to answer your query.",
                    "sql": None,
                    "results": [],
                    "sources": [],
                    "service": "tag"
                }
            
            # Get documents from the knowledge base for sources
            documents = await self._get_knowledge_base_documents(knowledge_base_id)
            
            # Extract document IDs and titles for sources
            sources = []
            for i, doc in enumerate(documents):
                if doc.content_type in [DocumentType.CSV, DocumentType.EXCEL]:
                    # Create a source with all required fields for MessageResponse validation
                    sources.append({
                        "document_id": doc.id,
                        "title": doc.title,
                        "score": 1.0,  # Default high score for TAG sources
                        "content": f"Table data from {doc.title}",  # Provide a description as content
                        "chunk_index": i,  # Use document index as chunk_index
                        "metadata": {
                            "document_id": doc.id,
                            "knowledge_base_id": knowledge_base_id,
                            "content_type": doc.content_type
                        }
                    })
            
            # Generate SQL from the natural language query
            sql_query = await self._generate_sql(query, table_schemas)
            
            if not sql_query:
                return {
                    "query": query,
                    "answer": "I couldn't generate a SQL query for your question.",
                    "sql": None,
                    "results": [],
                    "sources": sources,
                    "service": "tag"
                }
            
            # Execute the SQL query
            results = await self._execute_sql(sql_query)
            
            # Generate a natural language answer
            answer = await self._generate_answer(query, sql_query, results)
            
            return {
                "query": query,
                "answer": answer,
                "sql": sql_query,
                "results": results,
                "sources": sources,
                "service": "tag"
            }
            
        except Exception as e:
            logger.error(f"Error in TagService.retrieve: {e}", exc_info=True)
            return {
                "query": query,
                "answer": f"An error occurred while processing your query: {str(e)}",
                "sql": None,
                "results": [],
                "sources": [],
                "service": "tag",
                "error": str(e)
            }
    
    async def _get_all_table_schemas(self) -> Dict[str, Any]:
        """
        Get schemas for all tables in the storage database using direct SQL queries.
        
        Returns:
            Dictionary containing table schemas
        """
        try:
            schemas = {}
            
            # Use StorageRepository to execute SQL queries
            # First get all tables using SHOW TABLES
            logger.info("Fetching all tables from storage database")
            try:
                db = get_storage_db().__next__()
                tables_result = await StorageRepository.query(db, "SHOW TABLES")
                table_names = [row[0] for row in tables_result] if tables_result else []
            except Exception as e:
                logger.error(f"All table query methods failed: {e}")
                table_names = []
            
            logger.info(f"Found tables: {table_names}")
            
            # For each table, get its schema information
            for table_name in table_names:
                # Skip system tables
                if (table_name.startswith('sqlite_') or table_name.startswith('pg_') or 
                    table_name.startswith('alembic_') or table_name == 'spatial_ref_sys'):
                    continue
                
                # Get column information
                try:
                    # Try DESCRIBE command (MySQL/MariaDB)
                    describe_query = f"DESCRIBE {table_name}"
                    db = get_storage_db().__next__()
                    describe_result = await StorageRepository.query(db, describe_query)
                    
                    columns = []
                    for row in describe_result:
                        # DESCRIBE typically returns: Field, Type, Null, Key, Default, Extra
                        col_name = row[0]
                        col_type = row[1]
                        is_nullable = row[2].upper() == 'YES' if len(row) > 2 else True
                        key_type = row[3] if len(row) > 3 else ''
                        
                        columns.append({
                            "name": col_name,
                            "type": col_type,
                            "nullable": is_nullable,
                            "key": key_type
                        })
                    
                except Exception as e:
                    logger.error(f"All schema query methods failed for {table_name}: {e}")
                    # Add a minimal entry
                    columns = []
                
                # Get sample data (first few rows) to help LLM understand the data
                try:
                    sample_query = f"SELECT * FROM {table_name} LIMIT 3"
                    db = get_storage_db().__next__()
                    sample_result = await StorageRepository.query(db, sample_query)
                    
                    # Convert sample data to list of dicts
                    sample_data = []
                    if sample_result and len(sample_result) > 0:
                        if hasattr(sample_result[0], '_fields'):
                            fields = sample_result[0]._fields
                            for row in sample_result:
                                sample_data.append({field: getattr(row, field) for field in fields})
                        else:
                            # Fallback
                            sample_data = [dict(zip([c["name"] for c in columns], row)) for row in sample_result]
                except Exception as e:
                    logger.warning(f"Failed to get sample data for {table_name}: {e}")
                    sample_data = []
                
                # Store schema information
                schemas[table_name] = {
                    "columns": columns,
                    "sample_data": sample_data
                }
            
            if not schemas:
                logger.warning("No table schemas found in the storage database")
            
            return schemas
            
        except Exception as e:
            logger.error(f"Error getting table schemas: {e}", exc_info=True)
            return {}
    
    async def _get_knowledge_base_documents(self, knowledge_base_id: str) -> List[Any]:
        """
        Get all documents from a knowledge base.
        
        Args:
            knowledge_base_id: The ID of the knowledge base
            
        Returns:
            List of documents
        """
        try:
            
            db = get_db().__next__()
            documents = db.query(Document).filter(
                Document.knowledge_base_id == knowledge_base_id
            ).all()
            
            return documents
            
        except Exception as e:
            logger.error(f"Error getting knowledge base documents: {e}", exc_info=True)
            return []
    
    async def _generate_sql(self, query: str, table_schemas: Dict[str, Any]) -> str:
        """
        Generate SQL from a natural language query using an LLM.
        
        Args:
            query: The natural language query
            table_schemas: Dictionary of table schemas
            
        Returns:
            Generated SQL query as a string
        """
        try:
            # Format the schema information for the prompt
            schema_text = ""
            for table_name, schema in table_schemas.items():
                schema_text += f"Table: {table_name}\n"
                schema_text += "Columns:\n"
                
                for column in schema["columns"]:
                    key_info = ""
                    if column.get("key") == "PRI":
                        key_info = " (PRIMARY KEY)"
                    nullable = "NULL" if column.get("nullable", True) else "NOT NULL"
                    schema_text += f"  - {column['name']} ({column['type']}) {nullable}{key_info}\n"
                
                # Include sample data if available
                if schema.get("sample_data") and len(schema["sample_data"]) > 0:
                    schema_text += "\nSample data (first 3 rows):\n"
                    for i, row in enumerate(schema["sample_data"][:3]):
                        schema_text += f"Row {i+1}: {json.dumps(row)}\n"
                
                schema_text += "\n"
            
            # Get the prompt from the registry
            prompt = get_prompt("tag_service", "generate_sql", 
                                query=query, 
                                schema_text=schema_text)
            
            # Create a message for the LLM
            messages = [
                Message(role=Role.USER, content=prompt)
            ]
            
            # Set completion options
            options = CompletionOptions(
                temperature=0.2,  # Lower temperature for more deterministic SQL generation
                max_tokens=1000
            )
            
            # Generate SQL using LLM Factory
            response = await LLMFactory.complete(
                messages=messages,
                options=options
            )
            
            # Extract SQL from response
            sql_query = response.content.strip()
            
            # Remove any markdown code block formatting if present
            sql_query = re.sub(r'```sql\s*', '', sql_query)
            sql_query = re.sub(r'```', '', sql_query)
            
            # Log the generated SQL
            logger.info(f"Generated SQL query: {sql_query}")
            
            return sql_query
        
        except Exception as e:
            logger.error(f"Error generating SQL: {e}", exc_info=True)
            return ""
    
    async def _execute_sql(self, sql_query: str) -> List[Dict[str, Any]]:
        """
        Execute the SQL query against the database using the storage repository.
        
        Args:
            sql_query: The SQL query to execute
            
        Returns:
            List of results as dictionaries
        """
        try:
            # Security validation - only allow SELECT statements
            if not sql_query.strip().upper().startswith("SELECT"):
                logger.error(f"Attempted to execute non-SELECT query: {sql_query}")
                return []
            
            logger.info(f"Executing SQL query via Storage Repository: {sql_query}")
            
            # Execute the query using the storage repository
            # Use the instance method through self.storage_repository
            db = get_storage_db().__next__()
            result_proxy = await StorageRepository.query(db, sql_query)
            results = []
            
            # Convert result to list of dictionaries
            if result_proxy:
                # Get column names from the first result
                if hasattr(result_proxy[0], '_fields'):
                    columns = result_proxy[0]._fields
                elif hasattr(result_proxy[0], '_mapping'):
                    # For SQLAlchemy 2.0+ compatibility
                    columns = [col for col in result_proxy[0]._mapping.keys()]
                else:
                    # Try to infer column names from the result
                    logger.warning("Could not determine column names from result, using position")
                    columns = [f"column_{i}" for i in range(len(result_proxy[0]))]
                
                # Convert each row to a dictionary
                for row in result_proxy:
                    # For named tuples
                    if hasattr(row, '_asdict'):
                        row_dict = row._asdict()
                    # For SQLAlchemy 2.0+ Row objects
                    elif hasattr(row, '_mapping'):
                        row_dict = dict(row._mapping)
                    # Fallback
                    else:
                        # Try to convert by position
                        if isinstance(row, (list, tuple)):
                            row_dict = dict(zip(columns, row))
                        else:
                            # Last resort
                            row_dict = {f"value_{i}": val for i, val in enumerate(row)}
                    
                    # Handle special data types
                    for key, value in list(row_dict.items()):
                        # Convert date/time objects to ISO strings
                        if hasattr(value, 'isoformat'):
                            row_dict[key] = value.isoformat()
                        # Handle None values
                        elif value is None:
                            row_dict[key] = None
                        # Convert non-JSON serializable types to strings
                        elif not isinstance(value, (str, int, float, bool, type(None), list, dict)):
                            row_dict[key] = str(value)
                    
                    results.append(row_dict)
            
            logger.info(f"Query returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error executing SQL: {e}", exc_info=True)
            return []
    
    async def _generate_answer(self, query: str, sql: str, results: List[Dict[str, Any]]) -> str:
        """
        Generate a natural language answer based on query, SQL, and results.
        
        Args:
            query: The original natural language query
            sql: The SQL query that was executed
            results: The results from the SQL query
            
        Returns:
            Natural language answer as a string
        """
        try:
            # Format results for the prompt
            results_text = json.dumps(results[:10], indent=2)  # Limit to 10 rows for prompt size
            
            # Get the prompt from the registry
            prompt = get_prompt("tag_service", "generate_answer",
                                query=query,
                                sql=sql,
                                results=results_text)
            
            # Create a message for the LLM
            messages = [
                Message(role=Role.USER, content=prompt)
            ]
            
            # Set completion options
            options = CompletionOptions(
                temperature=0.5,  # Moderate temperature for natural language generation
                max_tokens=1000
            )
            
            # Generate answer using LLM Factory
            response = await LLMFactory.complete(
                messages=messages,
                options=options
            )
            
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}", exc_info=True)
            return f"I found results, but couldn't generate a natural language answer due to an error: {str(e)}"


@lru_cache()
def get_tag_service() -> TagService:
    """Get a singleton instance of TagService"""
    return TagService() 