from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
import os
import shutil
from datetime import datetime

from ..database import get_db
from ..models import User, ScannedProduct, Violation
from ..schemas import ScanResponse, ScanDetailResponse, ViolationResponse
from ..auth import get_current_active_user
from ..rules import extract_fields, evaluate_compliance
from ..ocr_pipeline import run_ocr, get_image_dimensions
from ..advanced_ocr import AdvancedOCR
from ..ai_extractor import AIExtractor

router = APIRouter(prefix="/scan", tags=["Scan"])

ai_extractor = AIExtractor()

# ============================================================
# Initialize Advanced OCR with fallback
# ============================================================
try:
    ocr_engine = AdvancedOCR()
    print("✅ Advanced OCR engine initialized")
except Exception as e:
    print(f"⚠️ Failed to initialize Advanced OCR: {e}")
    print("Using fallback OCR")
    # Fallback: use the original ocr_pipeline
    ocr_engine = None

# ============================================================
# Ensure uploads directory exists
# ============================================================
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ============================================================
# Helper function to run OCR with fallback
# ============================================================
def run_ocr_with_fallback(file_path):
    """
    Run OCR using AdvancedOCR with fallback to Tesseract
    """
    try:
        if ocr_engine:
            text = ocr_engine.extract_text(file_path)
            if text and text.strip():
                return text
        # Fallback to Tesseract
        print("⚠️ Advanced OCR returned empty, using Tesseract fallback")
        return run_ocr(file_path)
    except Exception as e:
        print(f"⚠️ OCR error: {e}, using Tesseract fallback")
        return run_ocr(file_path)

