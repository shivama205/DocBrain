from typing import List, Dict, Any, Tuple, Optional, Set
import logging
from pydantic import BaseModel
import google.generativeai as genai
from app.core.config import settings
from app.repositories.vector_repository import VectorRepository
from app.repositories.document_repository import DocumentRepository
from app.core.chunking import ChunkSize, QueryType, DocumentType
import re

logger = logging.getLogger(__name__)

class SubQuestion(BaseModel):
    """Structured format for sub-questions"""
    sub_question: str
    tool_name: str  # Knowledge base ID
    reasoning: str  # Why this sub-question is relevant

class RAGService:
    def __init__(self, vector_repository: VectorRepository):
        self.vector_repository = vector_repository
        # Initialize Gemini
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    async def process_query(self, query: str, knowledge_base_id: str, top_k: int = 5, metadata_filter: Optional[Dict] = None, similarity_threshold: float = 0.3) -> Dict[str, Any]:
        """
        Process a query through the RAG pipeline.
        
        Args:
            query: The query to process
            knowledge_base_id: The ID of the knowledge base to search
            top_k: The number of chunks to retrieve
            metadata_filter: Optional metadata filter to apply to the search
            similarity_threshold: Minimum similarity score for chunks to be included (default: 0.3)
            
        Returns:
            Dictionary containing the answer and sources
        """
        # First, identify relevant documents using LLM
        logger.info(f"Identifying relevant documents for query: '{query}'")
        relevant_doc_ids = await self._identify_relevant_documents(query, knowledge_base_id)
        
        # Create a copy of the metadata filter to avoid modifying the original
        if metadata_filter is None:
            metadata_filter = {}
        else:
            metadata_filter = metadata_filter.copy()
        
        # If we found relevant documents, add them to metadata filter
        llm_filtered = False
        if relevant_doc_ids:
            logger.info(f"Found {len(relevant_doc_ids)} relevant documents via LLM filtering")
            
            # Add document_id filter if we have relevant documents
            if len(relevant_doc_ids) > 0:
                # Use $in operator for multiple document IDs
                metadata_filter["document_id"] = {"$in": list(relevant_doc_ids)}
                logger.info(f"Added document_id filter with {len(relevant_doc_ids)} IDs")
                llm_filtered = True
        else:
            logger.info("No relevant documents identified by LLM, proceeding with standard search")
        
        # Now proceed with the original query using the updated metadata filter
        logger.info(f"Attempting retrieval with original query: '{query}'")
        chunks = await self.vector_repository.search_chunks(
            query=query,
            knowledge_base_id=knowledge_base_id,
            top_k=top_k,
            metadata_filter=metadata_filter,
            similarity_threshold=similarity_threshold
        )
        
        # If no chunks found and we used LLM filtering, try again without document filter
        if not chunks and llm_filtered:
            logger.info("No chunks found with LLM document filtering, trying without filter")
            # Remove the document_id filter
            if "document_id" in metadata_filter:
                del metadata_filter["document_id"]
            
            # Try again without document filter
            chunks = await self.vector_repository.search_chunks(
                query=query,
                knowledge_base_id=knowledge_base_id,
                top_k=top_k,
                metadata_filter=metadata_filter,
                similarity_threshold=similarity_threshold
            )
        
        if chunks:
            logger.info(f"Found {len(chunks)} chunks with original query")
            # Generate answer from chunks
            answer = await self._generate_answer(query, chunks, {
                "query_type": await self._classify_query_type(query),
                "knowledge_base_id": knowledge_base_id
            })
            
            # Transform chunks to match the Source schema
            formatted_sources = []
            for chunk in chunks:
                # Extract document_id from either direct property or metadata
                document_id = chunk.get('document_id', '')
                if not document_id and 'metadata' in chunk:
                    document_id = chunk['metadata'].get('document_id', '') or chunk['metadata'].get('doc_id', '')
                
                # Extract chunk_index from either direct property or metadata
                chunk_index = chunk.get('chunk_index', 0)
                if 'metadata' in chunk and chunk_index == 0:
                    chunk_index = chunk['metadata'].get('chunk_index', 0)
                
                # Extract title from either direct property or metadata
                title = chunk.get('title', '')
                if not title and 'metadata' in chunk:
                    title = chunk['metadata'].get('doc_title', 'Untitled')
                
                formatted_source = {
                    "document_id": document_id,
                    "title": title,
                    "content": chunk.get('content', ''),
                    "chunk_index": chunk_index,
                    "score": chunk.get('score', 0.0)
                }
                formatted_sources.append(formatted_source)
            
            return {
                "answer": answer,
                "sources": formatted_sources
            }
            
        # If no chunks found, try with sub-questions
        logger.info("No chunks found with original query, generating sub-questions")
        sub_questions = await self._generate_sub_questions(query, knowledge_base_id)
        
        if sub_questions:
            all_chunks = []
            sub_k = max(1, top_k // len(sub_questions))
            
            for sq in sub_questions:
                logger.info(f"Searching with sub-question: '{sq.sub_question}'")
                sq_chunks = await self.vector_repository.search_chunks(
                    query=sq.sub_question,
                    knowledge_base_id=knowledge_base_id,
                    top_k=sub_k,
                    metadata_filter=metadata_filter,
                    similarity_threshold=similarity_threshold
                )
                
                if sq_chunks:
                    logger.info(f"Found {len(sq_chunks)} chunks with sub-question")
                    all_chunks.extend(sq_chunks)
                    
            if all_chunks:
                # Remove duplicates based on chunk ID
                unique_chunks = []
                seen_ids = set()
                for chunk in all_chunks:
                    if chunk["id"] not in seen_ids:
                        seen_ids.add(chunk["id"])
                        unique_chunks.append(chunk)
                        
                logger.info(f"Found {len(unique_chunks)} unique chunks with sub-questions")
                # Generate answer from chunks
                answer = await self._generate_answer(query, unique_chunks[:top_k], {
                    "query_type": await self._classify_query_type(query),
                    "knowledge_base_id": knowledge_base_id,
                    "sub_questions": sub_questions
                })
                
                # Transform chunks to match the Source schema
                formatted_sources = []
                for chunk in unique_chunks[:top_k]:
                    # Extract document_id from either direct property or metadata
                    document_id = chunk.get('document_id', '')
                    if not document_id and 'metadata' in chunk:
                        document_id = chunk['metadata'].get('document_id', '') or chunk['metadata'].get('doc_id', '')
                    
                    # Extract chunk_index from either direct property or metadata
                    chunk_index = chunk.get('chunk_index', 0)
                    if 'metadata' in chunk and chunk_index == 0:
                        chunk_index = chunk['metadata'].get('chunk_index', 0)
                    
                    # Extract title from either direct property or metadata
                    title = chunk.get('title', '')
                    if not title and 'metadata' in chunk:
                        title = chunk['metadata'].get('doc_title', 'Untitled')
                    
                    formatted_source = {
                        "document_id": document_id,
                        "title": title,
                        "content": chunk.get('content', ''),
                        "chunk_index": chunk_index,
                        "score": chunk.get('score', 0.0)
                    }
                    formatted_sources.append(formatted_source)
                
                return {
                    "answer": answer,
                    "sources": formatted_sources
                }
                
        # If still no chunks, try with query variations
        logger.info("No chunks found with sub-questions, generating query variations")
        variations = await self._generate_query_variations(query, knowledge_base_id)
        
        if variations:
            all_chunks = []
            var_k = max(1, top_k // len(variations))
            
            for var in variations:
                logger.info(f"Searching with query variation: '{var}'")
                var_chunks = await self.vector_repository.search_chunks(
                    query=var,
                    knowledge_base_id=knowledge_base_id,
                    top_k=var_k,
                    metadata_filter=metadata_filter,
                    similarity_threshold=similarity_threshold
                )
                
                if var_chunks:
                    logger.info(f"Found {len(var_chunks)} chunks with query variation")
                    all_chunks.extend(var_chunks)
                    
            if all_chunks:
                # Remove duplicates based on chunk ID
                unique_chunks = []
                seen_ids = set()
                for chunk in all_chunks:
                    if chunk["id"] not in seen_ids:
                        seen_ids.add(chunk["id"])
                        unique_chunks.append(chunk)
                        
                logger.info(f"Found {len(unique_chunks)} unique chunks with query variations")
                # Generate answer from chunks
                answer = await self._generate_answer(query, unique_chunks[:top_k], {
                    "query_type": await self._classify_query_type(query),
                    "knowledge_base_id": knowledge_base_id,
                    "variations": variations
                })
                
                # Transform chunks to match the Source schema
                formatted_sources = []
                for chunk in unique_chunks[:top_k]:
                    # Extract document_id from either direct property or metadata
                    document_id = chunk.get('document_id', '')
                    if not document_id and 'metadata' in chunk:
                        document_id = chunk['metadata'].get('document_id', '') or chunk['metadata'].get('doc_id', '')
                    
                    # Extract chunk_index from either direct property or metadata
                    chunk_index = chunk.get('chunk_index', 0)
                    if 'metadata' in chunk and chunk_index == 0:
                        chunk_index = chunk['metadata'].get('chunk_index', 0)
                    
                    # Extract title from either direct property or metadata
                    title = chunk.get('title', '')
                    if not title and 'metadata' in chunk:
                        title = chunk['metadata'].get('doc_title', 'Untitled')
                    
                    formatted_source = {
                        "document_id": document_id,
                        "title": title,
                        "content": chunk.get('content', ''),
                        "chunk_index": chunk_index,
                        "score": chunk.get('score', 0.0)
                    }
                    formatted_sources.append(formatted_source)
                
                return {
                    "answer": answer,
                    "sources": formatted_sources
                }
                
        logger.info("No chunks found with any query form")
        return {
            "answer": "I could not find any relevant information to answer your question.",
            "sources": []
        }

    async def _analyze_and_rewrite_query(
        self,
        query: str,
        knowledge_base_id: str
    ) -> Dict[str, Any]:
        """Step 1: Analyze and rewrite the query"""
        try:
            # Classify query type using Gemini
            query_type = await self._classify_query_type(query)
            
            # Generate sub-questions if needed
            sub_questions = []
            if query_type in [QueryType.COMPARISON, QueryType.LIST, QueryType.EXPLANATION]:
                sub_questions = await self._generate_sub_questions(query, knowledge_base_id)
            
            # Generate query variations
            variations = await self._generate_query_variations(query, knowledge_base_id)
            # Combine into enhanced query
            rewritten_query = await self._combine_variations(query, variations)
            # rewritten_query = await self._rewrite_query(query, variations)
            
            return {
                'original_query': query,
                'rewritten_query': rewritten_query,
                'query_type': query_type,
                'sub_questions': sub_questions
            }
        except Exception as e:
            logger.error(f"Query analysis failed: {e}")
            return {
                'original_query': query,
                'rewritten_query': query,
                'query_type': QueryType.UNKNOWN,
                'sub_questions': []
            }

    async def _determine_chunk_size(
        self,
        query_type: QueryType,
        query: str,
    ) -> Tuple[ChunkSize, float]:
        """Enhanced chunk size selection with confidence score"""
        
        # Base weights for different factors
        weights = {
            'query_type': 0.3,
            'query_length': 0.2,
            'complexity': 0.5
        }
        
        # Score each chunk size based on multiple factors
        scores = {size: 0.0 for size in ChunkSize}
        
        # 1. Query Type Factor
        type_preferences = {
            QueryType.FACTOID: {
                ChunkSize.SMALL: 0.8,
                ChunkSize.MEDIUM: 0.4,
                ChunkSize.LARGE: 0.2
            },
            QueryType.EXPLANATION: {
                ChunkSize.SMALL: 0.3,
                ChunkSize.MEDIUM: 0.6,
                ChunkSize.LARGE: 0.9
            },
            QueryType.COMPARISON: {
                ChunkSize.SMALL: 0.4,
                ChunkSize.MEDIUM: 0.9,
                ChunkSize.LARGE: 0.6
            },
            QueryType.LIST: {
                ChunkSize.SMALL: 0.5,
                ChunkSize.MEDIUM: 0.8,
                ChunkSize.LARGE: 0.4
            },
            QueryType.PROCEDURAL: {
                ChunkSize.SMALL: 0.3,
                ChunkSize.MEDIUM: 0.9,
                ChunkSize.LARGE: 0.7
            },
            QueryType.DEFINITION: {
                ChunkSize.SMALL: 0.9,
                ChunkSize.MEDIUM: 0.6,
                ChunkSize.LARGE: 0.3
            },
            QueryType.CAUSE_EFFECT: {
                ChunkSize.SMALL: 0.3,
                ChunkSize.MEDIUM: 0.7,
                ChunkSize.LARGE: 0.9
            },
            QueryType.ANALYSIS: {
                ChunkSize.SMALL: 0.2,
                ChunkSize.MEDIUM: 0.6,
                ChunkSize.LARGE: 1.0
            }
        }
        
        for size in ChunkSize:
            scores[size] += weights['query_type'] * type_preferences.get(
                query_type,
                {size: 0.5}  # Default if query type not found
            ).get(size, 0.5)
        
        # 2. Query Length Factor
        query_words = len(query.split())
        length_factor = min(query_words / 50, 1.0)  # Normalize to 0-1
        for size in ChunkSize:
            if size == ChunkSize.SMALL:
                scores[size] += weights['query_length'] * (1 - length_factor)
            elif size == ChunkSize.LARGE:
                scores[size] += weights['query_length'] * length_factor
            else:
                scores[size] += weights['query_length'] * 0.5
        
        # 4. Query Complexity Factor
        complexity_indicators = [
            'compare', 'analyze', 'explain', 'describe',
            'what are the implications', 'how does',
            'why is', 'what is the relationship'
        ]
        complexity_score = sum(1 for indicator in complexity_indicators if indicator in query.lower())
        complexity_factor = min(complexity_score / 5, 1.0)  # Normalize to 0-1
        
        for size in ChunkSize:
            if size == ChunkSize.LARGE:
                scores[size] += weights['complexity'] * complexity_factor
            elif size == ChunkSize.SMALL:
                scores[size] += weights['complexity'] * (1 - complexity_factor)
            else:
                scores[size] += weights['complexity'] * 0.5
        
        # Select the best chunk size
        best_size = max(scores.items(), key=lambda x: x[1])
        return best_size[0], best_size[1]  # Return both size and confidence score

    async def _filter_chunks_by_metadata(
        self,
        chunks: List[Dict[str, Any]],
        query: str,
        query_type: QueryType = None
    ) -> List[Dict[str, Any]]:
        """Filter chunks based on metadata relevance to the query"""
        if not chunks:
            return []
            
        # If query type is not provided, determine it
        if not query_type:
            query_type = await self._classify_query_type(query)
            
        # Initialize scores for each chunk
        scored_chunks = []
        
        for chunk in chunks:
            metadata = chunk.get('metadata', {})
            score = chunk.get('score', 0.0)  # Base similarity score
            
            # Boost factors based on metadata
            boost = 1.0
            
            # 1. Boost based on chunk size appropriateness for query type
            chunk_size = metadata.get('chunk_size', ChunkSize.MEDIUM)
            if query_type in [QueryType.FACTOID, QueryType.DEFINITION] and chunk_size == ChunkSize.SMALL:
                boost *= 1.2  # Small chunks better for factoid questions
            elif query_type in [QueryType.EXPLANATION, QueryType.ANALYSIS] and chunk_size == ChunkSize.LARGE:
                boost *= 1.2  # Large chunks better for explanations
                
            # 2. Boost based on document type appropriateness
            document_type = metadata.get('document_type', DocumentType.UNSTRUCTURED_TEXT)
            if 'code' in query.lower() and document_type == DocumentType.CODE:
                boost *= 1.3  # Code documents for code-related queries
            elif 'legal' in query.lower() and document_type == DocumentType.LEGAL_DOCS:
                boost *= 1.3  # Legal documents for legal queries
                
            # 3. Boost based on section relevance
            section_path = metadata.get('section_path', [])
            nearest_header = metadata.get('nearest_header', '')
            
            # Check if any keywords from the query appear in section headers
            query_keywords = set(re.findall(r'\b\w+\b', query.lower()))
            header_keywords = set()
            
            if nearest_header:
                header_keywords.update(re.findall(r'\b\w+\b', nearest_header.lower()))
                
            for section in section_path:
                header_keywords.update(re.findall(r'\b\w+\b', section.lower()))
                
            # Calculate overlap between query keywords and header keywords
            overlap = len(query_keywords.intersection(header_keywords))
            if overlap > 0:
                boost *= (1.0 + 0.1 * overlap)
                
            # Apply boost to score
            adjusted_score = score * boost
            
            # Add to scored chunks
            scored_chunks.append({
                **chunk,
                'score': adjusted_score,
                'original_score': score,
                'boost': boost
            })
            
        # Sort by adjusted score
        scored_chunks.sort(key=lambda x: x['score'], reverse=True)
        
        # Log metadata filtering results
        logger.info(f"Applied metadata filtering to {len(chunks)} chunks")
        if scored_chunks:
            logger.info(f"Top chunk boost: {scored_chunks[0]['boost']:.2f}, " 
                       f"Score: {scored_chunks[0]['score']:.4f} (Original: {scored_chunks[0]['original_score']:.4f})")
            
        return scored_chunks

    async def _retrieve_relevant_chunks(
        self,
        rewritten_query: str,
        sub_questions: List[SubQuestion],
        knowledge_base_id: str,
        top_k: int,
        similarity_cutoff: float,
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant chunks using vector similarity search"""
        logger.info("=== Starting Retrieval Process ===")
        logger.info(f"Query: {rewritten_query}")
        logger.info(f"Knowledge Base: {knowledge_base_id}")
        logger.info(f"Top K: {top_k}, Similarity Cutoff: {similarity_cutoff}")
        
        # Get main query chunks
        main_chunks = await self.vector_repository.search_similar(
            rewritten_query,
            knowledge_base_id=knowledge_base_id,
            limit=top_k * 2,  # Get more chunks for filtering
            similarity_threshold=similarity_cutoff
        )
        
        if not main_chunks:
            logger.warning("No chunks found for main query")
            return []
            
        logger.info(f"Retrieved {len(main_chunks)} chunks for main query")
        
        # Process sub-questions if any
        all_chunks = list(main_chunks)
        if sub_questions:
            logger.info("=== Processing Sub-questions ===")
            sub_query_top_k = max(2, top_k // len(sub_questions))
            
            for i, sub_q in enumerate(sub_questions):
                logger.info(f"Processing sub-question {i+1}: {sub_q.sub_question}")
                
                sub_chunks = await self.vector_repository.search_similar(
                    sub_q.sub_question,
                    knowledge_base_id=knowledge_base_id,
                    limit=sub_query_top_k * 2,  # Get more chunks for filtering
                    similarity_threshold=similarity_cutoff
                )
                
                if sub_chunks:
                    logger.info(f"Retrieved {len(sub_chunks)} chunks for sub-question {i+1}")
                    all_chunks.extend(sub_chunks)
        
        # Deduplicate chunks
        seen_chunks = set()
        unique_chunks = []
        for chunk in all_chunks:
            # Handle both possible metadata structures
            try:
                # Direct access for document_id and chunk_index
                doc_id = chunk.get('document_id', '')
                chunk_index = chunk.get('chunk_index', 0)
                
                if not doc_id:
                    # Try nested metadata structure
                    doc_id = chunk.get('metadata', {}).get('document_id', '')
                    chunk_index = chunk.get('metadata', {}).get('chunk_index', 0)
                
                if not doc_id:
                    logger.warning(f"Skipping chunk with missing document_id")
                    continue
                
                chunk_key = f"{doc_id}_{chunk_index}"
                if chunk_key not in seen_chunks:
                    seen_chunks.add(chunk_key)
                    unique_chunks.append(chunk)
            except Exception as e:
                logger.error(f"Error processing chunk metadata: {e}")
                logger.debug(f"Problematic chunk structure: {chunk}")
                continue
        
        # Apply metadata filtering
        query_type = await self._classify_query_type(rewritten_query)
        filtered_chunks = await self._filter_chunks_by_metadata(unique_chunks, rewritten_query, query_type)
        
        # Take top_k after filtering
        result_chunks = filtered_chunks[:top_k] if len(filtered_chunks) > top_k else filtered_chunks
        
        logger.info(f"Final result: {len(result_chunks)} chunks after metadata filtering")
        return result_chunks

    async def _generate_answer(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> str:
        """Generate an answer using retrieved chunks"""
        try:
            logger.info(f"Starting answer generation with {len(chunks)} chunks")
            logger.info(f"Original query: {query}")
            
            if not chunks:
                logger.warning("No chunks provided for answer generation")
                return "I apologize, but I couldn't find any relevant information to answer your question."
            
            # Sort chunks by score and take only the top 5 most relevant ones
            sorted_chunks = sorted(chunks, key=lambda x: x.get('score', 0.0), reverse=True)
            top_chunks = sorted_chunks[:3]  # Limit to top 5 chunks
            
            logger.info(f"Using only the top {len(top_chunks)} most relevant chunks for answer generation")
            if len(chunks) > 3:
                logger.info(f"Filtered out {len(chunks) - 3} less relevant chunks")
            
            # Format chunks into context
            chunk_texts = []
            logger.info("Processing chunks for context building...")
            
            for i, chunk in enumerate(top_chunks, 1):
                try:
                    # Basic validation
                    if not isinstance(chunk, dict) or 'content' not in chunk:
                        logger.warning(f"Invalid chunk format at index {i}")
                        continue
                    
                    # Extract core information
                    content = chunk['content']
                    metadata = chunk.get('metadata', {})
                    title = chunk.get('title', 'Untitled')
                    score = chunk.get('score', 0.0)
                    
                    logger.info(f"Processing chunk {i}/{len(top_chunks)}:")
                    logger.info(f"  - Title: {title}")
                    logger.info(f"  - Score: {score:.3f}")
                    logger.info(f"  - Section: {metadata.get('section', 'No section')}")
                    
                    # Format chunk text with essential information
                    chunk_text = (
                        f"[Source {i}]\n"
                        f"Document: {title}\n"
                        f"Section: {metadata.get('section', 'No section')}\n"
                        f"Content: {content}\n"
                        f"Relevance: {score:.3f}\n"
                    )
                    
                    chunk_texts.append(chunk_text)
                    logger.info(f"Successfully processed chunk {i}")
                    
                except Exception as chunk_error:
                    logger.error(f"Error processing chunk {i}: {str(chunk_error)}")
                    logger.error(f"Problematic chunk: {chunk}")
                    continue
            
            if not chunk_texts:
                logger.warning("No valid chunks after processing")
                return "I apologize, but I couldn't process the relevant information to answer your question."
            
            logger.info(f"Successfully processed {len(chunk_texts)} chunks for context")
            
            # Create focused prompt
            prompt = f"""Based on the following sources, please answer the question.
If you cannot find a relevant answer in the sources, please say so.

Sources:
{'\n\n'.join(chunk_texts)}

Question: {query}

Please provide a clear, direct answer that:
1. Directly addresses the question
2. [Source X] notation is used to cite the sources
3. Only uses information from the provided sources
4. Maintains a professional and helpful tone"""

            logger.info("Generated prompt for answer generation")
            logger.info(f"Prompt length: {len(prompt)} characters")
            
            # Generate response using Gemini
            try:
                logger.info("Sending request to Gemini...")
                response = self.model.generate_content(prompt)
                logger.info("Successfully received response from Gemini")
                logger.info(f"Response length: {len(response.text)} characters")
                return response.text
                
            except Exception as model_error:
                logger.error(f"Error generating answer with Gemini: {str(model_error)}")
                logger.error("Model error details:", exc_info=True)
                raise
            
        except Exception as e:
            logger.error(f"Failed to generate answer: {str(e)}", exc_info=True)
            raise

    async def _classify_query_type(self, query: str) -> QueryType:
        """Enhanced query type classification using Gemini"""
        # First, check for common patterns
        query_lower = query.lower()
        
        # Pattern matching for quick classification
        patterns = {
            QueryType.DEFINITION: [
                r"what (is|are|does) .+ mean",
                r"define .+",
                r"what (is|are) .+\?",
            ],
            QueryType.PROCEDURAL: [
                r"how (do|can|should|would) (i|you|we)",
                r"steps? to",
                r"procedure for",
                r"guide to",
            ],
            QueryType.COMPARISON: [
                r"difference between",
                r"compare .+ (to|with|and)",
                r"which is (better|worse|more|less)",
            ],
            QueryType.LIST: [
                r"list .+",
                r"what are the .+",
                r"examples of",
                r"types of",
            ],
            QueryType.CAUSE_EFFECT: [
                r"what causes",
                r"effect[s]? of",
                r"why does",
                r"impact of",
            ]
        }
        
        # Check patterns first for efficiency
        for qtype, pattern_list in patterns.items():
            if any(re.search(pattern, query_lower) for pattern in pattern_list):
                return qtype
        
        # If no pattern match, use more sophisticated LLM classification
        prompt = f"""Analyze this question and classify it into one of these types:

FACTOID: Simple fact-based questions (who, what, when, where) that require specific, concise answers
COMPARISON: Questions comparing two or more things, requiring analysis of similarities/differences
EXPLANATION: How and why questions requiring detailed explanations
LIST: Questions asking for enumerations or multiple items
PROCEDURAL: Questions asking for step-by-step instructions or processes
DEFINITION: Questions asking for the meaning or definition of something
CAUSE_EFFECT: Questions about causes, effects, or relationships between events/concepts
ANALYSIS: Questions requiring in-depth analysis or comprehensive understanding
UNKNOWN: If none of the above fit

Question: "{query}"

Consider:
1. The question's structure and keywords
2. The expected answer format
3. The depth of analysis required
4. Whether it requires single or multiple pieces of information

Return only the classification type in uppercase."""

        response = self.model.generate_content(prompt)
        try:
            return QueryType(response.text.strip().lower())
        except ValueError:
            return QueryType.UNKNOWN

    async def _get_document_summaries(self, knowledge_base_id: str, max_samples: int = 5) -> List[Dict]:
        """
        Get document summaries from the knowledge base to provide context
        for query variations and sub-questions.
        
        Args:
            knowledge_base_id: The ID of the knowledge base to sample from
            max_samples: Maximum number of documents to retrieve (default: 5, 
                         but can be increased for document filtering)
            
        Returns:
            List of document summaries with metadata
        """
        try:
            # Create document repository instance
            doc_repo = DocumentRepository()
            
            # Get documents with summaries from the knowledge base
            documents = await doc_repo.get_by_knowledge_base(
                knowledge_base_id=knowledge_base_id,
                limit=max_samples,
                status="COMPLETED"  # Only get successfully processed documents
            )
            
            if not documents:
                logger.warning(f"No documents found in knowledge base {knowledge_base_id} for context sampling")
                return []
                
            # Format documents with summaries
            doc_summaries = []
            for doc in documents:
                if doc.summary:
                    doc_summary = {
                        "id": doc.id,
                        "document_id": doc.id,  # Add document_id directly to the top level
                        "title": doc.title,
                        "content": doc.summary,  # Use the summary as content
                        "chunk_index": 0,  # Add chunk_index for compatibility
                        "score": 1.0,  # Add a default score for compatibility
                        "metadata": {
                            "doc_title": doc.title,
                            "doc_id": doc.id,
                            "document_id": doc.id,  # Ensure document_id is in metadata too
                            "knowledge_base_id": knowledge_base_id
                        }
                    }
                    doc_summaries.append(doc_summary)
            
            logger.info(f"Retrieved {len(doc_summaries)} document summaries from knowledge base {knowledge_base_id}")
            return doc_summaries
            
        except Exception as e:
            logger.error(f"Error retrieving knowledge base document summaries: {e}")
            return []

    async def _generate_query_variations(self, query: str, knowledge_base_id: str) -> List[str]:
        """Generate variations of the query using Gemini with document summaries"""
        # Get document summaries from the knowledge base
        context_text = ""
        try:
            # Get document summaries from the knowledge base
            doc_summaries = await self._get_document_summaries(knowledge_base_id, max_samples=5)
            if doc_summaries:
                # Format the context information
                context_items = []
                for i, doc in enumerate(doc_summaries, 1):
                    title = doc.get('title', 'Untitled')
                    summary = doc.get('content', '')[:500] + "..." if len(doc.get('content', '')) > 500 else doc.get('content', '')
                    context_items.append(f"Document {i}: {title}\nSummary: {summary}")
                
                context_text = "\n\nKnowledge Base Context:\n" + "\n\n".join(context_items)
                logger.info(f"Added context from {len(doc_summaries)} document summaries for query variation generation")
        except Exception as e:
            logger.warning(f"Failed to get knowledge base context for query variations: {e}")
            # Continue without context if there's an error
        
        prompt = f"""Generate 3-5 alternative phrasings of the following query while maintaining its meaning.

Original Query: {query}{context_text}

Based on the knowledge base context (if provided), create variations that:
1. Use terminology and concepts that match the document content
2. Focus on aspects likely covered in the knowledge base
3. Restructure the sentence pattern while preserving the core question
4. Vary in specificity (some more general, some more specific)
5. Include domain-specific terms from the documents when relevant

Format your response as a numbered list of variations only, with no additional text.
Example:
1. [first variation]
2. [second variation]
3. [third variation]"""

        try:
            response = self.model.generate_content(prompt)
            variations = []
            
            # Parse the response to extract variations
            for line in response.text.strip().split('\n'):
                # Check if line starts with a number followed by a period
                if line and line[0].isdigit() and '. ' in line:
                    variation = line.split('. ', 1)[1].strip()
                    if variation:
                        variations.append(variation)
            
            logger.info(f"Generated {len(variations)} query variations:")
            for i, var in enumerate(variations):
                logger.info(f"  Variation {i+1}: {var}")
                
            return variations
        except Exception as e:
            logger.error(f"Error generating query variations: {e}")
            return []

    async def _generate_sub_questions(self, query: str, knowledge_base_id: str) -> List[SubQuestion]:
        """Generate sub-questions using Gemini with document summaries"""
        # Get document summaries from the knowledge base
        context_text = ""
        try:
            # Get document summaries from the knowledge base
            doc_summaries = await self._get_document_summaries(knowledge_base_id, max_samples=5)
            if doc_summaries:
                # Format the context information
                context_items = []
                for i, doc in enumerate(doc_summaries, 1):
                    title = doc.get('title', 'Untitled')
                    summary = doc.get('content', '')[:500] + "..." if len(doc.get('content', '')) > 500 else doc.get('content', '')
                    context_items.append(f"Document {i}: {title}\nSummary: {summary}")
                
                context_text = "\n\nKnowledge Base Context:\n" + "\n\n".join(context_items)
                logger.info(f"Added context from {len(doc_summaries)} document summaries for sub-question generation")
        except Exception as e:
            logger.warning(f"Failed to get knowledge base context for sub-questions: {e}")
            # Continue without context if there's an error
        
        prompt = f"""Break down this query into 2-3 specific sub-questions that would help retrieve relevant information from the knowledge base.

Main Query: {query}{context_text}

Based on the knowledge base context (if provided), create sub-questions that:
1. Focus on different aspects or components of the main query
2. Use terminology and concepts that match the document content
3. Target specific information likely to be in the knowledge base
4. Make them more specific and targeted than the original query
5. Ensure they're self-contained (can be answered independently)

Format each sub-question as:
QUESTION: [specific sub-question]
REASONING: [why this helps answer the main query]
---"""

        response = self.model.generate_content(prompt)
        sub_questions = []
        
        parts = response.text.split('---')
        for part in parts:
            if not part.strip():
                continue
                
            lines = part.strip().split('\n')
            question = ""
            reasoning = ""
            
            for line in lines:
                if line.startswith('QUESTION:'):
                    question = line.replace('QUESTION:', '').strip()
                elif line.startswith('REASONING:'):
                    reasoning = line.replace('REASONING:', '').strip()
            
            if question and reasoning:
                sub_questions.append(SubQuestion(
                    sub_question=question,
                    tool_name=knowledge_base_id,
                    reasoning=reasoning
                ))
        
        # Log the sub-questions
        logger.info(f"Generated {len(sub_questions)} sub-questions:")
        for i, sq in enumerate(sub_questions):
            logger.info(f"  Sub-question {i+1}: {sq.sub_question}")
            logger.info(f"    Reasoning: {sq.reasoning}")
            
        return sub_questions

    async def _rewrite_query(self, query: str, variations: List[str]) -> str:
        """Rewrite query using Gemini"""
        prompt = f"""
        You are a helpful assistant that rewrites queries to be more specific and to extract any implicit information for a RAG pipeline.
        You will be given a query and variations of that query. 
        Help to rewrite the query based on original query and variations.
        Do not assume any information, only use the information provided in the query and variations.
        If you do not have enough information to rewrite the query, just return the original query.
        If the query is already specific, just return it.

        Consider that this query will be used to search relevant information from a knowledge base of documents.
        Its part of a RAG pipeline that will use the rewritten query to find the most relevant chunks.  

        Query: {query}
        Variations: {variations}

        Rewrite:"""
        response = self.model.generate_content(prompt)
        return response.text.strip()

    async def _combine_variations(self, original_query: str, variations: List[str]) -> str:
        """Intelligently expand query with implicit context based on query type"""

        # Create prompt based on query type to expand with implicit details
        expansion_prompt = f"""
        You are a helpful assistant that expands queries to be more specific and to extract any implicit information for a RAG pipeline.
        Given a query, expand it by adding implicit details and context that would help find relevant information.
        Provide an expanded version that includes these implicit details. Keep it focused and relevant.
        If original query is already good, just return it.
        Do not assume any information, only use the information provided in the query and variations. 
        Consider that there might be context that has not been provided in the query, let that context be part of the expanded query. 
        Do not add context that is not provided in the query.

            Original query: {original_query}
            Variations: {variations}

            Format: Return only the expanded query, no explanations."""

        try:
            # Get expanded query from Gemini
            response = self.model.generate_content(expansion_prompt)
            expanded_query = response.text.strip()
            
            # Validate the expansion
            validation_prompt = f"""Rate how relevant and focused this query expansion is (0-100):

Original: {original_query}
Expanded: {expanded_query}

Consider:
1. Does it maintain the original intent?
2. Are the added details relevant?
3. Is it too broad or off-topic?

Return only the score (0-100)."""
            
            validation = self.model.generate_content(validation_prompt)
            try:
                score = int(validation.text.strip())
                
                if score >= 80:  # Only use expansion if it's highly relevant
                    logger.debug(f"Using expanded query (score {score}): {expanded_query}")
                    return expanded_query
                else:
                    logger.debug(f"Expansion score too low ({score}), using original query")
                    return original_query
                    
            except ValueError:
                logger.warning("Failed to parse validation score")
                return original_query
                
        except Exception as e:
            logger.warning(f"Error expanding query: {e}")
            return original_query 

    async def _identify_relevant_documents(self, query: str, knowledge_base_id: str) -> Set[str]:
        """
        Use LLM to identify the most relevant documents for a query based on document summaries.
        
        Args:
            query: The user's query
            knowledge_base_id: The ID of the knowledge base to search
            
        Returns:
            Set of document IDs that are most relevant to the query
        """
        try:
            # Get document summaries from the knowledge base
            doc_summaries = await self._get_document_summaries(knowledge_base_id, max_samples=20)
            
            if not doc_summaries:
                logger.warning(f"No document summaries found for knowledge base {knowledge_base_id}")
                return set()
            
            # Format document summaries for the LLM prompt
            formatted_docs = []
            doc_id_map = {}  # Map to store document IDs with their index
            
            for i, doc in enumerate(doc_summaries):
                doc_id = doc.get('document_id', '')
                title = doc.get('title', 'Untitled')
                summary = doc.get('content', '')[:500]  # Limit summary length
                
                # Store the document ID with its index
                index_id = f"doc_{i+1}"
                doc_id_map[index_id] = doc_id
                
                # Use the index ID in the prompt for simplicity
                formatted_docs.append(f"Document {index_id}:\nTitle: {title}\nSummary: {summary}")
            
            # Create prompt for LLM to identify relevant documents
            prompt = f"""Given the following user query and document summaries, identify which documents are most relevant to answering the query.

User Query: {query}

Document Summaries:
{'-' * 50}
{('\n' + '-' * 50 + '\n').join(formatted_docs)}
{'-' * 50}

Instructions:
1. Analyze the user query and each document summary
2. Determine which documents contain information that would help answer the query
3. Return ONLY the document identifiers (like doc_1, doc_2) of relevant documents in a comma-separated list
4. If no documents seem relevant, return "NONE"

Format your response as:
RELEVANT_DOCUMENTS: [comma-separated list of document identifiers]

Example response:
RELEVANT_DOCUMENTS: doc_1, doc_3, doc_5"""

            # Call LLM to identify relevant documents
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extract document IDs from response
            relevant_doc_ids = set()
            if "RELEVANT_DOCUMENTS:" in response_text:
                # Extract the list part after the prefix
                id_list = response_text.split("RELEVANT_DOCUMENTS:")[1].strip()
                
                # Handle the case where no documents are relevant
                if id_list.upper() == "NONE":
                    logger.info("LLM determined no documents are relevant to the query")
                    return set()
                
                # Split by comma and clean up each ID
                for index_id in id_list.split(','):
                    clean_index_id = index_id.strip()
                    # Map the index ID back to the actual document ID
                    if clean_index_id in doc_id_map:
                        actual_doc_id = doc_id_map[clean_index_id]
                        relevant_doc_ids.add(actual_doc_id)
                    else:
                        logger.warning(f"Unknown document index ID: {clean_index_id}")
            
            logger.info(f"LLM identified {len(relevant_doc_ids)} relevant documents: {relevant_doc_ids}")
            return relevant_doc_ids
            
        except Exception as e:
            logger.error(f"Error identifying relevant documents with LLM: {e}", exc_info=True)
            return set() 