namespace AutoGrade.WinForms.Models;

public sealed record QuestionSpec(
    string question_id,
    string type,
    string prompt,
    double max_points,
    string expected_answer,
    List<string> keywords
);

public sealed record OcrResponse(string raw_text, double confidence, List<string> extracted_answers);

public sealed record GradeResponse(double awarded_points, double confidence, string method, bool needs_human_review);

public sealed record FeedbackResponse(string feedback);

public sealed record TranslateResponse(string translated_text, string provider);
