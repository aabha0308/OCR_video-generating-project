
from pathlib import Path

project_path = Path(__file__).resolve().parents[1]
dataset_path = project_path / "data" / "raw" / "invoices"

images = {
    f.stem
    for f in dataset_path.rglob("*")
    if f.suffix.lower() in [".tif", ".tiff", ".png", ".jpg", ".jpeg"]
}

gt_files = {
    f.name[:-7]
    for f in dataset_path.rglob("*_gt.xml")
}

ocr_files = {
    f.name[:-8]
    for f in dataset_path.rglob("*_ocr.xml")
}

print("Images:", len(images))
print("Ground truth:", len(gt_files))
print("OCR annotations:", len(ocr_files))

print("\nImages without GT:")
print(sorted(images - gt_files)[:20])

print("\nGT without images:")
print(sorted(gt_files - images)[:20])

print("\nImages without OCR annotations:")
print(sorted(images - ocr_files)[:20])

print("\nOCR annotations without images:")
print(sorted(ocr_files - images)[:20])
