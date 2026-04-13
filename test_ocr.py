import pytesseract
from PIL import Image
import cv2
import numpy as np

# Indiquer le chemin absolu vers l'exécutable Tesseract sous Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Test simple avec une image de test
try:
    # Test si Tesseract fonctionne
    print("Test Tesseract avec une chaîne simple:")
    test_text = pytesseract.image_to_string(Image.new('RGB', (100, 30), color='white'), lang='eng')
    print(f"Résultat: '{test_text}'")

    # Créer une image de test avec du texte
    from PIL import ImageDraw, ImageFont

    # Créer une image simple
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)

    # Essayer d'utiliser une police par défaut
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()

    # Dessiner du texte
    draw.text((10, 10), "ID: 123456", fill='black', font=font)
    draw.text((10, 40), "Nom: Test Student", fill='black', font=font)
    draw.text((10, 70), "1 A", fill='black', font=font)
    draw.text((10, 100), "2 B", fill='black', font=font)
    draw.text((10, 130), "3 C", fill='black', font=font)
    draw.text((10, 160), "4 D", fill='black', font=font)

    # Tester l'OCR sur cette image
    print("\nTest OCR sur image générée:")
    text = pytesseract.image_to_string(img, lang='eng+fra')
    print(f"Texte extrait: '{text}'")

    # Test avec prétraitement
    print("\nTest avec prétraitement:")
    img_array = np.array(img)
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    processed_text = pytesseract.image_to_string(gray, lang='eng+fra')
    print(f"Texte après prétraitement: '{processed_text}'")

    # Vérifier les langues disponibles
    print("\nLangues Tesseract disponibles:")
    print(pytesseract.get_languages(config=''))

except Exception as e:
    print(f"Erreur: {e}")
    import traceback
    traceback.print_exc()