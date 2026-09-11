from sqlalchemy.orm import Session

from app.models.document import Document


def create_document(
    db: Session,
    filename: str,
    document_type: str,
    file_path: str,
    processing_status: str
):
    document = Document(
        filename=filename,
        document_type=document_type,
        file_path=file_path,
        processing_status=processing_status
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return document


def get_documents(db: Session):
    return (
        db.query(Document)
        .order_by(Document.uploaded_at.desc())
        .all()
    )