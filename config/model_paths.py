"""
Model Paths
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

WEIGHTS = ROOT / "weights"

DOC_LAYOUT_MODEL = WEIGHTS / "doclayout_yolo"

PADDLEOCR_MODEL = WEIGHTS / "paddleocr"

RAPIDOCR_MODEL = WEIGHTS / "rapidocr"