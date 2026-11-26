from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from pypdf import PdfReader
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


image2pdf = load_module("image2pdf", "trinetra-pdf.py")
mergepdf = load_module("mergepdf", "merge-pdf.py")
pdf2md = load_module("pdf2md", "pdf2md.py")


class Image2PdfTests(unittest.TestCase):
    def test_import_is_safe_and_selection_parsing(self):
        self.assertEqual(image2pdf.parse_selection("1,3-4", 5), [0, 2, 3])
        self.assertEqual(image2pdf.parse_selection("all", 3), [0, 1, 2])
        self.assertIsNone(image2pdf.parse_selection("0,2", 3))
        self.assertIsNone(image2pdf.parse_selection("4-2", 5))
        self.assertIsNone(image2pdf.parse_selection("1,,2", 5))

    def test_atomic_pdf_generation_and_skip_reporting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            good = root / "valid.png"
            bad = root / "broken.png"
            out = root / "result.pdf"
            Image.new("RGB", (320, 240), "white").save(good)
            bad.write_bytes(b"not an image")
            added, skipped = image2pdf.create_pdf([good, bad], out)
            self.assertEqual(added, 1)
            self.assertEqual(len(skipped), 1)
            self.assertEqual(len(PdfReader(str(out)).pages), 1)
            self.assertFalse(list(root.glob(".image2pdf-*")))

    def test_all_bad_images_do_not_replace_existing_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad = root / "broken.png"
            out = root / "existing.pdf"
            bad.write_bytes(b"bad")
            out.write_bytes(b"keep-this-file")
            with self.assertRaises(RuntimeError):
                image2pdf.create_pdf([bad], out)
            self.assertEqual(out.read_bytes(), b"keep-this-file")
            self.assertFalse(list(root.glob(".image2pdf-*")))


class MergePdfTests(unittest.TestCase):
    def test_merge_creates_valid_pdf_with_expected_page_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = []
            for index in range(2):
                path = root / f"source-{index}.pdf"
                pdf = canvas.Canvas(str(path))
                pdf.drawString(50, 750, f"Source page {index}")
                pdf.save()
                inputs.append(path)
            output = root / "merged.pdf"
            count = mergepdf.merge_pdfs(inputs, output)
            self.assertEqual(count, 2)
            self.assertEqual(len(PdfReader(str(output)).pages), 2)
            self.assertFalse(list(root.glob(".mergepdf-*")))


class Pdf2MdTests(unittest.TestCase):
    def test_conversion_uses_unique_atomic_temp_and_writes_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input.pdf"
            pdf = canvas.Canvas(str(source))
            pdf.drawString(50, 750, "test")
            pdf.showPage()
            pdf.drawString(50, 750, "test two")
            pdf.save()
            output = root / "result.md"
            with patch.object(pdf2md, "render_and_ocr", side_effect=["page one", "page two"]):
                pdf2md.convert_pdf(source, output)
            content = output.read_text(encoding="utf-8")
            self.assertIn("## Page 1", content)
            self.assertIn("## Page 2", content)
            self.assertIn("page two", content)
            self.assertFalse(list(root.glob(".pdf2md-*.tmp")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
