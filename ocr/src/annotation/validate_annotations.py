
"""
Validate the structure and basic quality of an OCR annotation CSV.

This script checks annotation consistency.
It does not independently verify transcriptions against images.
"""

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

REQUIRED_COLUMNS = [
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

VALID_STATUSES = {
    "pending",
    "correct",
    "minor_error",
    "major_error",
    "non_text",
    "unreadable",
}

STATUSES_REQUIRING_GROUND_TRUTH = {
    "correct",
    "minor_error",
    "major_error",
}


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Validate an OCR annotation CSV."
    )

    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to the annotation CSV.",
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Optional path for a text validation report.",
    )

    return parser.parse_args()


def validate_file(input_file):
    if not input_file.exists():
        raise FileNotFoundError(
            f"Annotation file not found: {input_file}"
        )

    errors = []
    warnings = []
    status_counts = Counter()
    seen_ids = set()
    total_rows = 0

    with input_file.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        actual_columns = reader.fieldnames or []

        missing_columns = [
            column
            for column in REQUIRED_COLUMNS
            if column not in actual_columns
        ]

        if missing_columns:
            errors.append(
                "Missing required columns: "
                + ", ".join(missing_columns)
            )
            return errors, warnings, status_counts, total_rows

        for row_number, row in enumerate(reader, start=2):
            total_rows += 1

            document_id = (row["document_id"] or "").strip()
            line_id = (row["ocr_line_id"] or "").strip()
            predicted = row["predicted_text"] or ""
            ground_truth = row["ground_truth_text"] or ""
            status = (row["validation_status"] or "").strip()

            status_counts[status] += 1

            if not document_id:
                errors.append(
                    f"Row {row_number}: missing document_id."
                )

            if not line_id:
                errors.append(
                    f"Row {row_number}: missing ocr_line_id."
                )

            key = (document_id, line_id)

            if key in seen_ids:
                errors.append(
                    f"Row {row_number}: duplicate document/line ID "
                    f"{key}."
                )
            else:
                seen_ids.add(key)

            if status not in VALID_STATUSES:
                errors.append(
                    f"Row {row_number}: invalid status '{status}'."
                )

            if status in STATUSES_REQUIRING_GROUND_TRUTH:
                if not ground_truth.strip():
                    errors.append(
                        f"Row {row_number}: status '{status}' requires "
                        "ground_truth_text."
                    )

            if status == "non_text" and ground_truth.strip():
                errors.append(
                    f"Row {row_number}: non_text should have an empty "
                    "ground_truth_text."
                )

            if status == "unreadable" and ground_truth.strip():
                warnings.append(
                    f"Row {row_number}: unreadable line has ground-truth "
                    "text. Please review this decision."
                )

            if status == "pending" and ground_truth.strip():
                warnings.append(
                    f"Row {row_number}: pending line already has "
                    "ground-truth text."
                )

            if not predicted.strip() and status not in {
                "non_text",
                "unreadable",
            }:
                warnings.append(
                    f"Row {row_number}: predicted_text is empty."
                )

            confidence = (
                row["ocr_line_confidence"] or ""
            ).strip()

            if confidence:
                try:
                    value = float(confidence)

                    if not 0.0 <= value <= 1.0:
                        errors.append(
                            f"Row {row_number}: confidence must be "
                            "between 0 and 1."
                        )

                except ValueError:
                    errors.append(
                        f"Row {row_number}: confidence is not numeric."
                    )

    return errors, warnings, status_counts, total_rows


def build_report(
    input_file,
    errors,
    warnings,
    status_counts,
    total_rows
):
    lines = [
        "OCR ANNOTATION VALIDATION REPORT",
        "=" * 65,
        f"Input file: {input_file}",
        f"Total rows: {total_rows}",
        "",
        "ANNOTATION STATUS COUNTS",
        "-" * 65,
    ]

    for status in sorted(status_counts):
        lines.append(
            f"{status}: {status_counts[status]}"
        )

    lines.extend([
        "",
        f"Errors: {len(errors)}",
        f"Warnings: {len(warnings)}",
        "",
        "ERROR DETAILS",
        "-" * 65,
    ])

    lines.extend(errors or ["No errors found."])

    lines.extend([
        "",
        "WARNING DETAILS",
        "-" * 65,
    ])

    lines.extend(warnings or ["No warnings found."])

    lines.extend([
        "",
        "LIMITATION",
        "-" * 65,
        "Structural validation does not prove that ground-truth text "
        "matches the original document image.",
    ])

    return "\n".join(lines)


def main():
    args = parse_arguments()

    try:
        errors, warnings, counts, total = validate_file(args.input)

        report = build_report(
            args.input,
            errors,
            warnings,
            counts,
            total
        )

        print(report)

        if args.report:
            args.report.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            args.report.write_text(
                report,
                encoding="utf-8"
            )

            print(f"\nReport saved to: {args.report}")

        if errors:
            sys.exit(1)

    except FileNotFoundError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
