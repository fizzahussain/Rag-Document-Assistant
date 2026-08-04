import pytest
import fitz
from backend.app.core.exceptions import OCRRequiredError, ValidationError
from backend.app.services.extractor import (
    CSVExtractor,
    ExtractorFactory,
    HTMLExtractor,
    JSONExtractor,
    PDFExtractor,
    TextExtractor,
)


def test_text_extractor():
    extractor = TextExtractor()
    content = "Hello world\nThis is a test document.".encode("utf-8")
    result = extractor.extract(content, "test.txt")
    assert "Hello world" in result.text
    assert len(result.pages) == 1


def test_json_extractor():
    extractor = JSONExtractor()
    content = '{"name": "RAG System", "version": 1.0}'.encode("utf-8")
    result = extractor.extract(content, "data.json")
    assert "RAG System" in result.text


def test_html_extractor():
    extractor = HTMLExtractor()
    content = "<html><head><title>Test</title></head><body><h1>Header</h1><p>Paragraph text</p></body></html>".encode("utf-8")
    result = extractor.extract(content, "page.html")
    assert "Header" in result.text
    assert "Paragraph text" in result.text
    assert "title" in result.metadata


def test_csv_extractor():
    extractor = CSVExtractor()
    content = "name,age\nAlice,30\nBob,25".encode("utf-8")
    result = extractor.extract(content, "data.csv")
    assert "Alice" in result.text
    assert "Columns: name, age" in result.text


def test_pdf_extractor_text():
    # Create an in-memory PDF with text using PyMuPDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Sample PDF Text Content For Testing Purpose")
    pdf_bytes = doc.write()
    doc.close()

    extractor = PDFExtractor()
    result = extractor.extract(pdf_bytes, "sample.pdf")
    assert "Sample PDF Text Content" in result.text
    assert len(result.pages) == 1


def test_pdf_extractor_scanned_detect():
    # Create an empty page PDF (simulating image-only/scanned PDF without text)
    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.write()
    doc.close()

    extractor = PDFExtractor()
    with pytest.raises(OCRRequiredError):
        extractor.extract(pdf_bytes, "scanned.pdf")


def test_extractor_factory():
    assert isinstance(ExtractorFactory.get_extractor("doc.pdf"), PDFExtractor)
    assert isinstance(ExtractorFactory.get_extractor("file.txt"), TextExtractor)
    assert isinstance(ExtractorFactory.get_extractor("data.json"), JSONExtractor)
