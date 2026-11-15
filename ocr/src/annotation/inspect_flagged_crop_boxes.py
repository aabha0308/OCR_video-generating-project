
import csv
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[3]

AUDIT_FILE = (
    PROJECT_ROOT / "ocr/reports/day16_gt_ocr_line_mapping_audit.csv"
)

RAW_IMAGE_DIR = (
    PROJECT_ROOT
    / "ocr/data/raw/invoices/archive/ImageAndXML_Data"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "ocr/reports/annotation/box_diagnostics/v1"
)

DOCUMENT_ID = "0011500947"

FLAGGED_LINES = {
    "Page1_Block9_l5",
    "Page1_Block9_l6",
    "Page1_Block9_l7",
    "Page1_Block9_l8",
    "Page1_Block9_l9",
    "Page1_Block1_l2",
    "Page1_Block1_l3",
}

CONTEXT_PADDING = 35
SCALE = 2


def read_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def find_image(document_id):
    for extension in (".tif", ".tiff", ".TIF", ".TIFF"):
        path = RAW_IMAGE_DIR / f"{document_id}{extension}"
        if path.exists():
            return path
    raise FileNotFoundError(
        f"Original TIFF not found for {document_id}"
    )


def get_box(row):
    return (
        float(row["ocr_x1"]),
        float(row["ocr_y1"]),
        float(row["ocr_x2"]),
        float(row["ocr_y2"]),
    )


def intersects(box_a, box_b):
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    return not (
        ax2 <= bx1
        or bx2 <= ax1
        or ay2 <= by1
        or by2 <= ay1
    )


def load_font(size):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def main():
    if not AUDIT_FILE.exists():
        raise FileNotFoundError(AUDIT_FILE)

    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"Diagnostic output already exists: {OUTPUT_DIR}\n"
            "Inspect it or choose a new version."
        )

    rows = read_csv(AUDIT_FILE)

    required = {
        "document_id",
        "ocr_line_id",
        "ocr_text",
        "ocr_x1",
        "ocr_y1",
        "ocr_x2",
        "ocr_y2",
    }

    missing = required - set(rows[0].keys())

    if missing:
        raise ValueError(f"Missing audit columns: {missing}")

    document_rows = [
        row for row in rows
        if row["document_id"] == DOCUMENT_ID
    ]

    if not document_rows:
        raise ValueError(
            f"No audit rows found for {DOCUMENT_ID}"
        )

    flagged_rows = [
        row for row in document_rows
        if row["ocr_line_id"] in FLAGGED_LINES
    ]

    found_ids = {row["ocr_line_id"] for row in flagged_rows}
    missing_ids = FLAGGED_LINES - found_ids

    if missing_ids:
        raise ValueError(
            f"Flagged lines not found in audit: {sorted(missing_ids)}"
        )

    image_path = find_image(DOCUMENT_ID)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)

    with Image.open(image_path) as source:
        original = source.convert("RGB")

    width, height = original.size

    print(f"Original image dimensions: {width} x {height}")
    print(f"Audit rows for document: {len(document_rows)}")
    print(f"Flagged lines: {len(flagged_rows)}")

    # ---------------------------------------------------------
    # 1. Full-page image with all OCR boxes.
    # Flagged boxes are red; other boxes are blue.
    # ---------------------------------------------------------

    page = original.copy()
    draw = ImageDraw.Draw(page)

    small_font = load_font(11)

    for row in document_rows:
        try:
            x1, y1, x2, y2 = get_box(row)
        except (ValueError, TypeError):
            continue

        is_flagged = row["ocr_line_id"] in FLAGGED_LINES

        color = "red" if is_flagged else "deepskyblue"
        line_width = 3 if is_flagged else 1

        draw.rectangle(
            (x1, y1, x2, y2),
            outline=color,
            width=line_width,
        )

        if is_flagged:
            draw.text(
                (x1, max(0, y1 - 15)),
                row["ocr_line_id"],
                fill="red",
                font=small_font,
            )

    page.save(OUTPUT_DIR / "full_page_all_boxes.png")

    # ---------------------------------------------------------
    # 2. Individual context images around each flagged line.
    # ---------------------------------------------------------

    report_rows = []

    for target in flagged_rows:
        target_id = target["ocr_line_id"]
        x1, y1, x2, y2 = get_box(target)

        left = max(0, int(x1) - CONTEXT_PADDING)
        top = max(0, int(y1) - CONTEXT_PADDING)
        right = min(width, int(x2 + CONTEXT_PADDING))
        bottom = min(height, int(y2 + CONTEXT_PADDING))

        context_box = (left, top, right, bottom)

        context = original.crop(context_box)
        context = context.resize(
            (context.width * SCALE, context.height * SCALE),
            Image.Resampling.LANCZOS,
        )

        context_draw = ImageDraw.Draw(context)
        font = load_font(12)

        neighbor_rows = []

        for other in document_rows:
            try:
                other_box = get_box(other)
            except (ValueError, TypeError):
                continue

            if intersects(other_box, context_box):
                neighbor_rows.append(other)

                ox1, oy1, ox2, oy2 = other_box

                local_box = (
                    (ox1 - left) * SCALE,
                    (oy1 - top) * SCALE,
                    (ox2 - left) * SCALE,
                    (oy2 - top) * SCALE,
                )

                color = (
                    "red"
                    if other["ocr_line_id"] == target_id
                    else "lime"
                )

                context_draw.rectangle(
                    local_box,
                    outline=color,
                    width=2,
                )

        output_name = (
            target_id.replace("/", "_").replace("\\", "_")
            + "_context.png"
        )

        context.save(OUTPUT_DIR / output_name)
        context.close()

        for neighbor in neighbor_rows:
            report_rows.append({
                "flagged_line_id": target_id,
                "neighbor_line_id": neighbor["ocr_line_id"],
                "neighbor_text": neighbor["ocr_text"],
                "is_target": (
                    neighbor["ocr_line_id"] == target_id
                ),
                "neighbor_x1": neighbor["ocr_x1"],
                "neighbor_y1": neighbor["ocr_y1"],
                "neighbor_x2": neighbor["ocr_x2"],
                "neighbor_y2": neighbor["ocr_y2"],
            })

        print(
            f"Created context image for {target_id}; "
            f"intersecting boxes: {len(neighbor_rows)}"
        )

    # ---------------------------------------------------------
    # 3. Save neighboring-line report.
    # ---------------------------------------------------------

    report_file = OUTPUT_DIR / "neighboring_boxes.csv"

    columns = [
        "flagged_line_id",
        "neighbor_line_id",
        "neighbor_text",
        "is_target",
        "neighbor_x1",
        "neighbor_y1",
        "neighbor_x2",
        "neighbor_y2",
    ]

    with open(
        report_file,
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(report_rows)

    original.close()
    page.close()

    print("\n" + "=" * 55)
    print("BOUNDING-BOX DIAGNOSTICS COMPLETED")
    print("=" * 55)
    print(f"Document: {DOCUMENT_ID}")
    print(f"Flagged lines inspected: {len(flagged_rows)}")
    print(f"Output directory: {OUTPUT_DIR}")
    print("Files:")
    print("  full_page_all_boxes.png")
    print("  *_context.png")
    print("  neighboring_boxes.csv")


if __name__ == "__main__":
    main()
