---
title: "Vector Databases for AI"
date: 2025-01-25
updated: 2025-01-25
tags: [ai, vector-db, chroma, milvus, weaviate, qdrant]
---

🚧 **TRANSLATION PENDING** - Last updated in Spanish: 2026-01-25


# Vector Databases

## Introduction

**Vector databases** are specialized systems for storing, indexing, and searching high-dimensional vectors (embeddings). They are fundamental for AI applications such as semantic search, RAG, recommendation systems, and similarity detection.

## Why Vector Databases?

### Difference from Traditional Databases

| Feature | Traditional DB | Vector DB |
|---------|----------------|-----------|
| Search | Exact (WHERE x=y) | Semantic similarity (k-NN) |
| Indexes | B-Tree, Hash | HNSW, IVF, LSH |
| Data | Structured | Embeddings (vectors) |
| Latency | ms | ms (with ANN) |
| Scalability | Vertical/Horizontal | Optimized Horizontal |

### Practical Example
```python
# Traditional search
SELECT * FROM docs WHERE title = 'Kubernetes'

# Vector search (semantic)
query_vector = embed("containers and orchestration")
results = vector_db.search(query_vector, top_k=5)
# Returns: Kubernetes, Docker Swarm, Nomad, ECS, Mesos
```

## Main Vector Databases

### 1. Chroma

**Description**: Open-source, lightweight, and easy-to-use vector DB.

**Features:**
- Built-in embeddings with OpenAI, Sentence Transformers
- Local or client-server storage
- Native integration with LangChain/LlamaIndex

**Installation and Usage:**
```python
pip install chromadb

import chromadb
from chromadb.config import Settings

# Local client
client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory="./chroma_data"
))

# Create collection
collection = client.create_collection("docs")

# Add documents
collection.add(
    documents=["Kubernetes is an orchestrator", "Docker is a container"],
    metadatas=[{"source": "k8s"}, {"source": "docker"}],
    ids=["id1", "id2"]
)

# Search
results = collection.query(
    query_texts=["containers"],
    n_results=2
)
```

**Use Case**: Prototypes, small/medium applications, local development.

### 2. Milvus

**Description**: High-performance vector DB for production at scale.

**Features:**
- Support for billions of vectors
- GPU acceleration
- Native horizontal distribution
- Multiple indexes (HNSW, IVF, ANNOY)

**Docker Installation:**
```bash
docker-compose up -d
```

```yaml
version: '3.5'
services:
  etcd:
    image: quay.io/coreos/etcd:latest
  minio:
    image: minio/minio:latest
  milvus:
    image: milvusdb/milvus:latest
    ports:
      - "19530:19530"
    depends_on:
      - etcd
      - minio
```

**Python Usage:**
```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

# Connect
connections.connect("default", host="localhost", port="19530")

# Define schema
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768),
    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=500)
]
schema = CollectionSchema(fields, "Document embeddings")
collection = Collection("docs", schema)

# Create index
index_params = {
    "metric_type": "L2",
    "index_type": "IVF_FLAT",
    "params": {"nlist": 128}
}
collection.create_index("embedding", index_params)

# Insert
collection.insert([
    [embedding_vector],
    ["Kubernetes documentation"]
])

# Search
search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
results = collection.search(
    data=[query_vector],
    anns_field="embedding",
    param=search_params,
    limit=10
)
```

**Use Case**: Large-scale production, millions of vectors, real-time search.

### 3. Weaviate

**Description**: Vector DB with GraphQL and data schema support.

**Features:**
- RESTful and GraphQL APIs
- Built-in automatic vectorization
- Advanced metadata filtering
- Multi-tenancy support

**Docker Installation:**
```bash
docker run -d \
  -p 8080:8080 \
  -e QUERY_DEFAULTS_LIMIT=25 \
  -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
  -e PERSISTENCE_DATA_PATH='/var/lib/weaviate' \
  semitechnologies/weaviate:latest
```

