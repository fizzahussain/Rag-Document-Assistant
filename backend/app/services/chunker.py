import hashlib
import re
import uuid

from pydantic import BaseModel

from backend.app.services.extractor import ExtractedDocument


class ChunkPayload(BaseModel):
    """Represents a clean, split chunk of text with location metadata."""

    chunk_id: uuid.UUID
    chunk_index: int
    page_number: int | None
    text: str
    chunk_hash: str


class TextChunker:
    """Handles text cleaning, normalization, and recursive sliding-window chunking."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    @staticmethod
    def clean_text(text: str) -> str:
        """Cleans and normalizes text while preserving paragraph structure."""
        if not text:
            return ""
        # Remove spaces before newlines
        text = re.sub(r"[ \t]+\n", "\n", text)
        # Replace multiple spaces/tabs with a single space
        text = re.sub(r"[ \t]+", " ", text)
        # Replace 3 or more newlines with double newline
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def chunk_document(self, doc: ExtractedDocument) -> list[ChunkPayload]:
        """Splits an extracted document into structured chunks with page numbers."""
        chunks: list[ChunkPayload] = []
        global_chunk_idx = 0

        # Process page by page to maintain accurate page numbers
        for page in doc.pages:
            cleaned_page_text = self.clean_text(page.text)
            if not cleaned_page_text:
                continue

            page_chunks_text = self._split_text(cleaned_page_text)
            for page_chunk in page_chunks_text:
                chunk_hash = hashlib.sha256(page_chunk.encode("utf-8")).hexdigest()
                chunks.append(
                    ChunkPayload(
                        chunk_id=uuid.uuid4(),
                        chunk_index=global_chunk_idx,
                        page_number=page.page_number,
                        text=page_chunk,
                        chunk_hash=chunk_hash,
                    )
                )
                global_chunk_idx += 1

        return chunks

    def _split_text(self, text: str) -> list[str]:
        """Recursively splits text using separators [\n\n, \n, . , space, ""] with overlap."""
        if len(text) <= self.chunk_size:
            return [text]

        separators = ["\n\n", "\n", ". ", " ", ""]
        return self._recursive_split(text, separators)

    def _recursive_split(self, text: str, separators: list[str]) -> list[str]:
        final_chunks: list[str] = []
        if not text.strip():
            return final_chunks

        if len(text) <= self.chunk_size or not separators:
            return [text.strip()]

        sep = separators[0]
        splits = text.split(sep) if sep else list(text)

        current_chunk: list[str] = []
        current_len = 0

        for split in splits:
            split_len = len(split) + len(sep)
            if current_len + split_len > self.chunk_size:
                if current_chunk:
                    joined = sep.join(current_chunk).strip()
                    if joined:
                        final_chunks.append(joined)

                # Apply sliding window overlap
                if self.chunk_overlap > 0 and current_chunk:
                    overlap_len = 0
                    overlap_items: list[str] = []
                    for item in reversed(current_chunk):
                        if overlap_len + len(item) <= self.chunk_overlap:
                            overlap_items.insert(0, item)
                            overlap_len += len(item) + len(sep)
                        else:
                            break
                    current_chunk = overlap_items
                    current_len = sum(len(i) + len(sep) for i in current_chunk)
                else:
                    current_chunk = []
                    current_len = 0

            current_chunk.append(split)
            current_len += split_len

        if current_chunk:
            joined = sep.join(current_chunk).strip()
            if joined:
                final_chunks.append(joined)

        return final_chunks
