
import csv
import xml.etree.ElementTree as ET

from collections import Counter
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

PROJECT_PATH = Path(__file__).resolve().parents[1]

DATASET_PATH = (
    PROJECT_PATH
    / "data"
    / "raw"
    / "invoices"
    / "archive"
    / "ImageAndXML_Data"
)

REPORTS_PATH = PROJECT_PATH / "reports"

FILE_AUDIT_PATH = (
    REPORTS_PATH / "day14_page_xml_structure_audit.csv"
)

PROPERTY_AUDIT_PATH = (
    REPORTS_PATH / "day14_page_xml_property_values.csv"
)

SAMPLE_AUDIT_PATH = (
    REPORTS_PATH / "day14_page_xml_sample_inspection.txt"
)


# ============================================================
# HELPERS
# ============================================================

def local_name(tag):
    """Remove XML namespace from a tag."""
    return tag.split("}")[-1]


def get_text(element):
    """Extract non-empty Unicode text from an element."""
    texts = []

    for child in element.iter():
        if local_name(child.tag) == "Unicode":
            if child.text and child.text.strip():
                texts.append(child.text.strip())

    return texts


def count_tags(root):
    """Count important PAGE XML elements."""
    tags = Counter(local_name(element.tag) for element in root.iter())

    return {
        "Page": tags["Page"],
        "TextRegion": tags["TextRegion"],
        "TextLine": tags["TextLine"],
        "Word": tags["Word"],
        "TextEquiv": tags["TextEquiv"],
        "Unicode": tags["Unicode"],
        "Coords": tags["Coords"],
        "Property": tags["Property"],
    }


def extract_properties(root):
    """Extract every Property key/value pair."""
    properties = []

    for element in root.iter():

        if local_name(element.tag) == "Property":

            key = element.attrib.get("key", "").strip()
            value = element.attrib.get("value", "").strip()

            if key or value:
                properties.append((key, value))

    return properties


def inspect_xml(xml_path, xml_type):

    result = {
        "document": xml_path.name.replace(
            f"_{xml_type}.xml", ""
        ),
        "xml_type": xml_type,
        "xml_path": str(xml_path),
        "file_size_bytes": xml_path.stat().st_size,
        "parse_status": "success",
        "error": "",
    }

    try:
        root = ET.parse(xml_path).getroot()

        result.update(count_tags(root))

        texts = get_text(root)

        result["nonempty_unicode_count"] = len(texts)
        result["sample_text"] = " | ".join(texts[:10])

        properties = extract_properties(root)

        result["property_count"] = len(properties)

        result["property_keys"] = "; ".join(
            sorted(set(key for key, value in properties if key))
        )

        result["property_values"] = "; ".join(
            sorted(set(value for key, value in properties if value))
        )

        result["has_text_regions"] = result["TextRegion"] > 0
        result["has_text_lines"] = result["TextLine"] > 0
        result["has_words"] = result["Word"] > 0
        result["has_unicode_text"] = len(texts) > 0
        result["has_coordinates"] = result["Coords"] > 0

        # A file is metadata-only if it has no regions,
        # no lines, no words, and no transcription text.
        result["metadata_only"] = (
            result["TextRegion"] == 0
            and result["TextLine"] == 0
            and result["Word"] == 0
            and len(texts) == 0
        )

        return result, properties, texts

    except Exception as error:

        result["parse_status"] = "error"
        result["error"] = str(error)

        for key in [
            "Page",
            "TextRegion",
            "TextLine",
            "Word",
            "TextEquiv",
            "Unicode",
            "Coords",
            "Property",
            "nonempty_unicode_count",
            "property_count",
        ]:
            result[key] = 0

        result["sample_text"] = ""
        result["property_keys"] = ""
        result["property_values"] = ""
        result["has_text_regions"] = False
        result["has_text_lines"] = False
        result["has_words"] = False
        result["has_unicode_text"] = False
        result["has_coordinates"] = False
        result["metadata_only"] = False

        return result, [], []


# ============================================================
# VALIDATE DATASET
# ============================================================

if not DATASET_PATH.exists():
    raise FileNotFoundError(
        f"Dataset folder not found:\n{DATASET_PATH}"
    )

REPORTS_PATH.mkdir(parents=True, exist_ok=True)


# ============================================================
# FIND XML FILES
# ============================================================

gt_files = sorted(DATASET_PATH.rglob("*_gt.xml"))
ocr_files = sorted(DATASET_PATH.rglob("*_ocr.xml"))

print("=" * 70)
print("PAGE XML STRUCTURE AUDIT")
print("=" * 70)

print(f"\nDataset folder: {DATASET_PATH}")
print(f"GT XML files found: {len(gt_files)}")
print(f"OCR XML files found: {len(ocr_files)}")


# ============================================================
# INSPECT ALL FILES
# ============================================================

all_results = []
all_properties = []

gt_results = []
ocr_results = []

gt_property_counter = Counter()
ocr_property_counter = Counter()

gt_text_samples = []
ocr_text_samples = []

for index, xml_path in enumerate(gt_files, start=1):

    result, properties, texts = inspect_xml(xml_path, "gt")

    all_results.append(result)
    gt_results.append(result)

    gt_property_counter.update(properties)

    if texts:
        gt_text_samples.append((result["document"], texts[:15]))

    if index % 50 == 0:
        print(f"Processed GT files: {index}/{len(gt_files)}")


for index, xml_path in enumerate(ocr_files, start=1):

    result, properties, texts = inspect_xml(xml_path, "ocr")

    all_results.append(result)
    ocr_results.append(result)

    ocr_property_counter.update(properties)

    if texts:
        ocr_text_samples.append((result["document"], texts[:15]))

    if index % 50 == 0:
        print(f"Processed OCR files: {index}/{len(ocr_files)}")


