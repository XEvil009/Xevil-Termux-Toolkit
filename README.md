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
- PDF2MD uses unique temporary output files and 180-second per-process timeouts for ImageMagick and Tesseract.
- PDF2MD currently records the source's full local path in its Markdown metadata. Review that metadata before sharing the Markdown file.
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

This is an engineering baseline. Functional tests in this repository do not replace device-level validation on Termux/Android. No deployment target is configured.
