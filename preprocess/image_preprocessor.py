"""
OpenCV Image Preprocessing Module
"""

import cv2
import numpy as np


class ImagePreprocessor:

    def __init__(self):
        pass

    # -----------------------------
    # Read Image
    # -----------------------------
    def load_image(self, image_path):

        image = cv2.imread(image_path)

        if image is None:
            raise FileNotFoundError(f"Unable to load image: {image_path}")

        return image

    # -----------------------------
    # Convert to Gray
    # -----------------------------
    def to_gray(self, image):

        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # -----------------------------
    # Remove Noise
    # -----------------------------
    def denoise(self, image):

        return cv2.fastNlMeansDenoising(image)

    # -----------------------------
    # CLAHE Contrast
    # -----------------------------
    def enhance_contrast(self, image):

        clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8, 8)
        )

        return clahe.apply(image)

    # -----------------------------
    # Adaptive Threshold
    # -----------------------------
    def threshold(self, image):

        return cv2.adaptiveThreshold(
            image,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            15,
        )

    # -----------------------------
    # Resize Large Images
    # -----------------------------
    def resize(self, image, width=1800):

        h, w = image.shape[:2]

        if w <= width:
            return image

        ratio = width / w

        new_height = int(h * ratio)

        return cv2.resize(
            image,
            (width, new_height),
            interpolation=cv2.INTER_AREA,
        )

    # -----------------------------
    # Automatic Deskew
    # -----------------------------
    def deskew(self, image):

        coords = np.column_stack(np.where(image > 0))

        if len(coords) == 0:
            return image

        angle = cv2.minAreaRect(coords)[-1]

        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        h, w = image.shape[:2]

        center = (w // 2, h // 2)

        matrix = cv2.getRotationMatrix2D(
            center,
            angle,
            1.0,
        )

        return cv2.warpAffine(
            image,
            matrix,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )

    # -----------------------------
    # Complete Pipeline
    # -----------------------------
    def preprocess(self, image_path):

        image = self.load_image(image_path)

        image = self.resize(image)

        image = self.to_gray(image)

        image = self.denoise(image)

        image = self.enhance_contrast(image)

        image = self.threshold(image)

        image = self.deskew(image)

        return image