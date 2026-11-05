
import os
from pathlib import Path
from PIL import Image

# Locate OCR project directory automatically
project_path = Path(__file__).resolve().parents[1]

# Dataset folder
dataset_path = project_path / "data" / "raw" / "invoices"

print("=" * 50)
print("OCR IMAGE VALIDATION")
print("=" * 50)

print("Dataset path:", dataset_path)

if not dataset_path.exists():
    print("ERROR: Dataset folder not found!")

else:

    image_extensions = (".jpg", ".jpeg", ".png", ".tif", ".tiff")

    total_images = 0
    valid_images = 0
    invalid_images = []

    for root, dirs, files in os.walk(dataset_path):

        for file in files:

            if file.lower().endswith(image_extensions):

                total_images += 1
                image_path = Path(root) / file

                try:
                    with Image.open(image_path) as img:
                        img.verify()

                    valid_images += 1

                except Exception:
                    invalid_images.append(str(image_path))

    print("\nTotal images:", total_images)
    print("Valid images:", valid_images)
    print("Invalid images:", len(invalid_images))

    print("\nIMAGE VALIDATION COMPLETED")


