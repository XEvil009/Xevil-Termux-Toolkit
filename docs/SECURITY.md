# Security and privacy notes

## Data handling

The utilities operate on local filesystem paths. They do not implement network uploads, telemetry, account authentication, or credential storage. Do not place passwords, tokens, private keys, or unrelated personal files in this repository.

PDF2MD embeds the source PDF's absolute local path in the generated Markdown. That can reveal a device-specific directory structure. Inspect the output and remove that metadata before sharing it externally.

## Input handling

- Image2Pdf accepts only regular, non-symlink files with supported image extensions and rejects images larger than 80 megapixels.
- MergePdf rejects encrypted and zero-page PDFs and validates the generated page count.
- PDF2MD rejects encrypted and zero-page PDFs. ImageMagick and Tesseract are launched with argument arrays (not a shell) and 180-second timeouts.
- PDF parsers and image decoders process untrusted input. Keep dependencies updated and avoid opening files from untrusted sources unless necessary.

## Output integrity

Image2Pdf and MergePdf write temporary output in the destination directory, validate it, and use `os.replace()` for final publication. PDF2MD writes to a uniquely named temporary file in the destination directory and atomically replaces the output after OCR completes.

## Scope and limitations

These controls are defensive measures, not a security certification. Resource exhaustion remains possible with unusually complex or large PDFs. Device-level testing is required on supported Termux versions. Report suspected vulnerabilities privately to the repository owner; do not include exploit samples containing real personal data in public issues.
