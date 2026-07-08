from pprint import pprint

from adapters.image_extractor import ImageExtractor

from utils.image_utils import select_image

image = select_image()

if image == "":
    print("No image selected.")
    exit()

extractor = ImageExtractor()

document = extractor.extract(image)

print()

print("=" * 60)

print("DOCUMENT OBJECT")

print("=" * 60)

pprint(document)