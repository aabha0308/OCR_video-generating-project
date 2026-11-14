
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter
from statistics import mean


# ============================================================
# CONFIGURATION
# ============================================================

DATA_DIR = Path(
    r"D:\OCR_Internship\ocr\data\raw\invoices\archive\ImageAndXML_Data"
)

REPORT_DIR = Path(
    r"D:\OCR_Internship\ocr\reports"
)

OUTPUT_CSV = REPORT_DIR / "day16_gt_ocr_line_mapping_audit.csv"
SUMMARY_TXT = REPORT_DIR / "day16_gt_ocr_line_mapping_summary.txt"

MIN_LINE_COVERAGE = 0.50
MIN_COVERAGE_MARGIN = 0.10


# ============================================================
# XML HELPERS
# ============================================================

def local_tag(element):
    """Return XML tag without its namespace."""
    return element.tag.split("}")[-1]


def direct_children(element, tag_name):
    """Return only direct children with the requested tag."""
    return [
        child for child in list(element)
        if local_tag(child) == tag_name
    ]


def extract_text_equiv(text_equiv):
    """
    Extract Unicode text from one TextEquiv element.
    Only reads its direct Unicode children.
    """
    unicode_elements = direct_children(text_equiv, "Unicode")

    parts = [
        (item.text or "").strip()
        for item in unicode_elements
        if (item.text or "").strip()
    ]

    return " ".join(parts).strip()


def extract_text_and_confidence(element):
    """
    Extract text and confidence from the first direct TextEquiv.
    Returns (text, confidence).
    """
    text_equivs = direct_children(element, "TextEquiv")

    if not text_equivs:
        return "", None

    selected = text_equivs[0]

    text = extract_text_equiv(selected)

    confidence = selected.attrib.get("conf")

    try:
        confidence = float(confidence) if confidence is not None else None
    except (ValueError, TypeError):
        confidence = None

    return text, confidence


# ============================================================
# GEOMETRY HELPERS
# ============================================================

def parse_points(points_string):
    points = []

    if not points_string:
        return points

    for item in points_string.strip().split():
        if "," not in item:
            continue

        try:
            x_str, y_str = item.split(",", 1)
            points.append((float(x_str), float(y_str)))
        except ValueError:
            continue

    return points


def points_to_bbox(points):
    if not points:
        return None

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]

    return min(xs), min(ys), max(xs), max(ys)


def extract_bbox(element):
    coords_elements = direct_children(element, "Coords")

    if not coords_elements:
        return None

    points_string = coords_elements[0].attrib.get("points", "")
    return points_to_bbox(parse_points(points_string))


def bbox_area(bbox):
    if bbox is None:
        return 0.0

    x1, y1, x2, y2 = bbox

    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def calculate_overlap(bbox_a, bbox_b):
    """
    Calculate intersection, OCR line coverage,
    GT region coverage and IoU using bounding boxes.
    """
    if bbox_a is None or bbox_b is None:
        return 0.0, 0.0, 0.0, 0.0

    ax1, ay1, ax2, ay2 = bbox_a
    bx1, by1, bx2, by2 = bbox_b

    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    intersection = (
        max(0.0, ix2 - ix1) *
        max(0.0, iy2 - iy1)
    )

    area_a = bbox_area(bbox_a)
    area_b = bbox_area(bbox_b)

    union = area_a + area_b - intersection

    line_coverage = (
        intersection / area_a if area_a > 0 else 0.0
    )

    gt_coverage = (
        intersection / area_b if area_b > 0 else 0.0
    )

    iou = intersection / union if union > 0 else 0.0

    return intersection, line_coverage, gt_coverage, iou


# ============================================================
# OCR TEXT EXTRACTION
# ============================================================

def extract_ocr_line_text(line):
    """
    Extract OCR text from a TextLine.

    PAGE XML may store text in either:
    1. A direct TextEquiv under TextLine.
    2. TextEquiv elements under individual Word children.

    This dataset commonly uses the second structure.
    """

    # Case 1: TextEquiv directly under TextLine
    direct_text, direct_confidence = extract_text_and_confidence(line)

    if direct_text:
        return {
            "text": direct_text,
            "confidence": direct_confidence,
            "word_count": 0,
            "confidence_source": (
                "line" if direct_confidence is not None
                else "line_text_no_confidence"
            )
        }

    # Case 2: TextEquiv under individual Word elements
    words = direct_children(line, "Word")

    word_texts = []
    word_confidences = []

    for word in words:
        word_text, word_confidence = extract_text_and_confidence(word)

        if word_text:
            word_texts.append(word_text)

        if word_confidence is not None:
            word_confidences.append(word_confidence)

    reconstructed_text = " ".join(word_texts).strip()

    if word_confidences:
        line_confidence = mean(word_confidences)
        confidence_source = "average_of_word_confidences"
    else:
        line_confidence = None
        confidence_source = "unavailable"

    return {
        "text": reconstructed_text,
        "confidence": line_confidence,
        "word_count": len(word_texts),
        "confidence_source": confidence_source
    }


