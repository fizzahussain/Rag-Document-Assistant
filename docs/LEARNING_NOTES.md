# 📚 Learning Notes

## RAG Is a System, Not a Single Model Call

The biggest lesson from this project is that answer quality depends on a chain of components:

```text
extraction
→ chunking
→ context representation
→ embeddings
→ vector retrieval
→ filtering
→ prompt construction
→ generation
→ citation
```

Weakness in any earlier stage reaches the final answer.

## OCR Trade-offs

Selective OCR showed why document type matters.

Text-native pages should stay native whenever possible. OCR is more expensive and introduces recognition errors, but it becomes essential for scanned pages.

## Chunking Trade-offs

Chunk size changes both retrieval precision and context completeness.

Overlap protects boundaries but increases storage. Rolling summaries improve continuity but also increase processing and prompt cost.

These settings need to be tuned together.

## Vector Search

The project connected abstract embedding concepts to database operations:

- embedding dimensionality
- cosine distance
- ranking
- score thresholds
- top-k
- approximate nearest neighbour indexing
- user/document filters

pgvector made it possible to keep this logic next to the normal relational schema.

## Local LLM Operations

Running Ollama locally exposed operational concerns that disappear behind hosted APIs:

- model download size
- model startup/warmup
- memory limits
- CPU vs GPU performance
- context length
- token generation limits
- request timeouts
- keeping models loaded between requests

## Speech Models

faster-whisper introduced similar systems questions:

- model caching
- quantized INT8 compute
- device selection
- VAD
- transcription latency
- audio file constraints

## Docker Networking

One of the most practical lessons was that container networking is not host networking.

`localhost` inside the backend container is not the Windows host, so host Ollama must be reached through `host.docker.internal`.

## Docker Persistence

Containers can be recreated; user data cannot.

Named volumes make database state, uploads, and model caches survive container replacement.

## Authentication and AI Data Isolation

RAG becomes a security problem when multiple users upload private documents.

The application therefore scopes:

- documents
- conversations
- retrieved chunks

to the authenticated user.

This is as important as the model itself.

## Evaluation

A convincing RAG project should have measurable retrieval checks.

The evaluation script uses expected context keywords to calculate a retrieval hit rate, creating a foundation for more advanced metrics such as:

- Recall@k
- Precision@k
- MRR
- faithfulness
- answer relevance
- citation correctness

## Software Engineering Lessons

The project also reinforced:

- provider abstractions
- async API design
- schema validation
- migrations
- structured errors
- health/readiness checks
- CI hygiene
- test layering
- secure environment configuration
