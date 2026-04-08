# Architecture - AutoGrade OCR

## Shared backend

The backend is the single source of business logic and model orchestration.

Flow:
1. Scan image input
2. OCR (GLM adapter)
3. Structured answer extraction
4. Partial auto-grading
5. Feedback generation
6. Translation

## Desktop clients

Two clients consume the same API:
- Tkinter client (Python)
- WinForms client (C#)

This ensures parity and avoids duplicated grading rules.

## GLM-OCR runtime strategy

Given the current GLM-OCR demo stack dependencies (GPU Linux), production strategy is:
- Run OCR inference in a Linux GPU service
- Keep Windows desktop clients as thin clients
- Route OCR through backend adapter

## Human-in-the-loop

Semi-automatic grading policy:
- MCQ: exact/fuzzy with high confidence threshold
- Short answer: keyword-based scoring with review threshold
- Essay: pre-score only, always reviewable

## Next technical milestones

1. Replace mock OCR output with real remote GLM inference call.
2. Add persistence (exam/session/review queue).
3. Add batch pipeline for multi-page scans.
4. Add export generation and reporting.
