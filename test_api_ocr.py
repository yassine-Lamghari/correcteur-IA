import base64
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import numpy as np
import cv2
import pytesseract

# Configure Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Create a test image
print("Creating test image...")
img = Image.new('RGB', (400, 200), color='white')
draw = ImageDraw.Draw(img)

try:
    font = ImageFont.truetype("arial.ttf", 20)
except:
    font = ImageFont.load_default()

# Draw exam content
draw.text((10, 10), "ID: 20234567", fill='black', font=font)
draw.text((10, 40), "Nom: Mohammed Ali", fill='black', font=font)
draw.text((10, 70), "1 A", fill='black', font=font)
draw.text((10, 100), "2 B", fill='black', font=font)
draw.text((10, 130), "3 C", fill='black', font=font)
draw.text((10, 160), "4 D", fill='black', font=font)

# Convert to base64
buffer = BytesIO()
img.save(buffer, format='JPEG', quality=95)
img_bytes = buffer.getvalue()
b64_string = base64.b64encode(img_bytes).decode('utf-8')

# Test the API endpoint
print("\nTesting API endpoint...")
try:
    # First, try without auth (some endpoints might not require it)
    url = "http://127.0.0.1:8000/api/v1/ocr"
    payload = {
        "image_base64": b64_string,
        "task": "Text"
    }

    print(f"Sending request to {url}")
    print(f"Payload size: {len(str(payload))} bytes")

    response = requests.post(url, json=payload, timeout=30)
    print(f"Status code: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print("\nAPI Response:")
        print(f"  Raw text: {result.get('raw_text', 'N/A')}")
        print(f"  Student ID: {result.get('student_id', 'N/A')}")
        print(f"  Student name: {result.get('student_name', 'N/A')}")
        print(f"  Extracted answers: {result.get('extracted_answers', 'N/A')}")
        print(f"  Confidence: {result.get('confidence', 'N/A')}")
    else:
        print(f"Error: {response.text}")

except requests.exceptions.RequestException as e:
    print(f"Request error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
    import traceback
    traceback.print_exc()

# Test with auth if needed
print("\n\nTrying with authentication...")
try:
    # First login with the test user
    login_url = "http://127.0.0.1:8000/api/v1/auth/login"
    login_data = {"username": "testuser", "password": "testpass123"}

    print("Attempting login...")
    login_response = requests.post(login_url, data=login_data, timeout=30)
    print(f"Login status: {login_response.status_code}")

    if login_response.status_code == 200:
        token = login_response.json().get("access_token")
        print("Login successful!")

        # Now test OCR with auth
        headers = {"Authorization": f"Bearer {token}"}
        ocr_response = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"\nOCR with auth - Status: {ocr_response.status_code}")

        if ocr_response.status_code == 200:
            result = ocr_response.json()
            print("API Response with auth:")
            print(f"  Raw text: {result.get('raw_text', 'N/A')}")
            print(f"  Student ID: {result.get('student_id', 'N/A')}")
            print(f"  Student name: {result.get('student_name', 'N/A')}")
            print(f"  Extracted answers: {result.get('extracted_answers', 'N/A')}")
            print(f"  Confidence: {result.get('confidence', 'N/A')}")
        else:
            print(f"OCR failed: {ocr_response.text}")
    else:
        print(f"Login failed: {login_response.text}")

except Exception as e:
    print(f"Auth test error: {e}")