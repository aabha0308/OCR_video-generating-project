import csv
import math
import textwrap
from pathlib import Path
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont


# --------------------------------------------------
# PATHS AND SETTINGS
# --------------------------------------------------

OCR_ROOT = Path(__file__).resolve().parents[2]

MANIFEST = (
    OCR_ROOT
    / "data"
    / "annotations"
    / "ocr_validation"
    / "v2"
    / "clean_training_manifest_v2.csv"
)

OUTPUT_DIR = (
    OCR_ROOT
    / "reports"
    / "annotation"
    / "crop_quality_review"
    / "v4_manifest_sample_2026-11-20"
)

SAMPLE_PER_DOCUMENT = 5
PADDINGS = [0, 1]

CARD_WIDTH = 600
CARD_HEIGHT = 220
COLUMNS = 3
CROP_DISPLAY_WIDTH = 560
CROP_DISPLAY_HEIGHT = 135


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def read_manifest():
    with MANIFEST.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        return list(csv.DictReader(f))


def select_sample(rows):
    """
    Select two lowest-confidence lines and three
    additional lines spread across the document.
    """

    selected = []

    # Two lowest-confidence lines.
    by_confidence = sorted(
        rows,
        key=lambda r: float(r["ocr_line_confidence"])
    )

    selected.extend(by_confidence[:2])

    selected_keys = {
        (r["document_id"], r["ocr_line_id"])
        for r in selected
    }

    # Remaining rows in manifest order.
    remaining = [
        r for r in rows
        if (r["document_id"], r["ocr_line_id"])
        not in selected_keys
    ]

    if not remaining:
        return selected

    # Pick three positions spread across the document.
    positions = [
        0,
        len(remaining) // 2,
        len(remaining) - 1
    ]

    for position in positions:
        candidate = remaining[position]

        key = (
            candidate["document_id"],
            candidate["ocr_line_id"]
        )

        if key not in selected_keys:
            selected.append(candidate)
            selected_keys.add(key)

    return selected


def safe_text(value):
    """
    Avoid font encoding errors in contact sheet labels.
    Original transcription remains unchanged in the CSV.
    """
    return str(value).encode(
        "ascii",
        errors="replace"
    ).decode("ascii")


def get_crop(image, row, padding):
    x1 = math.floor(float(row["x1"])) - padding
    y1 = math.floor(float(row["y1"])) - padding
    x2 = math.ceil(float(row["x2"])) + padding
    y2 = math.ceil(float(row["y2"])) + padding

    width, height = image.size

    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(width, x2)
    y2 = min(height, y2)

    if x2 <= x1 or y2 <= y1:
        raise ValueError(
            f"Invalid crop for {row['ocr_line_id']}"
        )

    return image.crop((x1, y1, x2, y2))


def make_contact_sheet(items, padding, output_path):

    rows_per_sheet = math.ceil(len(items) / COLUMNS)

    sheet = Image.new(
        "RGB",
        (
            COLUMNS * CARD_WIDTH,
            rows_per_sheet * CARD_HEIGHT
        ),
        "white"
    )

    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()

    for index, item in enumerate(items):

        row = item["row"]
        crop = item["crop"]

        column = index % COLUMNS
        row_number = index // COLUMNS

        left = column * CARD_WIDTH
        top = row_number * CARD_HEIGHT

        # Card border.
        draw.rectangle(
            [
                left + 5,
                top + 5,
                left + CARD_WIDTH - 5,
                top + CARD_HEIGHT - 5
            ],
            outline="gray",
            width=2
        )

        title = (
            f"{row['document_id']} | "
            f"{row['ocr_line_id']}"
        )

        confidence = (
            f"Confidence: {row['ocr_line_confidence']}"
        )

        transcription = safe_text(
            row["ground_truth_text"]
        )

        wrapped_text = textwrap.wrap(
            transcription,
            width=75
        )

        draw.text(
            (left + 15, top + 12),
            title,
            fill="black",
            font=font
        )

        draw.text(
            (left + 15, top + 30),
            confidence,
            fill="black",
            font=font
        )

        draw.text(
            (left + 15, top + 48),
            "GT: " + (wrapped_text[0] if wrapped_text else ""),
            fill="black",
            font=font
        )

        if len(wrapped_text) > 1:
            draw.text(
                (left + 15, top + 64),
                wrapped_text[1],
                fill="black",
                font=font
            )

        # Resize crop without changing aspect ratio.
        preview = crop.copy()
        preview.thumbnail(
            (CROP_DISPLAY_WIDTH, CROP_DISPLAY_HEIGHT),
            Image.Resampling.LANCZOS
        )

        preview_x = left + 15
        preview_y = top + 82

        sheet.paste(preview, (preview_x, preview_y))

    sheet.save(output_path)


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print("=" * 65)
    print("MANIFEST CROP PADDING EXPERIMENT")
    print("=" * 65)

    if not MANIFEST.exists():
        raise FileNotFoundError(MANIFEST)

    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"Output folder already exists:\n{OUTPUT_DIR}\n"
            "Nothing was overwritten. Inspect it before proceeding."
        )

    rows = read_manifest()

    if not rows:
        raise ValueError("Manifest is empty.")

    grouped = defaultdict(list)

    for row in rows:
        grouped[row["document_id"]].append(row)

    if len(grouped) != 5:
        raise ValueError(
            f"Expected 5 documents, found {len(grouped)}"
        )

    sample = []

    for document_id in sorted(grouped):

        document_rows = grouped[document_id]

        if len(document_rows) < SAMPLE_PER_DOCUMENT:
            raise ValueError(
                f"Not enough rows in {document_id}"
            )

        selected = select_sample(document_rows)

        if len(selected) != SAMPLE_PER_DOCUMENT:
            raise ValueError(
                f"Could not select 5 unique lines from {document_id}"
            )

        sample.extend(selected)

        print(
            f"{document_id}: "
            f"{len(selected)} sample lines selected"
        )

    OUTPUT_DIR.mkdir(parents=True)

    sample_csv = OUTPUT_DIR / "selected_sample_lines.csv"

    with sample_csv.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(sample[0].keys())
        )

        writer.writeheader()
        writer.writerows(sample)

    # Store crops for each padding value.
    for padding in PADDINGS:

        padding_dir = OUTPUT_DIR / f"padding_{padding}px"
        padding_dir.mkdir()

        print(f"\nGenerating crops with {padding}px padding...")

        items = []

        for index, row in enumerate(sample, start=1):

            image_path = Path(row["image_path"])

            with Image.open(image_path) as source:
                image = source.convert("RGB")
                crop = get_crop(image, row, padding)

            filename = (
                f"{index:02d}_"
                f"{row['document_id']}_"
                f"{row['ocr_line_id']}.png"
            )

            crop_path = padding_dir / filename
            crop.save(crop_path)

            items.append({
                "row": row,
                "crop": crop
            })

        contact_sheet = OUTPUT_DIR / (
            f"contact_sheet_padding_{padding}px.png"
        )

        make_contact_sheet(
            items,
            padding,
            contact_sheet
        )

        print(f"Saved {len(items)} crops.")
        print(f"Contact sheet: {contact_sheet}")

    print("\n" + "=" * 65)
    print("CROP EXPERIMENT COMPLETED")
    print("=" * 65)

    print(f"Documents: {len(grouped)}")
    print(f"Sample lines: {len(sample)}")
    print(f"Padding settings: {PADDINGS}")
    print(f"Total comparison crops: {len(sample) * len(PADDINGS)}")
    print(f"\nOutput folder:\n{OUTPUT_DIR}")


if __name__ == "__main__":
    main()