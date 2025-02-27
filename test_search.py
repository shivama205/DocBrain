import asyncio
import logging
from app.repositories.vector_repository import VectorRepository
from app.services.rag_service import RAGService

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_search():
    # Initialize repositories
    vector_repo = VectorRepository()
    rag_service = RAGService(vector_repo)
    
    # Test parameters
    knowledge_base_id = input("Enter knowledge base ID: ")
    query = input("Enter your query: ")
    similarity_threshold = float(input("Enter similarity threshold (0.0-1.0): ") or "0.5")
    
    print(f"\nRunning search with:")
    print(f"- Query: '{query}'")
    print(f"- Knowledge Base ID: {knowledge_base_id}")
    print(f"- Similarity Threshold: {similarity_threshold}")
    
    # Test direct vector search
    print("\n1. Testing direct vector search...")
    embedding = await vector_repo._get_embedding(query)
    print(f"Generated embedding with {len(embedding)} dimensions")
    
    # Query Pinecone directly
    filter = {"knowledge_base_id": {"$eq": knowledge_base_id}}
    response = vector_repo.index.query(
        vector=embedding,
        filter=filter,
        top_k=10,
        include_metadata=True
    )
    
    print(f"Raw Pinecone response: {len(response.matches)} matches")
    for i, match in enumerate(response.matches):
        print(f"Match {i+1}: score={match.score:.4f}, id={match.id}")
    
    # Test search_chunks method
    print("\n2. Testing search_chunks method...")
    chunks = await vector_repo.search_chunks(
        query=query,
        knowledge_base_id=knowledge_base_id,
        top_k=10,
        similarity_threshold=similarity_threshold
    )
    
    print(f"search_chunks returned {len(chunks)} chunks")
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1}: score={chunk.get('score', 'N/A'):.4f}, content={chunk.get('content', '')[:50]}...")
    
    # Test full RAG pipeline
    print("\n3. Testing full RAG pipeline...")
    result = await rag_service.process_query(
        query=query,
        knowledge_base_id=knowledge_base_id,
        top_k=10,
        similarity_threshold=similarity_threshold
    )
    
    print(f"RAG pipeline returned {len(result.get('sources', []))} sources")
    print(f"Answer: {result.get('answer', 'No answer generated')[:100]}...")

if __name__ == "__main__":
    asyncio.run(test_search()) 