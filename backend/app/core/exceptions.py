class AutoGradeException(Exception):
    """Base exception for AutoGrade application."""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class OCRError(AutoGradeException):
    """Raised when the OCR service fails."""
    def __init__(self, message: str):
        super().__init__(message, status_code=502)

class GradingError(AutoGradeException):
    """Raised when the grading process fails."""
    def __init__(self, message: str):
        super().__init__(message, status_code=500)

class AIServiceError(AutoGradeException):
    """Raised when an external AI service fails (like Gemini)."""
    def __init__(self, message: str):
        super().__init__(message, status_code=502)

class ValidationError(AutoGradeException):
    """Raised when there is a data validation error."""
    def __init__(self, message: str):
        super().__init__(message, status_code=400)
