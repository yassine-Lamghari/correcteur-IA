import base64
from app.services.glm_ocr import GLMOCRClient
from app.models.schemas import OCRTask

client = GLMOCRClient()
image_path = r'C:\Users\ASUS ROG\Desktop\yassine\examcorr\testimage.jpeg'

with open(image_path, 'rb') as f:
    b64_str = base64.b64encode(f.read()).decode('utf-8')

print('Processing...')
res = client.recognize(b64_str, OCRTask.text)

print(f'--- ID: {res.student_id} ---')
print(f'--- Name: {res.student_name} ---')
print(f'--- Extracted Answers: {res.extracted_answers} ---')
print('--- Raw Text ---')
print(res.raw_text)

