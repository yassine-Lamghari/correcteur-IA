import traceback
from fastapi import Request
from fastapi.exceptions import ResponseValidationError
from fastapi.responses import JSONResponse

class AutoGradeException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class OCRError(AutoGradeException):
    def __init__(self, message: str):
        super().__init__(message, status_code=502)

class GradingError(AutoGradeException):
    def __init__(self, message: str):
        super().__init__(message, status_code=500)

class AIServiceError(AutoGradeException):
    def __init__(self, message: str):
        super().__init__(message, status_code=500)

async def autograde_exception_handler(request: Request, exc: AutoGradeException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )

async def validation_exception_handler(request: Request, exc: ResponseValidationError):
    print("RESPONSE VALIDATION ERROR:", exc.errors())
    return JSONResponse(status_code=500, content={"detail": exc.errors()})

async def global_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(status_code=500, content={"detail": str(exc)})
