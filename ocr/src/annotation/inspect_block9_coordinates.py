
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"D:\OCR_Internship\ocr")

IMAGE_PATH = (
    ROOT / "data/raw/invoices/archive/"
    "ImageAndXML_Data/507484246.tif"
)

OUTPUT_DIR = (
    ROOT / "reports/annotation/box_diagnostics/507484246"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Original OCR coordinates from the XML
boxes = {
    "Block9_l2": (703, 85, 735, 100),
    "Block9_l3": (537, 99, 735, 113),
    "Block9_l4": (537, 108, 659, 120),
    "Block9_l5": (537, 126, 551, 133),
}

with Image.open(IMAGE_PATH) as image:
    image = image.convert("RGB")

    # Region surrounding all four lines
    region = image.crop((510, 75, 765, 145))

    # Enlarge for visual inspection
    scale = 4
    enlarged = region.resize(
        (region.width * scale, region.height * scale),
        Image.Resampling.LANCZOS
    )

    draw = ImageDraw.Draw(enlarged)

    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except OSError:
        font = ImageFont.load_default()

    colors = {
        "Block9_l2": "blue",
        "Block9_l3": "red",
        "Block9_l4": "lime",
        "Block9_l5": "yellow",
    }

    for name, (x1, y1, x2, y2) in boxes.items():

        # Convert original coordinates to enlarged crop coordinates
        coords = (
            (x1 - 510) * scale,
            (y1 - 75) * scale,
            (x2 - 510) * scale,
            (y2 - 75) * scale,
        )

        color = colors[name]

        draw.rectangle(coords, outline=color, width=3)

        draw.text(
            (coords[0], max(0, coords[1] - 18)),
            name,
            fill=color,
            font=font,
            stroke_width=1,
            stroke_fill="black"
        )

    output = OUTPUT_DIR / "block9_enlarged_diagnostic.png"

    enlarged.save(output)

    print("Diagnostic created successfully!")
    print("Original dimensions:", image.size)
    print("Diagnostic dimensions:", enlarged.size)
    print("Saved to:", output)
