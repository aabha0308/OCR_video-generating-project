# import os
# from PIL import Image
# import matplotlib.pyplot as plt

# folder_path = "ocr/data/raw/documents"

# files = os.listdir(folder_path)

# print("Total files:", len(files))

# for filename in files:

#     image_path = os.path.join(folder_path, filename)

#     try:
#         image = Image.open(image_path)

#         print("\nFile:", filename)
#         print("Format:", image.format)
#         print("Dimensions:", image.size)
#         print("Mode:", image.mode)

#         plt.imshow(image)
#         plt.title(filename)
#         plt.axis("off")
#         plt.show()

#     except Exception as e:
#         print("Could not open:", filename, e)

import os
from PIL import Image

folder_path = "ocr/data/raw/documents"

valid_images = 0
invalid_images = 0

for filename in os.listdir(folder_path):

    path = os.path.join(folder_path, filename)

    try:
        with Image.open(path) as image:
            image.verify()

        with Image.open(path) as image:
            width, height = image.size

        valid_images += 1

        if width < 300 or height < 300:
            print("Low resolution:", filename)

    except Exception:
        invalid_images += 1
        print("Invalid or corrupted:", filename)

print("\nInspection Summary")
print("Valid images:", valid_images)
print("Invalid images:", invalid_images)