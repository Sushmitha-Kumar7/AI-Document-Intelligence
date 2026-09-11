from fastapi.responses import FileResponse
import os
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session

from app.services.document_validation_service import validate_file
from app.services.ocr_service import extract_text
from app.services.extraction_service import extract_fields
from app.services.financial_validation_service import (
    validate_financial_data
)

from app.core.database import get_db
from app.services.document_service import save_document


router = APIRouter()


ALLOWED_TYPES = {
    "invoice",
    "balance_sheet",
    "profit_and_loss",
    "cash_flow_statement"
}


@router.post("/process")
async def process_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    db: Session = Depends(get_db)
):
    # 1. Validate document type
    if document_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid document_type"
        )

    # 2. Read uploaded file
    content = await file.read()

    # 3. Validate file
    validation_result = validate_file(
        file.filename,
        content
    )

    # 4. Stop if file validation fails
    if not validation_result["valid"]:
        return {
            "document_name": file.filename,
            "document_type": document_type,
            "processing_status": "FAILED",
            "file_validation": validation_result
        }

    # 5. Extract text
    text_extraction_result = extract_text(
        file.filename,
        content
    )

    # 6. Stop if text extraction fails
    if not text_extraction_result["success"]:
        return {
            "document_name": file.filename,
            "document_type": document_type,
            "processing_status": "FAILED",
            "file_validation": validation_result,
            "text_extraction": text_extraction_result
        }

    # 7. Extract structured fields using OpenAI
    ai_extraction_result = extract_fields(
        document_type,
        text_extraction_result["text"],
        content,
        file.filename
    )

    # 8. Stop if AI extraction fails
    if not ai_extraction_result["success"]:
        return {
            "document_name": file.filename,
            "document_type": document_type,
            "processing_status": "AI_EXTRACTION_FAILED",
            "file_validation": validation_result,
            "text_extraction": text_extraction_result,
            "ai_extraction": ai_extraction_result
        }

    # 9. Financial validation
    financial_validation_result = validate_financial_data(
        document_type,
        ai_extraction_result["data"]
    )

    # 10. Determine processing status
    overall_status = financial_validation_result["overall_status"]

    if overall_status == "FAIL":
        processing_status = "FAILED_VALIDATION"

    elif overall_status == "NOT_APPLICABLE":
        processing_status = "NOT_APPLICABLE"

    else:
        processing_status = "PASS"

    # 11. Save successfully processed document
    saved_document = save_document(
        db=db,
        filename=file.filename,
        content=content,
        document_type=document_type,
        processing_status=processing_status
    )

    # 12. Return complete processing result
    return {
        "document_name": file.filename,
        "document_type": document_type,
        "processing_status": processing_status,

        "document_storage": {
            "id": saved_document.id,
            "file_path": saved_document.file_path,
            "uploaded_at": saved_document.uploaded_at
        },

        "file_validation": validation_result,
        "text_extraction": text_extraction_result,
        "ai_extraction": ai_extraction_result,
        "financial_validation": financial_validation_result
    }


@router.get("")
def list_documents(db: Session = Depends(get_db)):
    from app.repositories.document_repository import get_documents

    documents = get_documents(db)

    return {
        "documents": [
            {
                "id": document.id,
                "filename": document.filename,
                "document_type": document.document_type,
                "file_path": document.file_path,
                "processing_status": document.processing_status,
                "uploaded_at": document.uploaded_at
            }
            for document in documents
        ]
    }

@router.get("/file/{document_id}")
def open_document_file(
    document_id: int,
    db: Session = Depends(get_db)
):
    from app.models.document import Document

    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    file_path = os.path.abspath(document.file_path)

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="Stored file not found"
        )

    return FileResponse(
    path=file_path,
    headers={
        "Content-Disposition": f'inline; filename="{document.filename}"'
    }
)
@router.get("/{document_name}")
def get_document(document_name: str):
    return {
        "document_name": document_name,
        "message": "Document lookup"
    }