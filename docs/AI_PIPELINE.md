# 🤖 AI & RAG Pipeline

## 1. Ingestion

The ingestion flow performs:

1. extension validation
2. size validation
3. content validation
4. SHA-256 duplicate detection
5. persistent file storage
6. extraction
7. optional OCR
8. context-aware chunking
9. embedding generation
10. vector persistence

## 2. OCR Strategy

PDF pages first use PyMuPDF native extraction.

When the amount of usable text is below `OCR_MIN_TEXT_CHARS`, OCR is attempted with Tesseract. The implementation can use PyMuPDF's OCR integration and fall back to the Tesseract CLI.

The stronger of native and OCR text is retained.

This avoids the cost and potential quality loss of OCRing every page.

## 3. Chunk Representation

A searchable chunk can carry:

- text
- page number
- chunk index
- SHA-style identity/hash
- context summary
- embedding

Physical overlap and rolling summaries solve different problems:

- overlap protects local boundaries
- summaries carry broader prior context

## 4. Embeddings

The default provider is Ollama with:

```text
nomic-embed-text
```

The configured vector dimension is:

```text
768
```

A provider abstraction also exists for OpenAI and deterministic mock embeddings for tests.

## 5. Vector Retrieval

The normal PostgreSQL path uses pgvector cosine distance.

The retrieval query is constrained by:

- authenticated user
- ready document status
- non-null embedding
- optional selected document IDs
- top-k limit
- optional relevance threshold

An HNSW index accelerates cosine-distance ordering as the stored corpus grows.

SQLite test mode falls back to in-memory cosine calculation so tests can run without pgvector.

## 6. Intent and Follow-Up Handling

Before retrieval, lightweight intent routing detects:

- greetings
- thanks
- farewells
- calculation-like messages
- document questions

Simple conversational intents can bypass retrieval.

For document questions, recent conversation history helps resolve follow-ups such as ordinal references and pronouns before a retrieval query is generated.

## 7. Grounded Generation

The generation prompt instructs the LLM to:

- use supplied document context for document claims
- avoid inventing unsupported details
- refuse when context is insufficient
- cite filename + page/chunk
- treat document text as untrusted data
- use conversation history only to understand follow-ups

This is an important RAG safety boundary: uploaded content is context, not system instruction.

## 8. Streaming

The backend provides a streaming chat path using Server-Sent Events.

The frontend can receive answer tokens incrementally instead of waiting for the entire LLM response.

## 9. Speech-to-Text

faster-whisper converts audio into text before it enters the normal RAG path.

Configuration covers:

- model size
- CPU/CUDA/auto device
- compute type
- language
- beam size
- timeout
- file size
- audio extensions

The default CPU + INT8 path is useful for local development on machines without a GPU.
