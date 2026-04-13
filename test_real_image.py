import base64
import logging
from io import BytesIO
from PIL import Image
import numpy as np
import cv2
import pytesseract
import re
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("autograde_test")

# Configure Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def process_image_file(image_path):
    """Process a real image file like the server does"""
    logger.info(f"\nProcessing image: {image_path}")

    try:
        # Read and encode to base64
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        logger.info(f"Base64 length: {len(b64)}")

        # Decode back to image
        image_data = base64.b64decode(b64)
        image = Image.open(BytesIO(image_data))

        logger.info(f"Image info: mode={image.mode}, size={image.size}")

        # Preprocess
        img_array = np.array(image)
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array

        # Apply threshold for better OCR
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # OCR
        raw_text = pytesseract.image_to_string(thresh, lang='eng+fra')
        logger.info(f"Raw text: '{raw_text[:200]}...' length: {len(raw_text)}")

        if raw_text.strip():
            # Parse answers
            answers = {}
            lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

            for line in lines:
                logger.info(f"Line: '{line}'")

                # Try different patterns
                patterns = [
                    r"^\s*(\d+)\s*[\.:\-\)]\s*([A-Da-d])\s*$",  # "1. A"
                    r"^\s*(\d+)\s+([A-Da-d])\s*$",               # "1 A"
                    r"^\s*(\d+)([A-Da-d])\s*$",                  # "1A"
                ]

                for pattern in patterns:
                    match = re.search(pattern, line, flags=re.IGNORECASE)
                    if match:
                        q_num = str(int(match.group(1)))
                        ans = match.group(2).upper()
                        answers[q_num] = ans
                        logger.info(f"Found answer: Q{q_num} = {ans}")
                        break

            logger.info(f"Final answers: {answers}")
        else:
            logger.warning("No text extracted from image")

    except Exception as e:
        logger.error(f"Error processing {image_path}: {e}")
        import traceback
        traceback.print_exc()

# Look for test images in common locations
test_paths = [
    r"C:\Users\ASUS ROG\Desktop\yassine\examcorr\test_images",
    r"C:\Users\ASUS ROG\Desktop\yassine\examcorr\sample_images",
    r"C:\Users\ASUS ROG\Desktop\yassine\examcorr\images",
    r"C:\Users\ASUS ROG\Desktop\yassine\examcorr\tkinter_client\test_images",
    r"C:\Users\ASUS ROG\Desktop",
]

found_images = False
for path in test_paths:
    if os.path.exists(path):
        print(f"\nLooking in: {path}")
        for file in os.listdir(path):
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                found_images = True
                process_image_file(os.path.join(path, file))

if not found_images:
    print("\nNo test images found. Creating a sample scan-like image...")

    # Create a more realistic test image
    img = Image.new('RGB', (600, 800), color='white')
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("arial.ttf", 24)
        font_normal = ImageFont.truetype("arial.ttf", 18)
    except:
        font_title = ImageFont.load_default()
        font_normal = ImageFont.load_default()

    # Draw header
    draw.text((50, 50), "EXAMEN DE MATHEMATIQUES", fill='black', font=font_title)
    draw.text((50, 90), "Filière: Informatique", fill='black', font=font_normal)
    draw.text((50, 120), "Durée: 1 heure", fill='black', font=font_normal)

    # Draw student info
    draw.text((50, 180), "ID: _______________", fill='black', font=font_normal)
    draw.text((50, 210), "Nom: _______________", fill='black', font=font_normal)

    # Draw questions
    questions = [
        ("1. Quelle est la capitale de la France?", "A) Madrid  B) Paris  C) Rome  D) Berlin"),
        ("2. 2 + 2 = ?", "A) 3  B) 4  C) 5  D) 6"),
        ("3. Quelle est l'année 2024?", "A) Année bissextile  B) Année normale  C) Année du chat  D) Année du dragon"),
        ("4. Python est un langage:", "A) Compilé  B) Interprété  C) Assemblage  D) Binaire")
    ]

    y_pos = 280
    for i, (q, options) in enumerate(questions, 1):
        draw.text((50, y_pos), q, fill='black', font=font_normal)
        draw.text((50, y_pos + 30), options, fill='black', font=font_normal)
        y_pos += 100

    # Add some noise to make it more realistic
    img_array = np.array(img)
    noise = np.random.randint(0, 25, img_array.shape, dtype='uint8')
    noisy = np.clip(img_array.astype(int) + noise, 0, 255).astype('uint8')
    img_noisy = Image.fromarray(noisy)

    # Save test image
    test_path = r"C:\Users\ASUS ROG\Desktop\test_exam.png"
    img_noisy.save(test_path, "PNG")
    print(f"Created test image: {test_path}")

    # Process it
    process_image_file(test_path)