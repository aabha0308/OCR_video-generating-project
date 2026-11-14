
"""
Create a per-document OCR validation CSV from the Day 16 audit.

Safety:
- Never modifies the source audit CSV.
- Never overwrites an existing review CSV unless --overwrite is supplied.
- Does not invent or automatically correct ground-truth text.
"""

import argparse
import csv
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_AUDIT_FILE = (
    PROJECT_ROOT
    / "ocr"
    / "reports"
    / "day16_gt_ocr_line_mapping_audit.csv"
)

DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT
    / "ocr"
    / "data"
    / "annotations"
    / "ocr_validation"
)

OUTPUT_COLUMNS = [
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

REQUIRED_AUDIT_COLUMNS = [
    "document_id",
    "ocr_line_id",
    "ocr_text",
    "matched_entity",
    "match_status",
    "ocr_line_confidence",
]


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Create an OCR validation CSV for one document."
    )

    parser.add_argument(
        "--document-id",
        required=True,
        help="Document ID, for example 0000223278.",
    )

    parser.add_argument(
        "--audit-file",
        type=Path,
        default=DEFAULT_AUDIT_FILE,
        help="Path to the Day 16 audit CSV.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional custom output CSV path.",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing an existing output file. Use carefully.",
    )

    return parser.parse_args()


def validate_document_id(document_id):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", document_id):
        raise ValueError(
            "Document ID may contain only letters, numbers, "
            "underscores and hyphens."
        )


def read_audit_rows(audit_file, document_id):
    if not audit_file.exists():
        raise FileNotFoundError(
            f"Audit CSV not found: {audit_file}"
        )

    selected_rows = []

    with audit_file.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        missing_columns = [
            column
            for column in REQUIRED_AUDIT_COLUMNS
            if column not in (reader.fieldnames or [])
        ]

        if missing_columns:
            raise ValueError(
                "Audit CSV is missing columns: "
                + ", ".join(missing_columns)
            )

        for source in reader:
            if source["document_id"] != document_id:
                continue

            selected_rows.append({
                "document_id": source["document_id"],
                "ocr_line_id": source["ocr_line_id"],
                "predicted_text": source["ocr_text"],
                "ground_truth_text": "",
                "validation_status": "pending",
                "matched_entity": source["matched_entity"],
                "match_status": source["match_status"],
                "ocr_line_confidence": source[
                    "ocr_line_confidence"
                ],
                "reviewer_notes": "",
            })

    if not selected_rows:
        raise ValueError(
            f"No OCR lines found for document {document_id}."
        )

    line_ids = [
        row["ocr_line_id"]
        for row in selected_rows
    ]

    if len(line_ids) != len(set(line_ids)):
        raise ValueError(
            f"Duplicate OCR line IDs found for document {document_id}."
        )

    return selected_rows


def write_csv(output_file, rows, overwrite):
    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if output_file.exists() and not overwrite:
        raise FileExistsError(
            f"Output already exists: {output_file}\n"
            "It may contain human annotations. "
            "Choose another output path or use --overwrite "
            "only if you intentionally want to replace it."
        )

    with output_file.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=OUTPUT_COLUMNS
        )

        writer.writeheader()
        writer.writerows(rows)


def main():
    args = parse_arguments()

    try:
        validate_document_id(args.document_id)

        output_file = args.output or (
            DEFAULT_OUTPUT_DIR
            / f"document_{args.document_id}_review.csv"
        )

        rows = read_audit_rows(
            args.audit_file,
            args.document_id
        )

        write_csv(
            output_file,
            rows,
            args.overwrite
        )

        print("=" * 65)
        print("OCR VALIDATION DATASET CREATED")
        print("=" * 65)
        print(f"Document ID: {args.document_id}")
        print(f"Total OCR lines: {len(rows)}")
        print(f"Initial status: pending")
        print(f"Source audit: {args.audit_file}")
        print(f"Output file: {output_file}")
        print("=" * 65)
        print("Original audit file was not modified.")

    except (ValueError, FileNotFoundError, FileExistsError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
