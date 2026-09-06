import os
from typing import Dict, Optional

# Try Gemini first
try:
    from .gemini_extractor import GeminiExtractor
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️ Gemini extractor not available")

class AIExtractor:
    def __init__(self):
        """Initialize AI extractor"""
        self.extractor = None
        self.use_ai = False
        
        # Try Gemini
        if GEMINI_AVAILABLE:
            try:
                self.extractor = GeminiExtractor()
                if self.extractor.use_ai:
                    self.use_ai = True
                    print("✅ Using Gemini AI")
                    return
            except Exception as e:
                print(f"⚠️ Gemini init failed: {e}")
        
        # Fallback to regex
        print("✅ Using regex fallback")
    
    def extract_fields(self, ocr_text: str) -> Dict[str, Optional[str]]:
        """Extract fields using AI or fallback"""
        if self.use_ai and self.extractor:
            return self.extractor.extract_fields(ocr_text)
        else:
            from .rules.rule_engine import extract_fields
            return extract_fields(ocr_text)