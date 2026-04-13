import base64
import logging
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2
import pytesseract
import re

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("autograde_test")

# Configure Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def clean_base64(payload: str) -> str:
    if "," in payload:
        return payload.split(",", 1)[1]
    return payload

def preprocess_image(image: Image.Image) -> Image.Image:
    logger.info(f"Input image mode: {image.mode}, size: {image.size}")

    # Convert to RGB if necessary
    if image.mode != 'RGB':
        image = image.convert('RGB')
        logger.info("Converted to RGB")

    # Convert PIL Image to numpy array
    img_array = np.array(image)
    logger.info(f"Array shape: {img_array.shape}")

    # Convert to grayscale
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    logger.info(f"Grayscale shape: {gray.shape}")

    return Image.fromarray(gray)

def parse_ocr_raw_text(raw_text: str):
    student_id = None
    student_name = None
    answers = {}

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    logger.info(f"Processing {len(lines)} lines from OCR")

    for line in lines:
        logger.info(f"Processing line: '{line}'")
        line_upper = line.upper()

        # Try to match ID
        if re.search(r"(?:ID|MATRICULE|CNE|APOGEE)[\s:]*(.+)$", line_upper):
            match = re.search(r"(?:ID|MATRICULE|CNE|APOGEE)[\s:]+(.+)$", line, flags=re.IGNORECASE)
            if match:
                student_id = match.group(1).strip()
                logger.info(f"Found student ID: {student_id}")
            continue

        # Try to match Name
        if re.search(r"(?:NOM|NAME|PRENOM|ETUDIANT)[\s:]*(.+)$", line_upper):
            match = re.search(r"(?:NOM|NAME|PRENOM|ETUDIANT)[\w\s]*[\s:]+(.+)$", line, flags=re.IGNORECASE)
            if match:
                student_name = match.group(1).strip()
                logger.info(f"Found student name: {student_name}")
            continue

        # Match question patterns
        match_answer = re.search(r"^\s*(?:\|\s*)?(?:(?:Q|Question)\s*)?(?:\*\*)?\s*(\d+)\s*(?:\*\*)?[\s:\|\.\-\)]*(.*?)\s*(?:\|\s*)?(?:\*)?$", line, flags=re.IGNORECASE)
        simple_answer = re.search(r"^\s*(\d+)\s*([A-Da-d])\s*$", line.strip())

        ocr_map = {'8': 'B', '0': 'D', '4': 'A', '1': 'I', '5': 'S', '6': 'G', '2': 'Z'}

        if match_answer:
            q_num_raw = match_answer.group(1)
            ans_raw = match_answer.group(2).strip().upper()
            logger.info(f"Found answer pattern 1 - Q{q_num_raw}: '{ans_raw}'")

            if not ans_raw and len(q_num_raw) > 1:
                ans_raw = q_num_raw[-1]
                q_num_raw = q_num_raw[:-1]
                logger.info(f"Split last char - Q{q_num_raw}: '{ans_raw}'")

            if ans_raw:
                q_num = str(int(q_num_raw))
                if ans_raw in ocr_map:
                    ans_raw = ocr_map[ans_raw]
                answers[q_num] = ans_raw
        elif simple_answer:
            q_num_raw = simple_answer.group(1)
            ans_raw = simple_answer.group(2).upper()
            logger.info(f"Found answer pattern 2 - Q{q_num_raw}: '{ans_raw}'")

            q_num = str(int(q_num_raw))
            if ans_raw in ocr_map:
                ans_raw = ocr_map[ans_raw]
            answers[q_num] = ans_raw

    return student_id, student_name, answers

# Test exactly like the server does
print("=== Testing Server OCR Logic ===")

# Create test image exactly like in the app
print("\n1. Creating test image...")
img = Image.new('RGB', (400, 200), color='white')
draw = ImageDraw.Draw(img)

try:
    font = ImageFont.truetype("arial.ttf", 20)
except:
    font = ImageFont.load_default()

draw.text((10, 10), "ID: 20234567", fill='black', font=font)
draw.text((10, 40), "Nom: Mohammed Ali", fill='black', font=font)
draw.text((10, 70), "1 A", fill='black', font=font)
draw.text((10, 100), "2 B", fill='black', font=font)
draw.text((10, 130), "3 C", fill='black', font=font)
draw.text((10, 160), "4 D", fill='black', font=font)

# Convert to base64
print("\n2. Converting to base64...")
buffer = BytesIO()
img.save(buffer, format='PNG')  # Changed to PNG to preserve quality
img_bytes = buffer.getvalue()
b64_string = base64.b64encode(img_bytes).decode('utf-8')
print(f"Base64 string length: {len(b64_string)}")

# Now simulate server processing
print("\n3. Server-side processing...")
try:
    # Clean base64
    clean_b64 = clean_base64(b64_string)
    logger.info(f"Cleaned base64 length: {len(clean_b64)}")

    # Decode
    image_data = base64.b64decode(clean_b64)
    logger.info(f"Decoded data length: {len(image_data)}")

    # Open image
    image = Image.open(BytesIO(image_data))
    logger.info(f"Image opened: mode={image.mode}, size={image.size}")

    # Preprocess
    preprocessed_image = preprocess_image(image)

    # OCR
    print("\n4. Running Tesseract OCR...")
    raw_text = pytesseract.image_to_string(preprocessed_image, lang='eng+fra')
    logger.info(f"Raw text from OCR: '{raw_text}', length: {len(raw_text)}")

    if not raw_text or raw_text.strip() == "":
        logger.error("OCR returned empty text")
        # Try with original image
        logger.info("Trying with original image...")
        raw_text = pytesseract.image_to_string(image, lang='eng+fra')
        logger.info(f"Raw text from OCR (original): '{raw_text}', length: {len(raw_text)}")

    if raw_text and raw_text.strip():
        print("\n5. Parsing results...")
        student_id, student_name, answers = parse_ocr_raw_text(raw_text)
        logger.info(f"Parsed results - ID: {student_id}, Name: {student_name}, Answers: {answers}")

        print("\n=== Final Results ===")
        print(f"Student ID: {student_id}")
        print(f"Student Name: {student_name}")
        print(f"Answers: {answers}")
        print(f"Raw Text:\n{raw_text}")
    else:
        print("ERROR: OCR failed to extract any text!")

except Exception as e:
    logger.error(f"OCR evaluation failed: {str(e)}", exc_info=True)
    import traceback
    traceback.print_exc()