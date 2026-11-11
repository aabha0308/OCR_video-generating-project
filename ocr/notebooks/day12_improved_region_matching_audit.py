
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter, defaultdict

try:
    from PIL import Image
except ImportError:
    Image = None


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

reports_path = project_path / "reports"
reports_path.mkdir(parents=True, exist_ok=True)

region_csv_path = (
    reports_path / "day12_improved_region_matching_audit.csv"
)

document_csv_path = (
    reports_path / "day12_document_type_review.csv"
)

IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"
}


# ============================================================
# XML HELPERS
# ============================================================

def local_name(tag):
    return tag.split("}")[-1]


def get_direct_child(element, child_name):
    for child in element:
        if local_name(child.tag) == child_name:
            return child
    return None


def get_coordinates(element):
    coords_element = get_direct_child(element, "Coords")

    if coords_element is None:
        return []

    points = coords_element.get("points", "")
    coordinates = []

    for point in points.split():
        try:
            x, y = point.split(",")
            coordinates.append((float(x), float(y)))
        except (ValueError, TypeError):
            continue

    return coordinates


def get_bbox(points):
    if not points:
        return None

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]

    bbox = (
        min(xs),
        min(ys),
        max(xs),
        max(ys)
    )

    x1, y1, x2, y2 = bbox

    if x2 <= x1 or y2 <= y1:
        return None

    return bbox


def get_page_dimensions(root):
    for element in root.iter():
        if local_name(element.tag) == "Page":
            try:
                width = int(element.get("imageWidth"))
                height = int(element.get("imageHeight"))
                return width, height
            except (TypeError, ValueError):
                return None, None

    return None, None


# ============================================================
# BOUNDING BOX METRICS
# ============================================================

def calculate_metrics(ocr_bbox, gt_bbox):
    ox1, oy1, ox2, oy2 = ocr_bbox
    gx1, gy1, gx2, gy2 = gt_bbox

    intersection_width = max(
        0, min(ox2, gx2) - max(ox1, gx1)
    )

    intersection_height = max(
        0, min(oy2, gy2) - max(oy1, gy1)
    )

    intersection_area = (
        intersection_width * intersection_height
    )

    ocr_area = (ox2 - ox1) * (oy2 - oy1)
    gt_area = (gx2 - gx1) * (gy2 - gy1)

    union_area = ocr_area + gt_area - intersection_area

    iou = (
        intersection_area / union_area
        if union_area > 0 else 0
    )

    ocr_coverage = (
        intersection_area / ocr_area
        if ocr_area > 0 else 0
    )

    gt_coverage = (
        intersection_area / gt_area
        if gt_area > 0 else 0
    )

    return {
        "intersection_area": intersection_area,
        "iou": iou,
        "ocr_coverage": ocr_coverage,
        "gt_coverage": gt_coverage
    }


# ============================================================
# EXTRACT GT REGIONS
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

        bbox = get_bbox(get_coordinates(element))

        if bbox:
            regions.append({
                "region_id": len(regions),
                "entity": entity or "unknown",
                "bbox": bbox
            })

    return root, regions


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

        bbox = get_bbox(get_coordinates(element))

        if not bbox:
            continue

        texts = []

        for child in element.iter():
            if local_name(child.tag) == "Unicode":
                if child.text and child.text.strip():
                    texts.append(child.text.strip())

        text = " ".join(texts).strip()

        if text:
            regions.append({
                "region_id": len(regions),
                "text": text,
                "bbox": bbox
            })

    return root, regions


# ============================================================
# IMAGE DIMENSION CHECK
# ============================================================

def find_image_for_xml(gt_file):
    stem = gt_file.name.replace("_gt.xml", "")

    for file_path in gt_file.parent.iterdir():
        if (
            file_path.is_file()
            and file_path.stem == stem
            and file_path.suffix.lower() in IMAGE_EXTENSIONS
        ):
            return file_path

    return None


