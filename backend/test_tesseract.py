import pytesseract
import sys
from PIL import Image, ImageDraw

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

print("Testing Tesseract...")
try:
    print("Tesseract Version: ", pytesseract.get_tesseract_version())
    
    img = Image.new('RGB', (200, 100), color = (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((10,10), "MATRICULE: 12345", fill=(0,0,0))
    d.text((10,40), "1 A", fill=(0,0,0))
    
    text = pytesseract.image_to_string(img)
    print("Extracted Text:", repr(text))
except Exception as e:
    import traceback
    print(f"Error during OCR extraction:\n")
    traceback.print_exc()
