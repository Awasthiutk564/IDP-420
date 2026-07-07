"""
Image Utility Functions
-----------------------

This module contains helper functions for

1. Selecting an image
2. Validating image files
3. Reading image metadata

Supported Formats
-----------------
PNG
JPG
JPEG
BMP
TIFF
WEBP
"""

import os
from pathlib import Path
from tkinter import Tk
from tkinter.filedialog import askopenfilename

from PIL import Image

from config.settings import SUPPORTED_IMAGE_FORMATS


# --------------------------------------------------------
# Check whether file is an image
# --------------------------------------------------------

def is_image_file(filepath: str) -> bool:
    """
    Returns True if filepath has a supported image extension.
    """

    extension = Path(filepath).suffix.lower()

    return extension in SUPPORTED_IMAGE_FORMATS


# --------------------------------------------------------
# Validate image
# --------------------------------------------------------

def validate_image(filepath: str):

    if not os.path.exists(filepath):
        return False, "Image does not exist."

    if not os.path.isfile(filepath):
        return False, "Path is not a file."

    if not is_image_file(filepath):
        return False, "Unsupported image format."

    try:

        img = Image.open(filepath)

        img.verify()

    except Exception as e:

        return False, str(e)

    return True, "Valid Image"


# --------------------------------------------------------
# Select Image using File Dialog
# --------------------------------------------------------

def select_image():

    root = Tk()

    root.withdraw()

    root.attributes("-topmost", True)

    filename = askopenfilename(

        title="Select an Image",

        filetypes=[

            ("Images", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp")

        ]

    )

    root.destroy()

    return filename


# --------------------------------------------------------
# Image Information
# --------------------------------------------------------

def get_image_information(filepath):

    image = Image.open(filepath)

    width, height = image.size

    return {

        "width": width,

        "height": height,

        "mode": image.mode,

        "format": image.format

    }