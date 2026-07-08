import os
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"

from paddleocr import PaddleOCR


class OCRModel:

    def __init__(self):

        self.ocr = PaddleOCR(
            lang="en",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=False
        )

    def extract_text(self, image):

        result = self.ocr.predict(image)

        extracted_text = []

        if result is None:
            return ""

        for page in result:

            if "rec_texts" in page:

                extracted_text.extend(page["rec_texts"])

        return "\n".join(extracted_text)