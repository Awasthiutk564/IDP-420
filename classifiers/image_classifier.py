"""
Image Document Classifier
"""

import cv2


class ImageClassifier:

    def __init__(self):
        pass

    def classify(self, document):

        image = document["processed_image"]

        height, width = image.shape[:2]

        # -----------------------------------
        # Orientation
        # -----------------------------------

        if height >= width:
            orientation = "Portrait"
        else:
            orientation = "Landscape"

        # -----------------------------------
        # Gray or Color
        # -----------------------------------

        if len(image.shape) == 2:
            image_type = "Grayscale"
        else:
            image_type = "RGB"

        # -----------------------------------
        # Resolution
        # -----------------------------------

        pixels = width * height

        if pixels > 2000000:
            quality = "High"

        elif pixels > 800000:
            quality = "Medium"

        else:
            quality = "Low"

        # -----------------------------------
        # Document Type
        # -----------------------------------

        extension = document["metadata"]["format"]

        if extension in ["PNG", "JPEG", "JPG", "BMP", "TIFF", "WEBP"]:
            doc_type = "Scanned Image"

        else:
            doc_type = "Unknown"

        document["classification"] = {

            "document_type": doc_type,

            "orientation": orientation,

            "image_type": image_type,

            "quality": quality

        }

        return document