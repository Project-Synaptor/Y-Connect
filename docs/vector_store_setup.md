# Vector Store Setup Guide

This guide explains how to set up and use the vector store integration for the Y-Connect WhatsApp Bot.

## Overview

The vector store integration enables semantic search over government scheme documents using embeddings. It consists of three main components:

1. **VectorStoreClient** - Low-level interface to Qdrant vector database
2. **EmbeddingGenerator** - Generates multilingual embeddings using sentence-transformers
3. **SchemeVectorStore** - High-level interface for scheme document operations

## Installation

### 1. Install Dependencies

```bash
pip install qdrant-client sentence-transformers
```

### 2. Set Up Qdrant

#### Option A: Docker (Recommended for Development)

```bash
docker run -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage \
    qdrant/qdrant
```

#### Option B: Qdrant Cloud

1. Sign up at https://cloud.qdrant.io
2. Create a cluster
3. Get your API key and cluster URL
4. Update `.env`:

```env
VECTOR_DB_URL=https://your-cluster.qdrant.io
VECTOR_DB_API_KEY=your-api-key-here
```

### 3. Configure Environment Variables

Update your `.env` file:

```env
# Vector Database (Qdrant)
VECTOR_DB_PROVIDER=qdrant
VECTOR_DB_URL=http://localhost:6333
VECTOR_DB_API_KEY=
VECTOR_DB_INDEX_NAME=y-connect-schemes
VECTOR_EMBEDDING_DIMENSION=384
```

## Usage

### Basic Usage

```python
from app.scheme_vector_store import SchemeVectorStore
from app.models import Scheme, SchemeCategory, SchemeAuthority, SchemeStatus

# Initialize vector store
vector_store = SchemeVectorStore()

# Create a scheme
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

# Index the scheme
vector_store.upsert_scheme_documents(scheme, language="en")

# Search for schemes
results = vector_store.search_schemes(
    query="farming support schemes",
    top_k=5,
    language="en",
    filters={"category": "agriculture", "status": "active"}
)

for result in results:
    print(f"Scheme: {result.scheme.scheme_name}")
    print(f"Score: {result.similarity_score}")
    print(f"Content: {result.content[:100]}...")
```

### Multilingual Support

The system supports 10 Indian languages:

```python
# Index scheme in multiple languages
languages = ["en", "hi", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa"]

for lang in languages:
    vector_store.upsert_scheme_documents(scheme, language=lang)

# Search in Hindi
results = vector_store.search_schemes(
    query="किसानों के लिए योजना",
    language="hi",
    filters={"category": "agriculture"}
)
```

### Updating Schemes

```python
# Update scheme information
scheme.description = "Updated description with new benefits"
scheme.benefits = "Enhanced benefits: ₹8000 per year"

# Update in vector store
vector_store.update_scheme_documents(scheme, languages=["en", "hi"])
```

### Filtering

Available filters:

- `category`: Scheme category (agriculture, education, health, etc.)
- `status`: Scheme status (active, expired, upcoming)
- `state`: Applicable state code or "ALL"
- `authority`: central or state
- `language`: Document language

```python
# Filter by multiple criteria
results = vector_store.search_schemes(
    query="education scholarship",
    filters={
        "category": "education",
        "status": "active",
        "state": "MH",
        "authority": "state"
    }
)
```

### Deleting Schemes

```python
# Delete all documents for a scheme
vector_store.delete_scheme_documents("PM_KISAN_001")

# Delete only specific language
vector_store.delete_scheme_documents("PM_KISAN_001", language="hi")
```

## Architecture

### Embedding Model

The system uses `paraphrase-multilingual-MiniLM-L12-v2` which:
- Supports 50+ languages including all Indian languages
- Produces 384-dimensional embeddings
- Balances quality and performance

### Document Chunking

Long documents are split into chunks:
- **Chunk size**: 512 tokens (configurable)
- **Overlap**: 50 tokens (configurable)
- **Strategy**: Word-level splitting with overlap

Each scheme is split into 4 document types:
1. **Overview**: Name + description
2. **Eligibility**: Eligibility criteria
3. **Benefits**: Scheme benefits
4. **Application**: Application process

### Vector Search

Uses cosine similarity for semantic search:
- **Distance metric**: Cosine
- **Index type**: HNSW (Hierarchical Navigable Small World)
- **Default top_k**: 5 results
- **Confidence threshold**: 0.7 (configurable)

## Testing

### Run Property Tests

```bash
# Test retrieval result count
pytest tests/test_vector_store_properties.py::TestVectorStoreProperties::test_property_13_retrieval_result_count -v

# Test embedding update propagation
pytest tests/test_vector_store_properties.py::TestVectorStoreProperties::test_property_17_embedding_update_propagation -v

# Run all vector store tests
pytest tests/test_vector_store_properties.py -v
```

### Verify Installation

```bash
python verify_vector_store.py
```

## Performance Considerations

### Embedding Generation

- **Cold start**: ~2-3 seconds (model loading)
- **Single embedding**: ~10-50ms
- **Batch embeddings**: ~5-10ms per text (batched)

### Vector Search

- **Search latency**: <100ms for 10K documents
- **Throughput**: 100+ queries/second
- **Memory**: ~1GB for 10K documents (384-dim embeddings)

### Optimization Tips

1. **Batch operations**: Use `batch_generate_embeddings()` for multiple texts
2. **Caching**: Cache embeddings for frequently searched queries
3. **GPU acceleration**: Set `device="cuda"` if GPU available
4. **Index tuning**: Adjust HNSW parameters for speed/accuracy tradeoff

## Troubleshooting

### Qdrant Connection Error

```
Error: Could not connect to Qdrant
```

**Solution**: Ensure Qdrant is running:
```bash
docker ps | grep qdrant
```

### Model Download Issues

```
Error: Could not download sentence-transformers model
```

**Solution**: Download manually:
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
```

### Memory Issues

```
Error: Out of memory
```

**Solution**: Reduce batch size:
```python
embeddings = generator.batch_generate_embeddings(texts, batch_size=8)
```

## Production Deployment

### Qdrant Cloud

For production, use Qdrant Cloud:
1. Higher availability and reliability
2. Automatic backups
3. Horizontal scaling
4. Monitoring and alerts

### Embedding Model Hosting

Options for embedding generation:
1. **Local**: Run on application server (simple, lower latency)
2. **Dedicated service**: Separate embedding service (scalable)
3. **API**: Use embedding API (e.g., OpenAI, Cohere)

### Monitoring

Key metrics to monitor:
- Search latency (p50, p95, p99)
- Embedding generation time
- Vector store size
- Query throughput
- Error rate

## References

- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Sentence Transformers](https://www.sbert.net/)
- [Multilingual Models](https://www.sbert.net/docs/pretrained_models.html#multi-lingual-models)
