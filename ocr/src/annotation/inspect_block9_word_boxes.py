
from pathlib import Path
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
    ROOT / "reports/annotation/"
    "box_diagnostics/507484246"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_LINES = {
    "Page1_Block9_l3": "red",
    "Page1_Block9_l4": "lime",
}

NS = {"p": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15"}

tree = ET.parse(XML_PATH)
root = tree.getroot()

with Image.open(IMAGE_PATH) as source:
    original = source.convert("RGB")

# Crop a larger region around Block9.
region = original.crop((510, 75, 765, 145))

scale = 5
canvas = region.resize(
    (region.width * scale, region.height * scale),
    Image.Resampling.LANCZOS
)

draw = ImageDraw.Draw(canvas)

try:
    font = ImageFont.truetype("arial.ttf", 10)
except OSError:
    font = ImageFont.load_default()

word_count = 0

for line_id, color in TARGET_LINES.items():

    line = root.find(f".//p:TextLine[@id='{line_id}']", NS)

    if line is None:
        print("WARNING: Line not found:", line_id)
        continue

    print("\nLINE:", line_id)

    for word in line.findall("p:Word", NS):

        word_id = word.attrib.get("id", "")

        coords = word.find("p:Coords", NS)
        text_element = word.find(
            "p:TextEquiv/p:Unicode", NS
        )

        if coords is None:
            continue

        points = coords.attrib["points"].split()

        xs = [int(point.split(",")[0]) for point in points]
        ys = [int(point.split(",")[1]) for point in points]

        x1, y1 = min(xs), min(ys)
        x2, y2 = max(xs), max(ys)

        text = (
            text_element.text
            if text_element is not None and text_element.text
            else ""
        )

        # Convert original image coordinates to diagnostic coordinates.
        box = (
            (x1 - 510) * scale,
            (y1 - 75) * scale,
            (x2 - 510) * scale,
            (y2 - 75) * scale,
        )

        draw.rectangle(box, outline=color, width=2)

        draw.text(
            (box[0], max(0, box[1] - 12)),
            word_id.split("_")[-1],
            fill=color,
            font=font,
            stroke_width=1,
            stroke_fill="black",
        )

        print(
            f"{word_id}: {text!r} "
            f"({x1}, {y1}, {x2}, {y2})"
        )

        word_count += 1

output_path = OUTPUT_DIR / "block9_word_boxes_overlay.png"
canvas.save(output_path)

print("\nWord boxes drawn:", word_count)
print("Saved:", output_path)
