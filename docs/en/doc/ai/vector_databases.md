---
title: "Vector Databases for AI"
updated: 2026-10-11
last_reviewed: 2026-10-11
tags: ['ai', 'vector-db']
difficulty: beginner
category: Artificial Intelligence
status: published
estimated_time: 28 min
prerequisites: ["Basic Python"]
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

# Local client
client = chromadb.PersistentClient(path="./chroma_data")

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
- Multiple indexes (HNSW, IVF, SCANN)

**Docker Installation:**
```bash
curl -sfL https://raw.githubusercontent.com/milvus-io/milvus/master/scripts/standalone_embed.sh -o standalone_embed.sh
bash standalone_embed.sh start
```

Official Milvus Standalone script (single container with embedded etcd; port 19530). For Docker Compose or cluster deployments, follow the official installation guide: <https://milvus.io/docs/install_standalone-docker-compose.md>.

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
collection.load()  # Milvus requires loading the collection into memory before searching

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
  -p 8080:8080 -p 50051:50051 \
  -e QUERY_DEFAULTS_LIMIT=25 \
  -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
  -e PERSISTENCE_DATA_PATH='/var/lib/weaviate' \
  cr.weaviate.io/semitechnologies/weaviate:1.40.0
```

**Python Usage:**
```python
import weaviate
from weaviate.classes.config import Configure, Property, DataType

client = weaviate.connect_to_local()  # HTTP 8080 and gRPC 50051

# Create collection (schema), with vectors you supply
client.collections.create(
    "Document",
    vector_config=Configure.Vectors.self_provided(),
    properties=[
        Property(name="content", data_type=DataType.TEXT),
        Property(name="source", data_type=DataType.TEXT),
    ],
)
docs = client.collections.use("Document")

# Insert
docs.data.insert(
    properties={"content": "Kubernetes orchestrates containers", "source": "k8s-docs"},
    vector=embedding_vector,
)

# Search
result = docs.query.near_vector(near_vector=query_vector, limit=5)

client.close()
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
from pinecone import Pinecone, ServerlessSpec

pc = Pinecone(api_key="YOUR_API_KEY")

# Create index (serverless)
pc.create_index(
    name="docs",
    dimension=768,
    metric="cosine",
    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
)
index = pc.Index("docs")

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
results = client.query_points(
    collection_name="docs",
    query=query_vector,
    limit=5
).points
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

!!! warning "Illustrative only"
    This manifest is illustrative: it is not a supported Milvus deployment. On Kubernetes, Milvus is installed with the Milvus Operator or the official Helm chart, which manage etcd, object storage and messaging.


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
    collection.add(ids=[str(i + j) for j in range(len(batch))], embeddings=embeddings, documents=batch)
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
    where={"$and": [{"source": "kubernetes-docs"}, {"year": {"$gte": 2023}}]}
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
