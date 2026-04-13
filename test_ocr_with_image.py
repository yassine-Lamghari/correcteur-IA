import base64
import os
import pytesseract
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np

# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Test OCR pipeline with base64 encoding/decoding
def test_ocr_pipeline():
    print("=== Test OCR Pipeline ===")

    # 1. Create a test image
    print("\n1. Creating test image...")
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()

    # Draw typical exam content
    draw.text((10, 10), "ID: 20234567", fill='black', font=font)
    draw.text((10, 40), "Nom: Mohammed Ali", fill='black', font=font)
    draw.text((10, 70), "1 A", fill='black', font=font)
    draw.text((10, 100), "2 B", fill='black', font=font)
    draw.text((10, 130), "3 C", fill='black', font=font)
    draw.text((10, 160), "4 D", fill='black', font=font)

    # 2. Save to bytes and encode to base64
    print("\n2. Encoding to base64...")
    from io import BytesIO
    buffer = BytesIO()
    img.save(buffer, format='JPEG', quality=95)
    img_bytes = buffer.getvalue()
    b64_string = base64.b64encode(img_bytes).decode('utf-8')
    print(f"   Base64 length: {len(b64_string)}")

    # 3. Decode base64 back to image
    print("\n3. Decoding from base64...")
    clean_b64 = b64_string.split(",", 1)[1] if "," in b64_string else b64_string
    decoded_data = base64.b64decode(clean_b64)
    decoded_image = Image.open(BytesIO(decoded_data))

    # 4. Preprocess and OCR
    print("\n4. Preprocessing and OCR...")
    # Convert to grayscale
    img_array = np.array(decoded_image)
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

    # Extract text with Tesseract
    raw_text = pytesseract.image_to_string(gray, lang='eng+fra')
    print(f"\n   Extracted text:\n{raw_text}")

    # 5. Parse answers
    print("\n5. Parsing answers...")
    answers = {}
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    import re
    ocr_map = {'8': 'B', '0': 'D', '4': 'A', '1': 'I', '5': 'S', '6': 'G', '2': 'Z'}

    for line in lines:
        print(f"   Processing line: '{line}'")

        # Match patterns
        match_answer = re.search(r"^\s*(?:\|\s*)?(?:(?:Q|Question)\s*)?(?:\*\*)?\s*(\d+)\s*(?:\*\*)?[\s:\|\.\-\)]*(.*?)\s*(?:\|\s*)?(?:\*)?$", line, flags=re.IGNORECASE)
        simple_answer = re.search(r"^\s*(\d+)\s*([A-Da-d])\s*$", line.strip())

        if match_answer:
            q_num_raw = match_answer.group(1)
            ans_raw = match_answer.group(2).strip().upper()
            print(f"     Found pattern 1 - Q{q_num_raw}: '{ans_raw}'")

            if not ans_raw and len(q_num_raw) > 1:
                ans_raw = q_num_raw[-1]
                q_num_raw = q_num_raw[:-1]
                print(f"     Split last char - Q{q_num_raw}: '{ans_raw}'")

            if ans_raw:
                q_num = str(int(q_num_raw))
                if ans_raw in ocr_map:
                    ans_raw = ocr_map[ans_raw]
                answers[q_num] = ans_raw
        elif simple_answer:
            q_num_raw = simple_answer.group(1)
            ans_raw = simple_answer.group(2).upper()
            print(f"     Found pattern 2 - Q{q_num_raw}: '{ans_raw}'")

            q_num = str(int(q_num_raw))
            if ans_raw in ocr_map:
                ans_raw = ocr_map[ans_raw]
            answers[q_num] = ans_raw

    print(f"\n   Final answers: {answers}")

    # 6. Test with a real image if available
    print("\n=== Testing with real images ===")
    test_dirs = [
        r"C:\Users\ASUS ROG\Desktop\yassine\examcorr\test_images",
        r"C:\Users\ASUS ROG\Desktop\yassine\examcorr\sample_images",
        r"C:\Users\ASUS ROG\Desktop\yassine\examcorr\images"
    ]

    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            print(f"\nLooking in {test_dir}...")
            for file in os.listdir(test_dir):
                if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    print(f"\nTesting real image: {file}")
                    try:
                        full_path = os.path.join(test_dir, file)
                        with open(full_path, 'rb') as f:
                            img_data = f.read()

                        # OCR the image
                        img = Image.open(BytesIO(img_data))
                        img_array = np.array(img)
                        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                        text = pytesseract.image_to_string(gray, lang='eng+fra')

                        print(f"Extracted text:\n{text[:500]}")
                    except Exception as e:
                        print(f"Error processing {file}: {e}")

if __name__ == "__main__":
    test_ocr_pipeline()