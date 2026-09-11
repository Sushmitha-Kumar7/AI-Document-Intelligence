import os
import uuid

from app.repositories.document_repository import create_document


STORAGE_DIR = "storage/documents"


def save_document(
    db,
    filename: str,
    content: bytes,
    document_type: str,
    processing_status: str
):
    os.makedirs(STORAGE_DIR, exist_ok=True)

    file_extension = os.path.splitext(filename)[1]
    unique_filename = f"{uuid.uuid4().hex}{file_extension}"

    file_path = os.path.join(
        STORAGE_DIR,
        unique_filename
    )

    with open(file_path, "wb") as f:
        f.write(content)

    document = create_document(
        db=db,
        filename=filename,
        document_type=document_type,
        file_path=file_path,
        processing_status=processing_status
    )

    return document