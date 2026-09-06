import os
import json
from typing import Dict, Optional

# Try the new Google GenAI SDK
try:
    from google import genai
    GENAI_AVAILABLE = True
    print("✅ Using new Google GenAI SDK")
except ImportError:
    GENAI_AVAILABLE = False
    print("⚠️ google-genai not installed. Run: pip install google-genai")


class GeminiExtractor:
    def __init__(self):
        """Initialize Gemini AI extractor with new SDK"""
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.use_ai = False
        
        if not self.api_key:
            print("⚠️ GEMINI_API_KEY not found in .env file")
            return
        
        if GENAI_AVAILABLE:
            try:
                self.client = genai.Client(api_key=self.api_key)
                self.use_ai = True
                print("✅ Gemini AI initialized with new SDK!")
                return
            except Exception as e:
                print(f"⚠️ New SDK init failed: {e}")
        
        print("❌ Gemini AI initialization failed - using regex fallback")
    
    def extract_fields(self, ocr_text: str) -> Dict[str, Optional[str]]:
        """Extract fields using Gemini AI"""
        
        if not self.use_ai or not ocr_text:
            print("🔄 Using regex fallback")
            from .rules.rule_engine import extract_fields
            return extract_fields(ocr_text)
        
        print("🤖 Calling Gemini AI for extraction...")
        
        # Truncate text if too long
        text = ocr_text[:6000]
        
        prompt = f"""
        You are a Legal Metrology compliance expert. Extract product information from this label text.
        
        Text:
        {text}
        
        Extract these fields and return ONLY valid JSON (no other text, no markdown):
        
        Fields:
        1. mrp: Maximum Retail Price (numeric only, e.g., "20.00")
        2. net_quantity: Net quantity with unit (e.g., "400 g", "52.5 g")
        3. mfg_date: Manufacturing date in DD/MM/YYYY
        4. exp_date: Expiry date in DD/MM/YYYY
        5. consumer_care: Phone number or email
        6. manufacturer: Company name
        7. country_of_origin: Country name
        8. product_name: Product name
        
        Rules:
        - MRP can be labeled as "MRP", "Price", "₹", "Rs."
        - Net Quantity can be "Net Wt", "Net Qty", "Weight"
        - If field not found, use null
        - Do NOT include license numbers or batch numbers as consumer care
        
        Example response:
        {{"mrp":"20.00","net_quantity":"52.5 g","mfg_date":"12/04/2024","exp_date":"11/10/2024","consumer_care":"1800224020","manufacturer":"PepsiCo India Holdings Pvt. Ltd.","country_of_origin":"India","product_name":"Lay's Classic"}}
        """
        
        try:
            # Use the correct model name for the new SDK
            # Available models: gemini-2.0-flash, gemini-1.5-flash, gemini-1.5-pro
            response = self.client.models.generate_content(
                model='gemini-2.0-flash',  # Changed from gemini-2.0-flash-exp
                contents=prompt,
                config={
                    'temperature': 0.1,
                    'max_output_tokens': 500,
                }
            )
            
            content = response.text
            
            # Clean markdown formatting
            content = content.strip()
            if content.startswith("```json"):
                content = content.split("```json")[1].split("```")[0]
            elif content.startswith("```"):
                content = content.split("```")[1].split("```")[0]
            
            extracted = json.loads(content)
            
            # Ensure all fields exist
            default_fields = {
                "mrp": None, "net_quantity": None, "mfg_date": None,
                "exp_date": None, "consumer_care": None, "manufacturer": None,
                "country_of_origin": None, "product_name": None
            }
            default_fields.update(extracted)
            
            print("✅ Gemini extraction successful!")
            return default_fields
            
        except json.JSONDecodeError as e:
            print(f"⚠️ Failed to parse AI response as JSON: {e}")
            return self._fallback_extract(ocr_text)
        except Exception as e:
            print(f"⚠️ Gemini extraction failed: {e}")
            return self._fallback_extract(ocr_text)
    
    def _fallback_extract(self, text: str) -> Dict[str, Optional[str]]:
        """Fallback to regex extraction"""
        from .rules.rule_engine import extract_fields
        return extract_fields(text)