import csv
from collections import Counter
from pathlib import Path
import sys


# --------------------------------------------------
# PATHS
# --------------------------------------------------

OCR_ROOT = Path(__file__).resolve().parents[2]

WORKBENCH_DIR = (
    OCR_ROOT
    / "data"
    / "annotations"
    / "ocr_validation"
    / "workbench_v1"
)

OUTPUT_DIR = (
    OCR_ROOT
    / "data"
    / "annotations"
    / "ocr_validation"
    / "v2"
)

OUTPUT_CSV = OUTPUT_DIR / "consolidated_annotations_v2.csv"
REPORT_FILE = OUTPUT_DIR / "consolidation_report.txt"


# --------------------------------------------------
# EXPECTED INPUT FILES AND ROW COUNTS
# --------------------------------------------------

EXPECTED_FILES = {
    "document_2061828225_review.csv": 223,
    "document_503116473+-6473_review.csv": 149,
    "document_507484246_review.csv": 269,
    "document_96052028_review.csv": 139,
    "document_ti31149327_9330_review.csv": 157,
}

REQUIRED_COLUMNS = {
    "document_id",
    "ocr_line_id",
    "predicted_text",
    "ground_truth_text",
    "validation_status",
    "matched_entity",
    "match_status",
    "ocr_line_confidence",
    "reviewer_notes",
}

TRAINING_STATUSES = {"correct", "minor_error", "major_error"}
EXCLUDED_STATUSES = {"non_text", "unreadable"}
VALID_STATUSES = TRAINING_STATUSES | EXCLUDED_STATUSES


# --------------------------------------------------
# LOAD AND CHECK INPUT FILES
# --------------------------------------------------

