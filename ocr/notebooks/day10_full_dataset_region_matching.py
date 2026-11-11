
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter
import csv


# ============================================================
# PATH CONFIGURATION
# ============================================================

project_path = Path(__file__).resolve().parents[1]

dataset_path = (
    project_path
    / "data"
    / "raw"
    / "invoices"
    / "archive"
    / "ImageAndXML_Data"
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def local_name(tag):
    return tag.split("}")[-1]


def get_coordinates(element):

    for child in element:

        if local_name(child.tag) == "Coords":

            points = child.get("points", "")
            coordinates = []

            for point in points.split():

                x, y = point.split(",")

                coordinates.append(
                    (float(x), float(y))
                )

            return coordinates

    return []


def get_bbox(points):

    if not points:
        return None

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]

    return (
        min(xs),
        min(ys),
        max(xs),
        max(ys)
    )


def calculate_overlap(ocr_bbox, gt_bbox):

    ox1, oy1, ox2, oy2 = ocr_bbox
    gx1, gy1, gx2, gy2 = gt_bbox

    intersection_width = max(
        0,
        min(ox2, gx2) - max(ox1, gx1)
    )

    intersection_height = max(
        0,
        min(oy2, gy2) - max(oy1, gy1)
    )

    intersection_area = (
        intersection_width * intersection_height
    )

    ocr_area = (
        (ox2 - ox1) * (oy2 - oy1)
    )

    if ocr_area <= 0:
        return 0

    return (
        intersection_area / ocr_area
    ) * 100


# ============================================================
# EXTRACT GROUND-TRUTH REGIONS
# ============================================================

def extract_gt_regions(file_path):

    tree = ET.parse(file_path)
    root = tree.getroot()

    regions = []

    for element in root.iter():

        if local_name(element.tag) != "TextRegion":
            continue

        entity = None

        for child in element:

            if local_name(child.tag) == "Property":

                if child.get("key") == "entity":
                    entity = child.get("value")

        bbox = get_bbox(
            get_coordinates(element)
        )

        if entity and bbox:

            regions.append({
                "entity": entity,
                "bbox": bbox
            })

    return regions


# ============================================================
# EXTRACT OCR REGIONS
# ============================================================

def extract_ocr_regions(file_path):

    tree = ET.parse(file_path)
    root = tree.getroot()

    regions = []

    for element in root.iter():

        if local_name(element.tag) != "TextRegion":
            continue

        bbox = get_bbox(
            get_coordinates(element)
        )

        if not bbox:
            continue

        texts = []

        for child in element.iter():

            if local_name(child.tag) == "Unicode":

                if child.text and child.text.strip():

                    texts.append(
                        child.text.strip()
                    )

        if texts:

            regions.append({
                "text": " ".join(texts),
                "bbox": bbox
            })

    return regions


# ============================================================
# FIELD EXTRACTION SAMPLE CONFIGURATION
# ============================================================

field_examples = {
    "invoice_info": [],
    "total": []
}

MAX_EXAMPLES_PER_FIELD = 15


# ============================================================
# INITIALIZE COUNTERS
# ============================================================

gt_files = sorted(
    dataset_path.rglob("*_gt.xml")
)

total_gt_regions = 0
total_ocr_regions = 0

strong_matches = 0
weak_matches = 0
unmatched_regions = 0

entity_counts = Counter()

file_errors = []
missing_ocr_files = []

# Store detailed information for every OCR region
audit_records = []


# ============================================================
# MAIN DATASET MATCHING AUDIT
# ============================================================

print("FULL DATASET REGION MATCHING AUDIT")
print("=" * 60)

for index, gt_file in enumerate(gt_files, start=1):

    sample_name = gt_file.name.replace(
        "_gt.xml", ""
    )

    ocr_file = gt_file.with_name(
        f"{sample_name}_ocr.xml"
    )

    if not ocr_file.exists():

        missing_ocr_files.append(sample_name)
        continue

    try:

        gt_regions = extract_gt_regions(gt_file)

        ocr_regions = extract_ocr_regions(ocr_file)

        total_gt_regions += len(gt_regions)

        total_ocr_regions += len(ocr_regions)

        # ----------------------------------------------------
        # MATCH EACH OCR REGION WITH THE BEST GT REGION
        # ----------------------------------------------------

        for ocr_region in ocr_regions:

            best_match = None
            best_overlap = 0

            for gt_region in gt_regions:

                overlap = calculate_overlap(
                    ocr_region["bbox"],
                    gt_region["bbox"]
                )

                if overlap > best_overlap:

                    best_overlap = overlap

                    best_match = gt_region["entity"]

            # ------------------------------------------------
            # CLASSIFY EACH OCR REGION
            # ------------------------------------------------

            if best_overlap >= 50:

                match_status = "Strong"

                strong_matches += 1

                entity_counts[best_match] += 1

                # Collect invoice information and total samples

                if best_match in field_examples:

                    if len(field_examples[best_match]) < MAX_EXAMPLES_PER_FIELD:

                        field_examples[best_match].append({

                            "invoice": sample_name,

                            "text": ocr_region["text"],

                            "overlap": round(best_overlap, 2)

                        })

            elif best_overlap > 0:

                match_status = "Weak"

                weak_matches += 1

            else:

                match_status = "Unmatched"

                unmatched_regions += 1

            # ------------------------------------------------
            # STORE EVERY OCR REGION
            # ------------------------------------------------

            audit_records.append({

                "invoice_id": sample_name,

                "ocr_text": ocr_region["text"],

                "matched_entity": best_match,

                "overlap_percentage": round(best_overlap, 2),

                "match_status": match_status,

                "ocr_bbox": str(ocr_region["bbox"])

            })

    except Exception as error:

        file_errors.append(
            (gt_file.name, str(error))
        )

    # --------------------------------------------------------
    # PROGRESS
    # --------------------------------------------------------

    if index % 50 == 0:

        print(
            f"Processed {index}/{len(gt_files)} GT files"
        )


