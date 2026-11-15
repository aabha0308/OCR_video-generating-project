
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

# Unicode escape avoids dependence on the source file's text encoding.
CORRECT_TEXT = "\u00A31.80"
REPLACEMENT_TEXT = "\uFFFD1.80"


def main():
    with open(REVIEW_FILE, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames
        rows = list(reader)

    matches = [r for r in rows if r["ocr_line_id"] == LINE_ID]

    if len(matches) != 1:
        raise ValueError("Expected exactly one matching line.")

    row = matches[0]
    current = row["ground_truth_text"]

    if current == CORRECT_TEXT:
        print("Text is already correctly encoded.")
        return

    if current != REPLACEMENT_TEXT:
        raise ValueError(
            f"Unexpected existing text: {current!r}. "
            "No changes made."
        )

    backup = REVIEW_FILE.with_name(
        REVIEW_FILE.stem
        + "_encoding_backup_"
        + datetime.now().strftime("%Y%m%d_%H%M%S")
        + ".csv"
    )

    shutil.copy2(REVIEW_FILE, backup)

    row["ground_truth_text"] = CORRECT_TEXT
    row["reviewer_notes"] = (
        "Visually transcribed as pound sign followed by 1.80. "
        "Unicode encoding corrected."
    )

    temp_file = REVIEW_FILE.with_suffix(".tmp")

    with open(temp_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    temp_file.replace(REVIEW_FILE)

    print("Encoding correction successful.")
    print("Ground truth:", repr(CORRECT_TEXT))
    print("Unicode code point:", hex(ord(CORRECT_TEXT[0])))
    print("Backup:", backup)


if __name__ == "__main__":
    main()
