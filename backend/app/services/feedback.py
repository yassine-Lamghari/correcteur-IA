from app.models.schemas import FeedbackRequest


class FeedbackService:
    def generate(self, request: FeedbackRequest) -> str:
        grade = request.grade
        max_points = request.question.max_points
        if grade.awarded_points >= 0.9 * max_points:
            return "Strong answer. Keep this level of precision."
        if grade.awarded_points >= 0.5 * max_points:
            return "Partially correct. Expand key concepts and add more detail."
        return "Answer is insufficient. Revisit the core definition and examples."
