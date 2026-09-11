import io
import os
import shutil
import fitz
import pytesseract
from PIL import Image
# Configure Tesseract for Windows and Linux/Render
if os.name == "nt":
    windows_tesseract = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    if os.path.exists(windows_tesseract):
        pytesseract.pytesseract.tesseract_cmd = windows_tesseract

else:
    linux_tesseract = shutil.which("tesseract")

    if linux_tesseract:
        pytesseract.pytesseract.tesseract_cmd = linux_tesseract

def extract_text(filename: str, content: bytes) -> dict:
    """
    Extract text from PDF or image files.

    PDFs:
        - Try native PDF text extraction first.
        - Use OCR for pages with little/no text.

    Images:
        - Use OCR directly.
    """

    filename_lower = filename.lower()

    if filename_lower.endswith(".pdf"):
        return extract_pdf_text(content)

    return extract_image_text(content)


def extract_pdf_text(content: bytes) -> dict:
    try:
        pdf = fitz.open(stream=content, filetype="pdf")

        pages = []
        full_text = []

        for page_number, page in enumerate(pdf, start=1):
            text = page.get_text("text").strip()

            if text:
                extraction_method = "native_text"
            else:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                image_bytes = pix.tobytes("png")

                image = Image.open(io.BytesIO(image_bytes))
                text = pytesseract.image_to_string(image).strip()

                extraction_method = "ocr"

            pages.append({
                "page_number": page_number,
                "text": text,
                "extraction_method": extraction_method
            })

            full_text.append(text)

        pdf.close()

        combined_text = "\n".join(full_text).strip()

        return {
            "success": True,
            "text": combined_text,
            "pages": pages
        }

    except Exception as e:
        return {
            "success": False,
            "text": "",
            "pages": [],
            "error": str(e)
        }


def extract_image_text(content: bytes) -> dict:
    try:
        image = Image.open(io.BytesIO(content))

        text = pytesseract.image_to_string(image).strip()

        return {
            "success": True,
            "text": text,
            "pages": [
                {
                    "page_number": 1,
                    "text": text,
                    "extraction_method": "ocr"
                }
            ]
        }

    except Exception as e:
        return {
            "success": False,
            "text": "",
            "pages": [],
            "error": str(e)
        }