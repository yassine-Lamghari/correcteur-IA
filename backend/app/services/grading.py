from rapidfuzz import fuzz

from app.models.schemas import GradeResult, QuestionSpec, QuestionType
from app.services.gemini import GeminiCorrector


class GradingService:
    def __init__(self):
        self.gemini_corrector = GeminiCorrector()

    def grade(self, question: QuestionSpec, student_answer: str, use_llm: bool = False) -> GradeResult:
        normalized_answer = student_answer.strip().lower()

        # Option 2: No expected answer, use Gemini
        if use_llm or (not question.expected_answer and not question.keywords and question.type != QuestionType.mcq):
            return self._grade_with_llm(question, student_answer)

        # Option 1: Use exact/fuzzy matching based on expected_answer / keywords
        if question.type == QuestionType.mcq:
            return self._grade_mcq(question, student_answer)
        if question.type == QuestionType.short_answer:
            return self._grade_short(question, student_answer)
        return self._grade_essay(question, student_answer)

    def _grade_with_llm(self, question: QuestionSpec, student_answer: str) -> GradeResult:
        result = self.gemini_corrector.evaluate_answer(
            prompt=question.prompt,
            student_answer=student_answer,
            max_points=question.max_points
        )
        return GradeResult(
            awarded_points=result["score"],
            confidence=result["confidence"],
            method="llm_evaluation",
            needs_human_review=result["confidence"] < 0.8
        )

    def _grade_mcq(self, question: QuestionSpec, student_answer: str) -> GradeResult:
        expected = (question.expected_answer or "").strip().lower()
        if not expected:
            return GradeResult(
                awarded_points=0,
                confidence=0,
                method="mcq_missing_key",
                needs_human_review=True,
            )

        similarity = fuzz.ratio(student_answer, expected) / 100.0
        if student_answer == expected:
            return GradeResult(
                awarded_points=question.max_points,
                confidence=0.98,
                method="mcq_exact",
                needs_human_review=False,
            )

        partial_points = question.max_points * 0.5 if similarity >= 0.8 else 0
        return GradeResult(
            awarded_points=partial_points,
            confidence=similarity,
            method="mcq_fuzzy",
            needs_human_review=similarity < 0.9,
        )

    def _grade_short(self, question: QuestionSpec, student_answer: str) -> GradeResult:
        if not question.keywords:
            return GradeResult(
                awarded_points=0,
                confidence=0,
                method="short_missing_keywords",
                needs_human_review=True,
            )

        matched = 0
        for keyword in question.keywords:
            ratio = fuzz.partial_ratio(keyword.lower(), student_answer) / 100.0
            if ratio >= 0.8:
                matched += 1

        ratio = matched / len(question.keywords)
        awarded = question.max_points * ratio
        return GradeResult(
            awarded_points=round(awarded, 2),
            confidence=round(max(0.45, ratio), 2),
            method="short_keyword_match",
            needs_human_review=ratio < 0.75,
        )

    def _grade_essay(self, question: QuestionSpec, student_answer: str) -> GradeResult:
        # Essays remain semi-automatic: pre-score then mandatory validation.
        length_factor = min(len(student_answer.split()) / 120.0, 1.0)
        awarded = round(question.max_points * 0.6 * length_factor, 2)
        return GradeResult(
            awarded_points=awarded,
            confidence=round(0.5 + 0.3 * length_factor, 2),
            method="essay_prescore",
            needs_human_review=True,
        )