# ============================================================
# SAVE DETAILED AUDIT REPORT
# ============================================================

reports_path = project_path / "reports"

reports_path.mkdir(
    parents=True,
    exist_ok=True
)

csv_path = reports_path / "day11_region_matching_audit.csv"

with open(
    csv_path,
    "w",
    newline="",
    encoding="utf-8-sig"
) as csv_file:

    fieldnames = [
        "invoice_id",
        "ocr_text",
        "matched_entity",
        "overlap_percentage",
        "match_status",
        "ocr_bbox"
    ]

    writer = csv.DictWriter(
        csv_file,
        fieldnames=fieldnames
    )

    writer.writeheader()

    writer.writerows(audit_records)


print("\nAUDIT CSV SAVED SUCCESSFULLY")

print(csv_path)

print("Total records:", len(audit_records))


# ============================================================
# CALCULATE FINAL MATCHING RESULTS
# ============================================================

matched_regions = (
    strong_matches + weak_matches
)

classified_regions = (
    strong_matches
    + weak_matches
    + unmatched_regions
)


# ============================================================
# DISPLAY FINAL RESULTS
# ============================================================

print("\nFINAL RESULTS")
print("=" * 60)

print("GT files found:", len(gt_files))

print("GT regions:", total_gt_regions)

print(
    "OCR regions containing text:",
    total_ocr_regions
)

print("\nMATCHING RESULTS")

print(
    "Regions with any overlap:",
    matched_regions
)

print(
    "Strong matches (>=50%):",
    strong_matches
)

print(
    "Weak matches (<50% but >0%):",
    weak_matches
)

print(
    "Regions with no overlap:",
    unmatched_regions
)


# ============================================================
# MATCHING PERCENTAGES
# ============================================================

if total_ocr_regions > 0:

    any_overlap_rate = (
        matched_regions / total_ocr_regions
    ) * 100

    strong_match_rate = (
        strong_matches / total_ocr_regions
    ) * 100

    print(
        "\nAny-overlap rate:",
        round(any_overlap_rate, 2),
        "%"
    )

    print(
        "Strong-match rate:",
        round(strong_match_rate, 2),
        "%"
    )


# ============================================================
# ENTITY DISTRIBUTION
# ============================================================

print("\nSTRONG MATCH ENTITY DISTRIBUTION")

print(entity_counts)


# ============================================================
# DATASET ERRORS
# ============================================================

print("\nDATASET ERRORS")

print(
    "Missing OCR files:",
    len(missing_ocr_files)
)

print(
    "XML processing errors:",
    len(file_errors)
)

if missing_ocr_files:

    print(
        "Missing OCR examples:",
        missing_ocr_files[:10]
    )

if file_errors:

    print(
        "Error examples:",
        file_errors[:5]
    )


# ============================================================
# CONSISTENCY CHECK
# ============================================================

print("\nCOUNT CONSISTENCY CHECK")
print("=" * 60)

print(
    "Total classified OCR regions:",
    classified_regions
)

print(
    "Total OCR regions:",
    total_ocr_regions
)

if classified_regions == total_ocr_regions:

    print("PASS: All OCR regions are classified exactly once.")

else:

    print("WARNING: OCR region counts do not match.")

    print(
        "Difference:",
        total_ocr_regions - classified_regions
    )


# ============================================================
# CSV RECORD CONSISTENCY CHECK
# ============================================================

print("\nCSV RECORD CONSISTENCY CHECK")

print(
    "CSV records:",
    len(audit_records)
)

if len(audit_records) == classified_regions:

    print("PASS: CSV records match classified OCR regions.")

else:

    print("WARNING: CSV record count does not match.")


# ============================================================
# FIELD EXTRACTION SAMPLES
# ============================================================

print("\nFIELD EXTRACTION SAMPLE")
print("=" * 60)

for entity, examples in field_examples.items():

    print(
        f"\nENTITY: {entity.upper()}"
    )

    for example in examples:

        print(
            "\nInvoice:",
            example["invoice"]
        )

        print(
            "Text:",
            example["text"]
        )

        print(
            "Overlap:",
            example["overlap"],
            "%"
        )


# ============================================================
# AUDIT COMPLETED
# ============================================================

print("\nFULL DATASET AUDIT COMPLETED")
