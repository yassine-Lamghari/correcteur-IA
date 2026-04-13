import base64
import sys
import logging
from app.services.glm_ocr import GLMOCRClient

logging.basicConfig(level=logging.DEBUG)

image_path = r'C:\Users\ASUS ROG\Desktop\yassine\examcorr\testimage.jpeg'
with open(image_path, 'rb') as f:
    b64 = base64.b64encode(f.read()).decode('utf-8')

client = GLMOCRClient()
result = client.recognize(b64, task="Task")
print('\n--- RESULTAT FINAL ---')
print('Texte brut:')
print(result.raw_text)
print('\nÉtudiant ID:', result.student_id)
print('Étudiant Name:', result.student_name)
print('Réponses extraites:', result.extracted_answers)
print('Confiance:', result.confidence)
