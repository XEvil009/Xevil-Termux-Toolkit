from pathlib import Path
from datetime import datetime
import subprocess
import tempfile
import shutil
import os
import sys

try:
    from pypdf import PdfReader
except ImportError:
    print("Missing pypdf. Install with: python -m pip install pypdf")
    sys.exit(1)

SHARED = (Path.home() / "storage" / "shared").resolve()
MAGICK = shutil.which("magick")
TESSERACT = shutil.which("tesseract")

def cancel(message="Operation cancelled."):
    print(f"\n{message}")
    return None

def inside_shared(path):
    try:
        path.resolve().relative_to(SHARED)
        return True
    except ValueError:
        return False

def folder_browser(start, create=False):
    current = start.resolve()

    while True:
        print("\n" + "=" * 55)
        print("PDF2MD — SHARED STORAGE BROWSER")
        print(f"Location: {current}")
        print("=" * 55)

        try:
            dirs = sorted(
                [p for p in current.iterdir()
                 if p.is_dir() and not p.is_symlink()],
                key=lambda p: p.name.lower()
            )
        except OSError as e:
            print(f"Cannot read folder: {e}")
            dirs = []

        for i, folder in enumerate(dirs, 1):
            print(f" {i:02}. [DIR] {folder.name}")

        print("\n 0. Select current folder")
        print(" b. Back")
        if create:
            print(" n. Create folder here")
        print(" q. Cancel")

        choice = input("\nSelection: ").strip().lower()

        if choice == "0":
            return current

        if choice == "q":
            return None

        if choice == "b":
            if current != SHARED:
                current = current.parent
            continue

        if create and choice == "n":
            name = input("New folder name: ").strip()
            if not name or name in (".", "..") or "/" in name or "\\" in name:
                print("Invalid folder name.")
                continue

            target = current / name
            try:
                target.mkdir()
                print(f"Created: {target}")
                return target
            except FileExistsError:
                print("Folder already exists.")
            except OSError as e:
                print(f"Cannot create folder: {e}")
            continue

        if choice.isdigit() and 1 <= int(choice) <= len(dirs):
            current = dirs[int(choice) - 1].resolve()
        else:
            print("Invalid selection.")

def list_pdfs(folder):
    try:
        files = [
            p for p in folder.iterdir()
            if p.is_file()
            and not p.is_symlink()
            and p.suffix.lower() == ".pdf"
        ]
    except OSError:
        return []

    def sort_time(path):
        try:
            st = path.stat()
            return max(st.st_ctime_ns, st.st_mtime_ns)
        except OSError:
            return 0

    return sorted(files, key=sort_time, reverse=True)

def select_pdf(folder):
    files = list_pdfs(folder)

    if not files:
        print("No PDF files found in this folder.")
        return None

    print("\nPDF FILES — NEWEST FIRST")
    for i, file in enumerate(files, 1):
        try:
            st = file.stat()
            date = datetime.fromtimestamp(
                max(st.st_ctime, st.st_mtime)
            ).strftime("%Y-%m-%d %H:%M")
            size = st.st_size / (1024 * 1024)
        except OSError:
            date, size = "Unknown", 0

        print(f"\n {i:02}. {file.name}")
        print(f"     Date: {date} | Size: {size:.2f} MB")

    while True:
        choice = input("\nPDF number (0 to cancel): ").strip()

        if choice == "0":
            return None

        if choice.isdigit() and 1 <= int(choice) <= len(files):
            return files[int(choice) - 1]

        print("Invalid selection.")

def markdown_filename(value):
    value = value.strip()
    if value.lower().endswith(".md"):
        value = value[:-3]

    if (not value or value in (".", "..")
            or "/" in value or "\\" in value):
        return None

    return value + ".md"

def clean_ocr_text(text):
    text = text.replace("\x0c", "")
    cleaned = []

    for line in text.splitlines():
        line = line.rstrip()
        cleaned.append(line)

    result = "\n".join(cleaned)

    while "\n\n\n" in result:
        result = result.replace("\n\n\n", "\n\n")

    return result.strip()


