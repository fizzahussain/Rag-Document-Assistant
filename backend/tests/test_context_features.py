from backend.app.services.chunker import TextChunker
from backend.app.services.extractor import ExtractedDocument, ExtractedPage
from backend.app.services.intent import classify_intent


def test_chunker_applies_real_overlap_and_rolling_context() -> None:
    """Verify adjacent chunks overlap and rolling context is stored"""
    text = " ".join(f"word{index}" for index in range(180))

    chunker = TextChunker(
        chunk_size=120,
        chunk_overlap=25,
        context_summary_enabled=True,
        context_summary_max_chars=100,
    )

    document = ExtractedDocument(
        text=text,
        pages=[ExtractedPage(page_number=1, text=text)],
        metadata={},
    )

    chunks = chunker.chunk_document(document)

    assert len(chunks) > 2
    assert chunks[0].context_summary is None
    assert chunks[1].context_summary
    assert chunks[2].context_summary

    first_words = chunks[0].text.split()
    second_words = chunks[1].text.split()

    overlap = set(first_words) & set(second_words)

    assert overlap
    assert "word15" in overlap
    assert "word16" in overlap


def test_context_summary_is_bounded() -> None:
    """Verify rolling context does not grow without limit"""
    text = " ".join(f"word{index}" for index in range(300))

    chunker = TextChunker(
        chunk_size=100,
        chunk_overlap=20,
        context_summary_enabled=True,
        context_summary_max_chars=80,
    )

    document = ExtractedDocument(
        text=text,
        pages=[ExtractedPage(page_number=1, text=text)],
        metadata={},
    )

    chunks = chunker.chunk_document(document)

    for chunk in chunks[1:]:
        assert chunk.context_summary
        assert len(chunk.context_summary) <= 80


def test_greeting_intent() -> None:
    """Verify greetings and thanks bypass document retrieval"""
    assert classify_intent("hello").value == "greeting"
    assert classify_intent("hi").value == "greeting"
    assert classify_intent("thank you").value == "thanks"


def test_document_question_intent() -> None:
    """Verify document questions use the RAG path"""
    assert classify_intent("Summarize this document") == "document"
    assert classify_intent("Explain neural networks") == "document"
