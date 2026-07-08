"""
DocLayout-YOLO Wrapper

This module is responsible for
loading the layout detection model
and returning detected document regions.
"""

from ultralytics import YOLO
from pathlib import Path

from config.model_paths import DOC_LAYOUT_MODEL


class DocLayoutModel:

    def __init__(self):

        self.model = None

        self.loaded = False

    def load(self):

        """
        Load DocLayout model
        """

        if self.loaded:
            return

        model_file = Path(DOC_LAYOUT_MODEL) / "doclayout_yolo.pt"

        if not model_file.exists():

            raise FileNotFoundError(
                f"Model not found:\n{model_file}"
            )

        self.model = YOLO(str(model_file))

        self.loaded = True

    def predict(self, image):

        """
        Perform layout detection.
        """

        if not self.loaded:
            self.load()

        results = self.model.predict(
            image,
            verbose=False
        )

        return results