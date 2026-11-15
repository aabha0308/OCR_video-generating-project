
import argparse
import csv
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATASET_DIR = (
    PROJECT_ROOT
    / "ocr"
    / "data"
    / "raw"
    / "invoices"
    / "archive"
    / "ImageAndXML_Data"
)

AUDIT_FILE = (
    PROJECT_ROOT
    / "ocr"
    / "reports"
    / "day16_gt_ocr_line_mapping_audit.csv"
)

REVIEW_DIR = (
    PROJECT_ROOT
    / "ocr"
    / "data"
    / "annotations"
    / "ocr_validation"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "ocr"
    / "reports"
    / "annotation"
    / "visual_review"
)


def read_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def load_font(size=16):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def get_crop(image, row, padding=5):
    x1 = float(row["ocr_x1"])
    y1 = float(row["ocr_y1"])
    x2 = float(row["ocr_x2"])
    y2 = float(row["ocr_y2"])

    left = max(0, int(x1 - padding))
    top = max(0, int(y1 - padding))
    right = min(image.width, int(x2 + padding))
    bottom = min(image.height, int(y2 + padding))

    if right <= left or bottom <= top:
        raise ValueError(
            f"Invalid bounding box for {row['ocr_line_id']}"
        )

    return image.crop((left, top, right, bottom))


def create_annotated_page(image, rows, output_path):
    page = image.convert("RGB").copy()
    draw = ImageDraw.Draw(page)

    font = load_font(12)

    for row in rows:
        x1 = int(float(row["ocr_x1"]))
        y1 = int(float(row["ocr_y1"]))
        x2 = int(float(row["ocr_x2"]))
        y2 = int(float(row["ocr_y2"]))

        draw.rectangle(
            (x1, y1, x2, y2),
            outline="red",
            width=2
        )

        # Short label keeps the original page readable.
        label = row["ocr_line_id"].split("_")[-1]

        label_y = max(0, y1 - 15)

        draw.text(
            (x1, label_y),
            label,
            fill="red",
            font=font,
            stroke_width=1,
            stroke_fill="white"
        )

    page.save(output_path)


def create_contact_sheet(image, rows, output_path):
    columns = 2
    card_width = 600
    card_height = 175
    crop_width = 560
    crop_height = 90
    gap = 12
    margin = 15

    total_rows = (len(rows) + columns - 1) // columns

    sheet_width = margin * 2 + columns * card_width + gap
    sheet_height = margin * 2 + total_rows * card_height

    sheet = Image.new(
        "RGB",
        (sheet_width, sheet_height),
        "white"
    )

    draw = ImageDraw.Draw(sheet)
    title_font = load_font(15)
    body_font = load_font(13)

    for index, row in enumerate(rows):
        column = index % columns
        row_number = index // columns

        x = margin + column * (card_width + gap)
        y = margin + row_number * card_height

        # Card boundary
        draw.rectangle(
            (
                x,
                y,
                x + card_width - 8,
                y + card_height - 8
            ),
            outline="gray",
            width=1
        )

        line_id = row["ocr_line_id"]
        confidence = row["ocr_line_confidence"]
        entity = row.get("matched_entity", "")
        match_status = row.get("match_status", "")

        header = (
            f"{line_id} | Confidence: {confidence} | "
            f"Entity: {entity} | Match: {match_status}"
        )

        draw.text(
            (x + 8, y + 7),
            header[:85],
            fill="black",
            font=title_font
        )

        predicted_text = row["ocr_text"].replace("\n", " ").strip()

        wrapped = textwrap.wrap(
            f"Predicted: {predicted_text}",
            width=75
        )

        text_y = y + 28

        for line in wrapped[:2]:
            draw.text(
                (x + 8, text_y),
                line,
                fill="blue",
                font=body_font
            )
            text_y += 17

        crop = get_crop(image, row, padding=6).convert("RGB")

        # Enlarge small text crops, but do not exceed card dimensions.
        scale = min(
            3,
            crop_width / crop.width,
            crop_height / crop.height
        )

        new_width = max(1, int(crop.width * scale))
        new_height = max(1, int(crop.height * scale))

        crop = crop.resize(
            (new_width, new_height),
            Image.Resampling.LANCZOS
        )

        crop_x = x + 8
        crop_y = y + 65

        sheet.paste(crop, (crop_x, crop_y))

    sheet.save(output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Generate OCR visual-review images."
    )

    parser.add_argument(
        "--document-id",
        required=True,
        help="Document ID, for example 0011500947"
    )

    args = parser.parse_args()
    document_id = args.document_id.strip()

    image_path = DATASET_DIR / f"{document_id}.tif"
    review_path = REVIEW_DIR / f"document_{document_id}_review.csv"

    if not image_path.exists():
        raise FileNotFoundError(
            f"Original TIFF image not found: {image_path}"
        )

    if not review_path.exists():
        raise FileNotFoundError(
            f"Review CSV not found: {review_path}"
        )

    audit_rows = read_csv(AUDIT_FILE)
    review_rows = read_csv(review_path)

    rows = [
        row for row in audit_rows
        if row["document_id"] == document_id
    ]

    if not rows:
        raise ValueError(
            f"No OCR audit rows found for {document_id}"
        )

    review_ids = {
        row["ocr_line_id"] for row in review_rows
    }

    audit_ids = {
        row["ocr_line_id"] for row in rows
    }

    if review_ids != audit_ids:
        raise ValueError(
            "Review CSV and audit contain different OCR line IDs. "
            "No output was generated."
        )

    required_columns = [
        "ocr_x1", "ocr_y1", "ocr_x2", "ocr_y2",
        "ocr_text", "ocr_line_id", "ocr_line_confidence"
    ]

    for row in rows:
        for column in required_columns:
            if row.get(column, "") == "":
                raise ValueError(
                    f"Missing {column} for {row['ocr_line_id']}"
                )

    output_folder = OUTPUT_DIR / document_id
    output_folder.mkdir(parents=True, exist_ok=True)

    page = Image.open(image_path)
    page.load()

    annotated_path = (
        output_folder / f"{document_id}_annotated_page.png"
    )

    contact_sheet_path = (
        output_folder / f"{document_id}_line_contact_sheet.png"
    )

    create_annotated_page(
        page,
        rows,
        annotated_path
    )

    create_contact_sheet(
        page,
        rows,
        contact_sheet_path
    )

    print("=" * 65)
    print("OCR VISUAL REVIEW FILES CREATED")
    print("=" * 65)
    print(f"Document ID: {document_id}")
    print(f"Image dimensions: {page.width} x {page.height}")
    print(f"OCR lines: {len(rows)}")
    print(f"Annotated page: {annotated_path}")
    print(f"Contact sheet: {contact_sheet_path}")
    print("=" * 65)
    print("Original image, audit CSV and review CSV were not modified.")


if __name__ == "__main__":
    main()
