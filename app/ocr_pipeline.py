import cv2
import pytesseract
import os
from PIL import Image
import numpy as np

# Configure Tesseract path for Windows
tesseract_paths = [
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
]
for path in tesseract_paths:
    if os.path.exists(path):
        pytesseract.pytesseract.tesseract_cmd = path
        break

def preprocess_image(image_path):
    """
    Preprocess image for better OCR
    """
    # Read image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Resize if too small
    height, width = gray.shape
    if height < 500 or width < 500:
        scale = max(800/width, 800/height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
    
    # Apply CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    
    # Apply adaptive threshold
    thresh = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 15, 2
    )
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(thresh)
    
    # Save preprocessed image
    processed_path = image_path.replace('.', '_processed.')
    cv2.imwrite(processed_path, denoised)
    
    return processed_path

def run_ocr(image_path):
    """
    Run OCR on image and return extracted text
    """
    try:
        # Preprocess
        processed_path = preprocess_image(image_path)
        
        # Open image
        img = Image.open(processed_path)
        
        # Try multiple configurations
        configs = [
            '--oem 3 --psm 6',
            '--oem 3 --psm 4',
            '--oem 3 --psm 11',
        ]
        
        best_text = ""
        for config in configs:
            try:
                text = pytesseract.image_to_string(img, config=config)
                if len(text) > len(best_text):
                    best_text = text
            except:
                continue
        
        return best_text
        
    except Exception as e:
        print(f"OCR Error: {e}")
        return ""

def get_image_dimensions(image_path):
    """
    Get image dimensions in pixels
    """
    img = cv2.imread(image_path)
    if img is not None:
        height, width = img.shape[:2]
        return width, height
    return 0, 0