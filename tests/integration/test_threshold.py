import asyncio
from app.repositories.vector_repository import VectorRepository

async def test_search():
    vr = VectorRepository()
    
    # Test with threshold 0.4
    chunks_04 = await vr.search_chunks(
        'what are the keyfeatures?', 
        '60d2ea3d-d3f1-48ba-83ca-5cf53bc852e0', 
        top_k=10, 
        similarity_threshold=0.4
    )
    print(f'Found {len(chunks_04)} chunks with threshold 0.4')
    for i, chunk in enumerate(chunks_04):
        print(f'Chunk {i+1}: score={chunk.get("score", "N/A"):.4f}')
    
    # Test with threshold 0.3
    chunks_03 = await vr.search_chunks(
        'what are the keyfeatures?', 
        '60d2ea3d-d3f1-48ba-83ca-5cf53bc852e0', 
        top_k=10, 
        similarity_threshold=0.3
    )
    print(f'\nFound {len(chunks_03)} chunks with threshold 0.3')
    for i, chunk in enumerate(chunks_03):
        print(f'Chunk {i+1}: score={chunk.get("score", "N/A"):.4f}')

if __name__ == "__main__":
    asyncio.run(test_search()) 