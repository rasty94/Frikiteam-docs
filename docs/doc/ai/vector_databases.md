# Bases de Datos Vectoriales

## Introducción

Las **bases de datos vectoriales** son sistemas especializados en almacenar, indexar y buscar vectores de alta dimensionalidad (embeddings). Son fundamentales para aplicaciones de IA como búsqueda semántica, RAG, sistemas de recomendación y detección de similitudes.

## ¿Por qué Vector Databases?

### Diferencia con Bases de Datos Tradicionales

| Característica | BD Tradicional | Vector DB |
|----------------|----------------|-----------|
| Búsqueda | Exacta (WHERE x=y) | Similitud semántica (k-NN) |
| Índices | B-Tree, Hash | HNSW, IVF, LSH |
| Datos | Estructurados | Embeddings (vectores) |
| Latencia | ms | ms (con ANN) |
| Escalabilidad | Vertical/Horizontal | Horizontal optimizada |

### Ejemplo Práctico
```python
# Búsqueda tradicional
SELECT * FROM docs WHERE title = 'Kubernetes'

# Búsqueda vectorial (semántica)
query_vector = embed("contenedores y orquestación")
results = vector_db.search(query_vector, top_k=5)
# Retorna: Kubernetes, Docker Swarm, Nomad, ECS, Mesos
```

## Principales Vector Databases

### 1. Chroma

**Descripción**: Vector DB open-source, ligera y fácil de usar.

**Características:**
- Embeddings integrados con OpenAI, Sentence Transformers
- Almacenamiento local o cliente-servidor
- Integración nativa con LangChain/LlamaIndex

**Instalación y Uso:**
```python
pip install chromadb

import chromadb
from chromadb.config import Settings

# Cliente local
client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory="./chroma_data"
))

# Crear colección
collection = client.create_collection("docs")

# Añadir documentos
collection.add(
    documents=["Kubernetes es un orquestador", "Docker es un contenedor"],
    metadatas=[{"source": "k8s"}, {"source": "docker"}],
    ids=["id1", "id2"]
)

# Buscar
results = collection.query(
    query_texts=["contenedores"],
    n_results=2
)
```

**Caso de Uso**: Prototipos, aplicaciones pequeñas/medianas, desarrollo local.

### 2. Milvus

**Descripción**: Vector DB de alto rendimiento para producción a escala.

**Características:**
- Soporte para billones de vectores
- GPU acceleration
- Distribución horizontal nativa
- Múltiples índices (HNSW, IVF, ANNOY)

**Instalación con Docker:**
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

**Uso con Python:**
```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

# Conectar
connections.connect("default", host="localhost", port="19530")

# Definir schema
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768),
    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=500)
]
schema = CollectionSchema(fields, "Document embeddings")
collection = Collection("docs", schema)

# Crear índice
index_params = {
    "metric_type": "L2",
    "index_type": "IVF_FLAT",
    "params": {"nlist": 128}
}
collection.create_index("embedding", index_params)

# Insertar
collection.insert([
    [embedding_vector],
    ["Kubernetes documentation"]
])

# Buscar
search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
results = collection.search(
    data=[query_vector],
    anns_field="embedding",
    param=search_params,
    limit=10
)
```

**Caso de Uso**: Producción a gran escala, millones de vectores, búsqueda en tiempo real.

### 3. Weaviate

**Descripción**: Vector DB con soporte para GraphQL y esquemas de datos.

**Características:**
- RESTful y GraphQL APIs
- Vectorización automática integrada
- Filtrado por metadatos avanzado
- Soporte para multi-tenancy

**Instalación con Docker:**
```bash
docker run -d \
  -p 8080:8080 \
  -e QUERY_DEFAULTS_LIMIT=25 \
  -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
  -e PERSISTENCE_DATA_PATH='/var/lib/weaviate' \
  semitechnologies/weaviate:latest
```

**Uso con Python:**
```python
import weaviate

client = weaviate.Client("http://localhost:8080")

# Crear clase (schema)
class_obj = {
    "class": "Document",
    "vectorizer": "text2vec-transformers",
    "properties": [
        {"name": "content", "dataType": ["text"]},
        {"name": "source", "dataType": ["string"]}
    ]
}
client.schema.create_class(class_obj)

# Insertar
client.data_object.create(
    data_object={
        "content": "Kubernetes orchestrates containers",
        "source": "k8s-docs"
    },
    class_name="Document"
)

# Buscar con GraphQL
result = client.query.get("Document", ["content", "source"])\
    .with_near_text({"concepts": ["container orchestration"]})\
    .with_limit(5)\
    .do()
```

**Caso de Uso**: Aplicaciones con datos estructurados y no estructurados, necesidad de GraphQL.

### 4. Pinecone

**Descripción**: Vector DB completamente gestionado (cloud).

**Características:**
- Managed service (sin infraestructura)
- Alta disponibilidad
- Escalado automático
- Pricing por uso

**Uso:**
```python
import pinecone

pinecone.init(api_key="YOUR_API_KEY", environment="us-west1-gcp")

# Crear índice
pinecone.create_index("docs", dimension=768, metric="cosine")
index = pinecone.Index("docs")

# Insertar
index.upsert([
    ("id1", embedding_vector, {"text": "Kubernetes guide"})
])

# Buscar
results = index.query(
    vector=query_vector,
    top_k=10,
    include_metadata=True
)
```

**Caso de Uso**: Startups, aplicaciones cloud-native, evitar gestión de infraestructura.

### 5. Qdrant

**Descripción**: Vector DB open-source con enfoque en rendimiento.

**Características:**
- Escrito en Rust (alto rendimiento)
- Filtrado por payload eficiente
- RESTful API y gRPC
- Soporte para sparse vectors

