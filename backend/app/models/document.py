from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)

    filename = Column(String, nullable=False)
    document_type = Column(String, nullable=False)
    file_path = Column(String, nullable=False)

    processing_status = Column(String, nullable=False)

    uploaded_at = Column(
        DateTime,
        default=datetime.utcnow
    )