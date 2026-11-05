
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter

project_path = Path(__file__).resolve().parents[1]
dataset_path = project_path / "data" / "raw" / "invoices"


def local_name(tag):
    return tag.split("}")[-1]


def analyze_xml(file_path):

    tree = ET.parse(file_path)
    root = tree.getroot()

    tags = Counter()
    text_values = []
    entities = []

    for element in root.iter():

        tag = local_name(element.tag)
        tags[tag] += 1

        if tag == "Unicode":
            if element.text and element.text.strip():
                text_values.append(element.text.strip())

        if tag == "Property" and element.get("key") == "entity":
            entities.append(element.get("value"))

    return tags, text_values, entities


gt_files = list(dataset_path.rglob("*_gt.xml"))
ocr_files = list(dataset_path.rglob("*_ocr.xml"))

gt_text_count = 0
ocr_text_count = 0

gt_tag_counts = Counter()
ocr_tag_counts = Counter()

entity_counts = Counter()

gt_errors = []
ocr_errors = []

print("DATASET QUALITY AUDIT")
print("=" * 60)

for file in gt_files:

    try:
        tags, texts, entities = analyze_xml(file)

        gt_tag_counts.update(tags)
        entity_counts.update(entities)

        if texts:
            gt_text_count += 1

    except Exception as e:
        gt_errors.append((file.name, str(e)))


for file in ocr_files:

    try:
        tags, texts, entities = analyze_xml(file)

        ocr_tag_counts.update(tags)

        if texts:
            ocr_text_count += 1


    except Exception as e:
        ocr_errors.append((file.name, str(e)))


print("\nTOTAL FILES")
print("GT XML:", len(gt_files))
print("OCR XML:", len(ocr_files))

print("\nFILES CONTAINING TEXT")
print("GT files with text:", gt_text_count)
print("OCR files with text:", ocr_text_count)

print("\nGROUND TRUTH XML ELEMENTS")
print(gt_tag_counts)

print("\nOCR XML ELEMENTS")
print(ocr_tag_counts)

print("\nENTITY LABEL DISTRIBUTION")
print(entity_counts)

print("\nXML ERRORS")
print("GT errors:", len(gt_errors))
print("OCR errors:", len(ocr_errors))

print("\nAUDIT COMPLETED")
