import cv2
import numpy as np
import os
from ultralytics import YOLO

class LabelDetector:
    def __init__(self):
        """Initialize YOLO model for label detection"""
        try:
            # Use a pre-trained model or custom trained model
            self.model = YOLO('yolov8n.pt')  # Small model for speed
            self.initialized = True
            print("✅ YOLO model loaded successfully")
        except Exception as e:
            print(f"⚠️ YOLO initialization failed: {e}")
            self.initialized = False
    
    def detect_label_region(self, image_path):
        """Detect the label/declaration panel region"""
        
        if not self.initialized:
            return None
        
        try:
            # Read image
            img = cv2.imread(image_path)
            results = self.model(img)
            
            # Find label region (look for text-like regions)
            # For now, we'll just return the full image
            # In production, train a custom model on product labels
            
            # Simple heuristic: assume label is in the center
            h, w = img.shape[:2]
            x1 = int(w * 0.1)
            y1 = int(h * 0.1)
            x2 = int(w * 0.9)
            y2 = int(h * 0.9)
            
            # Crop to label region
            cropped = img[y1:y2, x1:x2]
            
            # Save cropped image
            cropped_path = image_path.replace('.', '_cropped.')
            cv2.imwrite(cropped_path, cropped)
            
            return cropped_path
            
        except Exception as e:
            print(f"Label detection error: {e}")
            return None