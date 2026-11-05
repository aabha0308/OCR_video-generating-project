# import os
# import cv2
# import numpy as np
# import matplotlib.pyplot as plt
# from PIL import Image, ImageDraw

# # Project folders
# raw_folder = "ocr/data/raw/documents"
# processed_folder = "ocr/data/processed/images"

# os.makedirs(raw_folder, exist_ok=True)
# os.makedirs(processed_folder, exist_ok=True)

# # --------------------------------
# # STEP 1: CREATE A SAMPLE DOCUMENT
# # --------------------------------

# sample_path = os.path.join(raw_folder, "sample_document.png")

# if not os.path.exists(sample_path):

#     image = Image.new("RGB", (1200, 800), "white")
#     draw = ImageDraw.Draw(image)

#     draw.text((100, 100), "INVOICE", fill="black")
#     draw.text((100, 200), "Invoice Number: INV-1025", fill="black")
#     draw.text((100, 300), "Date: 29/10/2026", fill="black")
#     draw.text((100, 400), "Total Amount: 5000.00", fill="black")

#     image.save(sample_path)

# print("Sample document created.")

# # --------------------------------
# # STEP 2: READ ORIGINAL IMAGE
# # --------------------------------

# original = cv2.imread(sample_path)

# if original is None:
#     raise ValueError("Could not load sample image.")

# # --------------------------------
# # STEP 3: RESIZING
# # --------------------------------

# resized = cv2.resize(
#     original,
#     (900, 600),
#     interpolation=cv2.INTER_AREA
# )

# # --------------------------------
# # STEP 4: GRAYSCALE CONVERSION
# # --------------------------------

# gray = cv2.cvtColor(
#     resized,
#     cv2.COLOR_BGR2GRAY
# )

# # --------------------------------
# # STEP 5: NOISE REMOVAL
# # --------------------------------

# denoised = cv2.medianBlur(gray, 3)

# # --------------------------------
# # STEP 6: ADAPTIVE THRESHOLDING
# # --------------------------------

# threshold = cv2.adaptiveThreshold(
#     denoised,
#     255,
#     cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
#     cv2.THRESH_BINARY,
#     31,
#     10
# )

# # --------------------------------
# # STEP 7: SAVE PROCESSED IMAGES
# # --------------------------------

# cv2.imwrite(
#     os.path.join(processed_folder, "resized.png"),
#     resized
# )

# cv2.imwrite(
#     os.path.join(processed_folder, "grayscale.png"),
#     gray
# )

# cv2.imwrite(
#     os.path.join(processed_folder, "denoised.png"),
#     denoised
# )

# cv2.imwrite(
#     os.path.join(processed_folder, "threshold.png"),
#     threshold
# )

# # --------------------------------
# # STEP 8: DISPLAY COMPARISON
# # --------------------------------

# images = [
#     ("Original", cv2.cvtColor(original, cv2.COLOR_BGR2RGB)),
#     ("Resized", cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)),
#     ("Grayscale", gray),
#     ("Denoised", denoised),
#     ("Threshold", threshold)
# ]

# plt.figure(figsize=(15, 10))

# for i, (title, img) in enumerate(images):

#     plt.subplot(2, 3, i + 1)
#     plt.imshow(img, cmap="gray" if len(img.shape) == 2 else None)
#     plt.title(title)
#     plt.axis("off")

# plt.tight_layout()
# plt.show()

# print("Image preprocessing completed successfully!")

import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw

# Project folders
raw_folder = "ocr/data/raw/documents"
processed_folder = "ocr/data/processed/images"

os.makedirs(raw_folder, exist_ok=True)
os.makedirs(processed_folder, exist_ok=True)

# --------------------------------
# STEP 1: CREATE A SAMPLE DOCUMENT
# --------------------------------

sample_path = os.path.join(raw_folder, "sample_document.png")

if not os.path.exists(sample_path):

    image = Image.new("RGB", (1200, 800), "white")
    draw = ImageDraw.Draw(image)

    draw.text((100, 100), "INVOICE", fill="black")
    draw.text((100, 200), "Invoice Number: INV-1025", fill="black")
    draw.text((100, 300), "Date: 29/10/2026", fill="black")
    draw.text((100, 400), "Total Amount: 5000.00", fill="black")

    image.save(sample_path)

print("Sample document created.")

# --------------------------------
# STEP 2: READ ORIGINAL IMAGE
# --------------------------------

original = cv2.imread(sample_path)

if original is None:
    raise ValueError("Could not load sample image.")

# --------------------------------
# STEP 3: RESIZING
# --------------------------------

resized = cv2.resize(
    original,
    (900, 600),
    interpolation=cv2.INTER_AREA
)

# --------------------------------
# STEP 4: GRAYSCALE CONVERSION
# --------------------------------

gray = cv2.cvtColor(
    resized,
    cv2.COLOR_BGR2GRAY
)

# --------------------------------
# STEP 5: NOISE REMOVAL
# --------------------------------

denoised = cv2.medianBlur(gray, 3)

# --------------------------------
# STEP 6: ADAPTIVE THRESHOLDING
# --------------------------------

threshold = cv2.adaptiveThreshold(
    denoised,
    255,
    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv2.THRESH_BINARY,
    31,
    10
)

# --------------------------------
# STEP 7: SAVE PROCESSED IMAGES
# --------------------------------

cv2.imwrite(
    os.path.join(processed_folder, "resized.png"),
    resized
)

cv2.imwrite(
    os.path.join(processed_folder, "grayscale.png"),
    gray
)

cv2.imwrite(
    os.path.join(processed_folder, "denoised.png"),
    denoised
)

cv2.imwrite(
    os.path.join(processed_folder, "threshold.png"),
    threshold
)

# --------------------------------
# STEP 8: DISPLAY COMPARISON
# --------------------------------

images = [
    ("Original", cv2.cvtColor(original, cv2.COLOR_BGR2RGB)),
    ("Resized", cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)),
    ("Grayscale", gray),
    ("Denoised", denoised),
    ("Threshold", threshold)
]

plt.figure(figsize=(15, 10))

for i, (title, img) in enumerate(images):

    plt.subplot(2, 3, i + 1)
    plt.imshow(img, cmap="gray" if len(img.shape) == 2 else None)
    plt.title(title)
    plt.axis("off")

plt.tight_layout()
plt.show()

print("Image preprocessing completed successfully!")