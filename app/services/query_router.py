from typing import List, Dict, Any, Set, Optional
from app.services.rag.vector_store import get_vector_store
from app.core.config import settings
from app.db.models.knowledge_base import DocumentType
from app.services.rag_service import get_rag_service
from app.services.tag_service import get_tag_service
import logging
from functools import lru_cache
import json

# Replace direct Gemini import with our LLM factory
from app.services.llm.factory import LLMFactory, Message, Role, CompletionOptions
from app.core.prompts import get_prompt, register_prompt
from app.db.models.question import AnswerType

logger = logging.getLogger(__name__)

# Register query router prompts
register_prompt("query_router", "analyze_query", """
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
""")

# Document types categorization
UNSTRUCTURED_DOCUMENT_TYPES = {
    DocumentType.PDF,
    DocumentType.TXT,
    DocumentType.MARKDOWN,
    DocumentType.HTML
}

STRUCTURED_DOCUMENT_TYPES = {
    DocumentType.CSV,
    DocumentType.EXCEL,
    DocumentType.DOC,
    DocumentType.DOCX
}

class QueryRouter:
    """
    QueryRouter handles both routing and dispatching of queries.
    It analyzes document types to decide which service to use,
    then dispatches the query to the appropriate service.
    """
    
    def __init__(self):
        """Initialize the query router with service instances"""
        # Get singleton instances of services
        self.rag_service = get_rag_service()
        self.tag_service = get_tag_service()
        logger.info("Initialized QueryRouter")
    
    async def route_and_dispatch(
        self,
        query: str,
        metadata_filter: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.3,
        force_service: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Route a query to the appropriate service and dispatch it.
        
        Args:
            query: The query to route and dispatch
            metadata_filter: Optional filter for the query
            top_k: Number of results to retrieve (for RAG service)
            similarity_threshold: Similarity threshold (for RAG service)
            force_service: Optional service to force routing to
            
        Returns:
            Response from the service that processed the query
        """
        try:
            logger.info(f"Routing and dispatching query: '{query}'")
            
            # First, check if we have a direct answer in the questions index
            kb_id = metadata_filter.get("knowledge_base_id") if metadata_filter else None
            
            # Only search questions if we're not forcing a specific service
            if not force_service:
                direct_answer = await self._check_questions_index(query, kb_id)
                if direct_answer:
                    logger.info("Found direct answer in questions index")
                    return direct_answer
            
            # Continue with the regular routing flow if no direct answer was found
            # Use the specified service if provided
            if force_service:
                service = force_service.lower()
                if service not in ["rag", "tag"]:
                    logger.warning(f"Invalid force_service value: {force_service}. Defaulting to RAG.")
                    service = "rag"
                    
                # Create a routing info dict
                routing_info = {
                    "service": service,
                    "confidence": 1.0,  # High confidence since it's explicitly forced
                    "reasoning": f"Service was explicitly forced to {service}",
                    "fallback": False
                }
            else:
                # Get routing decision from LLM-based analysis
                routing_info = await self.analyze_query(query)
                service = routing_info.get("service", "rag")
            
            # Log which service was selected
            logger.info(f"Selected service: {service}")
            
            # Dispatch to the appropriate service
            if service == "tag":
                logger.info(f"Dispatching to TAG service: '{query}'")
                # TAG service no longer requires top_k and similarity_threshold
                response = await self.tag_service.retrieve(
                    knowledge_base_id=metadata_filter.get("knowledge_base_id") if metadata_filter else None,
                    query=query,
                    metadata_filter=metadata_filter
                )
                response["service"] = "tag"
            else:  # Default to RAG
                logger.info(f"Dispatching to RAG service: '{query}'")
                response = await self.rag_service.retrieve(
                    knowledge_base_id=metadata_filter.get("knowledge_base_id") if metadata_filter else None,
                    query=query,
                    top_k=top_k,
                    similarity_threshold=similarity_threshold,
                    metadata_filter=metadata_filter
                )
                response["service"] = "rag"
            
            # Add routing information to the response
            response["routing_info"] = routing_info
            
            return response
            
        except Exception as e:
            logger.error(f"Error in route_and_dispatch: {e}", exc_info=True)
            # Return a basic error response
            return {
                "query": query,
                "answer": f"An error occurred while processing your query: {str(e)}",
                "sources": [],
                "service": "unknown",
                "routing_info": {
                    "service": "unknown",
                    "confidence": 0,
                    "reasoning": f"Error: {str(e)}",
                    "fallback": True
                },
                "error": str(e)
            }
    
    async def _check_questions_index(self, query: str, knowledge_base_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Check if there's a direct answer in the questions index.
        
        Args:
            query: The user query
            knowledge_base_id: Optional ID of the knowledge base to search in
            
        Returns:
            Response with the direct answer found in questions index, None otherwise
        """
        try:
            logger.info(f"=== QUESTIONS INDEX CHECK ===")
            logger.info(f"Checking questions index for direct answer to: '{query}'")
            
            # Higher threshold for questions to ensure high quality matches
            QUESTIONS_SIMILARITY_THRESHOLD = 0.75
            logger.info(f"Using similarity threshold: {QUESTIONS_SIMILARITY_THRESHOLD}")
            
            if not knowledge_base_id:
                logger.info("No knowledge base ID provided, cannot search questions index")
                return None
                
            # Get the questions vector store
            logger.info(f"Getting vector store for questions index: {settings.PINECONE_QUESTIONS_INDEX_NAME}")
            questions_vector_store = get_vector_store(
                store_type="pinecone", 
                index_name=settings.PINECONE_QUESTIONS_INDEX_NAME
            )
            
            # Log the search parameters
            logger.info(f"Searching questions with: query='{query}', knowledge_base_id='{knowledge_base_id}', threshold={QUESTIONS_SIMILARITY_THRESHOLD}")
            
            # Search for similar questions in the knowledge base namespace
            try:
                results = await questions_vector_store.search_similar(
                    query=query,
                    knowledge_base_id=knowledge_base_id,  # Use knowledge_base_id as namespace
                    limit=1,  # We only need the top result
                    similarity_threshold=QUESTIONS_SIMILARITY_THRESHOLD
                )
            except Exception as e:
                logger.error(f"Error searching questions index: {e}", exc_info=True)
                return None
            
            # If we have a match
            if results and len(results) > 0:
                top_match = results[0]
                match_score = top_match.get('score', 0)
                
                logger.info(f"Found question match with score {match_score} (threshold: {QUESTIONS_SIMILARITY_THRESHOLD})")
                
                # Only use if the match is above our threshold
                if match_score >= QUESTIONS_SIMILARITY_THRESHOLD:
                    content = top_match.get('content', '')
                    metadata = top_match.get('metadata', {})
                    logger.info(f"Match content: {content[:100]}...")
                    
                    # Get question and answer from metadata if available
                    matched_question = metadata.get('question', '')
                    matched_answer = metadata.get('answer', '')
                    
                    # If not in metadata, try to parse from content as fallback
                    if not matched_question or not matched_answer:
                        logger.info("Question/answer not found in metadata, trying to parse from content")
                        parts = content.split('\nAnswer: ')
                        if len(parts) == 2:
                            matched_question = parts[0].replace('Question: ', '')
                            matched_answer = parts[1]
                        else:
                            logger.warning(f"Could not parse question/answer from content: {content}")
                            return None
                    
                    logger.info(f"Matched question: {matched_question}")
                    logger.info(f"Matched answer preview: {matched_answer[:100]}...")
                    
                    # Use LLM to generate the final answer based on the matched question and answer
                    logger.info("Generating answer with LLM using matched question and answer")
                    
                    # Create prompt for the LLM
                    prompt = f"""You are answering a user question based on an existing similar question and answer pair.

User Question: {query}

Similar Question: {matched_question}

Answer to Similar Question: {matched_answer}

Please provide an accurate, helpful answer to the user's question based on this information.
If the user's question is substantially different, just use the provided answer as context to help frame your response.
"""
                    
                    # Create message for LLM
                    messages = [
                        Message(role=Role.USER, content=prompt)
                    ]
                    
                    # Set completion options
                    options = CompletionOptions(
                        temperature=0.3,  # Lower temperature for more accurate response
                        max_tokens=500
                    )
                    
                    # Get LLM response
                    llm_response = await LLMFactory.complete(
                        messages=messages,
                        options=options
                    )
                    
                    final_answer = llm_response.content.strip()
                    logger.info(f"LLM generated answer: {final_answer[:100]}...")
                    
                    # Prepare response in the same format as other services
                    response = {
                        "query": query,
                        "answer": final_answer,
                        "sources": [{
                            # Content is the matched question for display
                            "content": matched_question,
                            # Add question-specific metadata using the updated schema
                            "question_id": metadata.get('question_id', ''),
                            "question": matched_question,
                            "answer": matched_answer,  # Include the original answer
                            "answer_type": metadata.get('answer_type', 'DIRECT'),
                            "score": match_score,
                            # We no longer need these document-specific fields
                            # but include dummy values for backward compatibility if needed
                            "metadata": {
                                "question_id": metadata.get('question_id', ''),
                                "knowledge_base_id": knowledge_base_id,
                                "score": match_score,
                                "answer": matched_answer  # Include answer in metadata too
                            }
                        }],
                        "service": "questions",
                        "routing_info": {
                            "service": "questions",
                            "confidence": match_score,
                            "reasoning": f"Found direct answer in questions index with confidence {match_score:.2f}",
                            "fallback": False
                        }
                    }
                    logger.info("Returning LLM-generated answer from questions index match")
                    logger.info(f"=== END QUESTIONS INDEX CHECK ===")
                    return response
                else:
                    logger.info(f"Match score {match_score} below threshold {QUESTIONS_SIMILARITY_THRESHOLD}, not using")
            else:
                logger.info("No matches found in questions index")
            
            logger.info("No suitable direct answer found in questions index")
            logger.info(f"=== END QUESTIONS INDEX CHECK ===")
            return None
            
        except Exception as e:
            logger.error(f"Error checking questions index: {e}", exc_info=True)
            logger.info(f"=== END QUESTIONS INDEX CHECK (ERROR) ===")
            return None
    
    async def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze a query to determine which service to route it to.
        Uses LLM to analyze query semantics and determine if it requires
        structured data analysis (TAG) or unstructured text search (RAG).
        
        Args:
            query: The query to analyze
            
        Returns:
            Dictionary containing routing information:
                - service: "tag" or "rag"
                - confidence: Confidence score (0-1)
                - reasoning: Explanation of the routing decision
                - fallback: Whether this is a fallback decision
        """
        try:
            logger.info(f"Analyzing query for routing: '{query}'")
            
            # Get the prompt from the registry
            prompt = get_prompt("query_router", "analyze_query", query=query)
            
            # Create a message for the LLM
            messages = [
                Message(role=Role.USER, content=prompt)
            ]
            
            # Set completion options
            options = CompletionOptions(
                temperature=0.3,  # Lower temperature for more deterministic results
                max_tokens=500
            )
            
            # Make the LLM call using our factory
            response = await LLMFactory.complete(
                messages=messages,
                options=options
            )
            
            # Parse the response as JSON
            response_text = response.content.strip()
            
            # Try to find JSON content, handling various ways the LLM might format it
            import re
            json_pattern = r"\{[\s\S]*\}"
            json_matches = re.search(json_pattern, response_text)
            
            if json_matches:
                json_str = json_matches.group(0)
                try:
                    routing_info = json.loads(json_str)
                except json.JSONDecodeError:
                    # If direct parsing fails, try to clean up the JSON string
                    # Remove any trailing commas before closing brackets
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)
                    try:
                        routing_info = json.loads(json_str)
                    except json.JSONDecodeError:
                        # If still failing, default to RAG
                        logger.warning(f"Failed to parse LLM response as JSON: {response_text}")
                        return {
                            "service": "rag",
                            "confidence": 0.6,
                            "reasoning": "Failed to parse routing decision, defaulting to RAG",
                            "fallback": True
                        }
            else:
                # If no JSON-like structure was found
                logger.warning(f"No JSON found in LLM response: {response_text}")
                return {
                    "service": "rag",
                    "confidence": 0.6,
                    "reasoning": "Could not extract routing information, defaulting to RAG",
                    "fallback": True
                }
            
            # Validate and normalize the routing info
            service = routing_info.get("service", "").lower()
            if service not in ["tag", "rag"]:
                # Default to RAG for invalid service
                service = "rag"
                routing_info["fallback"] = True
            
            # Ensure confidence is a float between 0 and 1
            confidence = routing_info.get("confidence", 0.5)
            try:
                confidence = float(confidence)
                if confidence < 0 or confidence > 1:
                    confidence = 0.5
            except (ValueError, TypeError):
                confidence = 0.5
            
            # Apply a lower threshold for TAG service to prefer RAG in unclear cases
            TAG_CONFIDENCE_THRESHOLD = 0.7
            if service == "tag" and confidence < TAG_CONFIDENCE_THRESHOLD:
                service = "rag"
                routing_info["reasoning"] = f"Original choice was TAG with confidence {confidence}, but this is below threshold {TAG_CONFIDENCE_THRESHOLD}. Defaulting to RAG."
                routing_info["fallback"] = True
                confidence = 0.6  # Set a moderate confidence for the fallback
            
            # Return the normalized routing info
            return {
                "service": service,
                "confidence": confidence,
                "reasoning": routing_info.get("reasoning", "No reasoning provided"),
                "fallback": routing_info.get("fallback", False)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing query: {e}", exc_info=True)
            # In case of any error, default to RAG service
            return {
                "service": "rag",
                "confidence": 0.5,
                "reasoning": f"Error during analysis: {str(e)}. Defaulting to RAG.",
                "fallback": True
            }
            
        
    async def get_relevant_knowledge_bases(self, query: str, knowledge_base_id: str) -> List[str]:
        """
        Get a list of knowledge base IDs that are relevant to the query.
        
        Args:
            query: The user query
            
        Returns:
            List of knowledge base IDs sorted by relevance
        """
        # Get the summary vector store
        summary_vector_store = get_vector_store(
            store_type="pinecone", 
            index_name=settings.PINECONE_SUMMARY_INDEX_NAME
        )
        
        # Search for relevant document summaries
        results = await summary_vector_store.search_similar(
            query=query,
            knowledge_base_id=knowledge_base_id,
            limit=10,
            similarity_threshold=0.3
        )
        
        # Extract knowledge base IDs from matches
        kb_ids = []
        for match in results:
            if "metadata" in match and "knowledge_base_id" in match["metadata"]:
                kb_id = match["metadata"]["knowledge_base_id"]
                if kb_id and kb_id not in kb_ids:
                    kb_ids.append(kb_id)
        
        logger.info(f"Relevant knowledge bases for query: {kb_ids}")
        return kb_ids

# Create a singleton instance of QueryRouter
@lru_cache()
def get_query_router() -> QueryRouter:
    """Get a singleton instance of QueryRouter"""
    return QueryRouter()
        
