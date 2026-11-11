
import csv
import xml.etree.ElementTree as ET

from pathlib import Path
from collections import Counter


# ============================================================
# CONFIGURATION
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

OUTPUT_TXT = REPORTS_PATH / "day15_deep_xml_inspection.txt"
OUTPUT_CSV = REPORTS_PATH / "day15_region_annotation_details.csv"

SAMPLE_DOCUMENTS = [
    "0011500947",
    "2041063035",
    "0001139626",
    "tob02910.64",
]

MAX_REGIONS_PER_DOCUMENT = 12
MAX_LINES_PER_DOCUMENT = 15
MAX_WORDS_PER_DOCUMENT = 25


# ============================================================
# HELPERS
# ============================================================

def local_name(tag):
    return tag.split("}")[-1]


def find_xml(document_id, suffix):
    filename = f"{document_id}_{suffix}.xml"

    matches = list(DATASET_PATH.rglob(filename))

    if not matches:
        return None

    return matches[0]


def get_unicode_text(element):
    values = []

    for child in element.iter():
        if local_name(child.tag) == "Unicode":
            if child.text and child.text.strip():
                values.append(child.text.strip())

    return " ".join(values)


def get_coords(element):
    for child in element:
        if local_name(child.tag) == "Coords":
            return child.attrib.get("points", "")

    return ""


def get_nearest_region(element, parent_map):
    current = element

    while current in parent_map:
        current = parent_map[current]

        if local_name(current.tag) == "TextRegion":
            return current

    return None


def get_properties(element):
    properties = []

    for child in element.iter():

        if local_name(child.tag) == "Property":

            properties.append({
                "key": child.attrib.get("key", ""),
                "value": child.attrib.get("value", ""),
            })

    return properties


def get_custom_attribute(element):
    return element.attrib.get("custom", "")


def find_direct_children(element, tag_name):
    return [
        child for child in element
        if local_name(child.tag) == tag_name
    ]


# ============================================================
# XML INSPECTION
# ============================================================

def inspect_gt(document_id, report, csv_rows):

    xml_path = find_xml(document_id, "gt")

    report.write("\n" + "=" * 85 + "\n")
    report.write(f"GT XML: {document_id}\n")
    report.write("=" * 85 + "\n")

    if xml_path is None:
        report.write("GT XML FILE NOT FOUND\n")
        return

    root = ET.parse(xml_path).getroot()

    parent_map = {
        child: parent
        for parent in root.iter()
        for child in parent
    }

    regions = [
        element for element in root.iter()
        if local_name(element.tag) == "TextRegion"
    ]

    report.write(f"File: {xml_path}\n")
    report.write(f"Total TextRegion elements: {len(regions)}\n")

    report.write("\nREGION DETAILS\n")
    report.write("-" * 85 + "\n")

    for index, region in enumerate(
        regions[:MAX_REGIONS_PER_DOCUMENT],
        start=1
    ):

        region_id = region.attrib.get("id", "")
        region_type = region.attrib.get("type", "")
        region_custom = get_custom_attribute(region)
        coords = get_coords(region)

        properties = get_properties(region)

        report.write(f"\nRegion {index}\n")
        report.write(f"  ID: {region_id}\n")
        report.write(f"  Type attribute: {region_type}\n")
        report.write(f"  Custom attribute: {region_custom}\n")
        report.write(f"  Coordinates: {coords}\n")
        report.write(f"  Direct children: {[local_name(c.tag) for c in region]}\n")

        if properties:
            report.write("  Properties:\n")

            for prop in properties:
                report.write(
                    f"    {prop['key']} = {prop['value']}\n"
                )
        else:
            report.write("  Properties: none\n")

        # Find every Property and identify its nearest TextRegion.
        for element in region.iter():

            if local_name(element.tag) != "Property":
                continue

            csv_rows.append({
                "document": document_id,
                "xml_type": "gt",
                "region_id": region_id,
                "region_type": region_type,
                "property_key": element.attrib.get("key", ""),
                "property_value": element.attrib.get("value", ""),
                "region_coordinates": coords,
                "text": get_unicode_text(region),
            })

    # Check whether properties occur outside TextRegion elements.
    outside_properties = []

    for element in root.iter():

        if local_name(element.tag) != "Property":
            continue

        nearest_region = get_nearest_region(element, parent_map)

        if nearest_region is None:
            outside_properties.append(element.attrib)

    report.write("\nPROPERTIES OUTSIDE TEXTREGION\n")
    report.write("-" * 85 + "\n")

    if outside_properties:
        for prop in outside_properties[:20]:
            report.write(f"{prop}\n")
    else:
        report.write("None found.\n")


