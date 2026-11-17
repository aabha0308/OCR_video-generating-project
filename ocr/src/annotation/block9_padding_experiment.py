
from pathlib import Path
import csv
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"D:\OCR_Internship\ocr")

IMAGE_PATH = (
    ROOT / "data/raw/invoices/archive/"
    "ImageAndXML_Data/507484246.tif"
)

XML_PATH = (
    ROOT / "data/raw/invoices/archive/"
    "ImageAndXML_Data/507484246_ocr.xml"
)

OUTPUT_DIR = (
    ROOT / "reports/annotation/crop_quality_review/"
    "block9_padding_experiment"
)

TARGET_LINES = [
    "Page1_Block9_l3",
    "Page1_Block9_l4",
]

PADDINGS = [0, 1, 2]

NS = {
    "p": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15"
}


def get_line_coordinates(root, line_id):
    line = root.find(
        f".//p:TextLine[@id='{line_id}']", NS
    )

    if line is None:
        raise ValueError(f"Line not found: {line_id}")

    coords = line.find("p:Coords", NS)

    if coords is None:
        raise ValueError(f"Coordinates missing: {line_id}")

    points = coords.attrib["points"].split()

    xs = [int(p.split(",")[0]) for p in points]
    ys = [int(p.split(",")[1]) for p in points]

    return min(xs), min(ys), max(xs), max(ys)


def load_font(size=18):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def main():
    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"Output already exists: {OUTPUT_DIR}\n"
            "Do not overwrite an earlier experiment."
        )

    if not IMAGE_PATH.exists():
        raise FileNotFoundError(IMAGE_PATH)

    if not XML_PATH.exists():
        raise FileNotFoundError(XML_PATH)

    tree = ET.parse(XML_PATH)
    root = tree.getroot()

    OUTPUT_DIR.mkdir(parents=True)

    crops_dir = OUTPUT_DIR / "individual_crops"
    crops_dir.mkdir()

    metadata = []
    panels = []

    with Image.open(IMAGE_PATH) as source:
        image = source.convert("RGB")
        image_width, image_height = image.size

        for line_id in TARGET_LINES:
            x1, y1, x2, y2 = get_line_coordinates(
                root, line_id
            )

            for padding in PADDINGS:
                left = max(0, x1 - padding)
                top = max(0, y1 - padding)
                right = min(image_width, x2 + padding)
                bottom = min(image_height, y2 + padding)

                crop = image.crop(
                    (left, top, right, bottom)
                )

                filename = (
                    f"{line_id}_padding_{padding}.png"
                )

                crop_path = crops_dir / filename
                crop.save(crop_path)

                metadata.append({
                    "line_id": line_id,
                    "padding": padding,
                    "x1": left,
                    "y1": top,
                    "x2": right,
                    "y2": bottom,
                    "width": crop.width,
                    "height": crop.height,
                    "crop_file": filename,
                })

                # Enlarge for visual comparison.
                scale = 5
                enlarged = crop.resize(
                    (
                        crop.width * scale,
                        crop.height * scale,
                    ),
                    Image.Resampling.LANCZOS,
                )

                panels.append({
                    "title": (
                        f"{line_id} | "
                        f"Padding: {padding}px"
                    ),
                    "image": enlarged,
                })

    # Save metadata.
    metadata_path = OUTPUT_DIR / "crop_metadata.csv"

    with metadata_path.open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(metadata[0].keys()),
        )
        writer.writeheader()
        writer.writerows(metadata)

    # Create comparison contact sheet.
    panel_width = 1100
    panel_height = 190
    margin = 20
    title_height = 35

    sheet = Image.new(
        "RGB",
        (
            panel_width,
            margin + len(panels) * (
                panel_height + margin
            ),
        ),
        "white",
    )

    draw = ImageDraw.Draw(sheet)
    font = load_font()

    y = margin

    for panel in panels:
        draw.text(
            (margin, y),
            panel["title"],
            fill="black",
            font=font,
        )

        image = panel["image"]
        image.thumbnail(
            (panel_width - 2 * margin,
             panel_height - title_height)
        )

        sheet.paste(
            image,
            (margin, y + title_height),
        )

        y += panel_height + margin

    contact_sheet = OUTPUT_DIR / "comparison_contact_sheet.png"
    sheet.save(contact_sheet)

    print("=" * 55)
    print("BLOCK9 PADDING EXPERIMENT COMPLETED")
    print("=" * 55)
    print("Lines:", len(TARGET_LINES))
    print("Padding values:", PADDINGS)
    print("Crops created:", len(metadata))
    print("Contact sheet:", contact_sheet)
    print("Metadata:", metadata_path)
    print("Individual crops:", crops_dir)


if __name__ == "__main__":
    main()
