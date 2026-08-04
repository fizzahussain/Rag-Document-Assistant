import pytest
from backend.app.services.chunker import TextChunker
from backend.app.services.embedder import (
    EmbeddingProviderFactory,
    MockEmbeddingProvider,
)
from backend.app.services.extractor import ExtractedDocument, ExtractedPage


def test_clean_text():
    raw = "  Hello    world!  \n\n\n\nNew paragraph  "
    cleaned = TextChunker.clean_text(raw)
    assert cleaned == "Hello world!\n\nNew paragraph"


def test_chunk_document():
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)
    doc = ExtractedDocument(
        text="Sample text",
        pages=[
            ExtractedPage(
                page_number=1,
                text="This is a long sentence meant to test the text chunker functionality and sliding window overlap.",
            )
        ],
        metadata={},
    )
    chunks = chunker.chunk_document(doc)
    assert len(chunks) > 0
    assert chunks[0].page_number == 1
    assert chunks[0].chunk_hash != ""


@pytest.mark.asyncio
async def test_mock_embedder():
    embedder = MockEmbeddingProvider(dimension=128)
    texts = ["chunk 1 text", "chunk 2 text"]
    embeddings = await embedder.embed_texts(texts)
    
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 128
    # Test vector normalization (length close to 1.0)
    norm = sum(x * x for x in embeddings[0]) ** 0.5
    assert pytest.approx(norm, 0.001) == 1.0


@pytest.mark.asyncio
async def test_embedding_factory():
    provider = EmbeddingProviderFactory.get_provider()
    assert provider is not None
