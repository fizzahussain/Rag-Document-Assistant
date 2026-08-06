import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.router import api_router
from backend.app.config import settings
from backend.app.core.exceptions import RAGException
from backend.app.core.logging import logger, setup_logging
from backend.app.database import close_database

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_database()


app = FastAPI(
    title="Multi-User RAG API",
    description="File ingestion, retrieval, and grounded question answering",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.ALLOWED_ORIGINS),
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(RAGException)
async def rag_exception_handler(request: Request, exc: RAGException):
    request_id = getattr(request.state, "request_id", None)
    logger.warning(
        "Application exception",
        error_code=exc.error_code,
        request_id=request_id,
    )
    status_code = status.HTTP_400_BAD_REQUEST
    if exc.error_code == "NOT_FOUND":
        status_code = status.HTTP_404_NOT_FOUND
    elif exc.error_code in {"STORAGE_ERROR", "VECTOR_DB_ERROR"}:
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "request_id": request_id,
            "details": exc.details,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    logger.exception("Unhandled server exception", request_id=request_id)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected server error occurred",
            "request_id": request_id,
            "details": {},
        },
    )


app.include_router(api_router)
