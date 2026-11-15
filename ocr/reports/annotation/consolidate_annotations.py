
import csv
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

INPUT_DIR = (
    PROJECT_ROOT
    / "ocr"
    / "data"
    / "annotations"
    / "ocr_validation"
)

SOURCE_FILES = [
    "document_0000223278_review.csv",
    "document_0011500947_review.csv",
]

OUTPUT_PARENT = (
    PROJECT_ROOT
    / "ocr"
    / "data"
    / "processed"
    / "annotations"
)

OUTPUT_DIR = OUTPUT_PARENT / "v1"
TEMP_OUTPUT_DIR = OUTPUT_PARENT / "v1.tmp"

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

TRAINING_STATUSES = {
    "correct",
    "minor_error",
    "major_error",
}

VALID_STATUSES = TRAINING_STATUSES | {
    "pending",
    "non_text",
    "unreadable",
}


def read_review_file(path):
    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError(f"Empty CSV: {path.name}")

        missing = set(REQUIRED_COLUMNS) - set(reader.fieldnames)

        if missing:
            raise ValueError(
                f"{path.name} is missing columns: {sorted(missing)}"
            )

        return list(reader)


def validate_records(records):
    seen_keys = set()

    for row in records:
        document_id = row["document_id"].strip()
        line_id = row["ocr_line_id"].strip()
        status = row["validation_status"].strip()
        ground_truth = row["ground_truth_text"]

        if not document_id or not line_id:
            raise ValueError("A row has a missing document or line ID.")

        key = (document_id, line_id)

        if key in seen_keys:
            raise ValueError(f"Duplicate annotation key: {key}")

        seen_keys.add(key)

        if status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status {status!r} for {key}"
            )

        if status == "pending":
            raise ValueError(
                f"Pending annotation found: {key}. "
                "Finish reviewing it before consolidation."
            )

        if status in TRAINING_STATUSES and not ground_truth.strip():
            raise ValueError(
                f"Missing ground truth for training record: {key}"
            )

        if status in {"non_text", "unreadable"} and ground_truth.strip():
            raise ValueError(
                f"{status} record unexpectedly has ground truth: {key}"
            )

    return len(seen_keys)


def write_csv(path, records):
    columns = ["source_file"] + REQUIRED_COLUMNS

    with open(
        path,
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=columns,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(records)


def create_report(path, all_records, training_records):
    status_counts = Counter(
        row["validation_status"] for row in all_records
    )

    document_counts = defaultdict(Counter)

    for row in all_records:
        document_counts[row["document_id"]][
            row["validation_status"]
        ] += 1

    lines = [
        "OCR ANNOTATION CONSOLIDATION REPORT",
        "=" * 65,
        "",
        f"Total reviewed records: {len(all_records)}",
        f"Training-ready text records: {len(training_records)}",
        f"Excluded non-text/unreadable records: "
        f"{len(all_records) - len(training_records)}",
        "",
        "STATUS COUNTS",
        "-" * 65,
    ]

    for status in sorted(VALID_STATUSES):
        lines.append(f"{status}: {status_counts[status]}")

    lines.extend([
        "",
        "DOCUMENT-WISE COUNTS",
        "-" * 65,
    ])

    for document_id in sorted(document_counts):
        counts = document_counts[document_id]
        total = sum(counts.values())

        lines.append(f"Document: {document_id}")
        lines.append(f"Total records: {total}")

        for status in sorted(counts):
            lines.append(f"  {status}: {counts[status]}")

        lines.append("")

    lines.extend([
        "OUTPUT FILES",
        "-" * 65,
        "all_review_annotations.csv",
        "training_ready_transcriptions.csv",
        "",
        "DATASET LIMITATIONS",
        "-" * 65,
        "This is a small pilot annotation dataset containing only "
        "two documents.",
        "It is not sufficient for final model training or "
        "performance claims.",
        "Ground truth has been visually reviewed but has not "
        "undergone independent second-review verification.",
        "Future train/validation/test splits must be performed "
        "at document level to prevent line leakage.",
        "",
    ])

    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"Version v1 already exists: {OUTPUT_DIR}\n"
            "Do not overwrite it. Review the existing version "
            "or create a new version intentionally."
        )

    if TEMP_OUTPUT_DIR.exists():
        raise FileExistsError(
            f"Temporary output already exists: {TEMP_OUTPUT_DIR}\n"
            "Inspect it before running again."
        )

    all_records = []

    for filename in SOURCE_FILES:
        source_path = INPUT_DIR / filename

        if not source_path.exists():
            raise FileNotFoundError(source_path)

        rows = read_review_file(source_path)

        expected_document_id = filename.replace(
            "document_", ""
        ).replace("_review.csv", "")

        for row in rows:
            if row["document_id"].strip() != expected_document_id:
                raise ValueError(
                    f"Unexpected document ID in {filename}: "
                    f"{row['document_id']}"
                )

            all_records.append({
                "source_file": filename,
                **row,
            })

    unique_count = validate_records(all_records)

    training_records = [
        row
        for row in all_records
        if row["validation_status"] in TRAINING_STATUSES
        and row["ground_truth_text"].strip()
    ]

    # Create a temporary directory first. Rename it to v1 only
    # after every output has been written successfully.
    OUTPUT_PARENT.mkdir(parents=True, exist_ok=True)
    TEMP_OUTPUT_DIR.mkdir()

    try:
        write_csv(
            TEMP_OUTPUT_DIR / "all_review_annotations.csv",
            all_records,
        )

        write_csv(
            TEMP_OUTPUT_DIR / "training_ready_transcriptions.csv",
            training_records,
        )

        create_report(
            TEMP_OUTPUT_DIR / "consolidation_report.txt",
            all_records,
            training_records,
        )

        TEMP_OUTPUT_DIR.rename(OUTPUT_DIR)

    except Exception:
        # Keep the temporary directory for inspection if a write fails.
        raise

    print("=" * 65)
    print("OCR ANNOTATION CONSOLIDATION COMPLETED")
    print("=" * 65)
    print(f"Source documents: {len(SOURCE_FILES)}")
    print(f"Total records: {len(all_records)}")
    print(f"Unique document-line keys: {unique_count}")
    print(f"Training-ready text records: {len(training_records)}")
    print(
        f"Excluded records: "
        f"{len(all_records) - len(training_records)}"
    )
    print()
    print(f"Output directory: {OUTPUT_DIR}")
    print("Files created:")
    print("  all_review_annotations.csv")
    print("  training_ready_transcriptions.csv")
    print("  consolidation_report.txt")
    print("=" * 65)
    print("Original per-document annotation files were not modified.")


if __name__ == "__main__":
    main()