# ============================================================
# Upload Product
# ============================================================
@router.post("/upload", response_model=ScanResponse)
async def upload_product(
    file: UploadFile = File(...),
    product_name: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload a product label image, run Advanced OCR,
    extract fields, and evaluate compliance.
    """

    # --------------------------------------------------------
    # Validate file type
    # --------------------------------------------------------
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )

    # --------------------------------------------------------
    # Generate unique filename
    # --------------------------------------------------------
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{current_user.id}_{timestamp}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    # --------------------------------------------------------
    # Save uploaded file
    # --------------------------------------------------------
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )

    # --------------------------------------------------------
    # Run OCR (with fallback)
    # --------------------------------------------------------
    try:
        ocr_text = run_ocr_with_fallback(file_path)
    except Exception as e:
        print("=" * 60)
        print("OCR ERROR")
        print("=" * 60)
        print(str(e))
        print("=" * 60)
        ocr_text = ""

    # --------------------------------------------------------
    # DEBUG: Print OCR text
    # --------------------------------------------------------
    print("=" * 60)
    print("ADVANCED OCR EXTRACTED TEXT:")
    print("=" * 60)
    print(repr(ocr_text))
    print("=" * 60)

    # --------------------------------------------------------
    # Extract fields from OCR text
    # --------------------------------------------------------
    extracted_fields = ai_extractor.extract_fields(ocr_text)

    # --------------------------------------------------------
    # Product name handling
    # --------------------------------------------------------
    if product_name:
        extracted_fields["product_name"] = product_name
    elif extracted_fields.get("product_name") is None:
        # Try to find product name from first line of OCR
        first_line = ocr_text.strip().split("\n")[0] if ocr_text else ""
        if first_line and len(first_line) < 50:
            extracted_fields["product_name"] = first_line

    # --------------------------------------------------------
    # Debug extracted fields
    # --------------------------------------------------------
    print("=" * 60)
    print("EXTRACTED FIELDS:")
    print("=" * 60)
    for field, value in extracted_fields.items():
        print(f"{field}: {value}")
    print("=" * 60)

    # --------------------------------------------------------
    # Evaluate compliance
    # --------------------------------------------------------
    compliance_result = evaluate_compliance(extracted_fields)

    # --------------------------------------------------------
    # Debug compliance result
    # --------------------------------------------------------
    print("=" * 60)
    print("COMPLIANCE RESULT:")
    print("=" * 60)
    print(compliance_result["summary"])
    print("=" * 60)

    # --------------------------------------------------------
    # Save scan to database
    # --------------------------------------------------------
    new_scan = ScannedProduct(
        user_id=current_user.id,
        image_path=file_path,
        image_filename=filename,
        product_name=extracted_fields.get("product_name"),
        mrp=extracted_fields.get("mrp"),
        net_quantity=extracted_fields.get("net_quantity"),
        mfg_date=extracted_fields.get("mfg_date"),
        exp_date=extracted_fields.get("exp_date"),
        consumer_care=extracted_fields.get("consumer_care"),
        manufacturer=extracted_fields.get("manufacturer"),
        country_of_origin=extracted_fields.get("country_of_origin"),
        ocr_text=ocr_text,
        is_compliant=compliance_result["summary"]["is_compliant"],
        overall_verdict=compliance_result["summary"]["verdict"]
    )

    db.add(new_scan)
    db.commit()
    db.refresh(new_scan)

    # --------------------------------------------------------
    # Save violations
    # --------------------------------------------------------
    for rule_result in compliance_result["rules"]:
        if not rule_result["passed"]:
            violation = Violation(
                product_id=new_scan.id,
                rule_id=rule_result["rule_id"],
                field_name=rule_result["field_name"],
                expected_value=str(rule_result["expected"]),
                actual_value=rule_result["actual"],
                severity=rule_result["severity"],
                description=rule_result["message"]
            )
            db.add(violation)

    db.commit()

    # --------------------------------------------------------
    # Return response
    # --------------------------------------------------------
    return ScanResponse(
        id=new_scan.id,
        image_filename=new_scan.image_filename,
        mrp=new_scan.mrp,
        net_quantity=new_scan.net_quantity,
        mfg_date=new_scan.mfg_date,
        exp_date=new_scan.exp_date,
        consumer_care=new_scan.consumer_care,
        manufacturer=new_scan.manufacturer,  # <-- ADD THIS
        country_of_origin=new_scan.country_of_origin,  # <-- ADD THIS
        is_compliant=new_scan.is_compliant,
        overall_verdict=new_scan.overall_verdict,
        created_at=new_scan.created_at
    )

# ============================================================
# Scan History
# ============================================================
@router.get("/history", response_model=list[ScanResponse])
def get_scan_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    limit: int = 50,
    skip: int = 0
):
    scans = (
        db.query(ScannedProduct)
        .filter(ScannedProduct.user_id == current_user.id)
        .order_by(ScannedProduct.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return scans

# ============================================================
# Get Scan Details
# ============================================================
@router.get("/{scan_id}", response_model=ScanDetailResponse)
def get_scan_details(
    scan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    scan = (
        db.query(ScannedProduct)
        .filter(
            ScannedProduct.id == scan_id,
            ScannedProduct.user_id == current_user.id
        )
        .first()
    )

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found"
        )

    violations = (
        db.query(Violation)
        .filter(Violation.product_id == scan_id)
        .all()
    )

    violation_responses = [
        ViolationResponse(
            rule_id=v.rule_id,
            field_name=v.field_name,
            expected_value=v.expected_value,
            actual_value=v.actual_value,
            severity=v.severity,
            description=v.description
        )
        for v in violations
    ]

    return ScanDetailResponse(
        id=scan.id,
        image_filename=scan.image_filename,
        mrp=scan.mrp,
        net_quantity=scan.net_quantity,
        mfg_date=scan.mfg_date,
        exp_date=scan.exp_date,
        consumer_care=scan.consumer_care,
        manufacturer=scan.manufacturer,  # <-- ADD THIS
        country_of_origin=scan.country_of_origin,  # <-- ADD THIS
        is_compliant=scan.is_compliant,
        overall_verdict=scan.overall_verdict,
        created_at=scan.created_at,
        ocr_text=scan.ocr_text,
        violations=violation_responses
    )