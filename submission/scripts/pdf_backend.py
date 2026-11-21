"""Offline, interchangeable PDF text and page image backends."""

from __future__ import annotations

import csv
import importlib
import io
import math
import os
import re
import shutil
import struct
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

Box = tuple[float, float, float, float]
CID = re.compile(r"\(cid:\d+\)")
BACKENDS = ("pymupdf", "poppler", "pdfplumber")


class BackendError(Exception):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code


@dataclass
class Word:
    text: str
    box: Box
    source_line: str | None = None
    confidence: float | None = None


@dataclass
class Page:
    number: int
    width: float
    height: float
    words: list[Word]
    backend: str
    label: str | None = None
    images: list[Box] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    error: str | None = None


def clip_box(coords, width: float, height: float) -> Box | None:
    x0, y0, x1, y1 = (float(v) for v in coords)
    if not all(math.isfinite(v) for v in (x0, y0, x1, y1)):
        return None
    box = (max(0., x0), max(0., y0), min(width, x1), min(height, y1))
    return box if box[0] < box[2] and box[1] < box[3] else None


def choose_pages(spec: str | None, count: int) -> list[int]:
    if spec is None:
        return list(range(1, count + 1))
    chosen = set()
    for part in spec.split(","):
        match = re.fullmatch(r"\s*(\d+)(?:\s*-\s*(\d+))?\s*", part)
        if not match:
            raise BackendError("invalid_page_selection", f"Invalid page selection: {spec!r}")
        low, high = int(match[1]), int(match[2] or match[1])
        if not 1 <= low <= high <= count:
            raise BackendError("invalid_page_selection",
                               f"Page range {low}-{high} is outside physical pages 1-{count}")
        chosen.update(range(low, high + 1))
    return sorted(chosen)


