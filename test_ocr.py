from adapters.image_extractor import ImageExtractor
from models.ocr_model import OCRModel
from utils.image_utils import select_image

image = select_image()

if image == "":
    print("No image selected.")
    exit()

extractor = ImageExtractor()

document = extractor.extract(image)

ocr = OCRModel()

text = ocr.extract_text(document["processed_image"])

print()

print("=" * 70)

print("EXTRACTED TEXT")

print("=" * 70)

print()

print(text)