def render_and_ocr(source, page_index, image_path):
    page_argument = f"{source}[{page_index}]"

    render = subprocess.run(
        [
            MAGICK,
            "-density", "220",
            page_argument,
            "-background", "white",
            "-alpha", "remove",
            "-alpha", "off",
            "-colorspace", "Gray",
            "-deskew", "40%",
            "-contrast-stretch", "1%x1%",
            "-unsharp", "0x1+0.7+0.02",
            "-strip",
            str(image_path)
        ],
        capture_output=True,
        text=True,
        timeout=180
    )

    if render.returncode != 0 or not image_path.is_file():
        error = render.stderr.strip() or "Unknown ImageMagick error"
        raise RuntimeError(
            f"Could not render page {page_index + 1}: {error}"
        )

    ocr = subprocess.run(
        [
            TESSERACT,
            str(image_path),
            "stdout",
            "-l", "eng",
            "--psm", "11",
            "-c", "preserve_interword_spaces=1"
        ],
        capture_output=True,
        text=True,
        timeout=180
    )

    if ocr.returncode != 0:
        raise RuntimeError(
            f"OCR failed on page {page_index + 1}: "
            f"{ocr.stderr.strip()}"
        )

    return clean_ocr_text(ocr.stdout)

def convert_pdf(source, destination):
    reader = PdfReader(str(source), strict=False)

    if reader.is_encrypted:
        raise ValueError("Encrypted PDFs are not supported.")

    total = len(reader.pages)
    if total < 1:
        raise ValueError("PDF contains no pages.")

    converted_at = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    lines = [
        f"# {source.name}",
        "",
        "> OCR-generated Markdown document",
        "",
        "## Source reference",
        "",
        f"- **PDF filename:** `{source.name.replace(chr(96), chr(92) + chr(96))}`",
        f"- **Page count:** {total}",
        f"- **Converted:** {converted_at}",
        "- **OCR engine:** Tesseract 5 (English)",
        "- **Image processing:** ImageMagick",
        "",
        "**Full source location:**",
        "",
        "```text",
        str(source.resolve()),
        "```",
        "",
        "---",
        ""
    ]

    with tempfile.TemporaryDirectory(prefix="pdf2md_") as temp:
        image_path = Path(temp) / "page.png"

        for index in range(total):
            print(
                f"\rRendering and OCR: page {index + 1}/{total}",
                end="",
                flush=True
            )

            text = render_and_ocr(source, index, image_path)

            lines.extend([
                f"## Page {index + 1}",
                "",
                text if text else "*No readable text detected on this page.*",
                "",
                "---",
                ""
            ])

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n",
            prefix=".pdf2md-", suffix=".tmp",
            dir=destination.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write("\n".join(lines).rstrip() + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

    print("\n\nConversion completed.")
    print(f"Source: {source.name}")
    print(f"Pages processed: {total}")
    print(f"Output: {destination}")
    print(f"Markdown size: {destination.stat().st_size / 1024:.2f} KB")

def main():
    print("\n" + "=" * 55)
    print("             X-EVIL NETWORK")
    print("                 PDF2MD")
    print("=" * 55)

    if not SHARED.is_dir():
        print(f"Shared storage not accessible: {SHARED}")
        print("No storage setup or permission changes will be made.")
        return

    if not MAGICK:
        print("ImageMagick 'magick' command not found.")
        return

    if not TESSERACT:
        print("Tesseract command not found.")
        return

    print("\nSTEP 1 — Browse shared storage")
    folder = folder_browser(SHARED)

    if folder is None:
        return

    print(f"\nSelected folder: {folder}")

    print("\nSTEP 2 — Select source PDF")
    source = select_pdf(folder)

    if source is None:
        return

    print(f"\nSelected PDF: {source.name}")

    print("\nSTEP 3 — Define output Markdown name")
    while True:
        name = markdown_filename(
            input("Markdown filename: ")
        )
        if name:
            break
        print("Invalid filename.")

    print("\nSTEP 4 — Select output folder")
    print("Choose an existing folder or create a new one.")
    output_folder = folder_browser(SHARED, create=True)

    if output_folder is None:
        return

    destination = output_folder / name

    if destination.resolve() == source.resolve():
        print("Output cannot overwrite the source PDF.")
        return

    if destination.exists():
        answer = input(
            f"{destination.name} exists. Overwrite? (y/N): "
        ).strip().lower()
        if answer != "y":
            return

    print("\n" + "=" * 55)
    print("CONVERSION SUMMARY")
    print("=" * 55)
    print(f"Source : {source}")
    print(f"Output : {destination}")
    print("Mode   : OCR every PDF page")
    print("Language: English")
    print("=" * 55)

    answer = input("\nStart conversion? (y/N): ").strip().lower()
    if answer != "y":
        return

    try:
        convert_pdf(source, destination)
    except Exception as e:
        print(f"\nConversion failed: {type(e).__name__}: {e}")

if __name__ == "__main__":
    main()