**Python Usage:**
```python
import weaviate

client = weaviate.Client("http://localhost:8080")

# Create class (schema)
class_obj = {
    "class": "Document",
    "vectorizer": "text2vec-transformers",
    "properties": [
        {"name": "content", "dataType": ["text"]},
        {"name": "source", "dataType": ["string"]}
    ]
}
client.schema.create_class(class_obj)

# Insert
client.data_object.create(
    data_object={
        "content": "Kubernetes orchestrates containers",
        "source": "k8s-docs"
    },
    class_name="Document"
)

# Search with GraphQL
result = client.query.get("Document", ["content", "source"])\
    .with_near_text({"concepts": ["container orchestration"]})\
    .with_limit(5)\
    .do()
```

**Use Case**: Applications with structured and unstructured data, GraphQL needs.

### 4. Pinecone

**Description**: Fully managed vector DB (cloud).

**Features:**
- Managed service (no infrastructure)
- High availability
- Auto-scaling
- Pay-per-use pricing

**Usage:**
```python
import pinecone

pinecone.init(api_key="YOUR_API_KEY", environment="us-west1-gcp")

# Create index
pinecone.create_index("docs", dimension=768, metric="cosine")
index = pinecone.Index("docs")

# Insert
index.upsert([
    ("id1", embedding_vector, {"text": "Kubernetes guide"})
])

# Search
results = index.query(
    vector=query_vector,
    top_k=10,
    include_metadata=True
)
```

**Use Case**: Startups, cloud-native apps, avoid infrastructure management.

### 5. Qdrant

**Description**: Open-source vector DB focused on performance.

**Features:**
- Written in Rust (high performance)
- Efficient payload filtering
- RESTful API and gRPC
- Sparse vector support

**Docker Installation:**
```bash
docker run -p 6333:6333 qdrant/qdrant
```

**Usage:**
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

client = QdrantClient("localhost", port=6333)

# Create collection
client.create_collection(
    collection_name="docs",
    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
)

# Insert
client.upsert(
    collection_name="docs",
    points=[
        PointStruct(
            id=1,
            vector=embedding_vector,
            payload={"text": "Kubernetes documentation"}
        )
    ]
)

# Search
results = client.search(
    collection_name="docs",
    query_vector=query_vector,
    limit=5
)
```

**Use Case**: On-premise apps, high performance, total control.

## Technical Comparison

| Vector DB | Hosting | Scalability | LangChain Integration | Pricing |
|-----------|---------|-------------|----------------------|---------|
| Chroma | Local/Self-hosted | Medium | Excellent | Free |
| Milvus | Self-hosted | High | Good | Free |
| Weaviate | Cloud/Self-hosted | High | Good | Freemium |
| Pinecone | Cloud | High | Excellent | Paid |
| Qdrant | Self-hosted/Cloud | High | Good | Freemium |

## Indexing Algorithms

### 1. HNSW (Hierarchical Navigable Small World)
- **Advantages**: High accuracy, fast search
- **Disadvantages**: Higher memory usage
- **Use**: High-performance production

### 2. IVF (Inverted File Index)
- **Advantages**: Balance accuracy/speed
- **Disadvantages**: Requires training
- **Use**: Large datasets (>1M vectors)

### 3. LSH (Locality-Sensitive Hashing)
- **Advantages**: Extreme scalability
- **Disadvantages**: Lower accuracy
- **Use**: Approximate searches in billions of vectors

## Kubernetes Architecture

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: milvus-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 100Gi
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: milvus
spec:
  serviceName: milvus
  replicas: 3
  selector:
    matchLabels:
      app: milvus
  template:
    metadata:
      labels:
        app: milvus
    spec:
      containers:
      - name: milvus
        image: milvusdb/milvus:latest
        ports:
        - containerPort: 19530
        volumeMounts:
        - name: data
          mountPath: /var/lib/milvus
        resources:
          requests:
            memory: "8Gi"
            cpu: "4"
          limits:
            memory: "16Gi"
            cpu: "8"
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 100Gi
```

