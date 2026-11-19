import csv
import sys
from pathlib import Path
from collections import Counter

try:
    from PIL import Image
except ImportError:
    print("Pillow is required. Install it using: python -m pip install Pillow")
    sys.exit(1)


# --------------------------------------------------
# PATHS
# --------------------------------------------------

OCR_ROOT = Path(__file__).resolve().parents[2]

ANNOTATION_FILE = (
    OCR_ROOT
    / "data"
    / "annotations"
    / "ocr_validation"
    / "v2"
    / "consolidated_annotations_v2.csv"
)

AUDIT_FILE = (
    OCR_ROOT
    / "reports"
    / "day16_gt_ocr_line_mapping_audit.csv"
)

IMAGE_DIR = (
    OCR_ROOT
    / "data"
    / "raw"
    / "invoices"
    / "archive"
    / "ImageAndXML_Data"
)

OUTPUT_DIR = (
    OCR_ROOT
    / "data"
    / "annotations"
    / "ocr_validation"
    / "v2"
)

OUTPUT_FILE = OUTPUT_DIR / "clean_training_manifest_v2.csv"
REPORT_FILE = OUTPUT_DIR / "manifest_build_report.txt"


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader), reader.fieldnames


def find_tiff_images():

    image_index = {}

    for path in IMAGE_DIR.rglob("*"):

        if not path.is_file():
            continue

        if path.suffix.lower() not in {".tif", ".tiff"}:
            continue

        image_index.setdefault(path.stem, []).append(path)

    return image_index


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print("=" * 65)
    print("BUILD CLEAN OCR TRAINING MANIFEST")
    print("=" * 65)

    if not ANNOTATION_FILE.exists():
        raise FileNotFoundError(ANNOTATION_FILE)

    if not AUDIT_FILE.exists():
        raise FileNotFoundError(AUDIT_FILE)

    if not IMAGE_DIR.exists():
        raise FileNotFoundError(IMAGE_DIR)

    if OUTPUT_FILE.exists() or REPORT_FILE.exists():
        raise FileExistsError(
            "Manifest output already exists. "
            "Nothing was overwritten. Inspect the existing files first."
        )

    annotations, annotation_columns = read_csv(ANNOTATION_FILE)
    audit_rows, audit_columns = read_csv(AUDIT_FILE)

    required_annotation = {
        "document_id",
        "ocr_line_id",
        "ground_truth_text",
        "validation_status",
        "matched_entity",
        "ocr_line_confidence",
    }

    required_audit = {
        "document_id",
        "ocr_line_id",
        "ocr_x1",
        "ocr_y1",
        "ocr_x2",
        "ocr_y2",
    }

    if not required_annotation.issubset(annotation_columns):
        raise ValueError("Required annotation columns are missing.")

    if not required_audit.issubset(audit_columns):
        raise ValueError("Required audit columns are missing.")

    # Only use manually verified correct annotations.
    clean_rows = [
        row for row in annotations
        if row["validation_status"].strip().lower() == "correct"
    ]

    print(f"\nCorrect annotations: {len(clean_rows)}")

    # Build audit lookup.
    audit_index = {}

    for row in audit_rows:

        key = (
            row["document_id"].strip(),
            row["ocr_line_id"].strip()
        )

        if key in audit_index:
            raise ValueError(f"Duplicate audit key: {key}")

        audit_index[key] = row

    # Index original TIFF files.
    print("\nIndexing original TIFF images...")
    image_index = find_tiff_images()

    print(f"TIFF files found: {sum(len(v) for v in image_index.values())}")

    manifest_rows = []
    problems = []
    document_counts = Counter()

    # --------------------------------------------------
    # MATCH ANNOTATIONS, AUDIT BOXES AND TIFF IMAGES
    # --------------------------------------------------

    for row in clean_rows:

        document_id = row["document_id"].strip()
        line_id = row["ocr_line_id"].strip()
        key = (document_id, line_id)

        if key not in audit_index:
            problems.append(f"Missing audit record: {key}")
            continue

        audit_row = audit_index[key]

        image_matches = image_index.get(document_id, [])

        if len(image_matches) == 0:
            problems.append(f"Original TIFF not found: {document_id}")
            continue

        if len(image_matches) > 1:
            problems.append(
                f"Multiple TIFFs found for {document_id}: "
                + ", ".join(str(p) for p in image_matches)
            )
            continue

        image_path = image_matches[0]

        try:
            x1 = float(audit_row["ocr_x1"])
            y1 = float(audit_row["ocr_y1"])
            x2 = float(audit_row["ocr_x2"])
            y2 = float(audit_row["ocr_y2"])
        except (ValueError, TypeError):
            problems.append(f"Invalid coordinates: {key}")
            continue

        if x2 <= x1 or y2 <= y1:
            problems.append(f"Invalid box dimensions: {key}")
            continue

        # Check coordinates against original TIFF dimensions.
        try:
            with Image.open(image_path) as image:
                width, height = image.size
        except Exception as error:
            problems.append(
                f"Could not open TIFF for {document_id}: {error}"
            )
            continue

        if x1 < 0 or y1 < 0 or x2 > width or y2 > height:
            problems.append(
                f"Box outside image bounds: {key}; "
                f"box=({x1},{y1},{x2},{y2}); "
                f"image=({width},{height})"
            )
            continue

        ground_truth = row["ground_truth_text"].strip()

        if not ground_truth:
            problems.append(f"Empty transcription: {key}")
            continue

        manifest_rows.append({
            "document_id": document_id,
            "ocr_line_id": line_id,
            "image_path": str(image_path.resolve()),
            "image_width": width,
            "image_height": height,
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "ground_truth_text": row["ground_truth_text"],
            "predicted_text": row["predicted_text"],
            "validation_status": row["validation_status"],
            "matched_entity": row["matched_entity"],
            "ocr_line_confidence": row["ocr_line_confidence"],
        })

        document_counts[document_id] += 1

    # --------------------------------------------------
    # STOP IF ANY PROBLEMS EXIST
    # --------------------------------------------------

    if problems:

        print("\nMANIFEST BUILD STOPPED.")
        print(f"Problems found: {len(problems)}")

        for problem in problems[:30]:
            print(" -", problem)

        if len(problems) > 30:
            print(f"... and {len(problems) - 30} more.")

        raise RuntimeError(
            "Resolve the listed problems before building the manifest."
        )

    if len(manifest_rows) != len(clean_rows):
        raise RuntimeError("Manifest row count does not match clean rows.")

    # --------------------------------------------------
    # SAVE MANIFEST
    # --------------------------------------------------

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    columns = [
        "document_id",
        "ocr_line_id",
        "image_path",
        "image_width",
        "image_height",
        "x1",
        "y1",
        "x2",
        "y2",
        "ground_truth_text",
        "predicted_text",
        "validation_status",
        "matched_entity",
        "ocr_line_confidence",
    ]

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(manifest_rows)

    # Verify saved file.
    saved_rows, _ = read_csv(OUTPUT_FILE)

    if len(saved_rows) != len(manifest_rows):
        raise RuntimeError("Saved manifest verification failed.")

    # --------------------------------------------------
    # REPORT
    # --------------------------------------------------

    report = [
        "CLEAN OCR TRAINING MANIFEST REPORT",
        "=" * 60,
        f"Correct annotations: {len(clean_rows)}",
        f"Manifest rows created: {len(manifest_rows)}",
        f"Original TIFF directory: {IMAGE_DIR}",
        "",
        "DOCUMENT COUNTS",
        "-" * 60,
    ]

    for document_id, count in sorted(document_counts.items()):
        report.append(f"{document_id}: {count}")

    report.extend([
        "",
        "VALIDATION",
        "-" * 60,
        "Annotation-to-audit matching: PASS",
        "Original TIFF matching: PASS",
        "TIFF readability: PASS",
        "Bounding-box dimensions: PASS",
        "Bounding boxes inside image boundaries: PASS",
        "Ground-truth text present: PASS",
        f"Saved manifest rows: {len(saved_rows)}",
        "",
        "NOTE",
        "-" * 60,
        "This manifest does not prove that every crop is visually clean.",
        "Visual crop review is still required before model training.",
    ])

    REPORT_FILE.write_text("\n".join(report), encoding="utf-8")

    print("\n" + "=" * 65)
    print("MANIFEST CREATED SUCCESSFULLY")
    print("=" * 65)

    print(f"Manifest rows: {len(manifest_rows)}")
    print(f"Documents: {len(document_counts)}")
    print(f"\nCSV: {OUTPUT_FILE}")
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":

    try:
        main()

    except Exception as error:
        print("\nERROR:", error)
        sys.exit(1)