def extract_ocr_lines(ocr_xml_path):
    tree = ET.parse(ocr_xml_path)
    root = tree.getroot()

    lines = []

    for line in root.iter():

        if local_tag(line) != "TextLine":
            continue

        line_id = line.attrib.get("id", "")
        bbox = extract_bbox(line)

        if bbox is None:
            continue

        extracted = extract_ocr_line_text(line)

        lines.append({
            "line_id": line_id,
            "text": extracted["text"],
            "confidence": extracted["confidence"],
            "word_count": extracted["word_count"],
            "confidence_source": extracted["confidence_source"],
            "bbox": bbox
        })

    return lines


# ============================================================
# GROUND-TRUTH REGION EXTRACTION
# ============================================================

def extract_gt_regions(gt_xml_path):
    tree = ET.parse(gt_xml_path)
    root = tree.getroot()

    regions = []

    for region in root.iter():

        if local_tag(region) != "TextRegion":
            continue

        region_id = region.attrib.get("id", "")
        bbox = extract_bbox(region)

        entity = ""

        for prop in direct_children(region, "Property"):
            if prop.attrib.get("key") == "entity":
                entity = prop.attrib.get("value", "")
                break

        if bbox is None:
            continue

        regions.append({
            "region_id": region_id,
            "entity": entity,
            "bbox": bbox
        })

    return regions


# ============================================================
# SPATIAL MATCHING
# ============================================================

def match_line_to_regions(line, regions):
    candidates = []

    for region in regions:

        intersection, line_coverage, gt_coverage, iou = (
            calculate_overlap(line["bbox"], region["bbox"])
        )

        if intersection <= 0:
            continue

        candidates.append({
            "region_id": region["region_id"],
            "entity": region["entity"],
            "intersection": intersection,
            "line_coverage": line_coverage,
            "gt_coverage": gt_coverage,
            "iou": iou
        })

    candidates.sort(
        key=lambda item: (
            item["line_coverage"],
            item["iou"]
        ),
        reverse=True
    )

    if not candidates:
        return {
            "status": "unmatched",
            "best": None,
            "second": None
        }

    best = candidates[0]
    second = candidates[1] if len(candidates) > 1 else None

    if best["line_coverage"] < MIN_LINE_COVERAGE:
        status = "low_overlap"

    elif (
        second is not None
        and second["line_coverage"] >= MIN_LINE_COVERAGE
        and best["line_coverage"] - second["line_coverage"]
        < MIN_COVERAGE_MARGIN
    ):
        status = "ambiguous"

    else:
        status = "matched"

    return {
        "status": status,
        "best": best,
        "second": second
    }


# ============================================================
# MAIN AUDIT
# ============================================================

