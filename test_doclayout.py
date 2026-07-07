from adapters.image_extractor import ImageExtractor
from classifiers.image_classifier import ImageClassifier
from models.doclayout_model import DocLayoutModel
from utils.image_utils import select_image

image = select_image()

if image == "":
    print("No image selected.")
    exit()

extractor = ImageExtractor()

document = extractor.extract(image)

classifier = ImageClassifier()

document = classifier.classify(document)

layout = DocLayoutModel()

print()

print("Loading DocLayout-YOLO...")

layout.load()

print("Model Loaded Successfully")

results = layout.predict(document["processed_image"])

print(results)