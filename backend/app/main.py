from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.exceptions import AutoGradeException

app = FastAPI(
    title="AutoGrade OCR API",
    version="1.0.0",
    description="Shared backend for Tkinter and WinForms clients. Handles OCR extraction, intelligent grading, and generation of feedback.",
    contact={
        "name": "AutoGrade Support",
        "email": "support@autograde.local",
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

@app.exception_handler(AutoGradeException)
async def autograde_exception_handler(request: Request, exc: AutoGradeException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )

app.include_router(router)


@app.get("/health", tags=["system"])
def health() -> dict:
    return {
        "status": "ok",
        "service": settings.service_name,
        "glm_provider": settings.glm_provider,
    }
