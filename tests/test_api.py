from types import SimpleNamespace
from fastapi.testclient import TestClient
from PIL import Image
import io

from app.main import app
import app.api.routes.documents as documents

client = TestClient(app)


def make_test_image():
    image = Image.new("RGB", (100, 100), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_process_document():
    documents.validate_file = lambda filename, content: {
        "valid": True,
        "file_type": "png"
    }

    documents.extract_text = lambda filename, content: {
        "success": True,
        "text": "Invoice Number: INV001 Total: 1180"
    }

    documents.extract_fields = lambda *args: {
        "success": True,
        "data": {
            "fields": {
                "Subtotal": {"value": "1000"},
                "Tax": {"value": "180"},
                "Total": {"value": "1180"}
            },
            "line_items": []
        }
    }

    # IMPORTANT: directly replace the validator used by documents.py
    documents.validate_financial_data = lambda document_type, data: {
        "overall_status": "PASS",
        "checks": []
    }

    documents.save_document = lambda **kwargs: SimpleNamespace(
        id=1,
        file_path="storage/documents/test.png",
        uploaded_at=None
    )

    response = client.post(
        "/api/v1/documents/process",
        files={
            "file": (
                "test.png",
                make_test_image(),
                "image/png"
            )
        },
        data={
            "document_type": "invoice"
        }
    )

    assert response.status_code == 200

    result = response.json()

    assert result["processing_status"] == "PASS"
    assert result["document_type"] == "invoice"
    assert result["ai_extraction"]["success"] is True
    assert result["financial_validation"]["overall_status"] == "PASS"