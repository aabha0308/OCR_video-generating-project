
from pathlib import Path
import xml.etree.ElementTree as ET
from PIL import Image

project_path = Path(__file__).resolve().parents[1]
dataset_path = project_path / "data" / "raw" / "invoices"

# Select one sample
gt_file = next(dataset_path.rglob("*_gt.xml"))
sample_name = gt_file.name.replace("_gt.xml", "")

ocr_file = gt_file.with_name(sample_name + "_ocr.xml")

# Find matching image
image_file = None

for extension in [".tif", ".tiff", ".png", ".jpg"]:
    candidate = gt_file.with_name(sample_name + extension)

    if candidate.exists():
        image_file = candidate
        break

print("=" * 60)
print("SAMPLE DOCUMENT COMPARISON")
print("=" * 60)

print("\nDocument:", sample_name)

# Inspect original image
if image_file:

    with Image.open(image_file) as img:

        print("\nImage dimensions:", img.size)
        print("Image format:", img.format)

        # Save a preview without changing the original
        preview_path = project_path / "data" / "processed" / "sample_invoice_preview.png"

        img.convert("RGB").save(preview_path)

        print("Preview saved:", preview_path)

else:
    print("Matching image not found!")

# Extract OCR text
tree = ET.parse(ocr_file)
root = tree.getroot()

def tag_name(element):
    return element.tag.split("}")[-1]

print("\n" + "=" * 60)
print("OCR RECOGNIZED TEXT")
print("=" * 60)

for region in root.iter():

    if tag_name(region) == "TextRegion":

        print("\nREGION:", region.get("id"))

        for line in region.iter():

            if tag_name(line) == "TextLine":

                line_text = []

                for element in line.iter():

                    if tag_name(element) == "Unicode":
                        if element.text:
                            line_text.append(element.text.strip())

                if line_text:
                    print(" ".join(line_text))

# Inspect GT entity labels
gt_tree = ET.parse(gt_file)
gt_root = gt_tree.getroot()

print("\n" + "=" * 60)
print("GROUND TRUTH ENTITY LABELS")
print("=" * 60)

for region in gt_root.iter():

    if tag_name(region) == "TextRegion":

        entity = None

        for child in region:

            if tag_name(child) == "Property":
                if child.get("key") == "entity":
                    entity = child.get("value")

        print(region.get("id"), ":", entity)

print("\nCOMPARISON COMPLETED")
