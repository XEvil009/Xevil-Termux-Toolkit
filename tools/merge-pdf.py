#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime
from io import BytesIO
import os
import re
import sys
import tempfile

from pypdf import PdfReader, PdfWriter, Transformation
from pypdf import PageObject
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth


SHARED = (Path.home() / "storage" / "shared").resolve()


def pause():
    input("\nPress Enter to continue...")


def heading(text):
    print("\n" + "=" * 54)
    print(f"  {text}")
    print("=" * 54)


def inside_shared(path):
    try:
        path.resolve().relative_to(SHARED)
        return True
    except ValueError:
        return False


def browse_folder(start):
    """Interactive folder browser restricted to shared storage."""
    current = Path(start).resolve()

    while True:
        if not inside_shared(current) or not current.is_dir():
            print("Invalid folder.")
            current = SHARED

        heading("SHARED STORAGE BROWSER")
        print(f"Current: {current.relative_to(SHARED) or '.'}")
        print("\n  S. Select this folder")
        print("  U. Go up one folder")
        print("  Q. Cancel")
        print("\nFolders:")

        folders = sorted(
            (p for p in current.iterdir() if p.is_dir() and not p.is_symlink()),
            key=lambda p: p.name.lower()
        )

        for i, folder in enumerate(folders, 1):
            print(f"  {i:02d}. {folder.name}/")

        if not folders:
            print("  No subfolders.")

        choice = input("\nChoose folder number / S / U / Q: ").strip().lower()

        if choice == "s":
            return current
        if choice == "q":
            return None
        if choice == "u":
            if current != SHARED:
                current = current.parent
            else:
                print("Already at shared storage root.")
            continue

        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(folders):
                current = folders[index - 1].resolve()
            else:
                print("Invalid folder number.")
        else:
            print("Invalid selection.")


def newest_time(path):
    stat = path.stat()
    modified = stat.st_mtime
    created = getattr(stat, "st_birthtime", modified)
    return max(modified, created)


def show_pdfs(folder):
    files = sorted(
        (
            p for p in folder.iterdir()
            if p.is_file()
            and p.suffix.lower() == ".pdf"
            and not p.is_symlink()
        ),
        key=newest_time,
        reverse=True
    )

    heading("PDF FILES — NEWEST FIRST")
    print(f"Folder: {folder}\n")

    if not files:
        print("No PDF files found in this folder.")
        return []

    for i, path in enumerate(files, 1):
        modified = datetime.fromtimestamp(path.stat().st_mtime)
        size = path.stat().st_size / 1024
        print(f"  {i:02d}. {path.name}")
        print(f"      Modified: {modified:%Y-%m-%d %H:%M} | Size: {size:.1f} KB")

    return files


def parse_selection(value, total):
    value = value.strip().lower()

    if value == "all":
        return list(range(total))

    selected = []
    try:
        for part in value.split(","):
            part = part.strip()
            if not part:
                raise ValueError

            if "-" in part:
                start, end = map(int, part.split("-", 1))
                if start > end:
                    raise ValueError
                selected.extend(range(start, end + 1))
            else:
                selected.append(int(part))

        if any(n < 1 or n > total for n in selected):
            raise ValueError

        if len(set(selected)) != len(selected):
            raise ValueError

        return [n - 1 for n in selected]

    except ValueError:
        return None


