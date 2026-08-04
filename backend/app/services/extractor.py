import io
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import docx
import fitz
import pandas as pd
from bs4 import BeautifulSoup
from pydantic import BaseModel

from backend.app.core.exceptions import ExtractionError, OCRRequiredError


class ExtractedPage(BaseModel):
    """Represent text extracted from an individual page"""

    page_number: int
    text: str


class ExtractedDocument(BaseModel):
    """Contain document extraction output"""

    text: str
    pages: list[ExtractedPage]
    metadata: dict[str, Any]


class BaseExtractor(ABC):
    """Define the interface for file text extractors"""

    @abstractmethod
    def extract(self, file_bytes: bytes, filename: str) -> ExtractedDocument:
        """Extract text and metadata from file content"""


class PDFExtractor(BaseExtractor):
    """Extract text from text-based PDF files"""

    def extract(self, file_bytes: bytes, filename: str) -> ExtractedDocument:
        document = None

        try:
            document = fitz.open(stream=file_bytes, filetype="pdf")
            pages: list[ExtractedPage] = []
            full_text_list: list[str] = []

            for page_index, page in enumerate(document):
                page_text = page.get_text("text").strip()
                pages.append(
                    ExtractedPage(
                        page_number=page_index + 1,
                        text=page_text,
                    )
                )

                if page_text:
                    full_text_list.append(page_text)

            full_text = "\n\n".join(full_text_list).strip()
            total_clean_chars = len(full_text.replace(" ", "").replace("\n", ""))

            if total_clean_chars < 30:
                message = (
                    f"PDF document '{filename}' contains little or no "
                    f"extractable text ({total_clean_chars} chars). "
                    "OCR processing is required."
                )
                raise OCRRequiredError(message)

            metadata = {
                "page_count": len(document),
                "author": document.metadata.get("author", ""),
                "title": document.metadata.get("title", ""),
                "format": "PDF",
            }

            return ExtractedDocument(
                text=full_text,
                pages=pages,
                metadata=metadata,
            )
        except OCRRequiredError:
            raise
        except Exception as exc:
            raise ExtractionError(
                f"Failed to extract PDF content from '{filename}': {exc!s}"
            ) from exc
        finally:
            if document is not None:
                document.close()


class DOCXExtractor(BaseExtractor):
    """Extract paragraphs and table rows from DOCX files"""

    def extract(self, file_bytes: bytes, filename: str) -> ExtractedDocument:
        try:
            document = docx.Document(io.BytesIO(file_bytes))
            paragraphs: list[str] = []

            for paragraph in document.paragraphs:
                text = paragraph.text.strip()

                if text:
                    paragraphs.append(text)

            for table in document.tables:
                for row in table.rows:
                    row_text = " | ".join(
                        cell.text.strip() for cell in row.cells if cell.text.strip()
                    )

                    if row_text:
                        paragraphs.append(row_text)

            full_text = "\n\n".join(paragraphs)
            pages = [
                ExtractedPage(
                    page_number=1,
                    text=full_text,
                )
            ]
            metadata = {
                "paragraph_count": len(document.paragraphs),
                "table_count": len(document.tables),
                "format": "DOCX",
            }

            return ExtractedDocument(
                text=full_text,
                pages=pages,
                metadata=metadata,
            )
        except Exception as exc:
            raise ExtractionError(
                f"Failed to extract DOCX content from '{filename}': {exc!s}"
            ) from exc


class TextExtractor(BaseExtractor):
    """Extract plain text from TXT and Markdown files"""

    def extract(self, file_bytes: bytes, filename: str) -> ExtractedDocument:
        try:
            try:
                full_text = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                full_text = file_bytes.decode("latin-1")

            full_text = full_text.strip()
            pages = [
                ExtractedPage(
                    page_number=1,
                    text=full_text,
                )
            ]
            metadata = {"format": Path(filename).suffix.upper().lstrip(".")}

            return ExtractedDocument(
                text=full_text,
                pages=pages,
                metadata=metadata,
            )
        except Exception as exc:
            raise ExtractionError(
                f"Failed to extract text content from '{filename}': {exc!s}"
            ) from exc


