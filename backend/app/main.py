from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.documents import router as documents_router
from app.core.database import Base, engine
from app.models.document import Document
from fastapi.staticfiles import StaticFiles
from pathlib import Path
Base.metadata.create_all(bind=engine)
app = FastAPI(
    title="Intelligent Document Extraction API",
    description="AI-powered financial document extraction and validation platform",
    version="1.0.0"
)
STORAGE_PATH = Path(__file__).resolve().parent.parent / "storage"

app.mount(
    "/storage",
    StaticFiles(directory=str(STORAGE_PATH)),
    name="storage"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5501",
        "http://localhost:5501"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    documents_router,
    prefix="/api/v1/documents",
    tags=["Documents"]
)

@app.get("/api/v1/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "document-intelligence-api"
    }