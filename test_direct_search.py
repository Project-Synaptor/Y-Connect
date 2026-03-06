#!/usr/bin/env python3
"""Test direct search"""

from app.scheme_vector_store import SchemeVectorStore

print("Testing Direct Searches...")
print("=" * 60)

vector_store = SchemeVectorStore()

queries = [
    ("PM-KISAN", "en"),
    ("Pradhan Mantri Kisan Samman Nidhi", "en"),
    ("किसान", "hi"),
    ("farmer scheme", "en"),
    ("Ayushman Bharat", "en"),
]

for query, lang in queries:
    print(f"\nQuery: '{query}' (language: {lang})")
    print("-" * 60)
    
    results = vector_store.search_schemes(
        query=query,
        top_k=3,
        language=lang
    )
    
    if results:
        for i, doc in enumerate(results[:3], 1):
            print(f"{i}. {doc.scheme.scheme_name} (score: {doc.similarity_score:.4f})")
    else:
        print("No results found")
    print()
