
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


# ============================================================
# PATHS
# ============================================================

project_path = Path(__file__).resolve().parents[1]

dataset_path = (
    project_path
    / "data"
    / "raw"
    / "invoices"
    / "archive"
    / "ImageAndXML_Data"
)

reports_path = project_path / "reports"

document_csv = (
    reports_path / "day12_document_type_review.csv"
)

output_image = (
    reports_path / "day13_document_review_contact_sheet.jpg"
)

output_csv = (
    reports_path / "day13_manual_document_review.csv"
)

SAMPLES_PER_CATEGORY = 5
COLUMNS = 4
THUMBNAIL_WIDTH = 300
THUMBNAIL_HEIGHT = 390

CATEGORIES = [
    "invoice",
    "unclassified",
    "estimate",
    "purchase_order"
]


# ============================================================
# HELPERS
# ============================================================

def local_name(tag):
    return tag.split("}")[-1]


def find_image(xml_folder, document_name):
    for path in xml_folder.iterdir():
        if (
            path.is_file()
            and path.stem == document_name
            and path.suffix.lower() in {
                ".png", ".jpg", ".jpeg",
                ".tif", ".tiff", ".bmp"
            }
        ):
            return path

    return None


def extract_ocr_text(document_name, xml_folder):
    xml_path = xml_folder / f"{document_name}_ocr.xml"

    if not xml_path.exists():
        return ""

    try:
        root = ET.parse(xml_path).getroot()
        texts = []

        for element in root.iter():
            if local_name(element.tag) == "Unicode":
                if element.text and element.text.strip():
                    texts.append(element.text.strip())

        return " ".join(texts)

    except Exception:
        return ""


def choose_samples(records):
    selected = []

    for category in CATEGORIES:
        category_records = sorted(
            [
                row for row in records
                if row["suggested_document_type"] == category
            ],
            key=lambda row: row["document"]
        )

        if not category_records:
            continue

        # Spread the sample across the sorted category records.
        count = min(SAMPLES_PER_CATEGORY, len(category_records))

        if count == 1:
            indices = [0]
        else:
            indices = [
                round(i * (len(category_records) - 1) / (count - 1))
                for i in range(count)
            ]

        for index in indices:
            selected.append(category_records[index])

    return selected


# ============================================================
# LOAD DOCUMENT AUDIT
# ============================================================

if not document_csv.exists():
    raise FileNotFoundError(
        f"Could not find document audit CSV: {document_csv}"
    )

with open(
    document_csv,
    "r",
    encoding="utf-8-sig",
    newline=""
) as file:

    records = list(csv.DictReader(file))

samples = choose_samples(records)

if not samples:
    raise RuntimeError("No documents selected for manual review.")


# ============================================================
# PREPARE CONTACT SHEET
# ============================================================

try:
    font = ImageFont.truetype("arial.ttf", 15)
    small_font = ImageFont.truetype("arial.ttf", 12)
except OSError:
    font = ImageFont.load_default()
    small_font = ImageFont.load_default()

CARD_HEIGHT = THUMBNAIL_HEIGHT + 100
ROWS = (len(samples) + COLUMNS - 1) // COLUMNS

sheet = Image.new(
    "RGB",
    (
        COLUMNS * THUMBNAIL_WIDTH,
        ROWS * CARD_HEIGHT
    ),
    "white"
)

draw = ImageDraw.Draw(sheet)

manual_records = []

for index, record in enumerate(samples):

    document_name = record["document"]
    category = record["suggested_document_type"]

    image_path = find_image(
        dataset_path,
        document_name
    )

    x = (index % COLUMNS) * THUMBNAIL_WIDTH
    y = (index // COLUMNS) * CARD_HEIGHT

    draw.text(
        (x + 8, y + 5),
        f"{document_name} | {category}",
        fill="black",
        font=font
    )

    if image_path is not None:

        try:
            image = Image.open(image_path).convert("RGB")
            image.thumbnail(
                (THUMBNAIL_WIDTH - 20, THUMBNAIL_HEIGHT - 15)
            )

            paste_x = x + (THUMBNAIL_WIDTH - image.width) // 2
            paste_y = y + 35

            sheet.paste(image, (paste_x, paste_y))

        except Exception as error:
            draw.text(
                (x + 10, y + 50),
                f"Image error: {error}",
                fill="red",
                font=small_font
            )

    else:
        draw.text(
            (x + 10, y + 50),
            "IMAGE NOT FOUND",
            fill="red",
            font=font
        )

    ocr_text = extract_ocr_text(
        document_name,
        dataset_path
    )

    manual_records.append({
        "document": document_name,
        "suggested_type": category,
        "image_path": str(image_path) if image_path else "",
        "ocr_text_sample": ocr_text[:500],
        "verified_type": "",
        "review_notes": ""
    })


# ============================================================
# SAVE OUTPUTS
# ============================================================

sheet.save(
    output_image,
    quality=90
)

with open(
    output_csv,
    "w",
    encoding="utf-8-sig",
    newline=""
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=list(manual_records[0].keys())
    )

    writer.writeheader()
    writer.writerows(manual_records)


print("DOCUMENT TYPE REVIEW SAMPLE CREATED")
print("=" * 55)
print("Documents selected:", len(samples))
print("Contact sheet:", output_image)
print("Manual review CSV:", output_csv)

print("\nSAMPLE DISTRIBUTION")

for category in CATEGORIES:
    count = sum(
        1 for row in samples
        if row["suggested_document_type"] == category
    )
    print(f"{category}: {count}")

print("\nREVIEW DOCUMENTS AGAINST THEIR ACTUAL IMAGES.")
