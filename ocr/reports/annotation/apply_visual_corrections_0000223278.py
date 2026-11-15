
import csv
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

REVIEW_FILE = (
    PROJECT_ROOT
    / "ocr"
    / "data"
    / "annotations"
    / "ocr_validation"
    / "document_0000223278_review.csv"
)

# Only the 17 pending rows with sufficiently readable text.
CORRECTIONS = {
    "Page1_Block6_l2": (
        "3000 First National Tower,",
        "correct",
    ),
    "Page1_Block6_l3": (
        "101 South Fifth Street,",
        "correct",
    ),
    "Page1_Block6_l4": (
        "Louisville, Kentucky 40202,",
        "correct",
    ),
    "Page1_Block6_l5": (
        "U.S.A.",
        "correct",
    ),
    "Page1_Block7_l2": (
        "Telegraphic Address Export Woking",
        "major_error",
    ),
    "Page1_Block7_l3": (
        "Telex 8M101",
        "minor_error",
    ),
    "Page1_Block7_l4": (
        "VAT Reg. No. 239136S",
        "minor_error",
    ),
    "Page1_Block9_l1": (
        "Invoice No.",
        "minor_error",
    ),
    "Page1_Block10_l1": (
        "N. 1816",
        "minor_error",
    ),
    "Page1_Block11_l1": (
        "Date (Tax Point)",
        "minor_error",
    ),
    "Page1_Block12_l1": (
        "26.5.82",
        "minor_error",
    ),
    "Page1_Block13_l1": (
        "By debit in respect of:-",
        "correct",
    ),
    "Page1_Block13_l2": (
        "'Half of Counter Deal charges",
        "minor_error",
    ),
    "Page1_Block13_l3": (
        "in 1981 in excess of your earlier",
        "correct",
    ),
    "Page1_Block13_l4": (
        "estimate. Geoff Harper's telex",
        "correct",
    ),
    "Page1_Block13_l5": (
        "of 25/5/82 refers'.",
        "correct",
    ),
    "Page1_Block16_l1": (
        "US$13,600.00",
        "minor_error",
    ),
}

NOTES = {
    "Page1_Block7_l4": (
        "Transcribed from the invoice image; "
        "final VAT registration character should be checked."
    ),
    "Page1_Block13_l2": (
        "Opening quotation mark retained as printed."
    ),
    "Page1_Block13_l5": (
        "Closing quotation mark retained as printed."
    ),
}


def main():
    if not REVIEW_FILE.exists():
        raise FileNotFoundError(REVIEW_FILE)

    with open(
        REVIEW_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames
        rows = list(reader)

    required = {
        "document_id",
        "ocr_line_id",
        "predicted_text",
        "ground_truth_text",
        "validation_status",
        "reviewer_notes",
    }

    missing = required - set(columns or [])

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    ids = [row["ocr_line_id"] for row in rows]

    if len(ids) != len(set(ids)):
        raise ValueError(
            "Duplicate line IDs found. No changes made."
        )

    if len(rows) != 24:
        raise ValueError(
            f"Expected 24 rows, found {len(rows)}. "
            "No changes made."
        )

    row_by_id = {
        row["ocr_line_id"]: row
        for row in rows
    }

    missing_ids = set(CORRECTIONS) - set(row_by_id)

    if missing_ids:
        raise ValueError(
            f"Expected line IDs missing: {sorted(missing_ids)}"
        )

    # Protect every previously reviewed row.
    for line_id in CORRECTIONS:
        if row_by_id[line_id]["validation_status"] != "pending":
            raise ValueError(
                f"{line_id} is not pending. "
                "No changes made."
            )

    # Verify that the uncertain row remains untouched.
    uncertain_id = "Page1_Block13_l6"

    if row_by_id[uncertain_id]["validation_status"] != "pending":
        raise ValueError(
            "The uncertain line is no longer pending. "
            "Review it manually before proceeding."
        )

    # Create a backup before modifying the CSV.
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup = REVIEW_FILE.with_name(
        f"{REVIEW_FILE.stem}_backup_{timestamp}.csv"
    )

    shutil.copy2(REVIEW_FILE, backup)

    for line_id, (ground_truth, status) in CORRECTIONS.items():
        row = row_by_id[line_id]

        row["ground_truth_text"] = ground_truth
        row["validation_status"] = status

        row["reviewer_notes"] = NOTES.get(
            line_id,
            "Transcribed by visual comparison with the original invoice."
        )

    # Safe write using a temporary file.
    temporary_file = REVIEW_FILE.with_suffix(".tmp")

    try:
        with open(
            temporary_file,
            "w",
            encoding="utf-8-sig",
            newline=""
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=columns
            )
            writer.writeheader()
            writer.writerows(rows)

        temporary_file.replace(REVIEW_FILE)

    except Exception:
        if temporary_file.exists():
            temporary_file.unlink()
        raise

    counts = Counter(
        row["validation_status"]
        for row in rows
    )

    print("=" * 65)
    print("VISUAL CORRECTIONS APPLIED")
    print("=" * 65)
    print(f"Document: 0000223278")
    print(f"Total lines: {len(rows)}")
    print(f"Newly reviewed: {len(CORRECTIONS)}")
    print(f"Still pending: {counts['pending']}")
    print(f"Backup: {backup}")
    print(f"Updated CSV: {REVIEW_FILE}")
    print()
    print("FINAL STATUS COUNTS")

    for status, count in sorted(counts.items()):
        print(f"{status}: {count}")

    print("=" * 65)
    print("Original Day 16 audit was not modified.")


if __name__ == "__main__":
    main()