def make_title_page(source_page, filename):
    """Create a first page with a filename heading and scaled original content.

    pypdf 7 requires a page to belong to a writer before its content stream
    can be replaced. Attach a working copy to a temporary writer first; this
    also keeps the source reader's page object unchanged.
    """
    rotation_writer = PdfWriter()
    rotation_writer.add_page(source_page)
    source_page = rotation_writer.pages[0]
    source_page.transfer_rotation_to_content()

    width = float(source_page.mediabox.width)
    height = float(source_page.mediabox.height)

    margin = min(30, width * 0.05)
    header_height = min(76, height * 0.15)
    available_width = width - 2 * margin
    body_height = height - header_height - margin

    if available_width <= 0 or body_height <= 0:
        raise ValueError("Page dimensions are too small for a section heading.")

    scale = min(
        available_width / width,
        body_height / height
    )

    tx = (width - width * scale) / 2
    ty = margin

    output_page = PageObject.create_blank_page(
        width=width,
        height=height
    )

    output_page.merge_transformed_page(
        source_page,
        Transformation().scale(scale).translate(tx=tx, ty=ty)
    )

    # Draw the section heading in a separate top band.
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(width, height))

    pdf.setFillColorRGB(0.96, 0.97, 0.98)
    pdf.rect(0, height - header_height, width, header_height, fill=1, stroke=0)

    pdf.setFillColorRGB(0.12, 0.16, 0.22)
    pdf.setFont("Helvetica-Bold", 12)

    title = filename
    font_size = 12

    while stringWidth(title, "Helvetica-Bold", font_size) > available_width:
        font_size -= 0.5
        if font_size <= 6:
            break

    if stringWidth(title, "Helvetica-Bold", font_size) <= available_width:
        pdf.setFont("Helvetica-Bold", font_size)
        pdf.drawCentredString(width / 2, height - header_height / 2 - 4, title)
    else:
        # Wrap exceptionally long filenames across two lines.
        words = list(title)
        lines = ["", ""]

        for char in words:
            target = 0 if stringWidth(lines[0] + char, "Helvetica-Bold", 8) <= available_width else 1
            lines[target] += char

        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawCentredString(width / 2, height - 29, lines[0])
        pdf.drawCentredString(width / 2, height - 43, lines[1])

    pdf.setStrokeColorRGB(0.35, 0.42, 0.52)
    pdf.setLineWidth(0.7)
    pdf.line(margin, height - header_height, width - margin, height - header_height)

    pdf.save()
    buffer.seek(0)

    overlay = PdfReader(buffer).pages[0]
    output_page.merge_page(overlay)

    return output_page


def load_pdf(path):
    data = path.read_bytes()
    reader = PdfReader(BytesIO(data), strict=False)

    if reader.is_encrypted:
        raise ValueError("Encrypted/password-protected PDFs are not supported.")

    if len(reader.pages) == 0:
        raise ValueError("PDF contains no pages.")

    return reader


def merge_pdfs(selected, output_path):
    writer = PdfWriter()
    total_pages = 0

    # Validate all files before constructing the output.
    readers = []

    heading("VALIDATING SELECTED PDF FILES")

    for path in selected:
        print(f"Checking: {path.name}")
        reader = load_pdf(path)
        readers.append((path, reader))
        total_pages += len(reader.pages)

    print(f"\nFiles validated: {len(readers)}")
    print(f"Total pages: {total_pages}")

    for file_index, (path, reader) in enumerate(readers, 1):
        print(f"\nMerging {file_index}/{len(readers)}: {path.name}")

        for page_index, page in enumerate(reader.pages):
            if page_index == 0:
                page = make_title_page(page, path.name)

            writer.add_page(page)

    writer.add_metadata({
        "/Title": output_path.stem,
        "/Subject": "Merged PDF created with X-Evil Network MergePdf",
        "/Producer": "X-Evil Network MergePdf"
    })

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to a temporary file first, then replace the destination.
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=".pdf",
            prefix=".mergepdf-",
            dir=output_path.parent,
            delete=False
        ) as temp:
            temp_path = Path(temp.name)
            writer.write(temp)

        if not temp_path.exists() or temp_path.stat().st_size == 0:
            raise RuntimeError("Output validation failed: empty PDF.")

        # Confirm that the generated PDF can be opened.
        check = PdfReader(str(temp_path), strict=False)
        if check.is_encrypted or len(check.pages) != total_pages:
            raise RuntimeError("Output validation failed: page count mismatch.")

        os.replace(temp_path, output_path)

    except Exception:
        if temp_path and temp_path.exists():
            temp_path.unlink()
        raise

    return total_pages


