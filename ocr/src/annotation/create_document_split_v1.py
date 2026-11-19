
from pathlib import Path
import csv

# --------------------------------------------------
# PATHS
# --------------------------------------------------

OCR_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    OCR_ROOT
    / "data"
    / "processed"
    / "ocr_line_crops"
    / "final_v3"
    / "final_crop_manifest_v3.csv"
)

OUTPUT_DIR = (
    OCR_ROOT
    / "data"
    / "processed"
    / "ocr_line_crops"
    / "document_split_v1"
)

# --------------------------------------------------
# FIXED DOCUMENT-LEVEL SPLIT
# --------------------------------------------------

SPLIT_ASSIGNMENT = {
    "2061828225": "train",
    "503116473+-6473": "train",
    "507484246": "train",
    "96052028": "validation",
    "ti31149327_9330": "test",
}

EXPECTED_COUNTS = {
    "2061828225": 197,
    "503116473+-6473": 98,
    "507484246": 189,
    "96052028": 114,
    "ti31149327_9330": 151,
}

EXPECTED_TOTAL = 749

# --------------------------------------------------
# CHECK INPUT AND OUTPUT
# --------------------------------------------------

print("=" * 60)
print("CREATE OCR DOCUMENT SPLIT V1")
print("=" * 60)

if not INPUT_FILE.exists():
    raise FileNotFoundError(f"Input manifest not found: {INPUT_FILE}")

if OUTPUT_DIR.exists():
    raise FileExistsError(
        f"Output folder already exists: {OUTPUT_DIR}\n"
        "Nothing was overwritten. Use a new version folder "
        "if you need to run this again."
    )

# --------------------------------------------------
# READ MANIFEST
# --------------------------------------------------

with open(INPUT_FILE, "r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

required_columns = {
    "document_id",
    "ocr_line_id",
    "crop_path",
    "ground_truth_text",
}

if not fieldnames or not required_columns.issubset(fieldnames):
    raise ValueError(
        f"Manifest is missing required columns: "
        f"{required_columns - set(fieldnames or [])}"
    )

if len(rows) != EXPECTED_TOTAL:
    raise ValueError(
        f"Expected {EXPECTED_TOTAL} rows, found {len(rows)}"
    )

# --------------------------------------------------
# VALIDATE DOCUMENTS AND ROWS
# --------------------------------------------------

actual_counts = {}
seen_ids = set()
split_rows = {
    "train": [],
    "validation": [],
    "test": [],
}

missing_crops = []
empty_transcriptions = []

for row in rows:
    document_id = row["document_id"].strip()
    line_id = row["ocr_line_id"].strip()
    crop_path = Path(row["crop_path"])

    if document_id not in SPLIT_ASSIGNMENT:
        raise ValueError(f"Unexpected document ID: {document_id}")

    key = (document_id, line_id)

    if key in seen_ids:
        raise ValueError(f"Duplicate OCR line ID: {key}")

    seen_ids.add(key)

    actual_counts[document_id] = (
        actual_counts.get(document_id, 0) + 1
    )

    if not crop_path.is_file():
        missing_crops.append(str(crop_path))

    if not row["ground_truth_text"].strip():
        empty_transcriptions.append(key)

    split_name = SPLIT_ASSIGNMENT[document_id]
    split_rows[split_name].append(row)

if set(actual_counts) != set(EXPECTED_COUNTS):
    raise ValueError(
        f"Unexpected document set: {set(actual_counts)}"
    )

for document_id, expected in EXPECTED_COUNTS.items():
    actual = actual_counts.get(document_id, 0)

    if actual != expected:
        raise ValueError(
            f"{document_id}: expected {expected} rows, found {actual}"
        )

if missing_crops:
    raise ValueError(
        f"{len(missing_crops)} crop files are missing. "
        f"First missing path: {missing_crops[0]}"
    )

if empty_transcriptions:
    raise ValueError(
        f"{len(empty_transcriptions)} rows have empty transcriptions. "
        f"First example: {empty_transcriptions[0]}"
    )

# --------------------------------------------------
# VERIFY NO DOCUMENT LEAKAGE
# --------------------------------------------------

document_sets = {
    split: {row["document_id"] for row in split_rows[split]}
    for split in split_rows
}

if document_sets["train"] & document_sets["validation"]:
    raise ValueError("Document leakage between train and validation")

if document_sets["train"] & document_sets["test"]:
    raise ValueError("Document leakage between train and test")

if document_sets["validation"] & document_sets["test"]:
    raise ValueError("Document leakage between validation and test")

# --------------------------------------------------
# WRITE OUTPUTS
# --------------------------------------------------

OUTPUT_DIR.mkdir(parents=True, exist_ok=False)

output_files = {
    "train": OUTPUT_DIR / "train_manifest_v1.csv",
    "validation": OUTPUT_DIR / "validation_manifest_v1.csv",
    "test": OUTPUT_DIR / "test_manifest_v1.csv",
}

for split_name, output_file in output_files.items():
    with open(output_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(split_rows[split_name])

# --------------------------------------------------
# CREATE REPORT
# --------------------------------------------------

report_file = OUTPUT_DIR / "document_split_report_v1.txt"

report_lines = [
    "OCR DOCUMENT SPLIT V1 REPORT",
    "=" * 50,
    f"Source manifest: {INPUT_FILE}",
    f"Total rows: {len(rows)}",
    "",
    "DOCUMENT ASSIGNMENT",
    "-" * 50,
]

for document_id, split_name in SPLIT_ASSIGNMENT.items():
    report_lines.append(
        f"{document_id}: {actual_counts[document_id]} rows -> {split_name}"
    )

report_lines.extend([
    "",
    "SPLIT SUMMARY",
    "-" * 50,
])

for split_name, split_data in split_rows.items():
    count = len(split_data)
    percentage = count / len(rows) * 100

    report_lines.append(
        f"{split_name}: {count} crops ({percentage:.2f}%)"
    )

report_lines.extend([
    "",
    "VALIDATION RESULTS",
    "-" * 50,
    "Total rows verified: PASS",
    "Document counts verified: PASS",
    "Duplicate line IDs: 0",
    "Missing crop files: 0",
    "Empty transcriptions: 0",
    "Document overlap between splits: 0",
    "",
    "NOTE",
    "This is a preliminary document-level split using five documents.",
    "The validation and test results have limited document diversity.",
])

report_file.write_text(
    "\n".join(report_lines),
    encoding="utf-8"
)

# --------------------------------------------------
# FINAL OUTPUT
# --------------------------------------------------

print("\nSPLIT CREATED SUCCESSFULLY")
print("-" * 60)

for split_name, split_data in split_rows.items():
    print(f"{split_name.upper():12}: {len(split_data)} crops")

print(f"\nTotal rows: {sum(len(v) for v in split_rows.values())}")
print(f"Output folder: {OUTPUT_DIR}")
print(f"Report: {report_file}")
print("\nAll validation checks passed.")
