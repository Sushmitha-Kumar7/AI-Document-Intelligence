from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.routes.documents import router as documents_router
from app.core.database import Base, engine
from app.models.document import Document
from pathlib import Path

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Intelligent Document Extraction API",
    description="AI-powered financial document extraction and validation platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_PATH = PROJECT_ROOT / "frontend"

app.mount(
    "/",
    StaticFiles(directory=str(FRONTEND_PATH), html=True),
    name="frontend"
)