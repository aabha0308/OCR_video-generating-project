# OCR Annotation Guidelines

**Project:** OCR & Video Generation Model Fine-tuning  
**Component:** OCR  
**Guideline version:** 1.0  
**Status:** Draft  
**Last updated:** 14 November 2026

---

## 1. Purpose

These guidelines define how human reviewers must verify OCR predictions against original document images.

The objective is to produce consistent, reliable ground-truth transcriptions for OCR model training and evaluation.

## 2. Source of Truth

The original document image is the authoritative source for transcription.

Use the following hierarchy:

1. Original TIFF image
2. Enlarged image crop for the OCR line
3. OCR prediction as a reference for locating the text
4. Ground Truth XML entity labels as supplementary metadata

Neither OCR predictions nor spatially matched entity labels are automatically correct.

## 3. Annotation Procedure

For every OCR line:

1. Locate the corresponding document image.
2. Locate the OCR line using its bounding box.
3. Inspect the text at sufficient zoom.
4. Compare the OCR prediction with the visible text.
5. Enter the exact visible transcription.
6. Assign a validation status.
7. Add reviewer notes if necessary.
8. Save the annotation.
9. Run the annotation validation script.

Do not mark a line correct simply because the OCR confidence is high.

## 4. Status Definitions

### correct

Use when the OCR prediction matches the visible text.

### minor_error

Use when the prediction contains a small error, such as:

- One or two incorrect characters
- Minor punctuation differences
- Minor spacing differences
- A small capitalization error

### major_error

Use when the prediction contains substantial recognition errors, such as:

- Multiple incorrect words
- Missing words
- Incorrect names
- Incorrect numbers
- Incorrect text that changes the meaning

### non_text

Use when the OCR region contains no usable text, such as:

- Scanning noise
- Isolated marks
- Non-text artifacts

### unreadable

Use when text is present but cannot be reliably transcribed.

### pending

Use when the line has not yet been reviewed.

## 5. Transcription Rules

### 5.1 Capitalization

Preserve capitalization as printed.

Example:

Printed: `B.A.T. LIMITED`

Transcription: `B.A.T. LIMITED`

Do not convert it to `B.A.T. Limited`.

### 5.2 Punctuation

Preserve visible punctuation.

Examples:

- `Invoice No.`
- `Date (Tax Point)`
- `By debit in respect of:-`

Do not remove punctuation merely to make text look cleaner.

### 5.3 Numbers

Transcribe the visible digits exactly.

Examples:

- `26.5.82`
- `13,600.00`
- `1816`

Do not infer a missing digit from context.

### 5.4 Currency

Preserve the currency symbol.

Examples:

- `£1.80`
- `US$13,600.00`

Do not replace a currency symbol with a visually similar character.

### 5.5 Names and Addresses

Preserve the spelling visible in the source image.

Do not automatically replace a name with a more familiar spelling.

If a character is ambiguous, inspect the image more closely or mark the transcription unreadable.

### 5.6 Whitespace

Normalize repeated spaces to a single space where they do not represent meaningful layout.

Do not merge separate text lines.

### 5.7 Abbreviations

Preserve abbreviations as printed.

Examples:

- `U.S.A.`
- `VAT Reg. No.`
- `Telex`

Do not expand abbreviations.

## 6. Uncertain or Illegible Text

When a character cannot be identified confidently:

1. Inspect the original image at a higher zoom.
2. Check the full word or surrounding line for visual context.
3. Do not guess based solely on semantic context.
4. If the transcription cannot be established reliably, use unreadable.
5. Explain the uncertainty in reviewer_notes.

Do not insert guessed characters into ground truth.

## 7. Bounding Boxes and Line Boundaries

Each annotation must remain associated with its original OCR line ID.

Do not merge adjacent OCR lines, even if they form one sentence.

A crop must include the intended text and avoid unnecessary neighboring lines.

If the bounding box is incorrect, record the issue rather than silently changing source audit coordinates.

## 8. Entity Labels

The current entity categories include:

- supplier
- receiver
- invoice_info
- total
- positions
- other

These labels originate from spatial matching with Ground Truth regions.

They are provisional until independently checked against the original document.

Do not assume a spatial match proves semantic correctness.

## 9. Reviewer Notes

Use reviewer_notes to record:

- Ambiguous characters
- Poor image quality
- Possible OCR line segmentation errors
- Incorrect bounding boxes
- Unusual punctuation
- Any decision requiring a second reviewer

Keep notes concise and specific.

## 10. Quality Control

Every annotation file must pass the structural validator.

The validator checks:

- Required columns
- Valid statuses
- Duplicate line identifiers
- Ground-truth presence
- Confidence values
- Basic annotation consistency

Structural validation does not establish transcription accuracy.

A second reviewer should independently inspect a subset of annotations before the dataset is used for final model evaluation.

## 11. Prohibited Practices

Reviewers must not:

- Treat OCR predictions as ground truth.
- Guess unclear characters.
- Correct spelling based on external knowledge.
- Invent missing words.
- Mark uncertain text as correct.
- Use confidence scores as proof of correctness.
- Change original raw images or source audit CSVs.
- Mix document-level extraction labels with line-level transcription targets.

## 12. Versioning

Each annotation change must be traceable.

- Preserve the original raw data.
- Preserve source audit CSVs.
- Retain per-document annotation files.
- Create backups before modifying annotations.
- Generate new consolidated dataset versions rather than silently overwriting existing versions.
- Record guideline changes in version history.

---

## Version History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 14 November 2026 | Initial annotation guidelines |