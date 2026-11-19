
from pathlib import Path
import csv
import re
from collections import Counter

# --------------------------------------------------
# PATHS
# --------------------------------------------------

OCR_ROOT = Path(__file__).resolve().parents[2]

SPLIT_DIR = (
    OCR_ROOT
    / "data"
    / "processed"
    / "ocr_line_crops"
    / "document_split_v1"
)

OUTPUT_DIR = (
    OCR_ROOT
    / "reports"
    / "annotation"
    / "ground_truth_text_audit_v1"
)

SPLIT_FILES = {
    "train": SPLIT_DIR / "train_manifest_v1.csv",
    "validation": SPLIT_DIR / "validation_manifest_v1.csv",
    "test": SPLIT_DIR / "test_manifest_v1.csv",
}

# Detects text like "I D E N T I A L"
SPACED_LETTERS_PATTERN = re.compile(
    r"^(?:[A-Za-z]\s+){2,}[A-Za-z]$"
)

# --------------------------------------------------
# SAFETY CHECKS
# --------------------------------------------------

if OUTPUT_DIR.exists():
    raise FileExistsError(
        f"Output already exists: {OUTPUT_DIR}\n"
        "Use a new version folder rather than overwriting it."
    )

for split_name, path in SPLIT_FILES.items():
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing {split_name} manifest: {path}"
        )

# --------------------------------------------------
# AUDIT
# --------------------------------------------------

all_rows = []
flagged_rows = []
split_counts = Counter()
flag_counts = Counter()
character_counts = Counter()

for split_name, path in SPLIT_FILES.items():

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    split_counts[split_name] = len(rows)

    for row in rows:
        text = row["ground_truth_text"]
        flags = []

        if not text:
            flags.append("empty_text")

        if text != text.strip():
            flags.append("leading_or_trailing_whitespace")

        if "  " in text:
            flags.append("multiple_consecutive_spaces")

        if "\t" in text or "\n" in text or "\r" in text:
            flags.append("tab_or_newline")

        if SPACED_LETTERS_PATTERN.fullmatch(text.strip()):
            flags.append("possible_spaced_characters")

        if text and len(text.strip()) == 1:
            flags.append("single_character_label")

        if "\ufffd" in text:
            flags.append("replacement_character")

        for character in text:
            if not character.isspace():
                character_counts[character] += 1

        audit_row = {
            "split": split_name,
            "document_id": row["document_id"],
            "ocr_line_id": row["ocr_line_id"],
            "ground_truth_text": text,
            "character_length": len(text),
            "flags": "; ".join(flags),
        }

        all_rows.append(audit_row)

        for flag in flags:
            flag_counts[flag] += 1

        if flags:
            flagged_rows.append(audit_row)

# --------------------------------------------------
# CREATE OUTPUTS
# --------------------------------------------------

OUTPUT_DIR.mkdir(parents=True, exist_ok=False)

flagged_file = OUTPUT_DIR / "flagged_ground_truth_rows_v1.csv"
summary_file = OUTPUT_DIR / "ground_truth_audit_report_v1.txt"
characters_file = OUTPUT_DIR / "character_frequency_v1.csv"

fieldnames = [
    "split",
    "document_id",
    "ocr_line_id",
    "ground_truth_text",
    "character_length",
    "flags",
]

with open(flagged_file, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(flagged_rows)

with open(characters_file, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["character", "frequency"])

    for character, count in character_counts.most_common():
        writer.writerow([character, count])

# --------------------------------------------------
# REPORT
# --------------------------------------------------

report = [
    "GROUND-TRUTH TEXT AUDIT V1",
    "=" * 55,
    f"Total rows audited: {len(all_rows)}",
    f"Flagged rows: {len(flagged_rows)}",
    f"Rows without flags: {len(all_rows) - len(flagged_rows)}",
    "",
    "SPLIT COUNTS",
    "-" * 55,
]

for split_name, count in split_counts.items():
    report.append(f"{split_name}: {count}")

report.extend([
    "",
    "FLAG COUNTS",
    "-" * 55,
])

for flag, count in flag_counts.most_common():
    report.append(f"{flag}: {count}")

report.extend([
    "",
    "IMPORTANT",
    "-" * 55,
    "This audit only identifies patterns for manual inspection.",
    "It does not modify or normalize any ground-truth transcription.",
    "Single-character labels are not automatically errors.",
    "Possible spaced characters must be checked against original TIFFs.",
])

summary_file.write_text("\n".join(report), encoding="utf-8")

# --------------------------------------------------
# DISPLAY RESULTS
# --------------------------------------------------

print("=" * 60)
print("GROUND-TRUTH TEXT AUDIT V1")
print("=" * 60)

print(f"Total rows audited : {len(all_rows)}")
print(f"Flagged rows       : {len(flagged_rows)}")
print(f"Rows without flags : {len(all_rows) - len(flagged_rows)}")

print("\nFLAG COUNTS")

for flag, count in flag_counts.most_common():
    print(f"{flag}: {count}")

print("\nOUTPUT FILES")
print(flagged_file)
print(summary_file)
print(characters_file)

print("\nAudit completed. No original files were modified.")

