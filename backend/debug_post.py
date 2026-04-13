import base64
import io
from PIL import Image, ImageDraw
from app.services.glm_ocr import GLMOCRClient
from app.models.schemas import OCRTask

client = GLMOCRClient()

img = Image.new('RGB', (400, 300), color = (255, 255, 255))
d = ImageDraw.Draw(img)
d.text((10,10), "MATRICULE: 556677", fill=(0,0,0))
d.text((10,40), "1 A", fill=(0,0,0))
d.text((10,60), "2 B", fill=(0,0,0))

buffer = io.BytesIO()
img.save(buffer, format="JPEG")
img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

try:
    res = client.recognize(img_b64, OCRTask.text)
    print("Result ID:", res.student_id)
    print("Result Answers:", res.extracted_answers)
    print("Result Raw Text:", repr(res.raw_text))
except Exception as e:
    import traceback
    traceback.print_exc()
