
from app.advanced_ocr import AdvancedOCR
from app.rules import extract_fields
import os


UPLOAD_FOLDER = "uploads"


def find_latest_original_image():
    """Find the latest uploaded ORIGINAL image."""

    if not os.path.exists(UPLOAD_FOLDER):
        print("❌ uploads folder not found")
        return None

    valid_extensions = (
        ".png",
        ".jpg",
        ".jpeg",
        ".webp"
    )

    files = []

    for filename in os.listdir(UPLOAD_FOLDER):

        lower = filename.lower()

        if not lower.endswith(valid_extensions):
            continue

        # IMPORTANT:
        # Ignore all generated processed files.
        if "_processed" in lower:
            continue

        path = os.path.join(
            UPLOAD_FOLDER,
            filename
        )

        if os.path.isfile(path):
            files.append(path)

    if not files:
        return None

    # Find newest file based on modification time.
    files.sort(
        key=os.path.getmtime,
        reverse=True
    )

    return files[0]


# ============================================================
# FIND ORIGINAL IMAGE
# ============================================================

image_path = find_latest_original_image()

if image_path is None:

    print("❌ No original image found in uploads/")
    print(
        "Please upload a product package image "
        "before running this test."
    )

    raise SystemExit


print("=" * 80)
print("TEST IMAGE")
print("=" * 80)
print(image_path)


# ============================================================
# OCR
# ============================================================

ocr = AdvancedOCR()

ocr_text = ocr.extract_text(
    image_path
)


# ============================================================
# SHOW OCR TEXT
# ============================================================

print("\n" + "=" * 80)
print("OCR TEXT")
print("=" * 80)

print(ocr_text)

print("=" * 80)


# ============================================================
# FIELD EXTRACTION
# ============================================================

extracted = extract_fields(
    ocr_text
)


print("\n" + "=" * 80)
print("EXTRACTED FIELDS")
print("=" * 80)

for key, value in extracted.items():

    print(
        f"{key}: {value}"
    )

print("=" * 80)
