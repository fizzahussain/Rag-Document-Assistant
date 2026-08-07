import hashlib
import re
import uuid

from pydantic import BaseModel

from backend.app.config import settings
from backend.app.services.extractor import ExtractedDocument


class ChunkPayload(BaseModel):
    """Represent a document chunk and its rolling prior context"""

    chunk_id: uuid.UUID
    chunk_index: int
    page_number: int | None
    text: str
    context_summary: str | None = None
    chunk_hash: str


class TextChunker:
    """Clean text and create overlapping chunks with rolling context"""

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        context_summary_enabled: bool | None = None,
        context_summary_max_chars: int | None = None,
    ) -> None:
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP if chunk_overlap is None else chunk_overlap
        self.context_summary_enabled = (
            settings.CHUNK_CONTEXT_SUMMARY_ENABLED
            if context_summary_enabled is None
            else context_summary_enabled
        )
        self.context_summary_max_chars = (
            context_summary_max_chars or settings.CHUNK_CONTEXT_SUMMARY_MAX_CHARS
        )

        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        if self.chunk_overlap < 0 or self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be between 0 and chunk_size - 1")

    @staticmethod
    def clean_text(text: str) -> str:
        """Normalize spacing while preserving paragraph boundaries"""

        if not text:
            return ""

        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def chunk_document(self, doc: ExtractedDocument) -> list[ChunkPayload]:
        """Split an extracted document while preserving page metadata"""

        chunks: list[ChunkPayload] = []
        global_chunk_idx = 0
        rolling_summary = ""

        for page in doc.pages:
            cleaned_page_text = self.clean_text(page.text)
            if not cleaned_page_text:
                continue

            for page_chunk in self._split_text(cleaned_page_text):
                context_summary = rolling_summary or None
                chunk_hash = hashlib.sha256(page_chunk.encode("utf-8")).hexdigest()
                chunks.append(
                    ChunkPayload(
                        chunk_id=uuid.uuid5(
                            uuid.NAMESPACE_URL,
                            f"{page.page_number}:{global_chunk_idx}:{chunk_hash}",
                        ),
                        chunk_index=global_chunk_idx,
                        page_number=page.page_number,
                        text=page_chunk,
                        context_summary=context_summary,
                        chunk_hash=chunk_hash,
                    )
                )

                if self.context_summary_enabled:
                    rolling_summary = self._update_rolling_summary(
                        rolling_summary,
                        page_chunk,
                    )

                global_chunk_idx += 1

        return chunks

    def embedding_text(self, chunk: ChunkPayload) -> str:
        """Return text used to embed a chunk with bounded prior context"""

        if not chunk.context_summary:
            return chunk.text

        return (
            f"Previous document context:\n{chunk.context_summary}\n\nCurrent chunk:\n{chunk.text}"
        )

    def _split_text(self, text: str) -> list[str]:
        """Split text into reliable character-overlap windows"""

        if len(text) <= self.chunk_size:
            return [text]

        chunks: list[str] = []
        start = 0
        text_length = len(text)

        while start < text_length:
            hard_end = min(start + self.chunk_size, text_length)
            end = hard_end

            if hard_end < text_length:
                window = text[start:hard_end]
                minimum_boundary = max(int(self.chunk_size * 0.55), 1)
                boundary = self._best_boundary(window, minimum_boundary)
                if boundary is not None:
                    end = start + boundary

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            if end >= text_length:
                break

            next_start = max(0, end - self.chunk_overlap)
            if next_start <= start:
                next_start = end

            if self.chunk_overlap > 0:
                while next_start > start and not text[next_start - 1].isspace():
                    next_start -= 1
                if next_start <= start:
                    next_start = max(start + 1, end - self.chunk_overlap)

            start = next_start

        return chunks

    @staticmethod
    def _best_boundary(window: str, minimum_boundary: int) -> int | None:
        """Find a natural split point near the end of a chunk window"""

        candidates: list[int] = []
        for separator in ("\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " "):
            position = window.rfind(separator, minimum_boundary)
            if position >= minimum_boundary:
                candidates.append(position + len(separator))

        return max(candidates) if candidates else None

    def _update_rolling_summary(self, previous: str, current: str) -> str:
        """Compress prior context into a bounded extractive rolling summary"""

        combined = " ".join(part for part in (previous, current) if part).strip()
        if len(combined) <= self.context_summary_max_chars:
            return combined

        sentences = [
            item.strip() for item in re.split(r"(?<=[.!?])\s+|\n+", combined) if item.strip()
        ]
        if not sentences:
            return combined[-self.context_summary_max_chars :].strip()

        selected: list[str] = []
        for sentence in [*sentences[:2], *sentences[-5:]]:
            if sentence not in selected:
                selected.append(sentence)

        summary = " ".join(selected)
        if len(summary) > self.context_summary_max_chars:
            summary = summary[-self.context_summary_max_chars :]
            first_space = summary.find(" ")
            if first_space > 0:
                summary = summary[first_space + 1 :]

        return summary.strip()
