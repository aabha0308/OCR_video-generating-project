
import csv
import shutil
from pathlib import Path

# --------------------------------------------------
# PATHS
# --------------------------------------------------

PROJECT_PATH = Path(__file__).resolve().parents[1]

CSV_PATH = (
    PROJECT_PATH
    / "reports"
    / "day13_manual_document_review.csv"
)

BACKUP_PATH = (
    PROJECT_PATH
    / "reports"
    / "day13_manual_document_review_backup.csv"
)

# --------------------------------------------------
# MANUAL CLASSIFICATIONS
# --------------------------------------------------

CLASSIFICATIONS = {
    "0011500947": (
        "invoice",
        "Invoice document"
    ),

    "2041063035": (
        "invoice",
        "Invoice for event tickets"
    ),

    "2073883150": (
        "invoice",
        "Legal services invoice"
    ),

    "83553545": (
        "invoice",
        "Invoice for services and expenses"
    ),

    "ti31689150": (
        "invoice",
        "Invoice for processing and mailing services"
    ),

    "0001139626": (
        "estimate",
        "Advertising production estimate"
    ),

    "2024526163_2024526164": (
        "invoice",
        "Professional services invoice"
    ),

    "2071413111": (
        "other",
        "Grant or payment request; not a conventional invoice"
    ),

    "83554921": (
        "invoice",
        "Legal services invoice"
    ),

    "tob02910.64": (
        "uncertain",
        "Advertising cost recapitulation; requires further verification"
    ),

    "0000223278": (
        "invoice",
        "Debit/invoice document"
    ),

    "2047260303": (
        "invoice",
        "Invoice requesting payment for estimated research fees"
    ),

    "2084022167": (
        "estimate",
        "Newspaper advertising estimate"
    ),

    "50120516-0516": (
        "estimate",
        "Quotation document"
    ),

    "96403982": (
        "invoice",
        "Invoice for creative development services"
    ),

    "0001431487": (
        "purchase_order",
        "Purchase order document"
    ),

    "0060076945": (
        "purchase_order",
        "Purchase order document"
    ),

    "2085534883": (
        "invoice",
        "University invoice"
    ),

    "80233696": (
        "invoice",
        "Laboratory services invoice"
    ),

    "89000106": (
        "invoice",
        "Laboratory services invoice"
    )
}


# --------------------------------------------------
# VALIDATE INPUT FILE
# --------------------------------------------------

if not CSV_PATH.exists():
    raise FileNotFoundError(
        f"Manual review CSV not found:\n{CSV_PATH}"
    )

print("=" * 65)
print("APPLYING MANUAL DOCUMENT CLASSIFICATIONS")
print("=" * 65)

# --------------------------------------------------
# CREATE BACKUP
# --------------------------------------------------

if not BACKUP_PATH.exists():
    shutil.copy2(CSV_PATH, BACKUP_PATH)
    print(f"\nBackup created:\n{BACKUP_PATH}")
else:
    print(f"\nExisting backup preserved:\n{BACKUP_PATH}")

# --------------------------------------------------
# READ CSV
# --------------------------------------------------

with open(
    CSV_PATH,
    "r",
    encoding="utf-8-sig",
    newline=""
) as file:

    reader = csv.DictReader(file)

    if not reader.fieldnames:
        raise ValueError("CSV file has no header.")

    required_columns = {
        "document",
        "verified_type",
        "review_notes"
    }

    missing_columns = required_columns - set(reader.fieldnames)

    if missing_columns:
        raise ValueError(
            f"Missing required CSV columns: {missing_columns}"
        )

    fieldnames = reader.fieldnames
    rows = list(reader)


# --------------------------------------------------
# APPLY CLASSIFICATIONS
# --------------------------------------------------

updated_count = 0
missing_documents = []
updated_documents = []

for row in rows:

    document_id = row["document"].strip()

    if document_id in CLASSIFICATIONS:

        verified_type, review_notes = CLASSIFICATIONS[document_id]

        row["verified_type"] = verified_type
        row["review_notes"] = review_notes

        updated_count += 1
        updated_documents.append(document_id)

    else:
        missing_documents.append(document_id)


# --------------------------------------------------
# CHECK FOR EXPECTED DOCUMENTS
# --------------------------------------------------

expected_documents = set(CLASSIFICATIONS.keys())
found_documents = {
    row["document"].strip()
    for row in rows
}

not_found = expected_documents - found_documents

if not_found:
    print("\nWARNING: Some expected documents were not found:")

    for document in sorted(not_found):
        print(f"  - {document}")


# --------------------------------------------------
# SAVE UPDATED CSV
# --------------------------------------------------

with open(
    CSV_PATH,
    "w",
    encoding="utf-8-sig",
    newline=""
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(rows)


# --------------------------------------------------
# FINAL SUMMARY
# --------------------------------------------------

distribution = {}

for row in rows:

    verified_type = row["verified_type"].strip()

    if verified_type:
        distribution[verified_type] = (
            distribution.get(verified_type, 0) + 1
        )


print("\n" + "=" * 65)
print("CLASSIFICATION UPDATE SUMMARY")
print("=" * 65)

print(f"Total CSV records: {len(rows)}")
print(f"Documents classified: {updated_count}")
print(f"Expected documents: {len(CLASSIFICATIONS)}")

print("\nVERIFIED TYPE DISTRIBUTION")

for category, count in sorted(distribution.items()):
    print(f"{category:20s}: {count}")

print("\nUNCERTAIN DOCUMENTS")

for row in rows:
    if row["verified_type"].strip() == "uncertain":
        print(f"  {row['document']}")

print("\nOUTPUT FILE:")
print(CSV_PATH)

print("\nBACKUP FILE:")
print(BACKUP_PATH)

print("\nCLASSIFICATION UPDATE COMPLETED")
print("=" * 65)