def get_actual_image_dimensions(image_path):
    if image_path is None or Image is None:
        return None, None

    try:
        with Image.open(image_path) as image:
            return image.size
    except Exception:
        return None, None


# ============================================================
# DOCUMENT TYPE HEURISTIC
# ============================================================

DOCUMENT_KEYWORDS = {
    "invoice": [
        "invoice",
        "tax invoice",
        "invoice no",
        "invoice number"
    ],
    "purchase_order": [
        "purchase order",
        "purchase order no",
        "po number"
    ],
    "estimate": [
        "estimate",
        "quotation",
        "pro forma"
    ]
}


def suggest_document_type(all_text):
    text = all_text.lower()

    matches = {}

    for document_type, keywords in DOCUMENT_KEYWORDS.items():
        found = [
            keyword for keyword in keywords
            if keyword in text
        ]

        matches[document_type] = found

    # These are heuristic suggestions, not verified labels.
    priority = [
        "purchase_order",
        "estimate",
        "invoice"
    ]

    for document_type in priority:
        if matches[document_type]:
            return document_type, matches[document_type]

    return "unclassified", []


# ============================================================
# MAIN AUDIT
# ============================================================

gt_files = sorted(dataset_path.rglob("*_gt.xml"))

if not gt_files:
    raise FileNotFoundError(
        f"No GT XML files found in: {dataset_path}"
    )

all_region_records = []
document_records = []

total_gt_regions = 0
total_ocr_regions = 0

any_overlap_count = 0
iou_50_count = 0
iou_25_count = 0

ocr_coverage_50_count = 0
ocr_coverage_80_count = 0

gt_coverage_50_count = 0

gt_region_assignment_counts = Counter()
entity_counts = Counter()

missing_ocr_files = []
xml_errors = []
dimension_mismatches = []
missing_images = []

document_type_counts = Counter()

print("IMPROVED REGION MATCHING AUDIT")
print("=" * 65)

