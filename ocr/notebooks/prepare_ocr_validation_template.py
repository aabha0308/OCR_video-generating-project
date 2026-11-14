
import csv

from pathlib import Path

# Resolve project directories from this script's location.
# This script is inside: OCR_Internship/ocr/notebooks/

OCR_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = OCR_ROOT.parent

# Input: Day 16 OCR line mapping audit
SOURCE_CSV = (
    OCR_ROOT
    / "reports"
    / "day16_gt_ocr_line_mapping_audit.csv"
)

# Output: OCR validation annotation directory
OUTPUT_DIR = (
    OCR_ROOT
    / "data"
    / "annotations"
    / "ocr_validation"
)

OUTPUT_CSV = OUTPUT_DIR / "validation_annotations.csv"
GUIDELINES_FILE = OUTPUT_DIR / "validation_guidelines.md"


DOCUMENT_ID = "0000223278"

OUTPUT_CSV = OUTPUT_DIR / f"document_{DOCUMENT_ID}_review.csv"
GUIDELINES_FILE = OUTPUT_DIR / "validation_guidelines.md"


# --------------------------------------------------
# VALIDATION SCHEMA
# --------------------------------------------------

OUTPUT_FIELDS = [
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


# --------------------------------------------------
# GUIDELINES
# --------------------------------------------------

GUIDELINES = """# OCR Validation Guidelines

## Purpose

This file defines how OCR predictions are manually checked
against the original document images.

## Annotation statuses

- correct: Predicted text matches the visible image.
- minor_error: Small character, punctuation, or spacing error.
- major_error: Significant incorrect or missing text.
- non_text: The OCR system detected a non-text mark as text.
- unreadable: The image does not permit reliable transcription.
- pending: Not yet reviewed.

## Annotation rules

1. Always compare predictions with the original TIFF image.
2. Preserve the original OCR prediction in predicted_text.
3. Enter the corrected transcription in ground_truth_text.
4. Do not guess text that cannot be read reliably.
5. Preserve meaningful punctuation, numbers, and spacing.
6. Use non_text only when the region contains no meaningful text.
7. Use unreadable when text exists but cannot be reliably read.
8. Do not modify the original OCR XML or audit CSV.
9. Record uncertainties in reviewer_notes.

## Important distinction

OCR predictions are not ground truth.

Only manually verified transcriptions should be used
as reference text for OCR accuracy evaluation.

## Confidence

ocr_line_confidence is an arithmetic mean of word-level
confidence values when an original line-level confidence
is unavailable. It is not an original engine line score.
"""


# --------------------------------------------------
# GENERATE REVIEW TEMPLATE
# --------------------------------------------------

def main():

    if not SOURCE_CSV.exists():
        raise FileNotFoundError(
            f"Source audit CSV not found: {SOURCE_CSV}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    review_rows = []

    with SOURCE_CSV.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as source_file:

        reader = csv.DictReader(source_file)

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
                f"Missing expected columns in source CSV: {missing}"
            )

        for row in reader:

            if row["document_id"].strip() != DOCUMENT_ID:
                continue

            review_rows.append({
                "document_id": row["document_id"],
                "ocr_line_id": row["ocr_line_id"],
                "predicted_text": row["ocr_text"],
                "ground_truth_text": "",
                "validation_status": "pending",
                "matched_entity": row["matched_entity"],
                "match_status": row["match_status"],
                "ocr_line_confidence": row["ocr_line_confidence"],
                "reviewer_notes": "",
            })

    if not review_rows:
        raise ValueError(
            f"No OCR lines found for document {DOCUMENT_ID}"
        )

    # Save the review CSV
    with OUTPUT_CSV.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as output_file:

        writer = csv.DictWriter(
            output_file,
            fieldnames=OUTPUT_FIELDS
        )

        writer.writeheader()
        writer.writerows(review_rows)

    # Create guidelines only if they do not already exist
    if not GUIDELINES_FILE.exists():
        GUIDELINES_FILE.write_text(
            GUIDELINES,
            encoding="utf-8"
        )

    print("=" * 60)
    print("OCR VALIDATION TEMPLATE CREATED")
    print("=" * 60)
    print(f"Document ID: {DOCUMENT_ID}")
    print(f"Total OCR lines: {len(review_rows)}")
    print(f"Pending annotations: {len(review_rows)}")
    print(f"\nReview CSV: {OUTPUT_CSV}")
    print(f"Guidelines: {GUIDELINES_FILE}")
    print("\nOriginal audit CSV was not modified.")


if __name__ == "__main__":
    main()
