# OCR Validation Guidelines

## Purpose

This file defines how OCR predictions are manually checked
against the original document images.

## Annotation statuses

- correct: Predicted text matches the visible image.
- minor_error: Small character, punctuation, or spacing error.
- major_error: Significant incorrect or missing text.
- non_text: The OCR system detected a non-text mark as text.
- unreadable: The image does not permit reliable transcription.
- pending: Not yet reviewed.

## Annotation rules

1. Always compare predictions with the original TIFF image.
2. Preserve the original OCR prediction in predicted_text.
3. Enter the corrected transcription in ground_truth_text.
4. Do not guess text that cannot be read reliably.
5. Preserve meaningful punctuation, numbers, and spacing.
6. Use non_text only when the region contains no meaningful text.
7. Use unreadable when text exists but cannot be reliably read.
8. Do not modify the original OCR XML or audit CSV.
9. Record uncertainties in reviewer_notes.

## Important distinction

OCR predictions are not ground truth.

Only manually verified transcriptions should be used
as reference text for OCR accuracy evaluation.

## Confidence

ocr_line_confidence is an arithmetic mean of word-level
confidence values when an original line-level confidence
is unavailable. It is not an original engine line score.
