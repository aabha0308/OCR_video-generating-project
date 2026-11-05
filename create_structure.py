import os

base_path = "ocr"

folders = [
    "data/raw/documents",
    "data/raw/source_metadata",
    "data/processed/images",
    "data/processed/pdf_pages",
    "data/annotated",
    "data/splits",
    "notebooks",
    "src/preprocessing",
    "src/annotation",
    "src/training",
    "src/evaluation",
    "src/inference",
    "configs",
    "checkpoints",
    "reports"
]

files = [
    "data/annotated/annotations.json",
    "data/annotated/annotation_guidelines.md",
    "data/splits/train.json",
    "data/splits/validation.json",
    "data/splits/test.json",
    "data/data_card.md"
]

for folder in folders:
    os.makedirs(os.path.join(base_path, folder), exist_ok=True)

for file in files:
    path = os.path.join(base_path, file)
    with open(path, "w") as f:
        pass

print("OCR project structure created successfully!")