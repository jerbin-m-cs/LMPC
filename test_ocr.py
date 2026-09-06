import cv2
import pytesseract
from PIL import Image
import os

# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def test_ocr(image_path):
    # Read image
    img = cv2.imread(image_path)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Try different preprocessing
    methods = [
        ("Original", gray),
        ("Threshold", cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]),
        ("Adaptive", cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)),
        ("Resized", cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC))
    ]
    
    for name, img_processed in methods:
        print(f"\n=== Testing {name} ===")
        try:
            text = pytesseract.image_to_string(img_processed, config='--oem 3 --psm 6')
            print(text[:500])  # Print first 500 chars
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    # Update this path to your uploaded image
    image_path = "uploads/1_20260905_212853.png"
    if os.path.exists(image_path):
        test_ocr(image_path)
    else:
        print(f"Image not found: {image_path}")
        print("Available uploads:")
        for f in os.listdir("uploads"):
            print(f"  - {f}")
            