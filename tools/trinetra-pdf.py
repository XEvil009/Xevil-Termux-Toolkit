#!/usr/bin/env python3
"""Interactive Termux screenshot-to-PDF utility."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
import os
import re
import tempfile

from PIL import Image, ImageOps, UnidentifiedImageError
from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen import canvas

SOURCE = Path.home() / "storage/pictures/Screenshots"
OUTPUT = Path.home() / "storage/shared/Xevil-Network/Project/Trinetra"
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_PIXELS = 80_000_000


def list_images(source: Path = SOURCE) -> list[Path]:
    """Return supported regular image files, newest first."""
    if not source.is_dir():
        raise FileNotFoundError(f"Screenshot folder not found: {source}")
    return sorted(
        (p for p in source.iterdir()
         if p.is_file() and not p.is_symlink() and p.suffix.lower() in EXTENSIONS),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def parse_selection(value: str, total: int) -> list[int] | None:
    """Parse 1-based comma/range selection; return zero-based unique indices."""
    value = value.strip().lower()
    if value == "all":
        return list(range(total)) if total else None
    selected: set[int] = set()
    try:
        for part in value.split(","):
            part = part.strip()
            if not part:
                raise ValueError
            if re.fullmatch(r"\d+-\d+", part):
                start, end = map(int, part.split("-", 1))
                if start > end:
                    raise ValueError
                selected.update(range(start, end + 1))
            elif part.isdigit():
                selected.add(int(part))
            else:
                raise ValueError
        if not selected or min(selected) < 1 or max(selected) > total:
            raise ValueError
        return [n - 1 for n in sorted(selected)]
    except ValueError:
        return None


def validate_pdf(path: Path, expected_pages: int) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError("Generated PDF is empty or missing.")
    check = PdfReader(str(path), strict=False)
    try:
        if check.is_encrypted or len(check.pages) != expected_pages:
            raise RuntimeError("Generated PDF failed page-count validation.")
    finally:
        check.close()


def create_pdf(selected: list[Path], destination: Path) -> tuple[int, list[tuple[str, str]]]:
    """Build, validate and atomically publish a PDF; never publish zero pages."""
    if not selected:
        raise ValueError("Select at least one image.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    page_width, page_height = A4
    added = 0
    skipped: list[tuple[str, str]] = []
    temp_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".pdf", prefix=".image2pdf-",
            dir=destination.parent, delete=False
        ) as temp:
            temp_path = Path(temp.name)

        pdf = canvas.Canvas(str(temp_path), pagesize=A4)
        try:
            for image_path in selected:
                try:
                    with Image.open(image_path) as original:
                        if original.width * original.height > MAX_IMAGE_PIXELS:
                            raise ValueError("Image exceeds the 80-megapixel safety limit.")
                        img = ImageOps.exif_transpose(original).convert("RGB")
                        img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)

                        title = image_path.name
                        lines = simpleSplit(title, "Helvetica-Bold", 9, page_width - 60)[:2]
                        pdf.setFont("Helvetica-Bold", 9)
                        for line_no, line in enumerate(lines):
                            pdf.drawString(30, page_height - 28 - line_no * 11, line)

                        max_w, max_h = page_width - 60, page_height - 90
                        ratio = min(max_w / img.width, max_h / img.height)
                        draw_w, draw_h = img.width * ratio, img.height * ratio
                        x = (page_width - draw_w) / 2
                        y = (page_height - 75 - draw_h) / 2

                        buffer = BytesIO()
                        img.save(buffer, format="JPEG", quality=65, optimize=True, progressive=True)
                        buffer.seek(0)
                        pdf.drawImage(ImageReader(buffer), x, y, width=draw_w, height=draw_h)
                        pdf.showPage()
                        added += 1
                        print("Added:", title)
                except (OSError, ValueError, UnidentifiedImageError) as exc:
                    skipped.append((image_path.name, str(exc)))
                    print(f"Skipped: {image_path.name} — {exc}")
        finally:
            pdf.save()

        if added == 0:
            raise RuntimeError("No usable images were added; destination was not changed.")
        validate_pdf(temp_path, added)
        os.replace(temp_path, destination)
        temp_path = None
        return added, skipped
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def main() -> int:
    print("\n========== TRINETRA IMAGE TO PDF ==========\n")
    try:
        images = list_images()
    except (FileNotFoundError, OSError) as exc:
        print("ERROR:", exc)
        return 1
    if not images:
        print("No images found!")
        return 1

    print("AVAILABLE IMAGES (LATEST FIRST)\n")
    for i, image in enumerate(images, 1):
        modified = datetime.fromtimestamp(image.stat().st_mtime)
        print(f"{i:3}. {image.name}\n     Modified: {modified:%d-%m-%Y %H:%M}")

    print("\nSelect images: 1,3,5 | 1-5 | 1,3-6,9 | all")
    indexes = parse_selection(input("\nYour selection: "), len(images))
    if indexes is None:
        print("Invalid selection!")
        return 1
    selected = [images[i] for i in indexes]
    print("\nSELECTED IMAGES:")
    for image in selected:
        print(" -", image.name)

    pdfname = input("\nEnter your PDF filename: ").strip()
    if (not pdfname or pdfname in {".", ".."} or Path(pdfname).name != pdfname
            or any(ord(char) < 32 for char in pdfname)):
        print("Invalid PDF filename!")
        return 1
    if not pdfname.lower().endswith(".pdf"):
        pdfname += ".pdf"
    destination = OUTPUT / pdfname
    if destination.exists() and input("File exists. Overwrite? (y/n): ").strip().lower() != "y":
        print("Cancelled.")
        return 0

    try:
        added, skipped = create_pdf(selected, destination)
    except Exception as exc:
        print(f"\nPDF creation failed: {type(exc).__name__}: {exc}")
        return 1

    print("\n==========================================")
    print("PDF CREATED AND VALIDATED")
    print("==========================================")
    print("File:", destination)
    print(f"Images added: {added}/{len(selected)}")
    print("Images skipped:", len(skipped))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
