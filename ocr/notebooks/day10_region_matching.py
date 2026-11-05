
import xml.etree.ElementTree as ET
from pathlib import Path

project_path = Path(__file__).resolve().parents[1]
dataset_path = project_path / "data" / "raw" / "invoices"

sample_name = "0000223278"

gt_file = next(dataset_path.rglob(f"{sample_name}_gt.xml"))
ocr_file = next(dataset_path.rglob(f"{sample_name}_ocr.xml"))

print("GT FILE FOUND:", gt_file.exists())
print("OCR FILE FOUND:", ocr_file.exists())

def local_name(tag):
    return tag.split("}")[-1]


def get_coordinates(element):
    for child in element:
        if local_name(child.tag) == "Coords":
            points = child.get("points", "")
            coordinates = []

            for point in points.split():
                x, y = point.split(",")
                coordinates.append((float(x), float(y)))

            return coordinates

    return []

def get_bbox(points):
    if not points:
        return None

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    return min(xs), min(ys), max(xs), max(ys)

def contains(inner, outer):
    ix1, iy1, ix2, iy2 = inner
    ox1, oy1, ox2, oy2 = outer

    return (
        ix1 >= ox1 and
        iy1 >= oy1 and
        ix2 <= ox2 and
        iy2 <= oy2
    )


def calculate_overlap(ocr_bbox, gt_bbox):
    ox1, oy1, ox2, oy2 = ocr_bbox
    gx1, gy1, gx2, gy2 = gt_bbox

    intersection_width = max(0, min(ox2, gx2) - max(ox1, gx1))
    intersection_height = max(0, min(oy2, gy2) - max(oy1, gy1))

    intersection_area = intersection_width * intersection_height

    ocr_area = (ox2 - ox1) * (oy2 - oy1)

    if ocr_area == 0:
        return 0

    return intersection_area / ocr_area * 100

# Read ground-truth regions
gt_tree = ET.parse(gt_file)
gt_root = gt_tree.getroot()

regions = []

for element in gt_root.iter():
    if local_name(element.tag) == "TextRegion":
        entity = None

        for child in element:
            if local_name(child.tag) == "Property":
                if child.get("key") == "entity":
                    entity = child.get("value")

        bbox = get_bbox(get_coordinates(element))

        if entity and bbox:
            regions.append({
                "entity": entity,
                "bbox": bbox
            })

# Read OCR text regions
ocr_tree = ET.parse(ocr_file)
ocr_root = ocr_tree.getroot()

print("OCR TO GROUND-TRUTH REGION MATCHING")
print("=" * 60)
 
for element in ocr_root.iter():
    if local_name(element.tag) != "TextRegion":
        continue

    ocr_bbox = get_bbox(get_coordinates(element))

    if not ocr_bbox:
        continue

    texts = []

    for child in element.iter():
        if local_name(child.tag) == "Unicode":
            if child.text and child.text.strip():
                texts.append(child.text.strip())

    if not texts:
        continue

    # Find the best matching ground-truth region
    best_match = None
    best_overlap = 0

    for region in regions:
        overlap = calculate_overlap(ocr_bbox, region["bbox"])

        if overlap > best_overlap:
            best_overlap = overlap
            best_match = region["entity"]

    # Display results for every OCR region
    print("\nOCR TEXT:", " ".join(texts))
    print("OCR BBOX:", ocr_bbox)

    if best_overlap > 0:
        print("BEST MATCH:", best_match)
        print("OCR REGION OVERLAP:", round(best_overlap, 2), "%")
    else:
        print("BEST MATCH: No overlap")
        print("OCR REGION OVERLAP: 0%")


print("\nTOTAL GT REGIONS:", len(regions))
print("MATCHING CHECK COMPLETED")