# ============================================================
# DOCUMENT PAIR CHECK
# ============================================================

gt_ids = {
    path.name.replace("_gt.xml", "")
    for path in gt_files
}

ocr_ids = {
    path.name.replace("_ocr.xml", "")
    for path in ocr_files
}

missing_ocr = sorted(gt_ids - ocr_ids)
missing_gt = sorted(ocr_ids - gt_ids)


# ============================================================
# SAVE FILE-LEVEL AUDIT
# ============================================================

fieldnames = [
    "document",
    "xml_type",
    "xml_path",
    "file_size_bytes",
    "parse_status",
    "error",
    "Page",
    "TextRegion",
    "TextLine",
    "Word",
    "TextEquiv",
    "Unicode",
    "Coords",
    "Property",
    "nonempty_unicode_count",
    "property_count",
    "property_keys",
    "property_values",
    "has_text_regions",
    "has_text_lines",
    "has_words",
    "has_unicode_text",
    "has_coordinates",
    "metadata_only",
    "sample_text",
]

with open(
    FILE_AUDIT_PATH,
    "w",
    encoding="utf-8-sig",
    newline=""
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(all_results)


# ============================================================
# SAVE PROPERTY DISTRIBUTION
# ============================================================

with open(
    PROPERTY_AUDIT_PATH,
    "w",
    encoding="utf-8-sig",
    newline=""
) as file:

    writer = csv.writer(file)

    writer.writerow([
        "xml_type",
        "property_key",
        "property_value",
        "count"
    ])

    for (key, value), count in sorted(
        gt_property_counter.items()
    ):
        writer.writerow(["gt", key, value, count])

    for (key, value), count in sorted(
        ocr_property_counter.items()
    ):
        writer.writerow(["ocr", key, value, count])


# ============================================================
# SUMMARY FUNCTION
# ============================================================

def print_summary(xml_type, results):

    successful = [
        row for row in results
        if row["parse_status"] == "success"
    ]

    failed = len(results) - len(successful)

    print(f"\n{xml_type.upper()} XML SUMMARY")
    print("-" * 70)

    print(f"Total files: {len(results)}")
    print(f"Successfully parsed: {len(successful)}")
    print(f"Parse errors: {failed}")

    metrics = [
        ("Files with TextRegion", "has_text_regions"),
        ("Files with TextLine", "has_text_lines"),
        ("Files with Word", "has_words"),
        ("Files with Unicode text", "has_unicode_text"),
        ("Files with coordinates", "has_coordinates"),
        ("Metadata-only files", "metadata_only"),
    ]

    for label, key in metrics:

        count = sum(
            1 for row in successful
            if row[key]
        )

        print(f"{label}: {count}")


# ============================================================
# PRINT FINAL SUMMARY
# ============================================================

print_summary("GT", gt_results)
print_summary("OCR", ocr_results)

print("\n" + "=" * 70)
print("DOCUMENT PAIR CHECK")
print("=" * 70)

print(f"GT document IDs: {len(gt_ids)}")
print(f"OCR document IDs: {len(ocr_ids)}")
print(f"Matching document IDs: {len(gt_ids & ocr_ids)}")
print(f"GT files without OCR pair: {len(missing_ocr)}")
print(f"OCR files without GT pair: {len(missing_gt)}")


# ============================================================
# PRINT PROPERTY DISTRIBUTION
# ============================================================

print("\n" + "=" * 70)
print("GT PROPERTY KEY/VALUE DISTRIBUTION")
print("=" * 70)

for (key, value), count in gt_property_counter.most_common(50):

    print(
        f"key={key!r:20s} "
        f"value={value!r:25s} "
        f"count={count}"
    )


# ============================================================
# PRINT SAMPLE TEXT FROM GT
# ============================================================

print("\n" + "=" * 70)
print("SAMPLE TEXT FOUND IN GT XML FILES")
print("=" * 70)

if not gt_text_samples:
    print("No non-empty Unicode text found in GT XML files.")
else:
    for document, texts in gt_text_samples[:5]:
        print(f"\nDocument: {document}")

        for text in texts:
            print(f"  {text}")


# ============================================================
# SAVE HUMAN-READABLE SAMPLE REPORT
# ============================================================

with open(
    SAMPLE_AUDIT_PATH,
    "w",
    encoding="utf-8"
) as file:

    file.write("PAGE XML SAMPLE INSPECTION\n")
    file.write("=" * 70 + "\n\n")

    file.write("GT XML TEXT SAMPLES\n")
    file.write("-" * 70 + "\n")

    for document, texts in gt_text_samples[:10]:

        file.write(f"\nDocument: {document}\n")

        for text in texts:
            file.write(f"  {text}\n")

    file.write("\nOCR XML TEXT SAMPLES\n")
    file.write("-" * 70 + "\n")

    for document, texts in ocr_text_samples[:5]:

        file.write(f"\nDocument: {document}\n")

        for text in texts:
            file.write(f"  {text}\n")

    file.write("\nMISSING OCR PAIRS\n")
    file.write("\n".join(missing_ocr))

    file.write("\n\nMISSING GT PAIRS\n")
    file.write("\n".join(missing_gt))


# ============================================================
# FINAL OUTPUT
# ============================================================

print("\n" + "=" * 70)
print("OUTPUT FILES")
print("=" * 70)

print(f"File-level audit:\n{FILE_AUDIT_PATH}")
print(f"\nProperty distribution:\n{PROPERTY_AUDIT_PATH}")
print(f"\nSample inspection:\n{SAMPLE_AUDIT_PATH}")

print("\nPAGE XML STRUCTURE AUDIT COMPLETED")
print("=" * 70)