**Instalación con Docker:**
```bash
docker run -p 6333:6333 qdrant/qdrant
```

**Uso:**
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

client = QdrantClient("localhost", port=6333)

# Crear colección
client.create_collection(
    collection_name="docs",
    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
)

# Insertar
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

# Buscar
results = client.search(
    collection_name="docs",
    query_vector=query_vector,
    limit=5
)
```

**Caso de Uso**: Aplicaciones on-premise, alto rendimiento, control total.

## Comparativa Técnica

| Vector DB | Hosting | Escalabilidad | Integración LangChain | Precio |
|-----------|---------|---------------|------------------------|--------|
| Chroma | Local/Self-hosted | Media | Excelente | Gratis |
| Milvus | Self-hosted | Alta | Buena | Gratis |
| Weaviate | Cloud/Self-hosted | Alta | Buena | Freemium |
| Pinecone | Cloud | Alta | Excelente | Pago |
| Qdrant | Self-hosted/Cloud | Alta | Buena | Freemium |

## Algoritmos de Indexación

### 1. HNSW (Hierarchical Navigable Small World)
- **Ventajas**: Alta precisión, búsqueda rápida
- **Desventajas**: Mayor uso de memoria
- **Uso**: Producción de alto rendimiento

### 2. IVF (Inverted File Index)
- **Ventajas**: Balance precisión/velocidad
- **Desventajas**: Requiere entrenamiento
- **Uso**: Datasets grandes (>1M vectores)

### 3. LSH (Locality-Sensitive Hashing)
- **Ventajas**: Escalabilidad extrema
- **Desventajas**: Menor precisión
- **Uso**: Búsquedas aproximadas en billones de vectores

## Arquitectura en Kubernetes

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

## Métricas de Rendimiento

### Latencia de Búsqueda
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

### Recall (Precisión)
```python
def calculate_recall(true_neighbors, retrieved_neighbors, k=10):
    """
    Recall: % de vecinos verdaderos recuperados
    """
    true_set = set(true_neighbors[:k])
    retrieved_set = set(retrieved_neighbors[:k])
    recall = len(true_set & retrieved_set) / k
    return recall
```

## Mejores Prácticas

### 1. Elección de Dimensionalidad
```python
# Embeddings más pequeños = mejor rendimiento
from sentence_transformers import SentenceTransformer

# 384 dimensiones (rápido)
model_small = SentenceTransformer('all-MiniLM-L6-v2')

# 768 dimensiones (más preciso)
model_large = SentenceTransformer('all-mpnet-base-v2')
```

### 2. Batch Processing
```python
# Insertar en lotes para mejor rendimiento
batch_size = 100
for i in range(0, len(documents), batch_size):
    batch = documents[i:i+batch_size]
    embeddings = model.encode(batch)
    collection.add(embeddings=embeddings, documents=batch)
```

### 3. Monitoreo
```python
from prometheus_client import Gauge, Histogram

vector_db_size = Gauge('vector_db_documents', 'Total documents in vector DB')
search_latency = Histogram('vector_search_duration_seconds', 'Search latency')

@search_latency.time()
def search_vectors(query):
    return collection.query(query)

# Actualizar métricas
vector_db_size.set(collection.count())
```

## Casos de Uso Avanzados

### 1. Multi-modal Search
```python
# Búsqueda combinando texto e imágenes
from sentence_transformers import SentenceTransformer

clip_model = SentenceTransformer('clip-ViT-B-32')

# Embedding de imagen
image_embedding = clip_model.encode(image)

# Búsqueda cruzada: imagen → textos similares
results = collection.query(image_embedding, n_results=10)
```

### 2. Filtrado Híbrido
```python
# Combinar búsqueda vectorial con filtros
results = collection.query(
    query_embeddings=[query_vector],
    n_results=20,
    where={"source": "kubernetes-docs", "year": {"$gte": 2023}}
)
```

### 3. Reranking con Cross-Encoders
```python
from sentence_transformers import CrossEncoder

# 1. Búsqueda vectorial inicial (rápida, top 100)
candidates = collection.query(query_vector, n_results=100)

# 2. Reranking con cross-encoder (preciso, top 10)
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
scores = reranker.predict([(query, doc) for doc in candidates])
top_docs = sorted(zip(scores, candidates), reverse=True)[:10]
```

## Troubleshooting

### Problema: Búsquedas lentas
**Soluciones:**
- Cambiar a índice HNSW
- Reducir dimensionalidad de embeddings
- Aumentar recursos (CPU/memoria)
- Implementar caché

### Problema: Baja precisión (recall)
**Soluciones:**
- Usar embeddings de mayor calidad
- Ajustar parámetros del índice (nprobe, ef_search)
- Implementar reranking
- Limpiar datos de entrenamiento

### Problema: Alto consumo de memoria
**Soluciones:**
- Usar cuantización (int8, binary)
- Reducir dimensionalidad (PCA)
- Particionar en múltiples colecciones
- Usar almacenamiento en disco (mmap)

## Referencias

- [Chroma](https://www.trychroma.com/)
- [Milvus](https://milvus.io/)
- [Weaviate](https://weaviate.io/)
- [Pinecone](https://www.pinecone.io/)
- [Qdrant](https://qdrant.tech/)
- [HNSW Paper](https://arxiv.org/abs/1603.09320)

## Próximos Pasos

- [RAG Basics](rag_basics.md) - Implementar RAG con vector databases
- [Model Evaluation](model_evaluation.md) - Evaluar calidad de embeddings
- [Ollama Basics](ollama_basics.md) - Generar embeddings locales
