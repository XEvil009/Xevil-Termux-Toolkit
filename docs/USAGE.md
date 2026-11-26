# Usage

## Image2Pdf

Run `python tools/trinetra-pdf.py` or the optional `Image2Pdf` alias. The utility lists supported images in `~/storage/pictures/Screenshots`, newest first. Select using comma-separated numbers, ranges, or `all`; then enter a PDF filename. Existing files require explicit overwrite confirmation. The tool reports added and skipped images separately.

Supported image extensions: `.jpg`, `.jpeg`, `.png`, `.webp`. Images are EXIF-orientation corrected, converted to RGB, resized to at most 1600 × 1600 pixels, and embedded as JPEG at quality 65. The converter rejects images above 80 megapixels.

## MergePdf

Run `python tools/merge-pdf.py` or `MergePdf`. Browse to a folder in existing Termux shared storage, select at least two PDFs, choose merge order, and select an output folder/name. The first page of each input receives a filename heading. Encrypted PDFs are not supported.

## PDF2MD

Run `python tools/pdf2md.py` or `pdf2md`. Choose the source PDF, output filename, and output folder. Each page is rendered with ImageMagick and OCR is performed by Tesseract using English (`eng`) and page segmentation mode 11. Input files are limited to 100 MiB and 100 pages; each page is limited to 40 million rendered pixels at 220 DPI. ImageMagick has explicit resource limits, each external process has a 180-second timeout, and the complete conversion is limited to 30 minutes. Absolute source-path metadata is omitted by default.

OCR is not a faithful document-layout conversion. Check the resulting Markdown, especially tables, small print, multi-column pages, diagrams, and non-English content.
