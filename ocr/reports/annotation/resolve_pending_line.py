
import csv
import shutil
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

LINE_ID = "Page1_Block13_l6"
GROUND_TRUTH = "£1.80"


def main():
    with open(REVIEW_FILE, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames
        rows = list(reader)

    matches = [r for r in rows if r["ocr_line_id"] == LINE_ID]

    if len(matches) != 1:
        raise ValueError("Expected exactly one matching OCR line.")

    row = matches[0]

    if row["validation_status"] != "pending":
        raise ValueError("Line is no longer pending. No changes made.")

    backup = REVIEW_FILE.with_name(
        REVIEW_FILE.stem
        + "_backup_"
        + datetime.now().strftime("%Y%m%d_%H%M%S")
        + ".csv"
    )

    shutil.copy2(REVIEW_FILE, backup)

    row["ground_truth_text"] = GROUND_TRUTH
    row["validation_status"] = "minor_error"
    row["reviewer_notes"] = (
        "Visually transcribed as £1.80. "
        "OCR confused the pound symbol with @."
    )

    temp_file = REVIEW_FILE.with_suffix(".tmp")

    with open(temp_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    temp_file.replace(REVIEW_FILE)

    print("Remaining pending annotation updated.")
    print(f"Line: {LINE_ID}")
    print(f"Ground truth: {GROUND_TRUTH}")
    print(f"Backup: {backup}")


if __name__ == "__main__":
    main()

