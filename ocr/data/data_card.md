## Initial Dataset Inspection

- Total images: 520
- Valid images: 520
- Ground truth XML: 520
- OCR XML: 520
- Image format: TIFF
- Annotation format: PAGE XML

### Ground Truth XML
Contains document layout regions, coordinates
and entity labels.

Identified labels:
- supplier
- receiver
- invoice_info
- total
- positions
- other

### OCR XML
Contains OCR-generated text, including:
- TextRegion
- TextLine
- Word
- TextEquiv
- Unicode

### Current Limitations
- Ground truth text transcriptions have not been verified.
- OCR predictions may contain recognition errors.
- Language and document-domain suitability
  require further inspection.

### Next Steps
- Compare OCR predictions against original images.
- Verify annotation quality.
- Determine suitability for model training.