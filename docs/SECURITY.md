# Security and privacy notes

## Data handling

The utilities operate on local filesystem paths. They do not implement network uploads, telemetry, account authentication, or credential storage. Do not place passwords, tokens, private keys, or unrelated personal files in this repository.

PDF2MD omits the source PDF's absolute local path by default. The conversion function exposes an explicit `include_source_path=True` option; use it only when the output is not intended for external sharing.

## Input handling

- Image2Pdf accepts only regular, non-symlink files with supported image extensions and rejects images larger than 80 megapixels.
- MergePdf rejects encrypted and zero-page PDFs and validates the generated page count.
- PDF2MD rejects encrypted and zero-page PDFs, limits source files to 100 MiB and 100 pages, and rejects rendered pages above 40 million pixels at 220 DPI. ImageMagick receives memory, map, disk, time, and thread limits. Each external process has a 180-second timeout and the conversion uses a best-effort 30-minute elapsed-time budget. The budget is checked before and after synchronous PDF parsing and during page validation, rendering, OCR, and output publication; it cannot forcibly interrupt a synchronous parser or filesystem operation.
- PDF parsers and image decoders process untrusted input. Keep dependencies updated and avoid opening files from untrusted sources unless necessary.

## Output integrity

Image2Pdf and MergePdf write temporary output in the destination directory, validate it, and use `os.replace()` for final publication. PDF2MD writes to a uniquely named temporary file in the destination directory and atomically replaces the output after OCR completes.

## Scope and limitations

These controls are defensive measures, not a security certification. Resource exhaustion may still be possible within configured limits or through parser/delegate vulnerabilities. ImageMagick policy configuration and device-level testing remain necessary on supported Termux versions. On the tested Termux device, `magick -list policy` returned no policy entries; an active restrictive policy is therefore not verified. The PDF delegate listing showed Ghostscript commands using `-dSAFER`, but this alone does not establish that ImageMagick policy restrictions are active. Report suspected vulnerabilities privately to the repository owner; do not include exploit samples containing real personal data in public issues.
