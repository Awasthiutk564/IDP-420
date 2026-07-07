import cv2

from utils.image_utils import select_image
from preprocess.image_preprocessor import ImagePreprocessor

processor = ImagePreprocessor()

image_path = select_image()

if image_path == "":
    print("No image selected.")
    exit()

processed = processor.preprocess(image_path)

cv2.imshow("Processed Image", processed)

cv2.waitKey(0)

cv2.destroyAllWindows()