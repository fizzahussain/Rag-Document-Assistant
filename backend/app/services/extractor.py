import io
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import docx
import fitz  # PyMuPDF
import pandas as pd
from bs4 import BeautifulSoup
from pydantic import BaseModel

from backend.app.core.exceptions import ExtractionError, OCRRequiredError


class ExtractedPage(BaseModel):
    """Represents text extracted from an individual page."""

    page_number: int
    text: str


class ExtractedDocument(BaseModel):
    """Container for document extraction output."""

    text: str
    pages: list[ExtractedPage]
    metadata: dict[str, Any]


class BaseExtractor(ABC):
    """Abstract interface for file text extractors."""

    @abstractmethod
    def extract(self, file_bytes: bytes, filename: str) -> ExtractedDocument:
        """Extracts text and page metadata from file content bytes."""


class PDFExtractor(BaseExtractor):
    """Extracts text from text-based PDFs using PyMuPDF and checks for image-only/scanned PDFs."""

    def extract(self, file_bytes: bytes, filename: str) -> ExtractedDocument:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            pages: list[ExtractedPage] = []
            full_text_list: list[str] = []

            for page_idx, page in enumerate(doc):
                page_text = page.get_text("text").strip()
                pages.append(ExtractedPage(page_number=page_idx + 1, text=page_text))
                if page_text:
                    full_text_list.append(page_text)

            full_text = "\n\n".join(full_text_list).strip()

            # Check if PDF contains little or no text (scanned PDF detection)
            total_clean_chars = len(full_text.replace(" ", "").replace("\n", ""))
            if total_clean_chars < 30:
                raise OCRRequiredError(
                    f"PDF document '{filename}' contains little or no extractable text ({total_clean_chars} chars). OCR processing is required."
                )

            metadata = {
                "page_count": len(doc),
                "author": doc.metadata.get("author", ""),
                "title": doc.metadata.get("title", ""),
                "format": "PDF",
            }
            doc.close()

            return ExtractedDocument(text=full_text, pages=pages, metadata=metadata)
        except OCRRequiredError:
            raise
        except Exception as e:
            raise ExtractionError(
                f"Failed to extract PDF content from '{filename}': {e!s}"
            )


class DOCXExtractor(BaseExtractor):
    """Extracts text paragraphs and table rows from DOCX files."""

    def extract(self, file_bytes: bytes, filename: str) -> ExtractedDocument:
        try:
            doc_file = io.BytesIO(file_bytes)
            document = docx.Document(doc_file)

            paragraphs: list[str] = []
            for p in document.paragraphs:
                if p.text.strip():
                    paragraphs.append(p.text.strip())

            for table in document.tables:
                for row in table.rows:
                    row_text = " | ".join(
                        cell.text.strip() for cell in row.cells if cell.text.strip()
                    )
                    if row_text:
                        paragraphs.append(row_text)

            full_text = "\n\n".join(paragraphs)

            metadata = {
                "paragraph_count": len(document.paragraphs),
                "table_count": len(document.tables),
                "format": "DOCX",
            }
            # DOCX does not have page breaks easily without layout engines; default to 1 page
            pages = [ExtractedPage(page_number=1, text=full_text)]

            return ExtractedDocument(text=full_text, pages=pages, metadata=metadata)
        except Exception as e:
            raise ExtractionError(
                f"Failed to extract DOCX content from '{filename}': {e!s}"
            )


class TextExtractor(BaseExtractor):
    """Extracts plain text from TXT and Markdown files."""

    def extract(self, file_bytes: bytes, filename: str) -> ExtractedDocument:
        try:
            try:
                full_text = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                full_text = file_bytes.decode("latin-1")

            full_text = full_text.strip()
            pages = [ExtractedPage(page_number=1, text=full_text)]
            metadata = {"format": Path(filename).suffix.upper().lstrip(".")}

            return ExtractedDocument(text=full_text, pages=pages, metadata=metadata)
        except Exception as e:
            raise ExtractionError(
                f"Failed to extract text content from '{filename}': {e!s}"
            )


class CSVExtractor(BaseExtractor):
    """Extracts structured text representations from CSV files."""

    def extract(self, file_bytes: bytes, filename: str) -> ExtractedDocument:
        try:
            try:
                content_str = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                content_str = file_bytes.decode("latin-1")

            df = pd.read_csv(io.StringIO(content_str))
            lines: list[str] = []

            # Convert header
            headers = [str(col) for col in df.columns]
            lines.append("Columns: " + ", ".join(headers))

            # Format rows as text
            for idx, row in df.iterrows():
                row_str = " | ".join(
                    f"{col}: {val}" for col, val in row.items() if pd.notna(val)
                )
                lines.append(f"Row {idx + 1}: {row_str}")

            full_text = "\n".join(lines)
            pages = [ExtractedPage(page_number=1, text=full_text)]
            metadata = {
                "row_count": len(df),
                "column_count": len(df.columns),
                "format": "CSV",
            }

            return ExtractedDocument(text=full_text, pages=pages, metadata=metadata)
        except Exception as e:
            raise ExtractionError(
                f"Failed to extract CSV content from '{filename}': {e!s}"
            )


class HTMLExtractor(BaseExtractor):
    """Extracts main body text from HTML documents while removing tags and scripts."""

    def extract(self, file_bytes: bytes, filename: str) -> ExtractedDocument:
        try:
            try:
                html_str = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                html_str = file_bytes.decode("latin-1")

            soup = BeautifulSoup(html_str, "html.parser")

            # Remove scripts, styles, metadata
            for tag in soup(
                ["script", "style", "meta", "noscript", "header", "footer"]
            ):
                tag.decompose()

            full_text = soup.get_text(separator="\n", strip=True)
            pages = [ExtractedPage(page_number=1, text=full_text)]
            metadata = {
                "title": soup.title.string if soup.title else "",
                "format": "HTML",
            }

            return ExtractedDocument(text=full_text, pages=pages, metadata=metadata)
        except Exception as e:
            raise ExtractionError(
                f"Failed to extract HTML content from '{filename}': {e!s}"
            )


class JSONExtractor(BaseExtractor):
    """Extracts text content from JSON files."""

    def extract(self, file_bytes: bytes, filename: str) -> ExtractedDocument:
        try:
            try:
                json_str = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                json_str = file_bytes.decode("latin-1")

            data = json.loads(json_str)
            full_text = json.dumps(data, indent=2)
            pages = [ExtractedPage(page_number=1, text=full_text)]
            metadata = {"format": "JSON"}

            return ExtractedDocument(text=full_text, pages=pages, metadata=metadata)
        except Exception as e:
            raise ExtractionError(
                f"Failed to extract JSON content from '{filename}': {e!s}"
            )


class ExtractorFactory:
    """Factory class to return the appropriate extractor for a given filename."""

    @staticmethod
    def get_extractor(filename: str) -> BaseExtractor:
        ext = Path(filename).suffix.lower().lstrip(".")
        if ext == "pdf":
            return PDFExtractor()
        elif ext == "docx":
            return DOCXExtractor()
        elif ext in ["txt", "md", "markdown"]:
            return TextExtractor()
        elif ext == "csv":
            return CSVExtractor()
        elif ext in ["html", "htm"]:
            return HTMLExtractor()
        elif ext == "json":
            return JSONExtractor()
        else:
            raise ExtractionError(
                f"No extractor registered for file extension '.{ext}'"
            )
