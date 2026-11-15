
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
    / "document_0011500947_review.csv"
)

CORRECTIONS = {
    "Page1_Block1_l1": ("Analytic Insight, Inc.", "minor_error"),
    "Page1_Block1_l2": ("3255 North Arlington Heights Rd., Suite 510", "major_error"),
    "Page1_Block1_l3": ("Arlington Heights, IL 60004", "minor_error"),
    "Page1_Block1_l4": ("(708) 255-5511", "major_error"),
    "Page1_Block2_l1": ("INVOICE", "major_error"),
    "Page1_Block3_l1": ("DATE:", "correct"),
    "Page1_Block4_l1": ("August 14, 1995", "correct"),
    "Page1_Block6_l1": ("FROM:", "correct"),
    "Page1_Block7_l1": ("Ms. Vicki Clark CC: Mr. Ed Gelson", "correct"),
    "Page1_Block7_l2": ("Brown & Williamson Tobacco Corp.", "correct"),
    "Page1_Block7_l3": ("Analytic Insight, Inc.", "correct"),
    "Page1_Block8_l1": ("AMOUNT DUE: $11,780.63", "correct"),
    "Page1_Block9_l1": ("PROJECT: Lucky Strike Competitive Research", "correct"),
    "Page1_Block9_l2": ("(New York and Louisville)", "correct"),
    "Page1_Block9_l3": ("B&W Project No.: 1995-83D", "correct"),
    "Page1_Block9_l4": ("Analytic Insight Project No.: 95-703", "correct"),
    "Page1_Block9_l5": (
        "COMMENTS: This invoice represents the completion of the analysis",
        "correct"
    ),
    "Page1_Block9_l6": (
        "and covers the last one-third of Analytic Insight's",
        "correct"
    ),
    "Page1_Block9_l7": (
        "basic fee ($25,750) for this project plus the cost of",
        "correct"
    ),
    "Page1_Block9_l8": (
        "videotaping focus groups ($1,010.00) plus travel",
        "correct"
    ),
    "Page1_Block9_l9": (
        "expenses incurred by Analytic Insight moderators",
        "correct"
    ),
    "Page1_Block9_l10": ("($2,187.29).", "correct"),
    "Page1_Block10_l1": (
        "Expense reports and receipts are attached.",
        "correct"
    ),
    "Page1_Block11_l1": ("Vendor #", "correct"),
    "Page1_Block11_l2": ("Account #", "correct"),
    "Page1_Block11_l3": ("Acct. Desc.", "correct"),
    "Page1_Block11_l4": ("Dept. #", "correct"),
    "Page1_Block11_l5": ("Product #", "correct"),
    "Page1_Block13_l1": ("Thank you!", "correct"),
    "Page1_Block16_l1": ("1510", "major_error"),
    "Page1_Block17_l1": ("Account No.", "correct"),
    "Page1_Block17_l2": ("Pay Date", "correct"),
    "Page1_Block19_l1": ("Approval", "correct"),
    "Page1_Block19_l2": ("1995-83", "major_error"),
    "Page1_Block21_l1": ("465761403", "correct"),
}

REVIEWER_NOTES = {
    "Page1_Block16_l1": "Handwritten value visually transcribed as 1510.",
    "Page1_Block19_l2": "Handwritten value visually transcribed as 1995-83.",
}


def main():
    if not REVIEW_FILE.exists():
        raise FileNotFoundError(REVIEW_FILE)

    with open(REVIEW_FILE, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    required_columns = {
        "document_id",
        "ocr_line_id",
        "predicted_text",
        "ground_truth_text",
        "validation_status",
        "reviewer_notes",
    }

    missing = required_columns - set(fieldnames or [])

    if missing:
        raise ValueError(f"Missing CSV columns: {sorted(missing)}")

    row_ids = [row["ocr_line_id"] for row in rows]

    if len(row_ids) != len(set(row_ids)):
        raise ValueError("Duplicate OCR line IDs found. No changes made.")

    if len(rows) != len(CORRECTIONS):
        raise ValueError(
            f"Expected {len(CORRECTIONS)} rows, found {len(rows)}. "
            "No changes made."
        )

    if set(row_ids) != set(CORRECTIONS):
        missing_ids = set(CORRECTIONS) - set(row_ids)
        extra_ids = set(row_ids) - set(CORRECTIONS)

        raise ValueError(
            f"Line ID mismatch. Missing: {missing_ids}; "
            f"Unexpected: {extra_ids}. No changes made."
        )

    # Protect against overwriting previous human review.
    non_pending = [
        row["ocr_line_id"]
        for row in rows
        if row["validation_status"] != "pending"
    ]

    if non_pending:
        raise ValueError(
            "Some rows are no longer pending. "
            "Review the CSV before applying these corrections: "
            + ", ".join(non_pending)
        )

    # Create a timestamped backup before changing anything.
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = REVIEW_FILE.with_name(
        f"{REVIEW_FILE.stem}_backup_{timestamp}.csv"
    )

    shutil.copy2(REVIEW_FILE, backup_file)

    for row in rows:
        line_id = row["ocr_line_id"]
        ground_truth, status = CORRECTIONS[line_id]

        row["ground_truth_text"] = ground_truth
        row["validation_status"] = status
        row["reviewer_notes"] = REVIEWER_NOTES.get(
            line_id,
            "Transcribed by visual comparison with the original invoice image."
        )

    # Write to a temporary file, then replace the original.
    temporary_file = REVIEW_FILE.with_suffix(".tmp")

    with open(temporary_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    temporary_file.replace(REVIEW_FILE)

    print("=" * 65)
    print("VISUAL CORRECTIONS APPLIED")
    print("=" * 65)
    print(f"Document: 0011500947")
    print(f"Total reviewed lines: {len(rows)}")
    print(f"Backup: {backup_file}")
    print(f"Updated CSV: {REVIEW_FILE}")
    print("=" * 65)

    for status in ("correct", "minor_error", "major_error"):
        count = sum(
            1 for row in rows
            if row["validation_status"] == status
        )
        print(f"{status}: {count}")


if __name__ == "__main__":
    main()
