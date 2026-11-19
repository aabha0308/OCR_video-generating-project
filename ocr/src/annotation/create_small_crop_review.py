import csv
from pathlib import Path
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont
import math

OCR_ROOT = Path(__file__).resolve().parents[2]

MANIFEST = (
    OCR_ROOT / "data" / "processed" / "ocr_line_crops"
    / "final_v2" / "final_crop_manifest_v2.csv"
)

OUTPUT_DIR = (
    OCR_ROOT / "reports" / "annotation" / "crop_quality_review"
    / "v5_small_crop_review_2026-11-20"
)

CARD_W = 500
CARD_H = 190
COLUMNS = 2


def read_rows():
    with MANIFEST.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def make_sheet(document_id, rows):

    rows_per_sheet = math.ceil(len(rows) / COLUMNS)

    sheet = Image.new(
        "RGB",
        (CARD_W * COLUMNS, CARD_H * rows_per_sheet),
        "white"
    )

    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()

    for i, row in enumerate(rows):

        x = (i % COLUMNS) * CARD_W
        y = (i // COLUMNS) * CARD_H

        draw.rectangle(
            (x + 3, y + 3, x + CARD_W - 3, y + CARD_H - 3),
            outline="gray",
            width=2
        )

        title = f"{row['ocr_line_id']} | {row['crop_width']}x{row['crop_height']}"
        gt = row["ground_truth_text"].replace("\n", " ")

        draw.text((x + 10, y + 10), title, fill="black", font=font)
        draw.text(
            (x + 10, y + 27),
            "GT: " + gt[:100],
            fill="black",
            font=font
        )

        crop_path = Path(row["crop_path"])

        with Image.open(crop_path) as source:
            crop = source.convert("RGB")

            # Enlarge small characters without smoothing their edges.
            scale = min(
                8,
                440 / crop.width,
                100 / crop.height
            )

            new_size = (
                max(1, round(crop.width * scale)),
                max(1, round(crop.height * scale))
            )

            preview = crop.resize(
                new_size,
                Image.Resampling.NEAREST
            )

        sheet.paste(preview, (x + 10, y + 55))

    output = OUTPUT_DIR / f"{document_id}_small_crop_review.png"
    sheet.save(output)
    print(f"Saved: {output}")


def main():

    if not MANIFEST.exists():
        raise FileNotFoundError(MANIFEST)

    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"Review folder already exists: {OUTPUT_DIR}"
        )

    rows = read_rows()
    grouped = defaultdict(list)

    for row in rows:
        grouped[row["document_id"]].append(row)

    OUTPUT_DIR.mkdir(parents=True)

    selected_all = []

    for document_id, doc_rows in sorted(grouped.items()):

        selected = {}

        # Five shortest crops by height.
        for row in sorted(
            doc_rows,
            key=lambda r: (
                int(r["crop_height"]),
                int(r["crop_width"])
            )
        )[:5]:
            selected[row["ocr_line_id"]] = row

        # Three crops closest to median height.
        heights = sorted(int(r["crop_height"]) for r in doc_rows)
        middle_height = heights[len(heights) // 2]

        for row in sorted(
            doc_rows,
            key=lambda r: abs(
                int(r["crop_height"]) - middle_height
            )
        )[:3]:
            selected[row["ocr_line_id"]] = row

        # Two narrowest crops.
        for row in sorted(
            doc_rows,
            key=lambda r: int(r["crop_width"])
        )[:2]:
            selected[row["ocr_line_id"]] = row

        # Always include replacement-character transcriptions.
        for row in doc_rows:
            if "\ufffd" in row["ground_truth_text"]:
                selected[row["ocr_line_id"]] = row

        chosen = list(selected.values())
        selected_all.extend(chosen)

        print(f"\n{document_id}: {len(chosen)} crops selected")

        make_sheet(document_id, chosen)

    # Save exact list of selected crops.
    output_csv = OUTPUT_DIR / "selected_review_crops.csv"

    with output_csv.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(selected_all[0].keys())
        )
        writer.writeheader()
        writer.writerows(selected_all)

    print("\nReview selection completed.")
    print("Total selected:", len(selected_all))
    print("Output folder:", OUTPUT_DIR)


if __name__ == "__main__":
    main()