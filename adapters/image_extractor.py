"""
Image Extractor Adapter
-----------------------

Responsible for

1. Loading an image
2. Validating image
3. Preprocessing image
4. Returning a standardized document object
"""

import os

from preprocess.image_preprocessor import ImagePreprocessor

from utils.image_utils import (
    validate_image,
    get_image_information
)


class ImageExtractor:

    def __init__(self):

        self.preprocessor = ImagePreprocessor()

    # --------------------------------------------------
    # Extract Image
    # --------------------------------------------------

    def extract(self, image_path):

        valid, message = validate_image(image_path)

        if not valid:
            raise Exception(message)

        info = get_image_information(image_path)

        processed_image = self.preprocessor.preprocess(image_path)

        document = {

            "file_name": os.path.basename(image_path),

            "file_path": image_path,

            "document_type": "image",

            "metadata": info,

            "original_image": image_path,

            "processed_image": processed_image,

            "ocr": None,

            "layout": None,

            "tables": None,

            "equations": None,

            "figures": None,

            "charts": None,

            "text": "",

            "pages": 1

        }

        return document