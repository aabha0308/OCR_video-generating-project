
from pathlib import Path
from PIL import Image

project_path = Path(__file__).resolve().parents[1]

image_folder = (
    project_path
    / "data"
    / "raw"
    / "invoices"
    / "archive"
    / "ImageAndXML_Data"
)

output_folder = project_path / "reports" / "sample_images"
output_folder.mkdir(parents=True, exist_ok=True)

sample_names = [
    "0001136521",
    "0001139626"
]

for name in sample_names:

    image_path = image_folder / f"{name}.tif"

    if not image_path.exists():
        print("Image not found:", image_path)
        continue

    with Image.open(image_path) as image:

        output_path = output_folder / f"{name}.png"

        image.convert("RGB").save(output_path)

        print("Saved:", output_path)

print("\nIMAGE CONVERSION COMPLETED")