for index, gt_file in enumerate(gt_files, start=1):

    sample_name = gt_file.name.replace("_gt.xml", "")

    ocr_file = gt_file.with_name(
        f"{sample_name}_ocr.xml"
    )

    if not ocr_file.exists():
        missing_ocr_files.append(sample_name)
        continue

    try:
        gt_root, gt_regions = extract_gt_regions(gt_file)
        ocr_root, ocr_regions = extract_ocr_regions(ocr_file)

        total_gt_regions += len(gt_regions)
        total_ocr_regions += len(ocr_regions)

        gt_width, gt_height = get_page_dimensions(gt_root)
        ocr_width, ocr_height = get_page_dimensions(ocr_root)

        image_file = find_image_for_xml(gt_file)
        image_width, image_height = (
            get_actual_image_dimensions(image_file)
        )

        if image_file is None:
            missing_images.append(sample_name)

        dimensions_match = (
            gt_width == ocr_width
            and gt_height == ocr_height
        )

        image_dimensions_match = None

        if (
            image_width is not None
            and image_height is not None
            and gt_width is not None
            and gt_height is not None
        ):
            image_dimensions_match = (
                image_width == gt_width
                and image_height == gt_height
            )

            if not image_dimensions_match:
                dimension_mismatches.append({
                    "document": sample_name,
                    "gt_xml": f"{gt_width}x{gt_height}",
                    "image": f"{image_width}x{image_height}"
                })

        if not dimensions_match:
            dimension_mismatches.append({
                "document": sample_name,
                "gt_xml": f"{gt_width}x{gt_height}",
                "ocr_xml": f"{ocr_width}x{ocr_height}"
            })

        document_texts = [
            region["text"] for region in ocr_regions
        ]

        all_text = " ".join(document_texts)

        suggested_type, matched_keywords = (
            suggest_document_type(all_text)
        )

        document_type_counts[suggested_type] += 1

        document_records.append({
            "document": sample_name,
            "gt_region_count": len(gt_regions),
            "ocr_region_count": len(ocr_regions),
            "suggested_document_type": suggested_type,
            "matched_keywords": "; ".join(matched_keywords),
            "gt_page_width": gt_width,
            "gt_page_height": gt_height,
            "ocr_page_width": ocr_width,
            "ocr_page_height": ocr_height,
            "image_file_found": image_file is not None,
            "image_width": image_width,
            "image_height": image_height,
            "gt_ocr_dimensions_match": dimensions_match,
            "image_gt_dimensions_match": image_dimensions_match
        })

        # Each OCR region is matched to its best-IoU GT region.
        # A separate best OCR-coverage match is also recorded.

        for ocr_region in ocr_regions:

            best_iou_match = None
            best_coverage_match = None

            for gt_region in gt_regions:

                metrics = calculate_metrics(
                    ocr_region["bbox"],
                    gt_region["bbox"]
                )

                if metrics["intersection_area"] <= 0:
                    continue

                if (
                    best_iou_match is None
                    or metrics["iou"] > best_iou_match["iou"]
                ):
                    best_iou_match = {
                        **metrics,
                        "gt_region_id": gt_region["region_id"],
                        "entity": gt_region["entity"]
                    }

                if (
                    best_coverage_match is None
                    or metrics["ocr_coverage"]
                    > best_coverage_match["ocr_coverage"]
                ):
                    best_coverage_match = {
                        **metrics,
                        "gt_region_id": gt_region["region_id"],
                        "entity": gt_region["entity"]
                    }

            if best_iou_match is not None:
                any_overlap_count += 1

                iou = best_iou_match["iou"]

                if iou >= 0.50:
                    iou_50_count += 1

                if iou >= 0.25:
                    iou_25_count += 1

                gt_region_assignment_counts[
                    (sample_name, best_iou_match["gt_region_id"])
                ] += 1

                entity_counts[
                    best_iou_match["entity"]
                ] += 1

                if best_iou_match["gt_coverage"] >= 0.50:
                    gt_coverage_50_count += 1

            if best_coverage_match is not None:
                coverage = best_coverage_match["ocr_coverage"]

                if coverage >= 0.50:
                    ocr_coverage_50_count += 1

                if coverage >= 0.80:
                    ocr_coverage_80_count += 1

            all_region_records.append({
                "document": sample_name,
                "ocr_region_id": ocr_region["region_id"],
                "ocr_text": ocr_region["text"],
                "ocr_x1": ocr_region["bbox"][0],
                "ocr_y1": ocr_region["bbox"][1],
                "ocr_x2": ocr_region["bbox"][2],
                "ocr_y2": ocr_region["bbox"][3],

                "best_iou_gt_region_id": (
                    best_iou_match["gt_region_id"]
                    if best_iou_match else None
                ),
                "best_iou_entity": (
                    best_iou_match["entity"]
                    if best_iou_match else None
                ),
                "best_iou": (
                    round(best_iou_match["iou"], 5)
                    if best_iou_match else 0
                ),
                "gt_coverage_at_best_iou": (
                    round(best_iou_match["gt_coverage"], 5)
                    if best_iou_match else 0
                ),
                "ocr_coverage_at_best_iou": (
                    round(best_iou_match["ocr_coverage"], 5)
                    if best_iou_match else 0
                ),

                "best_coverage_gt_region_id": (
                    best_coverage_match["gt_region_id"]
                    if best_coverage_match else None
                ),
                "best_coverage_entity": (
                    best_coverage_match["entity"]
                    if best_coverage_match else None
                ),
                "best_ocr_coverage": (
                    round(best_coverage_match["ocr_coverage"], 5)
                    if best_coverage_match else 0
                ),
                "gt_coverage_at_best_ocr_coverage": (
                    round(best_coverage_match["gt_coverage"], 5)
                    if best_coverage_match else 0
                )
            })

    except Exception as error:
        xml_errors.append({
            "file": gt_file.name,
            "error": str(error)
        })

    if index % 50 == 0:
        print(f"Processed {index}/{len(gt_files)} GT files")


