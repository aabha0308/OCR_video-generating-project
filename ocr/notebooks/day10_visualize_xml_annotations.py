
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

project_path = Path(__file__).resolve().parents[1]

data_folder = (
    project_path
    / "data"
    / "raw"
    / "invoices"
    / "archive"
    / "ImageAndXML_Data"
)

output_folder = (
    project_path
    / "reports"
    / "annotated_images"
)

output_folder.mkdir(parents=True, exist_ok=True)

samples = ["0001136521", "0001139626"]


def local_name(tag):
    return tag.split("}")[-1]


def get_points(element):

    for child in element:

        if local_name(child.tag) == "Coords":

            points = child.get("points", "")

            return [
                tuple(map(float, point.split(",")))
                for point in points.split()
            ]

    return []


def get_bbox(points):

    if not points:
        return None

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    return min(xs), min(ys), max(xs), max(ys)


for sample in samples:

    image_path = data_folder / f"{sample}.tif"
    gt_path = data_folder / f"{sample}_gt.xml"
    ocr_path = data_folder / f"{sample}_ocr.xml"

    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)

    # Ground-truth entity regions
    tree = ET.parse(gt_path)
    root = tree.getroot()

    for element in root.iter():

        if local_name(element.tag) != "TextRegion":
            continue

        entity = None

        for child in element:

            if local_name(child.tag) == "Property":
                if child.get("key") == "entity":
                    entity = child.get("value")

        bbox = get_bbox(get_points(element))

        if entity and bbox:

            draw.rectangle(
                bbox,
                outline="red",
                width=3
            )

            draw.text(
                (bbox[0], max(0, bbox[1] - 15)),
                entity,
                fill="red"
            )

    # OCR text regions
    tree = ET.parse(ocr_path)
    root = tree.getroot()

    for element in root.iter():

        if local_name(element.tag) != "TextRegion":
            continue

        bbox = get_bbox(get_points(element))

        if bbox:

            draw.rectangle(
                bbox,
                outline="blue",
                width=1
            )

    output_path = output_folder / f"{sample}_annotated.png"

    image.save(output_path)

    print("Saved:", output_path)

print("\nANNOTATION VISUALIZATION COMPLETED")
