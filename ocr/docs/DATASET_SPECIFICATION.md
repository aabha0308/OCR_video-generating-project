# OCR Dataset Specification

**Project:** OCR & Video Generation Model Fine-tuning  
**Component:** Optical Character Recognition  
**Dataset version:** 1.0 – Specification  
**Status:** Draft  
**Last updated:** 14 November 2026

---

## 1. Purpose

This document defines the structure, scope, format and quality requirements of the OCR dataset used in the internship project.

The initial objective is to build a reliable text-recognition dataset from invoice and invoice-like document images.

The dataset will contain image regions paired with manually verified text transcriptions.

## 2. Task Definition

### Primary task: Text recognition

Given an image crop containing a text line, the OCR model must predict the corresponding text.

**Input:** Image crop containing one text line.

**Target:** Human-verified transcription of that text line.

Example:

| Input | Target |
|---|---|
| Image crop containing `Invoice No. 1816` | `Invoice No. 1816` |

The initial model will focus on English-language printed text.

### Separate future task: Invoice information extraction

A future extension may extract structured information such as:

- Invoice number
- Invoice date
- Supplier
- Receiver
- Total amount
- Line items

This task will use document-level inputs and structured output labels. It must not be mixed with the initial text-recognition dataset.

## 3. Dataset Sources

The initial source dataset contains:

- 520 TIFF document images
- 520 Ground Truth PAGE XML files
- 520 OCR PAGE XML files

Source directory:

`data/raw/invoices/archive/ImageAndXML_Data`

The Ground Truth XML files contain region coordinates and entity labels but do not contain verified text transcriptions.

The OCR XML files contain machine-generated text predictions and coordinates.

OCR predictions must not be treated as ground truth without visual verification.

## 4. Dataset Unit

The primary training example is one text-line image crop paired with its verified transcription.

Each example must have:

- Unique document ID
- Unique OCR line ID
- Original document image reference
- Bounding-box coordinates
- Image crop reference
- Predicted OCR text
- Verified ground-truth text
- Annotation status
- Review notes where applicable

A document-level split must be used to prevent lines from the same document appearing in different dataset partitions.

## 5. Annotation Schema

The annotation and training data should retain the following fields:

| Field | Description |
|---|---|
| document_id | Unique source document identifier |
| ocr_line_id | Unique OCR line identifier |
| image_path | Path to original document image |
| x1, y1, x2, y2 | OCR line bounding-box coordinates |
| crop_path | Path to extracted line image |
| predicted_text | Original OCR prediction |
| ground_truth_text | Human-verified transcription |
| validation_status | Annotation review status |
| matched_entity | Provisional GT entity classification |
| match_status | Spatial matching result |
| ocr_line_confidence | Average OCR word confidence |
| reviewer_notes | Annotation notes |

The existing annotation CSVs do not yet contain all image and crop references. These must be added through a reproducible preprocessing step before model training.

## 6. Annotation Statuses

| Status | Meaning | Training use |
|---|---|---|
| correct | OCR prediction matches the verified transcription | Include |
| minor_error | Small OCR transcription error | Include |
| major_error | Significant OCR transcription error | Include |
| non_text | Region contains no usable text | Exclude |
| unreadable | Text cannot be reliably transcribed | Exclude |
| pending | Not yet reviewed | Exclude |

A transcription marked correct, minor_error or major_error must have a non-empty ground_truth_text.

## 7. Text Transcription Policy

The transcription must reflect the visible source text.

Guidelines:

1. Preserve the original wording.
2. Preserve capitalization.
3. Preserve punctuation.
4. Preserve numbers and decimal separators.
5. Preserve currency symbols where visible.
6. Preserve meaningful abbreviations.
7. Do not silently correct spelling or grammar.
8. Do not infer missing or illegible characters.
9. Preserve line boundaries.
10. Do not merge separate OCR lines into one training target.

Whitespace should be normalized consistently, without changing the visible wording.

## 8. Data Quality Requirements

Before a record can enter the training dataset:

- The source document must exist.
- The OCR line must have a valid bounding box.
- The corresponding image crop must be generated successfully.
- The transcription must have been visually reviewed.
- The annotation status must be correct, minor_error or major_error.
- The ground-truth transcription must not be empty.
- Duplicate document-line identifiers must be rejected.
- The crop must contain the intended text line.

## 9. Dataset Splitting

The dataset will eventually be divided into:

- Training set
- Validation set
- Test set

Splitting must happen at document level, not line level.

This prevents data leakage where different lines from the same invoice appear in multiple partitions.

The test set must remain separate from training and model-selection decisions.

No train/validation/test split will be created until sufficient reviewed documents are available.

## 10. Evaluation

The primary OCR metric will be Character Error Rate (CER).

\[
CER = \frac{S+D+I}{N}
\]

Where:

- S = substitutions
- D = deletions
- I = insertions
- N = number of characters in the reference text

Word Error Rate (WER) may also be reported.

Evaluation must use verified ground truth and a document-level held-out test set.

## 11. Current Dataset Status

The initial pilot annotation contains:

| Metric | Count |
|---|---:|
| Documents reviewed | 2 |
| Total OCR lines reviewed | 59 |
| Text transcriptions | 58 |
| Non-text records | 1 |
| Pending records | 0 |

This pilot dataset is for workflow development and quality assessment. It is not sufficient for final model training or performance claims.

## 12. Known Limitations

- Only two documents have been manually reviewed.
- Independent second-review verification has not yet been completed.
- Entity labels originate from spatial matching and are not all independently verified.
- Image crops have not yet been generated as a versioned training dataset.
- The source dataset's full document-type distribution has not been established.
- The pilot sample may not represent the full dataset.

## 13. Next Steps

1. Finalize annotation guidelines.
2. Expand manual review across representative documents.
3. Implement reproducible image crop extraction.
4. Verify crop-to-transcription alignment.
5. Conduct independent annotation quality checks.
6. Create document-level train, validation and test splits.
7. Establish a baseline OCR model.
8. Fine-tune and evaluate the selected model.