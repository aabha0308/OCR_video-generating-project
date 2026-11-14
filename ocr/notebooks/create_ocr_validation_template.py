
import csv
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

AUDIT_FILE = (
    PROJECT_ROOT
    / "ocr"
    / "reports"
    / "day16_gt_ocr_line_mapping_audit.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "ocr"
    / "data"
    / "annotations"
    / "ocr_validation"
)

OUTPUT_FILE = OUTPUT_DIR / "validation_annotations.csv"

DOCUMENT_ID = "0000223278"


# ============================================================
# HUMAN-REVIEWED ANNOTATIONS
# Only include corrections based on the visual review.
# Do not modify the original OCR predictions.
# ============================================================

REVIEWED_ANNOTATIONS = {
    "Page1_Block1_l1": {
        "ground_truth_text": "",
        "validation_status": "non_text",
        "reviewer_notes": (
            "Appears to be stray marks rather than meaningful text. "
            "Confirm against the original image before final approval."
        ),
    },

    "Page1_Block5_l1": {
        "ground_truth_text": "B.A.T (U.K. AND EXPORT) LIMITED",
        "validation_status": "minor_error",
        "reviewer_notes": "Punctuation, capitalization and spacing corrected.",
    },

    "Page1_Block5_l2": {
        "ground_truth_text": "Export House Woking Surrey GU21 1YB England",
        "validation_status": "minor_error",
        "reviewer_notes": "Corrected spacing in postcode.",
    },

    "Page1_Block6_l1": {
        "ground_truth_text": "Brown & Williamson International Tobacco,",
        "validation_status": "correct",
        "reviewer_notes": "OCR text visually verified.",
    },

    "Page1_Block6_l6": {
        "ground_truth_text": "Attention Mr. Gary Kirschner",
        "validation_status": "major_error",
        "reviewer_notes": "Name corrected using the original image.",
    },

    "Page1_Block7_l1": {
        "ground_truth_text": "Telephone Woking 76111",
        "validation_status": "minor_error",
        "reviewer_notes": "Corrected OCR character recognition in Woking.",
    },
}


# ============================================================
# MAIN
# ============================================================

def main():

    if not AUDIT_FILE.exists():
        raise FileNotFoundError(
            f"Day 16 audit file not found: {AUDIT_FILE}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []

    with AUDIT_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        required_columns = {
            "document_id",
            "ocr_line_id",
            "ocr_text",
            "matched_entity",
            "match_status",
            "ocr_line_confidence",
        }

        missing = required_columns - set(reader.fieldnames or [])

        if missing:
            raise ValueError(
                f"Missing required columns in audit CSV: {missing}"
            )

        for source in reader:

            if source["document_id"] != DOCUMENT_ID:
                continue

            line_id = source["ocr_line_id"]

            # Default values for lines not yet reviewed.
            annotation = {
                "document_id": source["document_id"],
                "ocr_line_id": line_id,
                "predicted_text": source["ocr_text"],
                "ground_truth_text": "",
                "validation_status": "pending",
                "matched_entity": source["matched_entity"],
                "match_status": source["match_status"],
                "ocr_line_confidence": source["ocr_line_confidence"],
                "reviewer_notes": "",
            }

            # Apply existing human-reviewed annotations.
            reviewed = REVIEWED_ANNOTATIONS.get(line_id)

            if reviewed:
                annotation.update(reviewed)

            rows.append(annotation)

    if not rows:
        raise ValueError(
            f"No OCR lines found for document {DOCUMENT_ID}"
        )

    fieldnames = [
        "document_id",
        "ocr_line_id",
        "predicted_text",
        "ground_truth_text",
        "validation_status",
        "matched_entity",
        "match_status",
        "ocr_line_confidence",
        "reviewer_notes",
    ]

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(rows)

    reviewed_count = sum(
        row["validation_status"] != "pending"
        for row in rows
    )

    print("=" * 65)
    print("OCR VALIDATION TEMPLATE CREATED")
    print("=" * 65)
    print(f"Document ID: {DOCUMENT_ID}")
    print(f"Total OCR lines: {len(rows)}")
    print(f"Pre-filled reviewed lines: {reviewed_count}")
    print(f"Pending lines: {len(rows) - reviewed_count}")
    print(f"Output file: {OUTPUT_FILE}")
    print("=" * 65)


if __name__ == "__main__":
    main()
