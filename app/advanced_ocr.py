
import os
import re
import cv2
import numpy as np
import pytesseract


class AdvancedOCR:

    def __init__(self):
        """Initialize Tesseract and PaddleOCR."""

        # =========================================================
        # TESSERACT
        # =========================================================

        tesseract_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]

        self.tesseract_available = False

        for path in tesseract_paths:

            if os.path.exists(path):

                pytesseract.pytesseract.tesseract_cmd = path

                self.tesseract_available = True

                print(
                    f"✅ Tesseract found at: {path}"
                )

                break

        if not self.tesseract_available:
            print(
                "⚠️ Tesseract executable not found"
            )

        # =========================================================
        # PADDLE OCR
        # =========================================================

        self.use_paddle = False
        self.paddle_ocr = None

        try:

            from paddleocr import PaddleOCR

            # New PaddleOCR API.
            # Do NOT use show_log=False.
            self.paddle_ocr = PaddleOCR(
                use_angle_cls=True,
                lang="en"
            )

            self.use_paddle = True

            print(
                "✅ PaddleOCR initialized successfully"
            )

        except Exception as e:

            print(
                f"⚠️ PaddleOCR not available: {e}"
            )

            print(
                "➡️ Using Tesseract fallback"
            )

        print("✅ OCR initialized")

    # =============================================================
    # PREPROCESS IMAGE
    # =============================================================

    def preprocess_image(self, image_path):
        """
        Preprocess the ORIGINAL uploaded image.

        Returns multiple versions for OCR testing.
        """

        img = cv2.imread(image_path)

        if img is None:

            print(
                f"❌ Could not read image: {image_path}"
            )

            return None

        height, width = img.shape[:2]

        # ---------------------------------------------------------
        # Resize
        # ---------------------------------------------------------

        target_size = 1600

        if min(height, width) < target_size:

            scale = target_size / min(
                height,
                width
            )

            new_width = int(
                width * scale
            )

            new_height = int(
                height * scale
            )

            img = cv2.resize(
                img,
                (new_width, new_height),
                interpolation=cv2.INTER_CUBIC
            )

        # ---------------------------------------------------------
        # Grayscale
        # ---------------------------------------------------------

        gray = cv2.cvtColor(
            img,
            cv2.COLOR_BGR2GRAY
        )

        # ---------------------------------------------------------
        # Denoising
        # ---------------------------------------------------------

        gray_blur = cv2.GaussianBlur(
            gray,
            (3, 3),
            0
        )

        # ---------------------------------------------------------
        # CLAHE
        # ---------------------------------------------------------

        clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8, 8)
        )

        enhanced = clahe.apply(
            gray_blur
        )

        # ---------------------------------------------------------
        # Sharpen
        # ---------------------------------------------------------

        sharpen_kernel = np.array([
            [0, -1, 0],
            [-1, 5, -1],
            [0, -1, 0]
        ])

        sharpened = cv2.filter2D(
            enhanced,
            -1,
            sharpen_kernel
        )

        # ---------------------------------------------------------
        # Adaptive threshold
        # ---------------------------------------------------------

        adaptive = cv2.adaptiveThreshold(
            sharpened,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            10
        )

        # ---------------------------------------------------------
        # OTSU threshold
        # ---------------------------------------------------------

        _, otsu = cv2.threshold(
            sharpened,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        # ---------------------------------------------------------
        # Save ONLY one processed image.
        # ---------------------------------------------------------

        base, _ = os.path.splitext(
            image_path
        )

        # Remove repeated "_processed".
        while base.endswith("_processed"):

            base = base[:-10]

        processed_path = (
            base + "_processed.png"
        )

        cv2.imwrite(
            processed_path,
            adaptive
        )

        print(
            f"✅ Processed image saved: "
            f"{processed_path}"
        )

        return {
            "gray": gray,
            "enhanced": enhanced,
            "adaptive": adaptive,
            "otsu": otsu,
            "sharpened": sharpened,
            "processed_path": processed_path
        }

    # =============================================================
    # TESSERACT
    # =============================================================

    def _tesseract_ocr(
        self,
        image,
        label="image"
    ):
        """Run multiple Tesseract configurations."""

        if not self.tesseract_available:

            return ""

        configs = [

            (
                "--oem 3 --psm 6",
                "Block"
            ),

            (
                "--oem 3 --psm 4",
                "Column"
            ),

            (
                "--oem 3 --psm 11",
                "Sparse"
            ),

            (
                "--oem 3 --psm 3",
                "Automatic"
            )
        ]

        results = []

        for config, name in configs:

            try:

                text = pytesseract.image_to_string(
                    image,
                    config=config
                )

                text = text.strip()

                if text:

                    results.append(
                        (
                            len(text),
                            text,
                            name
                        )
                    )

            except Exception as e:

                print(
                    f"⚠️ Tesseract {name} failed: {e}"
                )

        if not results:

            return ""

        # Longest result for this image.
        results.sort(
            key=lambda x: x[0],
            reverse=True
        )

        length, text, name = results[0]

        print(
            f"✅ Best Tesseract configuration: "
            f"{name} ({length} characters)"
        )

        return text

    # =============================================================
    # PADDLE OCR
    # =============================================================

    def _paddle_ocr(
        self,
        image_path
    ):
        """
        Run PaddleOCR using the newer predict() API.

        Different PaddleOCR versions return different
        result structures, so several structures are handled.
        """

        if not self.use_paddle:

            return ""

        try:

            result = self.paddle_ocr.predict(
                image_path
            )

            if not result:

                return ""

            texts = []

            for page in result:

                # -------------------------------------------------
                # New PaddleOCR result object
                # -------------------------------------------------

                data = None

                if hasattr(page, "json"):

                    try:

                        data = page.json

                        if callable(data):
                            data = data()

                        if isinstance(
                            data,
                            str
                        ):

                            import json

                            data = json.loads(
                                data
                            )

                    except Exception:

                        data = None

                # -------------------------------------------------
                # Dictionary result
                # -------------------------------------------------

                if data is None:

                    if isinstance(
                        page,
                        dict
                    ):

                        data = page

                # -------------------------------------------------
                # Extract recognition text
                # -------------------------------------------------

                if isinstance(
                    data,
                    dict
                ):

                    # Common new PaddleOCR key.
                    rec_texts = data.get(
                        "rec_texts"
                    )

                    if isinstance(
                        rec_texts,
                        list
                    ):

                        for text in rec_texts:

                            if text:

                                texts.append(
                                    str(text).strip()
                                )

                    # Alternative structures.
                    for key in [
                        "texts",
                        "text"
                    ]:

                        value = data.get(
                            key
                        )

                        if isinstance(
                            value,
                            list
                        ):

                            for text in value:

                                if text:

                                    texts.append(
                                        str(text).strip()
                                    )

                        elif isinstance(
                            value,
                            str
                        ):

                            if value.strip():

                                texts.append(
                                    value.strip()
                                )

                # -------------------------------------------------
                # Old-style list structure
                # -------------------------------------------------

                elif isinstance(
                    page,
                    list
                ):

                    for line in page:

                        try:

                            if (
                                isinstance(
                                    line,
                                    (list, tuple)
                                )
                                and len(line) >= 2
                            ):

                                text_info = line[1]

                                if (
                                    isinstance(
                                        text_info,
                                        (list, tuple)
                                    )
                                    and len(text_info) >= 1
                                ):

                                    text = str(
                                        text_info[0]
                                    ).strip()

                                    if text:

                                        texts.append(
                                            text
                                        )

                        except Exception:

                            continue

            # Remove duplicates.
            unique_texts = []

            for text in texts:

                if (
                    text
                    and text not in unique_texts
                ):

                    unique_texts.append(
                        text
                    )

            final_text = "\n".join(
                unique_texts
            )

            return final_text

        except Exception as e:

            print(
                f"⚠️ PaddleOCR error: {e}"
            )

            return ""

    # =============================================================
    # OCR RESULT SCORING
    # =============================================================

    def _select_best_result(
        self,
        candidates
    ):
        """
        Select OCR result based on useful package-label
        keywords instead of simply choosing the longest result.
        """

        keywords = [

            "MRP",
            "MAXIMUM",
            "RETAIL",

            "NET",
            "QTY",
            "QUANTITY",
            "WEIGHT",

            "MFG",
            "MFD",
            "MANUFACTURED",

            "EXP",
            "EXPIRY",
            "USE BY",
            "BEST BEFORE",

            "BATCH",

            "CONSUMER",
            "CUSTOMER",
            "CARE",

            "INDIA",
            "MADE IN",
            "COUNTRY",

            "INGREDIENT",
            "FSSAI",

            "MANUFACTURER"
        ]

        best_score = -1
        best_text = ""

        for text in candidates:

            upper = text.upper()

            keyword_score = sum(
                1
                for keyword in keywords
                if keyword in upper
            )

            length_score = min(
                len(text) / 200,
                5
            )

            # Keyword score is more important than length.
            score = (
                keyword_score * 10
                + length_score
            )

            if score > best_score:

                best_score = score
                best_text = text

        print(
            f"✅ OCR result selected with score: "
            f"{best_score:.2f}"
        )

        return best_text

    # =============================================================
    # CLEAN OCR
    # =============================================================

    def _clean_text(
        self,
        text
    ):
        """Clean OCR output while preserving useful punctuation."""

        if not text:

            return ""

        lines = text.splitlines()

        cleaned_lines = []

        for line in lines:

            line = line.strip()

            if not line:

                continue

            # Normalize spaces.
            line = re.sub(
                r"[ \t]+",
                " ",
                line
            )

            # Count useful characters.
            alnum_count = sum(
                1
                for c in line
                if c.isalnum()
            )

            if alnum_count == 0:

                continue

            cleaned_lines.append(
                line
            )

        return "\n".join(
            cleaned_lines
        )

    # =============================================================
    # MAIN OCR FUNCTION
    # =============================================================

    def extract_text(
        self,
        image_path
    ):
        """
        Main OCR pipeline.

        1. PaddleOCR on original
        2. Tesseract on original
        3. Preprocess original
        4. Tesseract on multiple versions
        5. Select best result
        6. Clean text
        """

        try:

            candidates = []

            # -----------------------------------------------------
            # 1. PaddleOCR
            # -----------------------------------------------------

            if self.use_paddle:

                paddle_text = self._paddle_ocr(
                    image_path
                )

                if paddle_text.strip():

                    print(
                        f"✅ PaddleOCR extracted "
                        f"{len(paddle_text)} characters"
                    )

                    candidates.append(
                        paddle_text
                    )

            # -----------------------------------------------------
            # 2. Tesseract ORIGINAL
            # -----------------------------------------------------

            original = cv2.imread(
                image_path
            )

            if original is not None:

                original_text = (
                    self._tesseract_ocr(
                        original,
                        "original"
                    )
                )

                if original_text.strip():

                    print(
                        f"✅ Tesseract original image: "
                        f"{len(original_text)} characters"
                    )

                    candidates.append(
                        original_text
                    )

            # -----------------------------------------------------
            # 3. Preprocess
            # -----------------------------------------------------

            processed = self.preprocess_image(
                image_path
            )

            if processed is not None:

                # -------------------------------------------------
                # 4. OCR all useful preprocessing versions
                # -------------------------------------------------

                for name in [
                    "gray",
                    "enhanced",
                    "adaptive",
                    "otsu",
                    "sharpened"
                ]:

                    image = processed.get(
                        name
                    )

                    if image is None:

                        continue

                    text = self._tesseract_ocr(
                        image,
                        name
                    )

                    if text.strip():

                        print(
                            f"   {name}: "
                            f"{len(text)} characters"
                        )

                        candidates.append(
                            text
                        )

            # -----------------------------------------------------
            # 5. Check results
            # -----------------------------------------------------

            if not candidates:

                print(
                    "❌ No OCR text extracted"
                )

                return ""

            # -----------------------------------------------------
            # 6. Select best result
            # -----------------------------------------------------

            best_text = (
                self._select_best_result(
                    candidates
                )
            )

            # -----------------------------------------------------
            # 7. Clean
            # -----------------------------------------------------

            cleaned = self._clean_text(
                best_text
            )

            print(
                f"✅ Final OCR extracted "
                f"{len(cleaned)} characters"
            )

            return cleaned

        except Exception as e:

            print(
                f"❌ OCR error: {e}"
            )

            return ""

