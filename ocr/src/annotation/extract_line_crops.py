
import argparse
import csv
import math
import re
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Pillow is not installed.")
    print("Install it using: python -m pip install Pillow")
    sys.exit(1)



PROJECT_ROOT = Path(__file__).resolve().parents[2]

ANNOTATIONS_FILE = (
    PROJECT_ROOT
    / "data/processed/annotations/v1/training_ready_transcriptions.csv"
)

AUDIT_FILE = (
    PROJECT_ROOT
    / "reports/day16_gt_ocr_line_mapping_audit.csv"
)

RAW_IMAGE_DIR = (
    PROJECT_ROOT
    / "data/raw/invoices/archive/ImageAndXML_Data"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "ocr_line_crops" / "v3"

PADDING = 1

TEMP_PREFIX = "ocr_crops_v3_"

OUTPUT_COLUMNS = [
    "document_id",
    "ocr_line_id",
    "predicted_text",
    "ground_truth_text",
    "validation_status",
    "matched_entity",
    "match_status",
    "ocr_line_confidence",
    "ocr_word_count",
    "crop_path",
    "crop_width",
    "crop_height",
    "original_image",
]


def read_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def safe_filename(value):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value)


def get_image_path(document_id):
    for extension in (".tif", ".tiff", ".TIF", ".TIFF"):
        path = RAW_IMAGE_DIR / f"{document_id}{extension}"
        if path.exists():
            return path
    return None


def validate_unique_keys(rows, source_name):
    seen = set()

    for row in rows:
        key = (row["document_id"], row["ocr_line_id"])

        if key in seen:
            raise ValueError(
                f"Duplicate key in {source_name}: {key}"
            )

        seen.add(key)

    return seen


