import os
import json
import requests
from typing import Dict, Optional

class OpenRouterExtractor:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.use_ai = bool(self.api_key)
        
        if not self.api_key:
            print("⚠️ OPENROUTER_API_KEY not found. Using regex fallback.")
        else:
            print("✅ OpenRouter AI initialized (FREE)")
    
    def extract_fields(self, ocr_text: str) -> Dict[str, Optional[str]]:
        """Extract fields using OpenRouter AI or fallback to regex"""
        if not self.use_ai or not ocr_text:
            return self._fallback_extract(ocr_text)
        
        print("🤖 Calling OpenRouter AI for extraction...")
        
        # Limit text length
        text = ocr_text[:5000]
        
        prompt = f"""
        Extract product information from this label text. Return ONLY valid JSON.
        
        Text:
        {text}
        
        Fields to extract (use null if not found):
        - mrp: Maximum Retail Price (numeric only)
        - net_quantity: Net quantity with unit
        - mfg_date: Manufacturing date in DD/MM/YYYY
        - exp_date: Expiry date in DD/MM/YYYY
        - consumer_care: Phone number or email
        - manufacturer: Company name
        - country_of_origin: Country name
        - product_name: Product name
        
        Example: {{"mrp":"20.00","net_quantity":"400 g","mfg_date":"12/04/2024","exp_date":"11/10/2024","consumer_care":"18001031947","manufacturer":"Nestlé India Limited","country_of_origin":"India","product_name":"Nestlé EveryDay"}}
        """
        
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "google/gemini-2.0-flash-lite-preview-02-05:free",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 300
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # Clean response
                content = content.strip()
                if content.startswith("```json"):
                    content = content.split("```json")[1].split("```")[0]
                elif content.startswith("```"):
                    content = content.split("```")[1].split("```")[0]
                
                print("✅ AI extraction successful")
                extracted = json.loads(content)
                
                default_fields = {
                    "mrp": None, "net_quantity": None, "mfg_date": None,
                    "exp_date": None, "consumer_care": None, "manufacturer": None,
                    "country_of_origin": None, "product_name": None
                }
                default_fields.update(extracted)
                return default_fields
                
            elif response.status_code == 401:
                print("⚠️ Invalid OpenRouter API key. Please check your .env file.")
                print("   Get a free key from: https://openrouter.ai/keys")
                return self._fallback_extract(ocr_text)
            elif response.status_code == 429:
                print("⚠️ Rate limit exceeded. Using regex fallback.")
                return self._fallback_extract(ocr_text)
            else:
                print(f"⚠️ OpenRouter API error: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return self._fallback_extract(ocr_text)
                
        except requests.exceptions.Timeout:
            print("⚠️ OpenRouter API timeout - using regex fallback")
            return self._fallback_extract(ocr_text)
        except Exception as e:
            print(f"⚠️ OpenRouter extraction failed: {e}")
            return self._fallback_extract(ocr_text)
    
    def _fallback_extract(self, text: str) -> Dict[str, Optional[str]]:
        """Fallback to regex-based extraction"""
        print("🔄 Using regex fallback extraction")
        from .rules.rule_engine import extract_fields
        return extract_fields(text)