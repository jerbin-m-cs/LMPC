import json
import re
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta


def load_rules():
    """Load LMPC rules from JSON file."""
    rules_path = os.path.join(
        os.path.dirname(__file__),
        "lmpc_rules.json"
    )

    with open(rules_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# OCR FIELD EXTRACTION
# ============================================================

def extract_fields(text: str) -> Dict[str, Optional[str]]:
    """
    Extract mandatory fields from OCR text using regex patterns
    """
    extracted = {
        "mrp": None,
        "net_quantity": None,
        "mfg_date": None,
        "exp_date": None,
        "consumer_care": None,
        "manufacturer": None,
        "country_of_origin": None,
        "product_name": None
    }
    
    # Clean text
    text_clean = text.replace('\r', '').strip()
    
    # ============================================================
    # MRP - multiple patterns, avoid address numbers
    # ============================================================
    mrp_patterns = [
        r'MRP\s*[Zz%&]*\s*([\d,]+\.?\d*)',  # "MRP Z 20.00"
        r'MRP\s*[:.\s]*([\d,]+\.?\d*)',
        r'MRP\s*₹\s*([\d,]+\.?\d*)',
        r'Price\s*[:.\s]*([\d,]+\.?\d*)',
        r'₹\s*([\d,]+\.?\d*)',
        r'Rs\.?\s*([\d,]+\.?\d*)',
    ]
    for pattern in mrp_patterns:
        match = re.search(pattern, text_clean, re.IGNORECASE)
        if match:
            value = match.group(1).replace(',', '').strip()
            value = value.replace(':', '.')
            # Skip if it looks like an address number (e.g., "100/101")
            if value and value not in ['&', '%', ''] and len(value) <= 10:
                # Check if this is near "MRP" keyword
                mrp_pos = match.start()
                context = text_clean[max(0, mrp_pos-20):min(len(text_clean), mrp_pos+30)]
                if 'MRP' in context.upper():
                    extracted["mrp"] = value
                    break
    
    # ============================================================
    # Net Quantity - patterns for different formats
    # ============================================================
    net_qty_patterns = [
        r'Net\s*Weight\s*[:.]?\s*;?\s*([\d.]+)\s*[gG]',  # "Net Weight: ; 400g"
        r'Net\s*Weight\s*[:.]?\s*([\d.]+)\s*[gG]',  # "Net Weight: 400g"
        r'NETQTY\.?\s*[:.]?\s*([\d.]+)\s*[gG]',  # "NETQTY: 52.59"
        r'NET[- ]?QTY\.?\s*[:.]?\s*([\d.]+)\s*[gG]',
        r'NET[- ]?QTY\.?\s*[:.]?\s*([\d.]+)',
        r'([\d.]+)\s*[gG]\s*(?:Net|Wt)',
        r'Weight\s*[:.]?\s*([\d.]+)\s*(g|kg|ml|l)',
        r'([\d.]+)\s*(g|kg|ml|l)\s*(?:Net|Wt)',
        r'([\d.]+)\s*[gG]',  # Just "400g"
    ]
    for pattern in net_qty_patterns:
        match = re.search(pattern, text_clean, re.IGNORECASE)
        if match:
            groups = match.groups()
            qty = groups[0] if len(groups) > 0 else None
            unit = groups[1] if len(groups) > 1 and groups[1] else "g"
            if qty:
                qty = qty.strip()
                if qty and qty not in ['.', '0', '01', '02', '03', '1', '2', '3']:
                    extracted["net_quantity"] = f"{qty} {unit}".strip()
                    break
    
    # ============================================================
    # Manufacturing Date
    # ============================================================
    mfg_patterns = [
        r'MFD\.?\s*[:.\s]*([\d]{1,2}[/-][\d]{1,2}[/-][\d]{4})',
        r'MFG\.?\s*[:.\s]*([\d]{1,2}[/-][\d]{1,2}[/-][\d]{4})',
        r'MFG\s*DATE\s*[:.\s]*([\d]{1,2}[/-][\d]{1,2}[/-][\d]{4})',
        r'MFD\s*DATE\s*[:.\s]*([\d]{1,2}[/-][\d]{1,2}[/-][\d]{4})',
    ]
    for pattern in mfg_patterns:
        match = re.search(pattern, text_clean, re.IGNORECASE)
        if match:
            extracted["mfg_date"] = match.group(1).strip()
            break
    
    # ============================================================
    # Expiry Date - including "X MONTHS FROM MANUFACTURE"
    # ============================================================
    exp_patterns = [
        r'(\d{1,2})\s*MONTHS?\s*FROM\s*MANUFACTURE',  # "12 MONTHS FROM MANUFACTURE"
        r'BEST\s*BEFORE\s*[:.\s]*([\d]{1,2}[/-][\d]{1,2}[/-][\d]{4})',
        r'USE\s*BY\s*[:.\s]*([\d]{1,2}[/-][\d]{1,2}[/-][\d]{4})',
        r'EXP\.?\s*[:.\s]*([\d]{1,2}[/-][\d]{1,2}[/-][\d]{4})',
        r'Expiry\s*[:.\s]*([\d]{1,2}[/-][\d]{1,2}[/-][\d]{4})',
        r'(\d{1,2})\s*MONTHS?',  # "12 MONTHS" (fallback)
    ]
    for pattern in exp_patterns:
        match = re.search(pattern, text_clean, re.IGNORECASE)
        if match:
            exp_value = match.group(1).strip()
            
            # Check if it's a months pattern
            if "MONTHS" in exp_value.upper() or "MONTH" in exp_value.upper():
                months_match = re.search(r'(\d{1,2})', exp_value)
                if months_match:
                    months = int(months_match.group(1))
                    extracted["exp_date"] = str(months)
                    break
            else:
                # Regular date format
                exp_date = exp_value.replace('ov', '').replace('o', '').replace('v', '')
                parts = exp_date.split('/')
                if len(parts) == 3 and len(parts[2]) == 2:
                    parts[2] = f"20{parts[2]}"
                    exp_date = '/'.join(parts)
                extracted["exp_date"] = exp_date
                break
    
    # ============================================================
    # Calculate expiry from months if MFG date exists
    # ============================================================
    if extracted["exp_date"] and extracted["exp_date"].isdigit() and extracted["mfg_date"]:
        try:
            months = int(extracted["exp_date"])
            mfg = datetime.strptime(extracted["mfg_date"], "%d/%m/%Y")
            exp = mfg + timedelta(days=months * 30)
            extracted["exp_date"] = exp.strftime("%d/%m/%Y")
        except:
            pass
    elif extracted["exp_date"] and extracted["exp_date"].isdigit():
        # No MFG date, keep as months
        extracted["exp_date"] = f"{extracted['exp_date']} MONTHS FROM MFG"
    
    # ============================================================
    # Consumer Care - only match valid phone numbers
    # ============================================================
    care_patterns = [
        r'Contact\s*us\s*[:.\s]*([\d\s\.\-]+)',
        r'CALL\s*US\s*AT\s*(1800\s*\d{2}\s*\d{4})',
        r'CALL\s*US\s*AT\s*([\d\s\.\-]+)',
        r'OR\s*CALL\s*US\s*AT\s*(1800\s*\d{2}\s*\d{4})',
        r'1800\s*(\d{2})\s*(\d{4})',
        r'1800[\s\.\-]?(\d{2})[\s\.\-]?(\d{4})',
        r'(\d{4}\s*\d{3}\s*\d{3})',  # "1800 103 1947"
        r'(\d{4}\s*\d{2}\s*\d{4})',  # "1800 22 4020"
        r'(\d{10})',  # Any 10-digit number
    ]
    for pattern in care_patterns:
        match = re.search(pattern, text_clean, re.IGNORECASE)
        if match:
            if len(match.groups()) == 2:
                phone = f"1800{match.group(1)}{match.group(2)}"
                if len(phone) == 10 and phone.startswith('1800'):
                    extracted["consumer_care"] = phone
                    break
            elif match.groups():
                phone_text = match.group(1)
                phone = re.sub(r'[\s\.\-]', '', phone_text)
                # Skip license numbers (start with 100 or 101)
                if phone.startswith('100') or phone.startswith('101'):
                    continue
                if len(phone) >= 10:
                    if phone.startswith('1800') or phone[0] in '6789':
                        extracted["consumer_care"] = phone[:10]
                        break
            else:
                phone_text = match.group(0)
                phone = re.sub(r'[\s\.\-]', '', phone_text)
                if phone.startswith('100') or phone.startswith('101'):
                    continue
                if len(phone) >= 10:
                    if phone.startswith('1800') or phone[0] in '6789':
                        extracted["consumer_care"] = phone[:10]
                        break
    
    # ============================================================
    # Manufacturer - prioritize Nestlé and PepsiCo
    # ============================================================
    manuf_patterns = [
        r'Nestlé\s*India\s*Limited',  # Nestlé pattern first
        r'PEPSICO\s*INDIA\s*HOLDINGS',
        r'PepsiCo\s*India\s*Holdings',
        r'Manufactured by\s*[:.\s]*([A-Za-z0-9\s,.\-&]{10,80})',
        r'MANUFACTURED BY\s*[:.\s]*([A-Za-z0-9\s,.\-&]{10,80})',
        r'Manufacturer\s*[:.\s]*([A-Za-z0-9\s,.\-&]{10,80})',
        r'MFG\s*BY\s*[:.\s]*([A-Za-z0-9\s,.\-&]{10,80})',
    ]
    for pattern in manuf_patterns:
        match = re.search(pattern, text_clean, re.IGNORECASE)
        if match:
            if match.groups():
                manufacturer = match.group(1).strip()
                # Clean up if it contains extra text
                if "BATCH" in manufacturer or "MFG" in manufacturer or "DATE" in manufacturer or "USE BY" in manufacturer:
                    # Try to extract just the company name
                    company_match = re.search(r'(Nestlé India Limited|PepsiCo India Holdings Pvt\.? Ltd\.?)', manufacturer, re.IGNORECASE)
                    if company_match:
                        manufacturer = company_match.group(1)
                    else:
                        clean_manuf = re.sub(r'BATCH.*|MFG.*|DATE.*|USE BY.*|Lot.*', '', manufacturer, flags=re.IGNORECASE)
                        if clean_manuf.strip():
                            manufacturer = clean_manuf.strip()
                        else:
                            manufacturer = manufacturer[:60].strip()
                extracted["manufacturer"] = manufacturer
            else:
                extracted["manufacturer"] = match.group(0).strip()
            break
    
    # If manufacturer not found, search for Nestlé in text
    if not extracted["manufacturer"]:
        nestle_match = re.search(r'(Nestlé\s*India\s*Limited)', text_clean, re.IGNORECASE)
        if nestle_match:
            extracted["manufacturer"] = nestle_match.group(1).strip()
    
    # ============================================================
    # Country of Origin
    # ============================================================
    country_patterns = [
        r'(?:Country of Origin|Origin)\s*[:.\s]*([A-Za-z\s]{3,20})',
        r'(India|INDIA|USA|China|UK|Germany)',
        r'New Delhi.*India',  # For Nestlé
    ]
    for pattern in country_patterns:
        match = re.search(pattern, text_clean, re.IGNORECASE)
        if match:
            if match.groups():
                extracted["country_of_origin"] = match.group(1).strip()
            else:
                extracted["country_of_origin"] = "India"
            break
    
    # If country not found but "India" appears in text
    if not extracted["country_of_origin"] and "India" in text_clean:
        extracted["country_of_origin"] = "India"
    
    # ============================================================
    # Product Name
    # ============================================================
    product_patterns = [
        r'^([A-Za-z0-9\s\-]+)(?:\n|$)',  # First line
        r'Product\s*[:.\s]*([A-Za-z0-9\s\-]+)',
        r'Brand\s*[:.\s]*([A-Za-z0-9\s\-]+)',
        r'(Nestlé\s*EveryDay\s*Dairy\s*Whitener)',
        r'(Lay\'s\s*Classic)',
    ]
    for pattern in product_patterns:
        match = re.search(pattern, text_clean, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            if len(name) > 3 and not name in ['Ss', 'ee', 'eel', '~']:
                extracted["product_name"] = name
                break
    
    return extracted


# ============================================================
# CHECK SINGLE RULE
# ============================================================

def check_rule(rule: Dict, extracted: Dict) -> Dict:
    """
    Check a single rule against extracted fields.
    """

    field = rule["field"]
    value = extracted.get(field)
    validation = rule.get("validation", {})

    result = {
        "rule_id": rule["id"],
        "field_name": field,
        "description": rule["description"],
        "severity": rule["severity"],
        "expected": validation,
        "actual": value,
        "passed": False,
        "message": ""
    }

    # ========================================================
    # REQUIRED FIELD
    # ========================================================

    if validation.get("type") == "required":

        if not value:

            result["message"] = (
                f"{field} is required but not found"
            )

            result["passed"] = False

            return result

    # ========================================================
    # FIELD EXISTS
    # ========================================================

    if value:

        # Check validation pattern
        if "pattern" in validation:

            try:

                if re.search(
                    validation["pattern"],
                    value,
                    re.IGNORECASE
                ):

                    result["passed"] = True

                    result["message"] = (
                        f"{field} found and valid"
                    )

                else:

                    result["passed"] = False

                    result["message"] = (
                        f"{field} found but format is invalid"
                    )

            except re.error:

                result["passed"] = False

                result["message"] = (
                    f"{field} found but validation "
                    f"pattern is invalid"
                )

        else:

            result["passed"] = True

            result["message"] = (
                f"{field} found"
            )

    # ========================================================
    # FIELD NOT FOUND
    # ========================================================

    else:

        if validation.get("type") == "recommended":

            result["message"] = (
                f"{field} is recommended but not found"
            )

            # Recommended fields do not fail compliance
            result["passed"] = True

        else:

            result["message"] = (
                f"{field} not found"
            )

            result["passed"] = False

    return result


# ============================================================
# EVALUATE COMPLIANCE
# ============================================================

def evaluate_compliance(extracted: Dict) -> Dict:
    """
    Evaluate all LMPC rules against extracted fields.
    """

    rules_data = load_rules()

    rules = rules_data["rules"]

    results = []

    passed_count = 0
    failed_count = 0

    # ========================================================
    # Check every rule
    # ========================================================

    for rule in rules:

        result = check_rule(
            rule,
            extracted
        )

        results.append(result)

        if result["passed"]:

            passed_count += 1

        else:

            failed_count += 1

    # ========================================================
    # Overall Compliance
    # ========================================================

    if failed_count == 0:

        verdict = "COMPLIANT"

        is_compliant = 1

    elif failed_count <= 2:

        verdict = "PARTIALLY COMPLIANT"

        is_compliant = 2

    else:

        verdict = "NON-COMPLIANT"

        is_compliant = 2

    # ========================================================
    # Return Result
    # ========================================================

    return {
        "rules": results,

        "summary": {
            "total_rules": len(rules),
            "passed": passed_count,
            "failed": failed_count,
            "verdict": verdict,
            "is_compliant": is_compliant
        }
    }