def main():
    parser = argparse.ArgumentParser(
        description="Extract OCR line crops for verified annotations."
    )
    parser.add_argument(
        "--padding",
        type=int,
        default=PADDING,
        help="Extra pixels around each OCR line crop.",
    )
    args = parser.parse_args()

    if args.padding < 0:
        raise ValueError("Padding cannot be negative.")

    for path in (ANNOTATIONS_FILE, AUDIT_FILE, RAW_IMAGE_DIR):
        if not path.exists():
            raise FileNotFoundError(f"Required path not found: {path}")

    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"Output already exists: {OUTPUT_DIR}\n"
            "Do not overwrite a dataset version. "
            "Inspect it or create a new version."
        )

    annotations = read_csv(ANNOTATIONS_FILE)
    audit = read_csv(AUDIT_FILE)

    annotation_required = {
        "document_id",
        "ocr_line_id",
        "predicted_text",
        "ground_truth_text",
        "validation_status",
        "matched_entity",
        "match_status",
        "ocr_line_confidence",
    }

    audit_required = {
        "document_id",
        "ocr_line_id",
        "ocr_text",
        "ocr_line_confidence",
        "ocr_word_count",
        "ocr_x1",
        "ocr_y1",
        "ocr_x2",
        "ocr_y2",
    }

    if not annotations:
        raise ValueError("The annotation dataset is empty.")

    if not audit:
        raise ValueError("The Day 16 audit file is empty.")

    missing_annotation_columns = (
        annotation_required - set(annotations[0].keys())
    )
    missing_audit_columns = audit_required - set(audit[0].keys())

    if missing_annotation_columns:
        raise ValueError(
            f"Missing annotation columns: {missing_annotation_columns}"
        )

    if missing_audit_columns:
        raise ValueError(
            f"Missing audit columns: {missing_audit_columns}"
        )

    annotation_keys = validate_unique_keys(
        annotations, "annotations"
    )
    audit_keys = validate_unique_keys(audit, "Day 16 audit")

    audit_by_key = {
        (row["document_id"], row["ocr_line_id"]): row
        for row in audit
    }

    # Validate every record before creating output.
    prepared = []

    for annotation in annotations:
        key = (
            annotation["document_id"],
            annotation["ocr_line_id"],
        )

        if key not in audit_by_key:
            raise ValueError(
                f"No matching Day 16 audit row for {key}"
            )

        if annotation["validation_status"] not in {
            "correct", "minor_error", "major_error"
        }:
            raise ValueError(
                f"Unexpected training status for {key}: "
                f"{annotation['validation_status']}"
            )

        if not annotation["ground_truth_text"].strip():
            raise ValueError(
                f"Missing ground truth text for {key}"
            )

        audit_row = audit_by_key[key]

        try:
            x1 = float(audit_row["ocr_x1"])
            y1 = float(audit_row["ocr_y1"])
            x2 = float(audit_row["ocr_x2"])
            y2 = float(audit_row["ocr_y2"])
        except (ValueError, TypeError):
            raise ValueError(f"Invalid coordinates for {key}")

        if not all(math.isfinite(v) for v in (x1, y1, x2, y2)):
            raise ValueError(f"Non-finite coordinates for {key}")

        if x2 <= x1 or y2 <= y1:
            raise ValueError(f"Invalid bounding box for {key}")

        image_path = get_image_path(annotation["document_id"])

        if image_path is None:
            raise FileNotFoundError(
                f"TIFF image missing for document "
                f"{annotation['document_id']}"
            )

        prepared.append({
            "annotation": annotation,
            "audit": audit_row,
            "image_path": image_path,
            "coordinates": (x1, y1, x2, y2),
        })

    # Use a temporary directory so incomplete datasets are not
    # mistaken for successfully generated versions.
    OUTPUT_DIR.parent.mkdir(parents=True, exist_ok=True)

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix="ocr_crops_v3_",
            dir=OUTPUT_DIR.parent,
        )
    )

    records = []
    status_counts = Counter()
    crop_errors = []

    try:
        image_cache = {}

        for item in prepared:
            annotation = item["annotation"]
            audit_row = item["audit"]
            image_path = item["image_path"]

            document_id = annotation["document_id"]
            line_id = annotation["ocr_line_id"]

            if document_id not in image_cache:
                with Image.open(image_path) as source:
                    image_cache[document_id] = source.convert("RGB")

            image = image_cache[document_id]
            image_width, image_height = image.size

            x1, y1, x2, y2 = item["coordinates"]

            left = max(0, math.floor(x1) - args.padding)
            top = max(0, math.floor(y1) - args.padding)
            right = min(image_width, math.ceil(x2) + args.padding)
            bottom = min(image_height, math.ceil(y2) + args.padding)

            if right <= left or bottom <= top:
                raise ValueError(
                    f"Empty crop after clipping: {document_id}/{line_id}"
                )

            crop = image.crop((left, top, right, bottom))

            if crop.width == 0 or crop.height == 0:
                raise ValueError(
                    f"Zero-sized crop: {document_id}/{line_id}"
                )

            document_dir = (
                temp_dir
                / "images"
                / safe_filename(document_id)
            )
            document_dir.mkdir(parents=True, exist_ok=True)

            crop_filename = safe_filename(line_id) + ".png"
            crop_file = document_dir / crop_filename
            crop.save(crop_file, format="PNG")

            relative_crop_path = crop_file.relative_to(
                temp_dir
            ).as_posix()

            records.append({
                "document_id": document_id,
                "ocr_line_id": line_id,
                "predicted_text": annotation["predicted_text"],
                "ground_truth_text": annotation["ground_truth_text"],
                "validation_status": annotation["validation_status"],
                "matched_entity": annotation["matched_entity"],
                "match_status": annotation["match_status"],
                "ocr_line_confidence": annotation["ocr_line_confidence"],
                "ocr_word_count": audit_row["ocr_word_count"],
                "crop_path": relative_crop_path,
                "crop_width": crop.width,
                "crop_height": crop.height,
                "original_image": str(image_path.relative_to(PROJECT_ROOT)),
            })

            status_counts[annotation["validation_status"]] += 1

        # Save metadata.
        metadata_path = temp_dir / "line_crop_dataset.csv"

        with open(
            metadata_path,
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=OUTPUT_COLUMNS,
            )
            writer.writeheader()
            writer.writerows(records)

        # Save a reproducibility report.
        report_path = temp_dir / "crop_extraction_report.txt"

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("OCR LINE-CROP EXTRACTION REPORT\n")
            f.write("=" * 55 + "\n\n")
            f.write(f"Annotation records: {len(annotations)}\n")
            f.write(f"Audit records: {len(audit)}\n")
            f.write(f"Extracted crops: {len(records)}\n")
            f.write(
                f"Unique documents: "
                f"{len(set(r['document_id'] for r in records))}\n"
            )
            f.write(f"Padding: {args.padding} pixels\n\n")
            f.write("Annotation status counts:\n")

            for status, count in sorted(status_counts.items()):
                f.write(f"  {status}: {count}\n")

            f.write("\nLimitations:\n")
            f.write(
                "- Crops use OCR-generated bounding boxes.\n"
                "- Bounding boxes have not all been independently "
                "verified.\n"
                "- Ground-truth text comes from human-reviewed "
                "annotations.\n"
                "- This pilot dataset is too small for final "
                "training claims.\n"
            )

        # Close cached images before finalizing.
        for image in image_cache.values():
            image.close()

        # Atomic finalization.
        temp_dir.rename(OUTPUT_DIR)

    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise

    print("=" * 60)
    print("OCR LINE-CROP EXTRACTION COMPLETED")
    print("=" * 60)
    print(f"Annotation records: {len(annotations)}")
    print(f"Extracted crops: {len(records)}")
    print(f"Unique documents: {len(set(r['document_id'] for r in records))}")
    print(f"Output: {OUTPUT_DIR}")
    print()
    print("Status counts:")

    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")


if __name__ == "__main__":
    main()
