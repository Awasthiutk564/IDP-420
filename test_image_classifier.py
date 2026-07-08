from pprint import pprint

from adapters.image_extractor import ImageExtractor
from classifiers.image_classifier import ImageClassifier
from utils.image_utils import select_image

image = select_image()

if image == "":
    print("No image selected.")
    exit()

extractor = ImageExtractor()

document = extractor.extract(image)

classifier = ImageClassifier()

document = classifier.classify(document)

print()

print("=" * 60)

print("CLASSIFICATION")

print("=" * 60)

pprint(document["classification"])