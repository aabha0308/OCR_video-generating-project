
import csv
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]

WORKBENCH = (
    ROOT / "data/annotations/ocr_validation/workbench_v1"
)

DOCUMENTS = [
    "507484246",
    "2061828225",
    "ti31149327_9330",
    "503116473+-6473",
    "96052028",
]

STATUSES = [
    "pending",
    "correct",
    "minor_error",
    "major_error",
    "non_text",
    "unreadable",
]


def main():
    overall = Counter()
    total = 0
    missing_text = 0

    print("=" * 65)
    print("OCR WORKBENCH PROGRESS")
    print("=" * 65)

    for document_id in DOCUMENTS:
        path = (
            WORKBENCH
            / f"document_{document_id}_review.csv"
        )

        if not path.exists():
            print("\nMISSING:", path)
            continue

        with path.open(
            "r", encoding="utf-8-sig", newline=""
        ) as f:
            rows = list(csv.DictReader(f))

        counts = Counter(
            row["validation_status"] for row in rows
        )

        missing = sum(
            1 for row in rows
            if row["validation_status"] in {
                "correct", "minor_error", "major_error"
            }
            and not row["ground_truth_text"].strip()
        )

        total += len(rows)
        overall.update(counts)
        missing_text += missing

        reviewed = len(rows) - counts.get("pending", 0)

        print(f"\n{document_id}")
        print("-" * 45)
        print(f"Total lines: {len(rows)}")
        print(f"Reviewed: {reviewed}")
        print(f"Pending: {counts.get('pending', 0)}")

        for status in STATUSES:
            print(f"{status:15}: {counts.get(status, 0)}")

        print("Training-status rows missing text:", missing)

    reviewed_total = total - overall.get("pending", 0)

    print("\n" + "=" * 65)
    print("OVERALL")
    print("=" * 65)
    print("Total lines:", total)
    print("Reviewed:", reviewed_total)
    print("Pending:", overall.get("pending", 0))
    print("Training-status rows missing text:", missing_text)

    if total:
        print(
            "Completion: "
            f"{reviewed_total / total * 100:.2f}%"
        )

    print("\nStatus counts:")
    for status in STATUSES:
        print(f"{status:15}: {overall.get(status, 0)}")


if __name__ == "__main__":
    main()
