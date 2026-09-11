from pathlib import Path
import io

import fitz
from PIL import Image


ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_PAGES = 3


def validate_file(filename: str, content: bytes) -> dict:
    """Validate uploaded document before processing."""

    extension = Path(filename).suffix.lower()

    # Check file extension
    if extension not in ALLOWED_EXTENSIONS:
        return {
            "valid": False,
            "reason": "Unsupported file type. Only PDF, JPG and PNG are allowed.",
            "extension": extension,
        }

    # Check empty file
    if not content:
        return {
            "valid": False,
            "reason": "File is empty.",
            "extension": extension,
        }

    # Validate PDF
    if extension == ".pdf":
        return validate_pdf(content)

    # Validate image
    return validate_image(content, extension)


def validate_pdf(content: bytes) -> dict:
    try:
        pdf = fitz.open(stream=content, filetype="pdf")

        page_count = len(pdf)

        if page_count > MAX_PAGES:
            pdf.close()
            return {
                "valid": False,
                "reason": f"PDF exceeds maximum allowed pages ({MAX_PAGES}).",
                "pages": page_count,
            }

        if page_count == 0:
            pdf.close()
            return {
                "valid": False,
                "reason": "PDF contains no pages.",
                "pages": 0,
            }

        pdf.close()

        return {
            "valid": True,
            "file_type": "pdf",
            "pages": page_count,
        }

    except Exception:
        return {
            "valid": False,
            "reason": "Corrupted or unreadable PDF.",
        }


def validate_image(content: bytes, extension: str) -> dict:
    try:
        image = Image.open(io.BytesIO(content))
        image.verify()

        return {
            "valid": True,
            "file_type": extension.replace(".", ""),
            "pages": 1,
        }

    except Exception:
        return {
            "valid": False,
            "reason": "Corrupted or unreadable image.",
        }