def main():

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    if not DATA_DIR.exists():
        raise FileNotFoundError(
            f"Dataset directory does not exist: {DATA_DIR}"
        )

    gt_files = sorted(DATA_DIR.glob("*_gt.xml"))

    if not gt_files:
        raise FileNotFoundError(
            f"No GT XML files found in: {DATA_DIR}"
        )

    all_rows = []

    document_count = 0
    missing_ocr_count = 0
    xml_error_count = 0

    total_gt_regions = 0
    total_ocr_lines = 0

    status_counts = Counter()
    entity_counts = Counter()
    confidence_source_counts = Counter()

    lines_with_text = 0
    lines_without_text = 0
    lines_with_confidence = 0
    lines_without_confidence = 0

    for index, gt_path in enumerate(gt_files, start=1):

        document_id = gt_path.name.replace("_gt.xml", "")
        ocr_path = DATA_DIR / f"{document_id}_ocr.xml"

        if not ocr_path.exists():
            missing_ocr_count += 1
            print(f"Missing OCR XML: {document_id}")
            continue

        try:
            gt_regions = extract_gt_regions(gt_path)
            ocr_lines = extract_ocr_lines(ocr_path)

        except ET.ParseError as error:
            xml_error_count += 1
            print(f"XML parsing error: {document_id}: {error}")
            continue

        document_count += 1

        total_gt_regions += len(gt_regions)
        total_ocr_lines += len(ocr_lines)

        for line in ocr_lines:

            result = match_line_to_regions(line, gt_regions)

            best = result["best"]
            second = result["second"]

            if best:
                assigned_region_id = best["region_id"]
                assigned_entity = best["entity"]
                best_coverage = best["line_coverage"]
                best_gt_coverage = best["gt_coverage"]
                best_iou = best["iou"]
            else:
                assigned_region_id = ""
                assigned_entity = ""
                best_coverage = 0.0
                best_gt_coverage = 0.0
                best_iou = 0.0

            if second:
                second_region_id = second["region_id"]
                second_entity = second["entity"]
                second_coverage = second["line_coverage"]
                second_iou = second["iou"]
            else:
                second_region_id = ""
                second_entity = ""
                second_coverage = 0.0
                second_iou = 0.0

            status = result["status"]
            status_counts[status] += 1

            if status == "matched":
                entity_counts[assigned_entity] += 1

            text = line["text"]
            confidence = line["confidence"]

            if text:
                lines_with_text += 1
            else:
                lines_without_text += 1

            if confidence is not None:
                lines_with_confidence += 1
            else:
                lines_without_confidence += 1

            confidence_source_counts[
                line["confidence_source"]
            ] += 1

            x1, y1, x2, y2 = line["bbox"]

            all_rows.append({
                "document_id": document_id,
                "ocr_line_id": line["line_id"],
                "ocr_text": text,
                "ocr_line_confidence": (
                    round(confidence, 6)
                    if confidence is not None else ""
                ),
                "ocr_word_count": line["word_count"],
                "ocr_confidence_source": line["confidence_source"],
                "ocr_x1": x1,
                "ocr_y1": y1,
                "ocr_x2": x2,
                "ocr_y2": y2,
                "match_status": status,
                "matched_gt_region_id": assigned_region_id,
                "matched_entity": assigned_entity,
                "best_line_coverage": round(best_coverage, 5),
                "best_gt_coverage": round(best_gt_coverage, 5),
                "best_iou": round(best_iou, 5),
                "second_gt_region_id": second_region_id,
                "second_entity": second_entity,
                "second_line_coverage": round(second_coverage, 5),
                "second_iou": round(second_iou, 5)
            })

        if index % 50 == 0:
            print(f"Processed {index}/{len(gt_files)} GT files")

    # ========================================================
    # CSV OUTPUT
    # ========================================================

    fieldnames = [
        "document_id",
        "ocr_line_id",
        "ocr_text",
        "ocr_line_confidence",
        "ocr_word_count",
        "ocr_confidence_source",
        "ocr_x1",
        "ocr_y1",
        "ocr_x2",
        "ocr_y2",
        "match_status",
        "matched_gt_region_id",
        "matched_entity",
        "best_line_coverage",
        "best_gt_coverage",
        "best_iou",
        "second_gt_region_id",
        "second_entity",
        "second_line_coverage",
        "second_iou"
    ]

    with open(
        OUTPUT_CSV,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(all_rows)

    # ========================================================
    # SUMMARY OUTPUT
    # ========================================================

    total_lines = len(all_rows)

    def percentage(count, total):
        return count / total * 100 if total else 0.0

    summary = [
        "DAY 16: GT-OCR LINE MAPPING AUDIT - TEXT EXTRACTION FIX",
        "=" * 65,
        f"Dataset directory: {DATA_DIR}",
        f"GT XML files found: {len(gt_files)}",
        f"Documents successfully processed: {document_count}",
        f"Missing OCR XML files: {missing_ocr_count}",
        f"XML parsing errors: {xml_error_count}",
        "",
        f"Total GT regions: {total_gt_regions}",
        f"Total OCR text lines: {total_ocr_lines}",
        f"Total output rows: {total_lines}",
        "",
        "OCR TEXT EXTRACTION",
        "-" * 65,
        f"Lines with text: {lines_with_text} "
        f"({percentage(lines_with_text, total_lines):.2f}%)",
        f"Lines without text: {lines_without_text} "
        f"({percentage(lines_without_text, total_lines):.2f}%)",
        f"Lines with confidence: {lines_with_confidence} "
        f"({percentage(lines_with_confidence, total_lines):.2f}%)",
        f"Lines without confidence: {lines_without_confidence} "
        f"({percentage(lines_without_confidence, total_lines):.2f}%)",
        "",
        "CONFIDENCE EXTRACTION SOURCE",
        "-" * 65
    ]

    for source, count in confidence_source_counts.most_common():
        summary.append(f"{source}: {count}")

    summary.extend([
        "",
        "MATCH STATUS",
        "-" * 65
    ])

    for status in [
        "matched",
        "ambiguous",
        "low_overlap",
        "unmatched"
    ]:
        count = status_counts.get(status, 0)
        summary.append(
            f"{status}: {count} ({percentage(count, total_lines):.2f}%)"
        )

    summary.extend([
        "",
        "ENTITY DISTRIBUTION OF CONFIDENT MATCHES",
        "-" * 65
    ])

    for entity, count in entity_counts.most_common():
        summary.append(f"{entity}: {count}")

    summary.extend([
        "",
        "MATCHING SETTINGS",
        "-" * 65,
        f"Minimum OCR line coverage: {MIN_LINE_COVERAGE}",
        f"Minimum coverage margin: {MIN_COVERAGE_MARGIN}",
        "Geometry: axis-aligned bounding-box approximation",
        "Text: direct TextLine TextEquiv or reconstructed from Word Unicode",
        "Word confidence: arithmetic mean when line confidence is unavailable",
        "",
        "IMPORTANT LIMITATIONS",
        "-" * 65,
        "Spatial matching does not prove OCR text correctness.",
        "Bounding boxes approximate the original polygons.",
        "Word-average confidence is not an original engine line confidence.",
        "OCR predictions must be checked against original images.",
        "GT semantic labels are not verified text transcriptions."
    ])

    summary_text = "\n".join(summary)

    SUMMARY_TXT.write_text(summary_text, encoding="utf-8")

    print("\n" + summary_text)

    print("\nOUTPUT FILES")
    print("=" * 65)
    print(OUTPUT_CSV)
    print(SUMMARY_TXT)


if __name__ == "__main__":
    main()
