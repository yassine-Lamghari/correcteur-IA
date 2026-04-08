# Next Steps

## Priority 1

- Implement real GLM-OCR adapter in backend:
  - Use an inference endpoint reachable from backend
  - Add retry, timeout, and output sanitation

## Priority 2

- Add data persistence:
  - exams, questions, scans, ocr results, grades, feedback, translations

## Priority 3

- Add review queue UI in Tkinter and WinForms:
  - low-confidence answer triage
  - human correction commit

## Priority 4

- Add batch and reporting:
  - folder ingestion
  - CSV/PDF exports

## Quality targets

- OCR confidence target: >= 0.90 for auto-accept path
- Grading confidence target: >= 0.85 for auto-score path
- 100% audit trail for human overrides
