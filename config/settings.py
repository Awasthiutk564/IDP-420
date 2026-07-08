"""
Global Project Settings
"""

from pathlib import Path

# -------------------------------
# Root Directory
# -------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# -------------------------------
# Input Folder
# -------------------------------

INPUT_FOLDER = PROJECT_ROOT / "data" / "input"

# -------------------------------
# Output Folder
# -------------------------------

OUTPUT_FOLDER = PROJECT_ROOT / "data" / "output"

# -------------------------------
# Upload Folder
# -------------------------------

UPLOAD_FOLDER = PROJECT_ROOT / "uploads"

# -------------------------------
# Temporary Folder
# -------------------------------

TEMP_FOLDER = PROJECT_ROOT / "temp"

# -------------------------------
# Log Folder
# -------------------------------

LOG_FOLDER = PROJECT_ROOT / "logs"

# -------------------------------
# Supported PDF Formats
# -------------------------------

SUPPORTED_PDF_FORMATS = [
    ".pdf"
]

# -------------------------------
# Supported Image Formats
# -------------------------------

SUPPORTED_IMAGE_FORMATS = [
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tif",
    ".tiff",
    ".webp"
]

SUPPORTED_FORMATS = (
    SUPPORTED_PDF_FORMATS +
    SUPPORTED_IMAGE_FORMATS
)

# -------------------------------
# OCR Settings
# -------------------------------

OCR_LANGUAGE = "en"

OCR_USE_GPU = False

OCR_CONFIDENCE_THRESHOLD = 0.50

# -------------------------------
# Image Processing
# -------------------------------

MAX_IMAGE_SIZE = 4000

RESIZE_LONG_EDGE = 2000

ENABLE_DENOISE = True

ENABLE_DESKEW = True

ENABLE_BINARIZATION = True

# -------------------------------
# Output Formats
# -------------------------------

GENERATE_JSON = True

GENERATE_HTML = True

GENERATE_XML = True

GENERATE_MARKDOWN = True

GENERATE_LATEX = True

# -------------------------------
# Logging
# -------------------------------

ENABLE_LOGGING = True