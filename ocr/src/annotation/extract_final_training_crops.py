import csv
import re
import sys
import math
from pathlib import Path
from collections import Counter
from PIL import Image


# --------------------------------------------------
# PATHS
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
    / "data"
    / "processed"
    / "ocr_line_crops"
    / "final_v2"
)

IMAGE_DIR = OUTPUT_DIR / "images"
CROP_MANIFEST = OUTPUT_DIR / "final_crop_manifest_v2.csv"
REPORT = OUTPUT_DIR / "crop_extraction_report.txt"

PADDING = 0


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def safe_filename(value):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", value)


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print("=" * 65)
    print("FINAL OCR TRAINING CROP EXTRACTION")
    print("=" * 65)

    if not MANIFEST.exists():
        raise FileNotFoundError(MANIFEST)

    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"Output folder already exists:\n{OUTPUT_DIR}\n"
            "Nothing was overwritten."
        )

    rows = read_csv(MANIFEST)

    if len(rows) != 751:
        raise ValueError(
            f"Expected 751 manifest rows, found {len(rows)}"
        )

    OUTPUT_DIR.mkdir(parents=True)
    IMAGE_DIR.mkdir()

    output_rows = []
    document_counts = Counter()
    small_crops = []
    failures = []

    for index, row in enumerate(rows, start=1):

        document_id = row["document_id"]
        line_id = row["ocr_line_id"]
        image_path = Path(row["image_path"])

        try:
            x1 = math.floor(float(row["x1"]))
            y1 = math.floor(float(row["y1"]))
            x2 = math.ceil(float(row["x2"]))
            y2 = math.ceil(float(row["y2"]))

            if not image_path.exists():
                raise FileNotFoundError(image_path)

            with Image.open(image_path) as source:

                image = source.convert("RGB")

                width, height = image.size

                if x1 < 0 or y1 < 0 or x2 > width or y2 > height:
                    raise ValueError("Bounding box outside image")

                if x2 <= x1 or y2 <= y1:
                    raise ValueError("Invalid bounding box dimensions")

                crop = image.crop((x1, y1, x2, y2))

                crop_width, crop_height = crop.size

                filename = (
                    f"{index:04d}_"
                    f"{safe_filename(document_id)}_"
                    f"{safe_filename(line_id)}.png"
                )

                crop_path = IMAGE_DIR / filename

                crop.save(crop_path, format="PNG")

            review_flag = (
                "review_small_crop"
                if crop_height < 12 or crop_width < 8
                else ""
            )

            if review_flag:
                small_crops.append(
                    f"{document_id} | {line_id} | "
                    f"{crop_width}x{crop_height}"
                )

            output_rows.append({
                "document_id": document_id,
                "ocr_line_id": line_id,
                "crop_path": str(crop_path.resolve()),
                "ground_truth_text": row["ground_truth_text"],
                "predicted_text": row["predicted_text"],
                "matched_entity": row["matched_entity"],
                "ocr_line_confidence": row["ocr_line_confidence"],
                "crop_width": crop_width,
                "crop_height": crop_height,
                "padding_pixels": PADDING,
                "review_flag": review_flag,
            })

            document_counts[document_id] += 1

        except Exception as error:
            failures.append(
                f"{document_id} | {line_id} | {error}"
            )

        if index % 100 == 0:
            print(f"Processed {index}/{len(rows)} lines")

    # Stop if any crop failed.
    if failures:

        print("\nCROP EXTRACTION FAILED")
        print(f"Failed crops: {len(failures)}")

        for failure in failures:
            print(failure)

        raise RuntimeError(
            "Some crops failed. Inspect errors before proceeding."
        )

    if len(output_rows) != len(rows):
        raise RuntimeError("Output crop count does not match input.")

    # Save crop manifest.
    with CROP_MANIFEST.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(output_rows[0].keys())
        )

        writer.writeheader()
        writer.writerows(output_rows)

    # Verify saved manifest.
    saved_rows = read_csv(CROP_MANIFEST)

    if len(saved_rows) != len(rows):
        raise RuntimeError("Saved crop manifest verification failed.")

    # Save report.
    report_lines = [
        "FINAL OCR CROP EXTRACTION REPORT",
        "=" * 65,
        f"Source manifest: {MANIFEST}",
        f"Padding: {PADDING}px",
        f"Total source rows: {len(rows)}",
        f"Successful crops: {len(output_rows)}",
        f"Failed crops: {len(failures)}",
        f"Small crops flagged for review: {len(small_crops)}",
        "",
        "DOCUMENT COUNTS",
        "-" * 65,
    ]

    for document_id, count in sorted(document_counts.items()):
        report_lines.append(f"{document_id}: {count}")

    report_lines.extend([
        "",
        "SMALL CROP REVIEW FLAGS",
        "-" * 65,
    ])

    report_lines.extend(small_crops or ["None"])

    report_lines.extend([
        "",
        "NOTE",
        "-" * 65,
        "Small crops are flagged, not automatically excluded.",
        "Visual quality review is required before training.",
    ])

    REPORT.write_text(
        "\n".join(report_lines),
        encoding="utf-8"
    )

    print("\n" + "=" * 65)
    print("CROP EXTRACTION COMPLETED")
    print("=" * 65)

    print(f"Successful crops: {len(output_rows)}")
    print(f"Failed crops: {len(failures)}")
    print(f"Small crops flagged: {len(small_crops)}")
    print(f"\nImages: {IMAGE_DIR}")
    print(f"Manifest: {CROP_MANIFEST}")
    print(f"Report: {REPORT}")


if __name__ == "__main__":

    try:
        main()

    except Exception as error:
        print("\nERROR:", error)
        sys.exit(1)