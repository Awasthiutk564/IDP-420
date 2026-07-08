import os
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"

from paddleocr import PaddleOCR
from utils.math_normalizer import normalize_math_text, is_likely_math


class OCRModel:
    """
    OCR model using PaddleOCR with math-aware post-processing.

    After standard text extraction, each line is checked against
    is_likely_math() heuristics. Lines identified as math are passed
    through normalize_math_text() to convert Unicode superscripts,
    Greek letters, and common OCR math artifacts into proper
    ASCII/LaTeX notation (e.g. x^2, \\alpha, \\sqrt{x}).
    """

    def __init__(self):
        self.ocr = PaddleOCR(
            lang="en",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=False,
        )

    def extract_text(self, image) -> str:
        """
        Run OCR on the given image and return extracted text.
        Math lines are normalized automatically.

        Args:
            image: File path (str) or preprocessed numpy/PIL image.

        Returns:
            Multi-line string with extracted (and math-normalized) text.
        """
        result = self.ocr.predict(image)

        if result is None:
            return ""

        extracted_lines = []

        for page in result:
            if "rec_texts" in page:
                for line_text in page["rec_texts"]:
                    if line_text:
                        # Apply math normalization if line looks like math
                        if is_likely_math(line_text):
                            line_text = normalize_math_text(line_text)
                        extracted_lines.append(line_text)

        return "\n".join(extracted_lines)

    def extract_text_with_math(self, image) -> dict:
        """
        Extended extraction that returns both plain text and a list of
        detected math lines separately (useful for pipeline math stage).

        Returns:
            {
                "full_text": str,         # all lines joined
                "lines": list[str],       # individual lines
                "math_lines": list[str],  # lines identified as math (normalized)
                "math_indices": list[int] # indices of math lines in `lines`
            }
        """
        result = self.ocr.predict(image)

        if result is None:
            return {
                "full_text": "",
                "lines": [],
                "math_lines": [],
                "math_indices": [],
            }

        lines = []
        math_lines = []
        math_indices = []

        for page in result:
            if "rec_texts" in page:
                for line_text in page["rec_texts"]:
                    if not line_text:
                        continue
                    idx = len(lines)
                    if is_likely_math(line_text):
                        normalized = normalize_math_text(line_text)
                        lines.append(normalized)
                        math_lines.append(normalized)
                        math_indices.append(idx)
                    else:
                        lines.append(line_text)

        return {
            "full_text": "\n".join(lines),
            "lines": lines,
            "math_lines": math_lines,
            "math_indices": math_indices,
        }