from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError, ResponseValidationError

from app.api.routes import router
from app.core.config import settings
from app.core.exceptions import (
    AutoGradeException,
    autograde_exception_handler,
    validation_exception_handler,
    global_exception_handler,
)

app = FastAPI(
    title="AutoGrade OCR API",
    version="1.0.0",
    description="Shared backend for Tkinter and WinForms clients. Handles OCR extraction, intelligent grading, and generation of feedback.",
    contact={
        "name": "AutoGrade Support",
    }
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AutoGradeException, autograde_exception_handler)
app.add_exception_handler(ResponseValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

app.include_router(router)


@app.get("/health", tags=["system"])
def health() -> dict:
    return {
        "status": "ok",
        "service": settings.service_name,
        "glm_provider": settings.glm_provider,
        # Aide au débogage : si absent, le client pointe vers un backend trop ancien (404 sur /courses/*).
        "api_features": {"courses_generate": True, "exams_generate": True},
    }
