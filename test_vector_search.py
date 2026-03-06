#!/usr/bin/env python3
"""Test vector search"""

from app.scheme_vector_store import SchemeVectorStore

print("Testing Vector Search...")
print("=" * 60)

vector_store = SchemeVectorStore()

# Test search
query = "PM-KISAN ke baare mein batao"
print(f"\nQuery: {query}")
print("-" * 60)

results = vector_store.search_schemes(
    query=query,
    top_k=5,
    language="hi"
)

print(f"\nFound {len(results)} results:\n")

for i, doc in enumerate(results, 1):
    print(f"{i}. {doc.scheme.scheme_name}")
    print(f"   Scheme ID: {doc.scheme_id}")
    print(f"   Similarity: {doc.similarity_score:.4f}")
    print(f"   Language: {doc.language}")
    print(f"   Content preview: {doc.content[:100]}...")
    print()

# Check if PM-KISAN is in results
pm_kisan_found = any('PM-KISAN' in doc.scheme.scheme_name or 'किसान' in doc.scheme.scheme_name for doc in results)

print("=" * 60)
if pm_kisan_found:
    print("✓ PM-KISAN found in results!")
else:
    print("✗ PM-KISAN not found")
print("=" * 60)
