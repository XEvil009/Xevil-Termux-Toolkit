# X-Evil Termux Toolkit

A collection of local Python utilities for Termux. This repository contains the three scripts listed below; it does not install aliases, modify shell startup files, request Android storage permissions, or upload documents.

## Tools

| Command | Script | Purpose |
|---|---|---|
| `Image2Pdf` | `tools/trinetra-pdf.py` | Select screenshots and create a compressed A4 PDF |
| `MergePdf` | `tools/merge-pdf.py` | Merge selected PDFs with filename section headings |
| `pdf2md` | `tools/pdf2md.py` | Render PDF pages and extract English OCR into Markdown |

## Requirements

- Python 3.10 or later
- Pillow, ReportLab and pypdf (see `requirements.txt`)
- For PDF2MD: ImageMagick (`magick`) and Tesseract (`tesseract`) with English language data
- Termux shared-storage access must already be configured by the device owner for MergePdf and PDF2MD. The scripts do not configure it.

Install Python dependencies:

```sh
python -m pip install -r requirements.txt
```

## Termux installation

Copy the scripts to your home directory using your preferred method. Preserve the existing script names. Suggested aliases, if you choose to add them manually:

```sh
alias Image2Pdf='python "$HOME/trinetra-pdf.py"'
alias MergePdf='python "$HOME/merge-pdf.py"'
alias pdf2md='python "$HOME/pdf2md.py"'
```

The screenshot converter reads from `~/storage/pictures/Screenshots` and writes to `~/storage/shared/Xevil-Network/Project/Trinetra`. MergePdf and PDF2MD browse existing shared storage. No script writes to `.bashrc` or changes the Termux startup UI.

## Safety and behavior

- Image2Pdf creates a temporary PDF beside the destination, validates its page count, and atomically replaces the destination only when at least one image was added.
- MergePdf validates selected inputs and validates the generated output before replacement.
- PDF2MD enforces input-size, page-count, and per-page rendered-pixel limits, ImageMagick resource limits, per-process timeouts, and a best-effort 30-minute elapsed-time budget. The budget cannot forcibly interrupt synchronous PDF parsing or filesystem operations.
- PDF2MD omits the absolute source path by default. The conversion function supports explicit path inclusion for workflows that require it.
- OCR output is approximate and may lose layout, tables, columns, and non-English text. Review extracted content before relying on it.
- These tools process local files. They do not send files to a network service.

## Development checks

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m compileall -q tools tests
```

See `docs/SECURITY.md` and `docs/USAGE.md` for additional details.

## Project status

This is a local Termux utility baseline. Functional tests and reported device checks do not constitute a security certification. PDF-processing hardening is ongoing; no deployment target is configured.
