import io
import fitz
from PIL import Image

from backend.app.services.document_validation_service import validate_file


def test_valid_png():
    image = Image.new("RGB", (100, 100), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    result = validate_file("test.png", buffer.getvalue())

    assert result["valid"] is True
    assert result["file_type"] == "png"


def test_unsupported_file_type():
    result = validate_file("test.txt", b"hello")

    assert result["valid"] is False
    assert "Unsupported file type" in result["reason"]


def test_empty_file():
    result = validate_file("test.pdf", b"")

    assert result["valid"] is False
    assert result["reason"] == "File is empty."


def test_valid_pdf():
    pdf = fitz.open()
    pdf.new_page()
    pdf_bytes = pdf.tobytes()
    pdf.close()

    result = validate_file("test.pdf", pdf_bytes)

    assert result["valid"] is True
    assert result["file_type"] == "pdf"
    assert result["pages"] == 1


def test_corrupted_pdf():
    result = validate_file("test.pdf", b"not a real pdf")

    assert result["valid"] is False
    assert result["reason"] == "Corrupted or unreadable PDF."