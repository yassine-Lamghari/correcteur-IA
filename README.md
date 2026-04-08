# AutoGrade OCR

Initial implementation for semi-automatic exam correction with:
- OCR of scanned copies
- Extraction of typed/handwritten answers
- Partial auto-grading
- Feedback generation
- Translation of instructions/corrections
- Dual clients: Tkinter and WinForms

## Architecture

- Shared backend: FastAPI service in `backend/`
- Python desktop client: Tkinter in `tkinter_client/`
- C# desktop client: WinForms in `winforms_client/`

Both clients call the same backend contract (`/api/v1/ocr`, `/api/v1/grade`, `/api/v1/feedback`, `/api/v1/translate`).

## GLM-OCR integration choice

Target OCR model: https://huggingface.co/spaces/prithivMLmods/GLM-OCR-Demo

Current backend adapter contains a stable placeholder extractor to keep the whole product flow testable.
Next step is wiring a real GLM inference endpoint (Linux GPU host recommended).

## Quick start

### 1) Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 2) Tkinter client

```bash
cd tkinter_client
pip install -r requirements.txt
python main.py
```

### 3) WinForms client

```bash
cd winforms_client
# open AutoGrade.WinForms.sln in Visual Studio and run
```

## Current scope

Implemented:
- Backend contracts and service modules
- OCR endpoint and answer extraction flow
- Partial grading for MCQ / short answers / essay pre-score
- Feedback and translation endpoints
- Tkinter app connected to backend
- WinForms app connected to backend

Pending (next iterations):
- Real GLM-OCR remote inference connector
- Batch processing and review queue persistence
- Report export (PDF/CSV)
- Authentication and audit trail
