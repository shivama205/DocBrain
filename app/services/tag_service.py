from typing import Dict, Any, List, Optional
import logging
import json
from app.core.config import settings
from app.db.database import get_db
from functools import lru_cache
import google.generativeai as genai
import re
from app.db.models.knowledge_base import DocumentType
from app.db.storage import get_storage_db
from app.repositories.storage_repository import StorageRepository
from app.db.models.knowledge_base import Document


logger = logging.getLogger(__name__)

class TagService:
    """
    Text-to-SQL service for handling structured data formats like CSV, Excel, etc.
    This service converts natural language queries to SQL and executes them against
    structured data stored in a database.
    """
    
    def __init__(self):
        """Initialize the Tag Service"""
        logger.info("Initializing TagService")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
    
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
            table_schemas: Dictionary containing table schemas with sample data
            
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
            
            # Construct a prompt for the LLM
            prompt = f"""
            You are a SQL expert. Given the following database schema with sample data:
            
            {schema_text}
            
            Generate a SQL query for the following natural language question:
            "{query}"
            
            Rules:
            1. Only use tables and columns that exist in the schema
            2. For safety, do not use any SQL commands that modify data (INSERT, UPDATE, DELETE, etc.)
            3. Return only the SQL query inside a markdown code block with sql syntax highlighting
            4. Use proper SQL syntax for JOINs when querying across multiple tables
            5. Use appropriate WHERE clauses to filter data according to the question
            6. If the question involves aggregation, use GROUP BY clauses
            7. Base your column selection on the information needed to answer the question
            8. Examine the sample data to understand the structure and content of the database
            9. Do not include explanations before or after the SQL code block
            """
            
            # Call the LLM to generate SQL
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extract SQL from markdown code blocks if present
            # Try to extract SQL from code blocks
            sql_pattern = r"```sql\s*([\s\S]*?)\s*```"
            matches = re.search(sql_pattern, response_text, re.IGNORECASE)
            
            if matches:
                # Extract just the SQL from within the code block
                sql_query = matches.group(1).strip()
                logger.info(f"Extracted SQL from code block: {sql_query}")
            else:
                # If no code block, check if it's just SQL without code blocks
                # Look for SELECT statement
                select_pattern = r"SELECT\s+[\s\S]*"
                select_matches = re.search(select_pattern, response_text, re.IGNORECASE)
                
                if select_matches:
                    sql_query = select_matches.group(0).strip()
                    logger.info(f"Extracted SQL without code block: {sql_query}")
                else:
                    # No SQL found, return empty string to trigger fallback
                    logger.warning(f"No SQL found in response: {response_text}")
                    return ""
            
            # Basic safety check - only allow SELECT statements
            if not sql_query.strip().upper().startswith("SELECT"):
                logger.warning(f"Generated query doesn't start with SELECT: {sql_query}")
                return "SELECT 1 WHERE false; -- Invalid query detected"
            
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
        Generate a natural language answer from SQL results using an LLM.
        
        Args:
            query: The original natural language query
            sql: The SQL query executed
            results: The results from the SQL query
            
        Returns:
            Natural language answer
        """
        try:
            # Format the results as JSON for the prompt
            results_json = json.dumps(results[:10], indent=2)  # Limit to first 10 results
            
            # Construct a prompt for the LLM
            prompt = f"""
            Given the following:
            
            Original question: "{query}"
            
            SQL query used:
            ```sql
            {sql}
            ```
            
            Query results:
            ```json
            {results_json}
            ```
            
            Generate a clear, concise natural language answer to the original question based on these results.
            Include key numbers and insights, but keep your answer direct and to the point.
            If there are no results, explain that no data was found that matches the query.
            If there are many results, summarize them appropriately.
            DO NOT mention the SQL query itself in your answer.
            """
            
            # Call the LLM to generate the answer
            response = self.model.generate_content(prompt)
            answer = response.text.strip()
            
            return answer
                
        except Exception as e:
            logger.error(f"Error generating answer: {e}", exc_info=True)
            
            # Fallback to a basic answer
            if len(results) == 0:
                return "No results found for your query."
            elif len(results) == 1:
                return f"I found one record matching your query: {json.dumps(results[0], indent=2)}"
            else:
                return f"I found {len(results)} records matching your query."

@lru_cache()
def get_tag_service() -> TagService:
    """
    Get a singleton instance of the TagService.
    
    Returns:
        TagService instance
    """
    return TagService() 