# ============================================================
# DUPLICATE / MANY-TO-ONE ASSIGNMENT ANALYSIS
# ============================================================

assigned_gt_regions = len(gt_region_assignment_counts)

reused_gt_regions = sum(
    1 for count in gt_region_assignment_counts.values()
    if count > 1
)

extra_assignments = sum(
    count - 1
    for count in gt_region_assignment_counts.values()
    if count > 1
)

unassigned_ocr_regions = (
    total_ocr_regions - any_overlap_count
)


# ============================================================
# SAVE REGION CSV
# ============================================================

if all_region_records:
    with open(
        region_csv_path,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=list(all_region_records[0].keys())
        )

        writer.writeheader()
        writer.writerows(all_region_records)


# ============================================================
# SAVE DOCUMENT REVIEW CSV
# ============================================================

if document_records:
    with open(
        document_csv_path,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=list(document_records[0].keys())
        )

        writer.writeheader()
        writer.writerows(document_records)


# ============================================================
# FINAL REPORT
# ============================================================

def percentage(count, total):
    return round((count / total) * 100, 2) if total else 0


print("\nFINAL DATASET COUNTS")
print("=" * 65)
print("GT files found:", len(gt_files))
print("GT regions:", total_gt_regions)
print("OCR regions containing text:", total_ocr_regions)

print("\nIOU MATCHING")
print("=" * 65)
print("OCR regions with any intersection:", any_overlap_count)
print("OCR regions with IoU >= 0.25:", iou_25_count)
print("OCR regions with IoU >= 0.50:", iou_50_count)
print("No intersection:", unassigned_ocr_regions)

print("\nCOVERAGE METRICS")
print("=" * 65)
print("OCR coverage >= 50%:", ocr_coverage_50_count)
print("OCR coverage >= 80%:", ocr_coverage_80_count)
print("GT coverage >= 50% at best IoU:", gt_coverage_50_count)

print("\nMANY-TO-ONE ASSIGNMENTS")
print("=" * 65)
print("Distinct GT regions assigned:", assigned_gt_regions)
print("GT regions receiving multiple OCR assignments:", reused_gt_regions)
print("Extra OCR assignments beyond first:", extra_assignments)

print("\nENTITY DISTRIBUTION AT BEST IOU")
print("=" * 65)
print(entity_counts)

print("\nSUGGESTED DOCUMENT TYPE DISTRIBUTION")
print("=" * 65)
print(document_type_counts)

print("\nDIMENSION AND FILE CHECKS")
print("=" * 65)
print("Missing OCR XML files:", len(missing_ocr_files))
print("XML processing errors:", len(xml_errors))
print("Images not found beside GT XML:", len(missing_images))
print("Dimension mismatch records:", len(dimension_mismatches))
print("Pillow available:", Image is not None)

print("\nRATES")
print("=" * 65)
print(
    "Any intersection rate:",
    percentage(any_overlap_count, total_ocr_regions), "%"
)
print(
    "IoU >= 0.25 rate:",
    percentage(iou_25_count, total_ocr_regions), "%"
)
print(
    "IoU >= 0.50 rate:",
    percentage(iou_50_count, total_ocr_regions), "%"
)
print(
    "Unmatched OCR region rate:",
    percentage(unassigned_ocr_regions, total_ocr_regions), "%"
)

print("\nOUTPUT FILES")
print("=" * 65)
print("Region audit:", region_csv_path)
print("Document review:", document_csv_path)

print("\nERROR EXAMPLES")
print("=" * 65)
print("Missing OCR examples:", missing_ocr_files[:10])
print("XML error examples:", xml_errors[:5])
print("Dimension mismatch examples:", dimension_mismatches[:10])

print("\nAUDIT COMPLETED")
