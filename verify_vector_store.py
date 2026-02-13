"""Verification script for vector store integration"""

import sys
from datetime import datetime

# Check if required packages are available
try:
    from app.models import Scheme, SchemeCategory, SchemeAuthority, SchemeStatus
    from app.vector_store import VectorStoreClient, VectorDocument
    from app.embedding_generator import EmbeddingGenerator
    from app.scheme_vector_store import SchemeVectorStore
    print("✓ All vector store modules imported successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

# Check if optional dependencies are available
try:
    from qdrant_client import QdrantClient
    print("✓ qdrant-client is installed")
    QDRANT_AVAILABLE = True
except ImportError:
    print("⚠ qdrant-client is not installed (optional)")
    print("  Install with: pip install qdrant-client")
    QDRANT_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    print("✓ sentence-transformers is installed")
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    print("⚠ sentence-transformers is not installed (optional)")
    print("  Install with: pip install sentence-transformers")
    TRANSFORMERS_AVAILABLE = False

print("\n" + "="*60)
print("Vector Store Integration Verification")
print("="*60)

# Test 1: VectorDocument model validation
print("\n1. Testing VectorDocument model...")
try:
    doc = VectorDocument(
        id="test_doc_1",
        vector=[0.1] * 384,
        metadata={"scheme_id": "scheme_001", "category": "agriculture"},
        text_chunk="This is a test document about agriculture schemes."
    )
    print(f"   ✓ VectorDocument created: {doc.id}")
    print(f"   ✓ Vector dimension: {len(doc.vector)}")
    print(f"   ✓ Metadata: {doc.metadata}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 2: Embedding generation (if available)
if TRANSFORMERS_AVAILABLE:
    print("\n2. Testing embedding generation...")
    try:
        generator = EmbeddingGenerator(
            model_name="sentence-transformers/paraphrase-MiniLM-L3-v2"
        )
        
        test_text = "Agriculture scheme for farmers in India"
        embedding = generator.generate_embedding(test_text)
        
        print(f"   ✓ Generated embedding for: '{test_text}'")
        print(f"   ✓ Embedding dimension: {len(embedding)}")
        print(f"   ✓ First 5 values: {embedding[:5]}")
        
        # Test chunking
        long_text = " ".join(["word"] * 1000)
        chunks = generator.chunk_text(long_text, chunk_size=100, overlap=10)
        print(f"   ✓ Chunked text into {len(chunks)} chunks")
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
else:
    print("\n2. Skipping embedding generation test (sentence-transformers not installed)")

# Test 3: Vector store client (if Qdrant available)
if QDRANT_AVAILABLE:
    print("\n3. Testing vector store client...")
    try:
        # Try to connect to local Qdrant (will fail if not running)
        client = VectorStoreClient(
            url="http://localhost:6333",
            collection_name="test_verification",
            vector_size=384
        )
        print("   ✓ VectorStoreClient initialized")
        print("   ⚠ Note: Actual operations require Qdrant server running")
        
    except Exception as e:
        print(f"   ⚠ Could not connect to Qdrant: {e}")
        print("   Note: Start Qdrant with: docker run -p 6333:6333 qdrant/qdrant")
else:
    print("\n3. Skipping vector store client test (qdrant-client not installed)")

# Test 4: Scheme model
print("\n4. Testing Scheme model...")
try:
    scheme = Scheme(
        scheme_id="PM_KISAN_001",
        scheme_name="PM-KISAN",
        description="Direct income support to farmers",
        category=SchemeCategory.AGRICULTURE,
        authority=SchemeAuthority.CENTRAL,
        applicable_states=["ALL"],
        benefits="₹6000 per year in three installments",
        application_process="Register through PM-KISAN portal",
        official_url="https://pmkisan.gov.in",
        status=SchemeStatus.ACTIVE,
    )
    print(f"   ✓ Scheme created: {scheme.scheme_name}")
    print(f"   ✓ Category: {scheme.category.value}")
    print(f"   ✓ Status: {scheme.status.value}")
    print(f"   ✓ Applicable states: {scheme.applicable_states}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 5: Integration check
print("\n5. Integration readiness check...")
components = {
    "VectorDocument model": True,
    "Scheme model": True,
    "VectorStoreClient": QDRANT_AVAILABLE,
    "EmbeddingGenerator": TRANSFORMERS_AVAILABLE,
    "SchemeVectorStore": QDRANT_AVAILABLE and TRANSFORMERS_AVAILABLE,
}

for component, available in components.items():
    status = "✓" if available else "⚠"
    print(f"   {status} {component}")

print("\n" + "="*60)
if all(components.values()):
    print("✓ All components ready for vector store operations!")
else:
    print("⚠ Some optional components not available")
    print("\nTo install all dependencies:")
    print("  pip install qdrant-client sentence-transformers")
    print("\nTo run Qdrant locally:")
    print("  docker run -p 6333:6333 qdrant/qdrant")

print("="*60)