def inspect_ocr(document_id, report):

    xml_path = find_xml(document_id, "ocr")

    report.write("\n" + "=" * 85 + "\n")
    report.write(f"OCR XML: {document_id}\n")
    report.write("=" * 85 + "\n")

    if xml_path is None:
        report.write("OCR XML FILE NOT FOUND\n")
        return

    root = ET.parse(xml_path).getroot()

    report.write(f"File: {xml_path}\n")

    for tag_name in ["TextRegion", "TextLine", "Word"]:

        elements = [
            element for element in root.iter()
            if local_name(element.tag) == tag_name
        ]

        report.write(
            f"Total {tag_name} elements: {len(elements)}\n"
        )

    # Inspect TextLine elements.
    lines = [
        element for element in root.iter()
        if local_name(element.tag) == "TextLine"
    ]

    report.write("\nTEXT LINE SAMPLES\n")
    report.write("-" * 85 + "\n")

    for index, line in enumerate(
        lines[:MAX_LINES_PER_DOCUMENT],
        start=1
    ):

        line_id = line.attrib.get("id", "")
        coords = get_coords(line)
        text = get_unicode_text(line)

        report.write(f"\nLine {index}\n")
        report.write(f"  ID: {line_id}\n")
        report.write(f"  Coordinates: {coords}\n")
        report.write(f"  Text: {text}\n")

        for element in line.iter():

            if local_name(element.tag) == "TextEquiv":
                report.write(
                    f"  TextEquiv attributes: {element.attrib}\n"
                )

    # Inspect Word elements.
    words = [
        element for element in root.iter()
        if local_name(element.tag) == "Word"
    ]

    report.write("\nWORD SAMPLES\n")
    report.write("-" * 85 + "\n")

    for index, word in enumerate(
        words[:MAX_WORDS_PER_DOCUMENT],
        start=1
    ):

        word_id = word.attrib.get("id", "")
        coords = get_coords(word)
        text = get_unicode_text(word)

        report.write(
            f"{index}. ID={word_id} | Text={text!r} | "
            f"Coordinates={coords}\n"
        )

        for element in word.iter():

            if local_name(element.tag) == "TextEquiv":
                report.write(
                    f"   TextEquiv attributes: {element.attrib}\n"
                )


# ============================================================
# MAIN
# ============================================================

def main():

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset folder not found: {DATASET_PATH}"
        )

    REPORTS_PATH.mkdir(parents=True, exist_ok=True)

    csv_rows = []

    print("=" * 70)
    print("DAY 15: DEEP PAGE XML INSPECTION")
    print("=" * 70)

    with open(
        OUTPUT_TXT,
        "w",
        encoding="utf-8"
    ) as report:

        report.write("DEEP PAGE XML INSPECTION\n")
        report.write("=" * 85 + "\n")

        for document_id in SAMPLE_DOCUMENTS:

            print(f"Inspecting: {document_id}")

            inspect_gt(
                document_id,
                report,
                csv_rows
            )

            inspect_ocr(
                document_id,
                report
            )

    with open(
        OUTPUT_CSV,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        fieldnames = [
            "document",
            "xml_type",
            "region_id",
            "region_type",
            "property_key",
            "property_value",
            "region_coordinates",
            "text",
        ]

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(csv_rows)

    print("\n" + "=" * 70)
    print("INSPECTION COMPLETED")
    print("=" * 70)

    print(f"Documents inspected: {len(SAMPLE_DOCUMENTS)}")
    print(f"GT annotation records: {len(csv_rows)}")

    print(f"\nText report:\n{OUTPUT_TXT}")
    print(f"\nRegion details CSV:\n{OUTPUT_CSV}")


if __name__ == "__main__":
    main()
