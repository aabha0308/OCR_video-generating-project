import csv
from pathlib import Path
from collections import Counter, defaultdict
from statistics import median

OCR_ROOT = Path(__file__).resolve().parents[2]

MANIFEST = (
    OCR_ROOT
    / "data"
    / "processed"
    / "ocr_line_crops"
    / "final_v2"
    / "final_crop_manifest_v2.csv"
)

OUTPUT = (
    OCR_ROOT
    / "reports"
    / "annotation"
    / "crop_quality_review"
    / "v4_manifest_sample_2026-11-20"
    / "crop_dimension_analysis.txt"
)


def main():

    if not MANIFEST.exists():
        raise FileNotFoundError(MANIFEST)

    with MANIFEST.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        rows = list(csv.DictReader(f))

    by_document = defaultdict(list)
    reasons = Counter()
    all_widths = []
    all_heights = []

    for row in rows:

        width = int(row["crop_width"])
        height = int(row["crop_height"])

        all_widths.append(width)
        all_heights.append(height)

        by_document[row["document_id"]].append(row)

        if height < 12 and width < 8:
            reasons["Both width and height"] += 1
        elif height < 12:
            reasons["Height only"] += 1
        elif width < 8:
            reasons["Width only"] += 1
        else:
            reasons["Not flagged"] += 1

    lines = [
        "OCR CROP DIMENSION ANALYSIS",
        "=" * 65,
        f"Total crops: {len(rows)}",
        f"Flagged crops: {sum(reasons.values()) - reasons['Not flagged']}",
        "",
        "FLAG REASONS",
        "-" * 65,
    ]

    for reason, count in reasons.items():
        lines.append(f"{reason}: {count}")

    lines.extend([
        "",
        "OVERALL DIMENSION STATISTICS",
        "-" * 65,
        f"Width - minimum: {min(all_widths)}",
        f"Width - median: {median(all_widths)}",
        f"Width - maximum: {max(all_widths)}",
        f"Height - minimum: {min(all_heights)}",
        f"Height - median: {median(all_heights)}",
        f"Height - maximum: {max(all_heights)}",
        "",
        "PER-DOCUMENT ANALYSIS",
        "-" * 65,
    ])

    for document_id, document_rows in sorted(by_document.items()):

        widths = [int(r["crop_width"]) for r in document_rows]
        heights = [int(r["crop_height"]) for r in document_rows]

        flagged = sum(
            1 for r in document_rows
            if int(r["crop_height"]) < 12
            or int(r["crop_width"]) < 8
        )

        lines.extend([
            "",
            f"Document: {document_id}",
            f"Total crops: {len(document_rows)}",
            f"Flagged: {flagged}",
            f"Width min/median/max: "
            f"{min(widths)}/{median(widths)}/{max(widths)}",
            f"Height min/median/max: "
            f"{min(heights)}/{median(heights)}/{max(heights)}",
        ])

        # Show 5 smallest crops by area for investigation.
        smallest = sorted(
            document_rows,
            key=lambda r: (
                int(r["crop_width"]) * int(r["crop_height"])
            )
        )[:5]

        lines.append("Five smallest crops:")

        for row in smallest:
            lines.append(
                f"  {row['ocr_line_id']}: "
                f"{row['crop_width']}x{row['crop_height']} | "
                f"GT: {row['ground_truth_text']}"
            )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print(f"\nReport saved to:\n{OUTPUT}")


if __name__ == "__main__":
    main()