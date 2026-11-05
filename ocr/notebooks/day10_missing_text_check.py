
import xml.etree.ElementTree as ET
from pathlib import Path

project_path = Path(__file__).resolve().parents[1]
dataset_path = project_path / "data" / "raw" / "invoices"

ocr_files = list(dataset_path.rglob("*_ocr.xml"))

missing_text_files = []

for file in ocr_files:
    tree = ET.parse(file)
    root = tree.getroot()

    texts = []

    for element in root.iter():
        if element.tag.endswith("Unicode"):
            if element.text and element.text.strip():
                texts.append(element.text.strip())

    if not texts:
        missing_text_files.append(file)

print("OCR FILES WITHOUT TEXT")
print("=" * 50)

if missing_text_files:
    for file in missing_text_files:
        print(file.name)
else:
    print("No missing files found.")

print("\nTotal missing OCR files:", len(missing_text_files))
