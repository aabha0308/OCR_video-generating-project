
import csv
from pathlib import Path
from collections import Counter

ROOT = Path(r"D:\OCR_Internship\ocr")

ANNOTATION_DIR = (
    ROOT / "data/annotations/ocr_validation"
)

DOCUMENTS = [
    "507484246",
    "2061828225",
    "ti31149327_9330",
    "503116473+-6473",
    "96052028",
]

VALID_STATUSES = [
    "pending",
    "correct",
    "minor_error",
    "major_error",
    "non_text",
    "unreadable",
]


def main():
    overall = Counter()
    total_rows = 0
    total_missing_gt = 0

    print("=" * 75)
    print("OCR HUMAN ANNOTATION PROGRESS")
    print("=" * 75)

    for document_id in DOCUMENTS:
        path = (
            ANNOTATION_DIR
            / f"document_{document_id}_review.csv"
        )

        if not path.exists():
            print(f"\nMISSING FILE: {path.name}")
            continue

        with path.open(
            "r", encoding="utf-8-sig", newline=""
        ) as f:
            rows = list(csv.DictReader(f))

        counts = Counter(
            row.get("validation_status", "").strip()
            for row in rows
        )

        missing_gt = sum(
            1 for row in rows
            if not row.get("ground_truth_text", "").strip()
        )

        print(f"\nDOCUMENT: {document_id}")
        print("-" * 45)
        print("Total lines:", len(rows))

        for status in VALID_STATUSES:
            print(
                f"{status:15}: "
                f"{counts.get(status, 0)}"
            )

        print("Missing ground truth:", missing_gt)

        total_rows += len(rows)
        total_missing_gt += missing_gt
        overall.update(counts)

    print("\n" + "=" * 75)
    print("OVERALL SUMMARY")
    print("=" * 75)

    print("Total lines:", total_rows)

    for status in VALID_STATUSES:
        print(
            f"{status:15}: "
            f"{overall.get(status, 0)}"
        )

    print("Missing ground truth:", total_missing_gt)

    completed = sum(
        overall.get(status, 0)
        for status in [
            "correct",
            "minor_error",
            "major_error",
            "non_text",
            "unreadable",
        ]
    )

    pending = overall.get("pending", 0)

    print("\nCompletion:")
    if total_rows:
        print(
            f"{completed}/{total_rows} "
            f"({completed / total_rows * 100:.2f}%)"
        )

    print("Still pending:", pending)

    print("\nNote: A non-pending status means reviewed,")
    print("not necessarily eligible for OCR model training.")


if __name__ == "__main__":
    main()
