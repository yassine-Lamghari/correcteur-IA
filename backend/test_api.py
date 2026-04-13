import requests
import base64
from PIL import Image, ImageDraw
import io

img = Image.new('RGB', (400, 300), color = (255, 255, 255))
d = ImageDraw.Draw(img)
d.text((10,10), "MATRICULE: 556677", fill=(0,0,0))
d.text((10,40), "1 A", fill=(0,0,0))
d.text((10,60), "2 B", fill=(0,0,0))

buffer = io.BytesIO()
img.save(buffer, format="JPEG")
img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

payload = {
    "subject_id": 1,
    "class_id": 1,
    "submissions": [img_b64],
    "correct_answers": {"1": "A", "2": "B"}
}

try:
    headers = {"Content-Type": "application/json"}
    # Token required? 
    response = requests.post("http://127.0.0.1:8000/api/v1/batch-grade", json=payload, headers=headers)
    print("Status:", response.status_code)
    print("Response:", response.text)
except Exception as e:
    print(e)
