from utils.image_utils import *

image = select_image()

if image == "":

    print("No image selected.")

    exit()

print()

print("Selected Image:")

print(image)

print()

valid, message = validate_image(image)

print(message)

print()

if valid:

    info = get_image_information(image)

    print(info)