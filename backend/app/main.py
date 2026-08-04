import uuid
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from backend.app.api.router import api_router
from backend.app.config import settings
from backend.app.core.exceptions import RAGException
from backend.app.core.logging import logger, setup_logging
from backend.app.database import init_db

# Setup structured logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB on startup
    await init_db()
    yield


app = FastAPI(
    title="Production Multi-User RAG API",
    description="Backend API for multi-user file ingestion, vector search, and RAG QA",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(RAGException)
async def rag_exception_handler(request: Request, exc: RAGException):
    request_id = getattr(request.state, "request_id", None)
    logger.warning("Application exception", error_code=exc.error_code, message=exc.message, request_id=request_id)
    
    status_code = status.HTTP_400_BAD_REQUEST
    if exc.error_code == "NOT_FOUND":
        status_code = status.HTTP_404_NOT_FOUND
    elif exc.error_code == "STORAGE_ERROR" or exc.error_code == "VECTOR_DB_ERROR":
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

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
    logger.error("Unhandled server exception", error=str(exc), request_id=request_id, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected server error occurred. Please try again later.",
            "request_id": request_id,
            "details": {},
        },
    )


app.include_router(api_router)