def load_annotations():

    if not WORKBENCH_DIR.exists():
        raise FileNotFoundError(
            f"Workbench folder not found:\n{WORKBENCH_DIR}"
        )

    all_rows = []
    reference_columns = None
    document_counts = {}
    status_counts = Counter()
    seen_ids = set()

    for filename, expected_count in EXPECTED_FILES.items():

        file_path = WORKBENCH_DIR / filename

        if not file_path.exists():
            raise FileNotFoundError(
                f"Expected annotation file is missing:\n{file_path}"
            )

        print(f"\nReading: {filename}")

        with file_path.open(
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as csv_file:

            reader = csv.DictReader(csv_file)

            if reader.fieldnames is None:
                raise ValueError(f"No CSV header found in {filename}")

            columns = reader.fieldnames

            missing_columns = REQUIRED_COLUMNS - set(columns)

            if missing_columns:
                raise ValueError(
                    f"{filename} is missing columns: "
                    f"{sorted(missing_columns)}"
                )

            if reference_columns is None:
                reference_columns = columns

            elif columns != reference_columns:
                raise ValueError(
                    f"Column names or order differ in {filename}.\n"
                    f"Expected: {reference_columns}\n"
                    f"Found:    {columns}"
                )

            rows = list(reader)

        actual_count = len(rows)

        if actual_count != expected_count:
            raise ValueError(
                f"Unexpected row count in {filename}: "
                f"expected {expected_count}, found {actual_count}"
            )

        document_counts[filename] = actual_count

        for row_number, row in enumerate(rows, start=2):

            document_id = row["document_id"].strip()
            line_id = row["ocr_line_id"].strip()
            status = row["validation_status"].strip().lower()
            ground_truth = row["ground_truth_text"].strip()

            if not document_id or not line_id:
                raise ValueError(
                    f"Missing document_id or ocr_line_id "
                    f"in {filename}, CSV row {row_number}"
                )

            unique_key = (document_id, line_id)

            if unique_key in seen_ids:
                raise ValueError(
                    f"Duplicate document/line ID found: {unique_key}"
                )

            seen_ids.add(unique_key)

            if status not in VALID_STATUSES:
                raise ValueError(
                    f"Unexpected status '{status}' in "
                    f"{filename}, CSV row {row_number}"
                )

            if status == "pending":
                raise ValueError(
                    f"Pending annotation found in "
                    f"{filename}, CSV row {row_number}"
                )

            if status in TRAINING_STATUSES and not ground_truth:
                raise ValueError(
                    f"Training annotation has empty ground_truth_text "
                    f"in {filename}, CSV row {row_number}"
                )

            if status in EXCLUDED_STATUSES and ground_truth:
                raise ValueError(
                    f"Excluded annotation has ground_truth_text. "
                    f"Check {filename}, CSV row {row_number}, "
                    f"status '{status}'."
                )

            try:
                confidence = float(row["ocr_line_confidence"])
            except (ValueError, TypeError):
                raise ValueError(
                    f"Invalid OCR confidence in "
                    f"{filename}, CSV row {row_number}"
                )

            if not 0 <= confidence <= 1:
                raise ValueError(
                    f"OCR confidence outside 0-1 in "
                    f"{filename}, CSV row {row_number}"
                )

            status_counts[status] += 1
            all_rows.append(row)

        print(f"  Rows checked: {actual_count}")
        print("  Checks passed.")

    return all_rows, reference_columns, document_counts, status_counts


# --------------------------------------------------
# CREATE CONSOLIDATED DATASET
# --------------------------------------------------

def main():

    print("=" * 65)
    print("OCR ANNOTATION CONSOLIDATION - VERSION 2")
    print("=" * 65)

    # Never overwrite an existing output.
    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"\nOutput folder already exists:\n{OUTPUT_DIR}\n\n"
            "Nothing was overwritten. Inspect the folder before "
            "deciding whether to use a different output version."
        )

    rows, columns, document_counts, status_counts = load_annotations()

    total_rows = len(rows)

    expected_total = sum(EXPECTED_FILES.values())

    if total_rows != expected_total:
        raise ValueError(
            f"Expected {expected_total} total rows, found {total_rows}"
        )

    training_rows = sum(
        status_counts[status] for status in TRAINING_STATUSES
    )

    excluded_rows = sum(
        status_counts[status] for status in EXCLUDED_STATUSES
    )

    if training_rows + excluded_rows != total_rows:
        raise ValueError("Status counts do not match total row count.")

    # Create output only after every check passes.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)

    with OUTPUT_CSV.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as output_file:

        writer = csv.DictWriter(
            output_file,
            fieldnames=columns
        )

        writer.writeheader()
        writer.writerows(rows)

    # Verify the saved CSV.
    with OUTPUT_CSV.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as saved_file:

        saved_rows = list(csv.DictReader(saved_file))

    if len(saved_rows) != total_rows:
        raise RuntimeError(
            "Saved CSV row count does not match source row count."
        )

    # Create a readable report.
    report_lines = [
        "OCR ANNOTATION CONSOLIDATION REPORT",
        "=" * 65,
        "",
        "Dataset version: v2",
        f"Source folder: {WORKBENCH_DIR}",
        f"Output file: {OUTPUT_CSV}",
        "",
        "SOURCE FILES",
        "-" * 65,
    ]

    for filename, count in document_counts.items():
        report_lines.append(f"{filename}: {count} rows")

    report_lines.extend([
        "",
        "TOTAL ROWS",
        "-" * 65,
        f"Total reviewed OCR lines: {total_rows}",
        f"Training-eligible rows: {training_rows}",
        f"Excluded rows: {excluded_rows}",
        "",
        "ANNOTATION STATUS COUNTS",
        "-" * 65,
    ])

    for status in sorted(VALID_STATUSES):
        report_lines.append(
            f"{status}: {status_counts[status]}"
        )

    report_lines.extend([
        "",
        "VALIDATION CHECKS",
        "-" * 65,
        "All five expected input files found: PASS",
        "Expected row counts: PASS",
        "Required columns present: PASS",
        "Column names and order consistent: PASS",
        "Duplicate document/line IDs: NONE",
        "Pending annotations: NONE",
        "Training rows have transcription: PASS",
        "Excluded rows have empty transcription: PASS",
        "OCR confidence values within 0-1: PASS",
        f"Saved output row count: {len(saved_rows)}",
        "",
        "NOTE",
        "-" * 65,
        "These checks verify dataset structure and consistency.",
        "They do not independently verify transcription accuracy.",
    ])

    REPORT_FILE.write_text(
        "\n".join(report_lines),
        encoding="utf-8"
    )

    print("\n" + "=" * 65)
    print("CONSOLIDATION SUCCESSFUL")
    print("=" * 65)

    print(f"\nTotal rows: {total_rows}")
    print(f"Training-eligible rows: {training_rows}")
    print(f"Excluded rows: {excluded_rows}")

    print("\nStatus counts:")
    for status in sorted(VALID_STATUSES):
        print(f"  {status}: {status_counts[status]}")

    print(f"\nConsolidated CSV:\n{OUTPUT_CSV}")
    print(f"\nReport:\n{REPORT_FILE}")

    print("\nOriginal workbench files were not modified.")


if __name__ == "__main__":

    try:
        main()

    except Exception as error:
        print("\nCONSOLIDATION STOPPED")
        print("-" * 65)
        print(error)
        sys.exit(1)