def choose_output_folder():
    heading("OUTPUT LOCATION")
    print("  1. Select an existing shared-storage folder")
    print("  2. Create a new folder inside shared storage")
    print("  3. Cancel")

    choice = input("\nChoose: ").strip()

    if choice == "1":
        return browse_folder(SHARED)

    if choice == "2":
        parent = browse_folder(SHARED)
        if parent is None:
            return None

        while True:
            name = input("New folder name: ").strip()

            if not name or name in (".", "..") or "/" in name or "\\" in name:
                print("Enter a valid folder name.")
                continue

            target = parent / name

            if target.exists():
                if target.is_dir():
                    print("That folder already exists. Select it instead.")
                else:
                    print("A file with that name already exists.")
                continue

            try:
                target.mkdir()
                print(f"Created: {target}")
                return target
            except OSError as exc:
                print(f"Could not create folder: {exc}")

    return None


def main():
    heading("X-EVIL NETWORK — MERGEPDF")
    print("PDF merger with filename section headings")
    print("Shared storage:", SHARED)

    if not SHARED.is_dir():
        print("\nShared storage is unavailable.")
        print("Run: termux-setup-storage")
        return

    print("\nSTEP 1 — Select the folder containing source PDFs.")
    source_folder = browse_folder(SHARED)

    if source_folder is None:
        print("Operation cancelled.")
        return

    print("\nSTEP 2 — Select PDF files.")
    pdfs = show_pdfs(source_folder)

    if len(pdfs) < 2:
        print("\nAt least two PDFs are required.")
        return

    print("\nEnter PDF numbers separated by commas or ranges.")
    print("Examples: 1,3,5   |   1-4   |   1,3-5")
    print("Enter ALL to select every listed PDF.")

    while True:
        raw = input("\nPDF selection: ").strip()
        indexes = parse_selection(raw, len(pdfs))

        if indexes is None:
            print("Invalid selection. Check the numbers and ranges.")
            continue

        if len(indexes) < 2:
            print("You must select at least two different PDFs.")
            continue

        break

    # The entered selection order determines the merge order.
    selected = [pdfs[index] for index in indexes]

    heading("MERGE ORDER")
    for i, path in enumerate(selected, 1):
        print(f"  {i:02d}. {path.name}")

    print("\nThe original filename will appear as a section heading")
    print("on the first page of each selected PDF.")

    confirm = input("\nContinue? (y/n): ").strip().lower()
    if confirm != "y":
        print("Operation cancelled.")
        return

    print("\nSTEP 3 — Choose the output folder.")
    output_folder = choose_output_folder()

    if output_folder is None:
        print("Operation cancelled.")
        return

    print("\nSTEP 4 — Define the output PDF filename.")

    while True:
        name = input("Output filename (without extension is okay): ").strip()

        if not name:
            print("Filename cannot be empty.")
            continue

        if "/" in name or "\\" in name or name in (".", ".."):
            print("Enter a filename, not a path.")
            continue

        if not name.lower().endswith(".pdf"):
            name += ".pdf"

        if name in (".pdf",):
            print("Invalid filename.")
            continue

        break

    output_path = (output_folder / name).resolve()

    if not inside_shared(output_path):
        print("Output must remain inside shared storage.")
        return

    if output_path in [p.resolve() for p in selected]:
        print("Output filename matches one of the source PDFs.")
        print("Choose a different output filename.")
        return

    if output_path.exists():
        answer = input(
            f"\n{output_path.name} already exists. Overwrite? (y/n): "
        ).strip().lower()

        if answer != "y":
            print("Operation cancelled. Choose another filename next time.")
            return

    heading("FINAL CONFIRMATION")
    print("Source folder:", source_folder)
    print("Selected PDFs:", len(selected))
    print("Output file:", output_path)

    if input("\nStart merging? (y/n): ").strip().lower() != "y":
        print("Operation cancelled.")
        return

    try:
        pages = merge_pdfs(selected, output_path)

        heading("MERGE COMPLETED SUCCESSFULLY")
        print("Output:", output_path)
        print("PDF files merged:", len(selected))
        print("Total pages:", pages)
        print(f"Output size: {output_path.stat().st_size / 1024:.1f} KB")

    except Exception as exc:
        print("\nMERGE FAILED")
        print("Reason:", exc)
        print("Original source PDFs have not been modified.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as exc:
        print(f"\nUnexpected error: {exc}")
        sys.exit(1)