## Performance Metrics

### Search Latency
```python
import time
import numpy as np

def benchmark_search(vector_db, query_vector, iterations=100):
    latencies = []
    for _ in range(iterations):
        start = time.time()
        vector_db.search(query_vector, top_k=10)
        latencies.append(time.time() - start)
    
    return {
        "avg_latency": np.mean(latencies),
        "p50": np.percentile(latencies, 50),
        "p95": np.percentile(latencies, 95),
        "p99": np.percentile(latencies, 99)
    }
```

### Recall (Precision)
```python
def calculate_recall(true_neighbors, retrieved_neighbors, k=10):
    """
    Recall: % of true neighbors retrieved
    """
    true_set = set(true_neighbors[:k])
    retrieved_set = set(retrieved_neighbors[:k])
    recall = len(true_set & retrieved_set) / k
    return recall
```

## Best Practices

### 1. Dimensionality Choice
```python
# Smaller embeddings = better performance
from sentence_transformers import SentenceTransformer

# 384 dimensions (fast)
model_small = SentenceTransformer('all-MiniLM-L6-v2')

# 768 dimensions (more accurate)
model_large = SentenceTransformer('all-mpnet-base-v2')
```

### 2. Batch Processing
```python
# Insert in batches for better performance
batch_size = 100
for i in range(0, len(documents), batch_size):
    batch = documents[i:i+batch_size]
    embeddings = model.encode(batch)
    collection.add(embeddings=embeddings, documents=batch)
```

### 3. Monitoring
```python
from prometheus_client import Gauge, Histogram

vector_db_size = Gauge('vector_db_documents', 'Total documents in vector DB')
search_latency = Histogram('vector_search_duration_seconds', 'Search latency')

@search_latency.time()
def search_vectors(query):
    return collection.query(query)

# Update metrics
vector_db_size.set(collection.count())
```

## Advanced Use Cases

### 1. Multi-modal Search
```python
# Search combining text and images
from sentence_transformers import SentenceTransformer

clip_model = SentenceTransformer('clip-ViT-B-32')

# Image embedding
image_embedding = clip_model.encode(image)

# Cross-search: image → similar texts
results = collection.query(image_embedding, n_results=10)
```

### 2. Hybrid Filtering
```python
# Combine vector search with filters
results = collection.query(
    query_embeddings=[query_vector],
    n_results=20,
    where={"source": "kubernetes-docs", "year": {"$gte": 2023}}
)
```

### 3. Reranking with Cross-Encoders
```python
from sentence_transformers import CrossEncoder

# 1. Initial vector search (fast, top 100)
candidates = collection.query(query_vector, n_results=100)

# 2. Reranking with cross-encoder (accurate, top 10)
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
scores = reranker.predict([(query, doc) for doc in candidates])
top_docs = sorted(zip(scores, candidates), reverse=True)[:10]
```

## Troubleshooting

### Issue: Slow searches
**Solutions:**
- Switch to HNSW index
- Reduce embedding dimensionality
- Increase resources (CPU/memory)
- Implement cache

### Issue: Low accuracy (recall)
**Solutions:**
- Use higher quality embeddings
- Adjust index parameters (nprobe, ef_search)
- Implement reranking
- Clean training data

### Issue: High memory consumption
**Solutions:**
- Use quantization (int8, binary)
- Reduce dimensionality (PCA)
- Partition into multiple collections
- Use disk storage (mmap)

## References

- [Chroma](https://www.trychroma.com/)
- [Milvus](https://milvus.io/)
- [Weaviate](https://weaviate.io/)
- [Pinecone](https://www.pinecone.io/)
- [Qdrant](https://qdrant.tech/)
- [HNSW Paper](https://arxiv.org/abs/1603.09320)

## Next Steps

- [RAG Basics](rag_basics.md) - Implement RAG with vector databases
- [Model Evaluation](model_evaluation.md) - Evaluate embedding quality
- [Ollama Basics](ollama_basics.md) - Generate local embeddings
