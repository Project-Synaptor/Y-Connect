#!/usr/bin/env python3
"""Debug bot test"""

import asyncio
from app.yconnect_pipeline import YConnectPipeline
from app.query_processor import QueryProcessor
from app.scheme_vector_store import SchemeVectorStore

async def test():
    print("Testing Y-Connect Bot (Debug Mode)...")
    print("=" * 60)
    
    # Test query processing
    query_processor = QueryProcessor()
    query = "PM-KISAN ke baare mein batao"
    
    print(f"\n1. Processing query: {query}")
    from app.session_manager import UserSession
    session = UserSession(phone_number="+919876543210")
    processed = await query_processor.process_query(query, session)
    print(f"   Language: {processed.language}")
    print(f"   Intent: {processed.intent}")
    print(f"   Entities: {processed.entities}")
    
    # Test vector search
    print(f"\n2. Searching vector store...")
    vector_store = SchemeVectorStore()
    results = vector_store.search_schemes(
        query=query,
        top_k=5,
        language=processed.language
    )
    
    print(f"   Found {len(results)} results:")
    for i, doc in enumerate(results[:3], 1):
        print(f"   {i}. {doc.scheme.scheme_name}")
        print(f"      Similarity: {doc.similarity_score:.4f}")
        print(f"      Scheme ID: {doc.scheme_id}")
    
    # Test full pipeline
    print(f"\n3. Testing full pipeline...")
    pipeline = YConnectPipeline()
    response = await pipeline.process_message(query, '+919876543210')
    
    print(f"\nResponse ({len(response)} chars):")
    print(response[:500])
    
    # Check success
    success = any(keyword in response.lower() for keyword in ['pm-kisan', 'किसान', 'farmer', '6000', '6,000'])
    
    print("\n" + "=" * 60)
    if success:
        print("✓ TEST PASSED")
    else:
        print("✗ TEST FAILED")
    print("=" * 60)
    
    return success

if __name__ == '__main__':
    result = asyncio.run(test())
    exit(0 if result else 1)
