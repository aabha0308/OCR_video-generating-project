
import csv
import math
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATASET_DIR = (
    PROJECT_ROOT / "ocr/data/processed/ocr_line_crops/v1"
)

METADATA_FILE = DATASET_DIR / "line_crop_dataset.csv"

OUTPUT_DIR = (
    PROJECT_ROOT / "ocr/reports/annotation/crop_quality_review/v1"
)

COLUMNS = 2
ROWS_PER_SHEET = 4

CELL_WIDTH = 900
CELL_HEIGHT = 230
IMAGE_MAX_WIDTH = 850
IMAGE_MAX_HEIGHT = 150

BACKGROUND = "white"
TEXT_COLOR = "black"
BORDER_COLOR = "#999999"


def load_font(size):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def main():
    if not METADATA_FILE.exists():
        raise FileNotFoundError(
            f"Dataset metadata not found: {METADATA_FILE}"
        )

    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"Output already exists: {OUTPUT_DIR}\n"
            "Inspect it or choose a new version."
        )

    with open(
        METADATA_FILE,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        records = list(csv.DictReader(f))

    if not records:
        raise ValueError("No crop records found.")

    grouped = defaultdict(list)

    for record in records:
        grouped[record["document_id"]].append(record)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)

    title_font = load_font(28)
    label_font = load_font(19)
    small_font = load_font(15)

    sheet_count = 0

    for document_id, document_records in sorted(grouped.items()):

        total_per_sheet = COLUMNS * ROWS_PER_SHEET
        number_of_sheets = math.ceil(
            len(document_records) / total_per_sheet
        )

        for sheet_index in range(number_of_sheets):
            start = sheet_index * total_per_sheet
            end = start + total_per_sheet

            batch = document_records[start:end]

            sheet_width = COLUMNS * CELL_WIDTH
            sheet_height = 70 + ROWS_PER_SHEET * CELL_HEIGHT

            sheet = Image.new(
                "RGB",
                (sheet_width, sheet_height),
                BACKGROUND,
            )

            draw = ImageDraw.Draw(sheet)

            title = (
                f"Document: {document_id} | "
                f"Sheet {sheet_index + 1}/{number_of_sheets}"
            )

            draw.text(
                (20, 15),
                title,
                fill=TEXT_COLOR,
                font=title_font,
            )

            for index, record in enumerate(batch):
                column = index % COLUMNS
                row = index // COLUMNS

                x = column * CELL_WIDTH
                y = 70 + row * CELL_HEIGHT

                draw.rectangle(
                    (
                        x + 5,
                        y + 5,
                        x + CELL_WIDTH - 5,
                        y + CELL_HEIGHT - 5,
                    ),
                    outline=BORDER_COLOR,
                    width=2,
                )

                line_id = record["ocr_line_id"]
                status = record["validation_status"]
                predicted = record["predicted_text"]
                ground_truth = record["ground_truth_text"]

                draw.text(
                    (x + 18, y + 12),
                    f"{line_id} | {status}",
                    fill=TEXT_COLOR,
                    font=label_font,
                )

                crop_path = DATASET_DIR / record["crop_path"]

                if not crop_path.exists():
                    raise FileNotFoundError(
                        f"Crop missing: {crop_path}"
                    )

                with Image.open(crop_path) as source:
                    crop = source.convert("RGB")

                crop.thumbnail(
                    (IMAGE_MAX_WIDTH, IMAGE_MAX_HEIGHT),
                    Image.Resampling.LANCZOS,
                )

                crop_x = x + 18
                crop_y = y + 43

                sheet.paste(crop, (crop_x, crop_y))

                text_y = y + CELL_HEIGHT - 47

                draw.text(
                    (x + 18, text_y),
                    f"GT: {ground_truth[:90]}",
                    fill=TEXT_COLOR,
                    font=small_font,
                )

                draw.text(
                    (x + 18, text_y + 19),
                    f"OCR: {predicted[:90]}",
                    fill=TEXT_COLOR,
                    font=small_font,
                )

                crop.close()

            output_file = (
                OUTPUT_DIR
                / f"{document_id}_sheet_{sheet_index + 1:02d}.png"
            )

            sheet.save(output_file)
            sheet.close()

            sheet_count += 1

            print(f"Created: {output_file}")

    print("\n" + "=" * 55)
    print("CROP CONTACT SHEETS CREATED")
    print("=" * 55)
    print(f"Documents: {len(grouped)}")
    print(f"Crop records: {len(records)}")
    print(f"Contact sheets: {sheet_count}")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