class CSVExtractor(BaseExtractor):
    """Extract structured text from CSV files"""

    def extract(self, file_bytes: bytes, filename: str) -> ExtractedDocument:
        try:
            try:
                content = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                content = file_bytes.decode("latin-1")

            dataframe = pd.read_csv(io.StringIO(content))
            lines: list[str] = []

            headers = [str(column) for column in dataframe.columns]
            lines.append("Columns: " + ", ".join(headers))

            for row_index, row in dataframe.iterrows():
                row_text = " | ".join(
                    f"{column}: {value}" for column, value in row.items() if pd.notna(value)
                )
                lines.append(f"Row {row_index + 1}: {row_text}")

            full_text = "\n".join(lines)
            pages = [
                ExtractedPage(
                    page_number=1,
                    text=full_text,
                )
            ]
            metadata = {
                "row_count": len(dataframe),
                "column_count": len(dataframe.columns),
                "format": "CSV",
            }

            return ExtractedDocument(
                text=full_text,
                pages=pages,
                metadata=metadata,
            )
        except Exception as exc:
            raise ExtractionError(
                f"Failed to extract CSV content from '{filename}': {exc!s}"
            ) from exc


class HTMLExtractor(BaseExtractor):
    """Extract visible text from HTML documents"""

    def extract(self, file_bytes: bytes, filename: str) -> ExtractedDocument:
        try:
            try:
                html = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                html = file_bytes.decode("latin-1")

            soup = BeautifulSoup(html, "html.parser")

            removable_tags = [
                "script",
                "style",
                "meta",
                "noscript",
                "header",
                "footer",
            ]

            for tag in soup(removable_tags):
                tag.decompose()

            full_text = soup.get_text(separator="\n", strip=True)
            pages = [
                ExtractedPage(
                    page_number=1,
                    text=full_text,
                )
            ]
            metadata = {
                "title": soup.title.string if soup.title else "",
                "format": "HTML",
            }

            return ExtractedDocument(
                text=full_text,
                pages=pages,
                metadata=metadata,
            )
        except Exception as exc:
            raise ExtractionError(
                f"Failed to extract HTML content from '{filename}': {exc!s}"
            ) from exc


class JSONExtractor(BaseExtractor):
    """Extract formatted text from JSON files"""

    def extract(self, file_bytes: bytes, filename: str) -> ExtractedDocument:
        try:
            try:
                json_text = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                json_text = file_bytes.decode("latin-1")

            data = json.loads(json_text)
            full_text = json.dumps(data, indent=2)
            pages = [
                ExtractedPage(
                    page_number=1,
                    text=full_text,
                )
            ]
            metadata = {"format": "JSON"}

            return ExtractedDocument(
                text=full_text,
                pages=pages,
                metadata=metadata,
            )
        except Exception as exc:
            raise ExtractionError(
                f"Failed to extract JSON content from '{filename}': {exc!s}"
            ) from exc


class ExtractorFactory:
    """Return the appropriate extractor for a filename"""

    @staticmethod
    def get_extractor(filename: str) -> BaseExtractor:
        extension = Path(filename).suffix.lower().lstrip(".")

        extractors: dict[str, type[BaseExtractor]] = {
            "pdf": PDFExtractor,
            "docx": DOCXExtractor,
            "txt": TextExtractor,
            "md": TextExtractor,
            "markdown": TextExtractor,
            "csv": CSVExtractor,
            "html": HTMLExtractor,
            "htm": HTMLExtractor,
            "json": JSONExtractor,
        }

        extractor_class = extractors.get(extension)

        if extractor_class is None:
            raise ExtractionError(f"No extractor registered for file extension '.{extension}'")

        return extractor_class()
