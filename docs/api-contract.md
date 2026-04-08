# API Contract (v1)

Base URL: http://127.0.0.1:8000

## POST /api/v1/ocr

Request:
- image_base64: string
- task: Text | Formula | Table

Response:
- raw_text: string
- confidence: number [0..1]
- extracted_answers: string[]

## POST /api/v1/grade

Request:
- question:
  - question_id: string
  - type: mcq | short_answer | essay
  - prompt: string
  - max_points: number
  - expected_answer: string?
  - keywords: string[]
- student_answer: string

Response:
- awarded_points: number
- confidence: number [0..1]
- method: string
- needs_human_review: boolean

## POST /api/v1/feedback

Request:
- question
- student_answer
- grade

Response:
- feedback: string

## POST /api/v1/translate

Request:
- text: string
- source_lang: string
- target_lang: string

Response:
- translated_text: string
- provider: string