def executable(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise BackendError("dependency_unavailable", f"{name} is not on PATH")
    return found


def command(args: list[str], timeout: float) -> tuple[bytes, str]:
    try:
        result = subprocess.run(
            args, capture_output=True, timeout=timeout, check=False,
            env={**os.environ, "LC_ALL": "C"},
        )
    except subprocess.TimeoutExpired as exc:
        raise BackendError("tool_timeout", f"{Path(args[0]).name} exceeded {timeout:g}s") from exc
    except OSError as exc:
        raise BackendError("tool_unavailable", str(exc)) from exc
    stderr = result.stderr.decode("utf-8", "replace").strip()
    if result.returncode:
        code = "encrypted_pdf" if re.search(r"password|encrypted", stderr, re.I) else "tool_error"
        detail = stderr[:300] or f"exit code {result.returncode}"
        raise BackendError(code, f"{Path(args[0]).name}: {detail}")
    return result.stdout, stderr


def fitz_module():
    try:
        return importlib.import_module("pymupdf")
    except ImportError:
        module = importlib.import_module("fitz")
        if not hasattr(module, "TEXTFLAGS_WORDS"):
            raise ImportError("the fitz module is not PyMuPDF")
        return module


def pymupdf_pages(pdf: Path, spec: str | None, _timeout: float):
    fitz = fitz_module()
    with fitz.open(str(pdf)) as doc:
        if doc.needs_pass:
            raise BackendError("encrypted_pdf", "PyMuPDF reports a required password")
        count = len(doc)
        answer = []
        for number in choose_pages(spec, count):
            page = doc[number - 1]
            width, height = float(page.rect.width), float(page.rect.height)
            record = Page(number, width, height, [], "pymupdf", page.get_label() or None)
            answer.append(record)
            try:
                for item in page.get_text("words", flags=fitz.TEXTFLAGS_WORDS, sort=False):
                    rect = fitz.Rect(item[:4]) * page.rotation_matrix
                    box = clip_box(rect, width, height)
                    if box and item[4].strip():
                        record.words.append(Word(item[4], box, f"{item[5]}:{item[6]}"))
                for image in page.get_image_info():
                    rect = fitz.Rect(image["bbox"]) * page.rotation_matrix
                    box = clip_box(rect, width, height)
                    if box:
                        record.images.append(box)
            except (OSError, RuntimeError, ValueError) as exc:
                record.flags.append("page_extraction_interrupted")
                record.error = str(exc)[:300]
    version = getattr(fitz, "VersionBind", "?")
    return count, answer, version


def poppler_pages(pdf: Path, spec: str | None, timeout: float):
    tool = executable("pdftotext")
    # BBox Layout supplies native block/line order and word boxes in one pass.
    data, stderr = command([tool, "-bbox-layout", "-cropbox", "-enc", "UTF-8", str(pdf), "-"], timeout)
    elements = list(ET.fromstring(data).iterfind(".//{*}page"))
    if not elements:
        raise BackendError("unreadable_pdf", "pdftotext returned no pages")
    answer = []
    for number in choose_pages(spec, len(elements)):
        element = elements[number - 1]
        width, height = float(element.attrib["width"]), float(element.attrib["height"])
        page = Page(number, width, height, [], "poppler")
        answer.append(page)
        for j, line in enumerate(element.iterfind(".//{*}line"), start=1):
            for word in line.iterfind("{*}word"):
                raw = "".join(word.itertext())
                box = clip_box([word.attrib[k] for k in ("xMin", "yMin", "xMax", "yMax")], width, height)
                if box and raw.strip():
                    page.words.append(Word(raw, box, str(j)))
        if stderr:
            page.flags.append("extractor_emitted_diagnostics")
    try:
        _, version_text = command([tool, "-v"], 3)
        match = re.search(r"pdftotext version (\S+)", version_text)
        version = match[1] if match else None
    except BackendError:
        version = None
    return len(elements), answer, version


def pdfplumber_pages(pdf: Path, spec: str | None, _timeout: float):
    pdfplumber = importlib.import_module("pdfplumber")
    try:
        with pdfplumber.open(pdf) as doc:
            count = len(doc.pages)
            answer = []
            for number in choose_pages(spec, count):
                page = doc.pages[number - 1]
                mx0, my0, mx1, my1 = page.bbox
                x0, y0, x1, y1 = page.cropbox or page.bbox
                x0, y0, x1, y1 = max(mx0, x0), max(my0, y0), min(mx1, x1), min(my1, y1)
                width, height = x1 - x0, y1 - y0
                record = Page(number, width, height, [], "pdfplumber")
                answer.append(record)
                try:
                    # Text-flow mode keeps evidence of the native traversal.
                    for word in page.extract_words(use_text_flow=True, expand_ligatures=False):
                        box = clip_box((word["x0"] - x0, word["top"] - y0,
                                        word["x1"] - x0, word["bottom"] - y0), width, height)
                        if box and word["text"].strip():
                            record.words.append(Word(word["text"], box))
                    for image in page.images:
                        box = clip_box((image["x0"] - x0, image["top"] - y0,
                                        image["x1"] - x0, image["bottom"] - y0), width, height)
                        if box:
                            record.images.append(box)
                except (OSError, RuntimeError, ValueError) as exc:
                    record.flags.append("page_extraction_interrupted")
                    record.error = str(exc)[:300]
                finally:
                    page.close()
    except Exception as exc:
        related = (exc, exc.__cause__, exc.__context__, *exc.args)
        if any("password" in type(issue).__name__.lower() for issue in related):
            raise BackendError("encrypted_pdf", "pdfplumber reports a required password") from exc
        raise
    return count, answer, pdfplumber.__version__


def read_pdf(pdf: Path, spec: str | None, backend: str, timeout: float):
    readers = {"pymupdf": pymupdf_pages, "poppler": poppler_pages, "pdfplumber": pdfplumber_pages}
    attempts = []
    for name in BACKENDS if backend == "auto" else (backend,):
        try:
            count, pages, version = readers[name](pdf, spec, timeout)
            if not pages:
                raise BackendError("unreadable_pdf", "No physical pages were returned")
            attempts.append({"backend": name, "status": "used", "version": version})
            return count, pages, attempts
        except BackendError as exc:
            code, detail = exc.code, str(exc)
        except ImportError as exc:
            code, detail = "dependency_unavailable", str(exc)
        except Exception as exc:
            code, detail = "backend_error", f"{type(exc).__name__}: {exc}"
        attempts.append({"backend": name, "status": code, "detail": detail[:300]})
        if code == "invalid_page_selection":
            break
    return None, [], attempts


def render_page(pdf: Path, number: int, target: Path, dpi: int, timeout: float) -> str:
    errors = []
    try:
        tool = executable("pdftoppm")
        prefix = target.with_suffix("")
        command([tool, "-cropbox", "-f", str(number), "-l", str(number),
                 "-r", str(dpi), "-png", "-singlefile", str(pdf), str(prefix)], timeout)
        if not target.is_file():
            raise BackendError("render_failed", "pdftoppm did not produce an image")
        return "pdftoppm"
    except BackendError as exc:
        errors.append(str(exc))
    try:
        fitz = fitz_module()
        with fitz.open(str(pdf)) as doc:
            if doc.needs_pass:
                raise BackendError("encrypted_pdf", "A password is required to render this PDF")
            doc[number - 1].get_pixmap(dpi=dpi, alpha=False).save(str(target))
        return "pymupdf"
    except (ImportError, OSError, RuntimeError, ValueError, IndexError, BackendError) as exc:
        errors.append(str(exc))
    try:
        pdfplumber = importlib.import_module("pdfplumber")
        with pdfplumber.open(pdf) as doc:
            doc.pages[number - 1].to_image(resolution=dpi).save(target, format="PNG")
        return "pdfplumber"
    except Exception as exc:
        errors.append(str(exc))
    raise BackendError("render_failed", " / ".join(errors)[:500])


def suspect(text: str) -> bool:
    return bool(CID.search(text)) or any(
        c == "\ufffd" or (ord(c) < 32 and not c.isspace()) or
        "\ue000" <= c <= "\uf8ff" or "\U000f0000" <= c <= "\U0010fffd"
        for c in text
    )


def ocr_page(pdf: Path, page: Page, work: Path, lang: str, timeout: float,
             dpi: int = 220) -> tuple[list[Word], dict]:
    tool = executable("tesseract")
    with tempfile.TemporaryDirectory(prefix="ocr-", dir=work) as tmp:
        image = Path(tmp) / "page.png"
        renderer = render_page(pdf, page.number, image, dpi, timeout)
        with image.open("rb") as stream:
            header = stream.read(24)
        if not header.startswith(b"\x89PNG\r\n\x1a\n") or len(header) < 24:
            raise BackendError("render_failed", "Unexpected raster file")
        w_px, h_px = struct.unpack(">II", header[16:24])
        sx, sy = page.width / w_px, page.height / h_px
        if abs(sx - sy) > 0.02 * max(sx, sy):
            raise BackendError("coordinate_mismatch", "Rendered page aspect differs from PDF extraction")
        data, _ = command([tool, str(image), "stdout", "-l", lang, "--psm", "3", "tsv"], timeout)
    words = []
    for row in csv.DictReader(io.StringIO(data.decode("utf-8", "replace")), delimiter="\t",
                              quoting=csv.QUOTE_NONE):
        text = (row.get("text") or "").strip()
        if row.get("level") != "5" or not text:
            continue
        try:
            x, y, w, h = (int(row[k]) for k in ("left", "top", "width", "height"))
            confidence = float(row["conf"])
            box = clip_box((x*sx, y*sy, (x+w)*sx, (y+h)*sy), page.width, page.height)
            line = ":".join(row[k] for k in ("block_num", "par_num", "line_num"))
        except (ValueError, TypeError, KeyError):
            continue
        if box:
            words.append(Word(text, box, line, confidence if 0 <= confidence <= 100 else None))
    return words, {"engine": "tesseract", "renderer": renderer, "language": lang, "dpi": dpi}
