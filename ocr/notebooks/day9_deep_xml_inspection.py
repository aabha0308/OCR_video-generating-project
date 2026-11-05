
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter

project_path = Path(__file__).resolve().parents[1]
dataset_path = project_path / "data" / "raw" / "invoices"

gt_files = list(dataset_path.rglob("*_gt.xml"))
ocr_files = list(dataset_path.rglob("*_ocr.xml"))


def inspect_xml(file_path):

    tree = ET.parse(file_path)
    root = tree.getroot()

    # Count XML element types
    tags = Counter(
        element.tag.split("}")[-1]
        for element in root.iter()
    )

    # Extract all property labels
    entities = []

    for element in root.iter():
        if element.tag.split("}")[-1] == "Property":
            if element.get("key") == "entity":
                entities.append(element.get("value"))

    # Extract all text elements
    text_values = []

    for element in root.iter():

        tag = element.tag.split("}")[-1]

        if tag in ["Unicode", "PlainText", "Text"]:
            if element.text and element.text.strip():
                text_values.append(element.text.strip())

    return tags, entities, text_values


print("=" * 60)
print("GROUND TRUTH XML ANALYSIS")
print("=" * 60)

gt_tags, gt_entities, gt_text = inspect_xml(gt_files[0])

print("\nXML element counts:")
for tag, count in gt_tags.items():
    print(tag, ":", count)

print("\nEntity labels:")
print(Counter(gt_entities))

print("\nExtracted text:")
print(gt_text[:30])

print("\n" + "=" * 60)
print("OCR XML ANALYSIS")
print("=" * 60)

ocr_tags, ocr_entities, ocr_text = inspect_xml(ocr_files[0])

print("\nXML element counts:")
for tag, count in ocr_tags.items():
    print(tag, ":", count)

print("\nEntity labels:")
print(Counter(ocr_entities))

print("\nExtracted text:")
print(ocr_text[:30])

print("\n" + "=" * 60)
print("INVESTIGATION COMPLETED")
print("=" * 60)
