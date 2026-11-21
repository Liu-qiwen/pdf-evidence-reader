#!/usr/bin/env python3
"""Extract, query, and render source evidence from a local PDF."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

from pdf_backend import BACKENDS, BackendError, Page, choose_pages, ocr_page, read_pdf, render_page, suspect
from reading_order import geometric_lines, page_edges, page_layout, word_records

VERSION = "1.0.0"
MARGINS = {"running_header_candidate", "running_footer_candidate", "page_number_candidate"}


def save_json(path: Path, value: dict) -> None:
    staged = path.with_name(path.name + ".tmp")
    staged.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n",
                      encoding="utf-8")
    staged.replace(path)


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8-sig") as stream:
        return json.load(stream)


def say(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))


def file_input(pdf: Path) -> dict:
    source = {"path": str(pdf), "file_name": pdf.name}
    with pdf.open("rb") as stream:
        first = stream.read(1024)
        sha = hashlib.sha256(first)
        if b"%PDF-" not in first:
            raise ValueError("The input has no PDF header in the first 1024 bytes")
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
    return {**source, "sha256": sha.hexdigest()}


def ingest_ocr(pdf: Path, page: Page, args, work: Path, remaining: int):
    native = page.words
    if not native:
        page.flags.append("no_native_text")
    broken = sum(suspect(w.text) for w in native)
    sparse_image = len(native) < 18 and any(
        (x1-x0) * (y1-y0) >= .45 * page.width * page.height for x0, y0, x1, y1 in page.images
    )
    if native and sparse_image:
        page.flags.append("sparse_text_over_large_image")
    needs_ocr = not native or sparse_image or broken > max(3, .20 * len(native))
    if args.ocr == "off" or (args.ocr == "auto" and not needs_ocr):
        return None, remaining
    if remaining <= 0:
        page.flags.append("ocr_budget_exhausted")
        return None, remaining
    try:
        words, meta = ocr_page(pdf, page, work, args.ocr_lang, args.ocr_timeout)
    except BackendError as exc:
        page.flags.append("ocr_unavailable_or_failed")
        return {"status": exc.code, "detail": str(exc)}, remaining - 1
    if not words:
        page.flags.append("ocr_returned_no_words")
        return {"status": "no_words", **meta}, remaining - 1
    good_ocr = sum(w.confidence is not None and w.confidence >= 60 and not suspect(w.text)
                   for w in words)
    use = not native or (needs_ocr and good_ocr > len(native) - broken)
    other = native if use else words
    if use:
        page.words = words
        page.flags.append("ocr_text_requires_visual_check")
    return {"status": "selected" if use else "alternative", **meta,
            "other_layer": "native" if use else "ocr", "words_in_other_layer_order": word_records(other)
            }, remaining - 1


def layout_summary(record: dict, source_rel: str) -> dict:
    return {
        "page": record["page"], "file": source_rel, "status": record["status"],
        "pdf_page_label": record["pdf_page_label"],
        "word_count": len(record["words_in_backend_order"]),
        "block_count": len(record["blocks"]),
        "layout": record["layout"]["method"],
        "columns_candidate": len(record["layout"]["gutters"]) + 1 if record["blocks"] else None,
        "flags": record["flags"],
        "anchors": [
            {"id": block["id"], "kind": block["kind"], "text_preview": block["text"][:140]}
            for block in record["blocks"]
            if block["kind"] in {"title_candidate", "heading_candidate", "abstract_candidate",
                                 "table_caption_candidate", "figure_caption_candidate",
                                 "equation_candidate", "page_number_candidate"}
        ],
    }


def continuation(previous: dict | None, record: dict) -> dict | None:
    if previous is None or previous["page"] + 1 != record["page"]:
        return None
    before = [b for b in previous["blocks"] if b["kind"] not in MARGINS | {"footnote_candidate"}]
    after = [b for b in record["blocks"] if b["kind"] not in MARGINS | {"footnote_candidate"}]
    if not before or not after:
        return None
    tail, head = before[-1], after[0]
    if tail["kind"] == head["kind"] == "paragraph" and not tail["text"].endswith((".", "。", "?", "!", "：", ":")):
        if re.match(r"^[a-z]", head["text"]) or tail["text"].endswith(("-", "\u00ad")):
            return {"from": tail["id"], "to": head["id"], "status": "candidate_only"}
    return None


def parse(args) -> int:
    pdf = args.pdf.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    index_path = out / "index.json"
    index = {
        "schema_version": VERSION, "case_id": args.case_id, "status": "running",
        "source": {"path": str(pdf), "file_name": pdf.name},
        "coordinates": "PDF physical pages 1-based; displayed CropBox [x0, top, x1, bottom] in points, top-left origin",
        "requested_pages": args.pages, "pages": [], "issues": [], "possible_page_continuations": [],
    }
    try:
        with index_path.open("x", encoding="utf-8") as stream:
            json.dump(index, stream, ensure_ascii=False)
    except FileExistsError:
        raise ValueError(f"Run already exists: {index_path}; use a fresh output directory") from None

    try:
        index["source"] = file_input(pdf)
    except FileNotFoundError as exc:
        index.update(status="failed", issues=[{"code": "input_missing", "detail": str(exc)}])
    except (OSError, ValueError) as exc:
        index.update(status="failed", issues=[{"code": "unreadable_input", "detail": str(exc)}])
    if index["status"] == "failed":
        save_json(index_path, index)
        say({"status": index["status"], "index": str(index_path), "issues": index["issues"]})
        return 2

    count, pages, attempts = read_pdf(pdf, args.pages, args.backend, args.timeout)
    index.update(page_count=count, extraction_attempts=attempts, selected_pages=[p.number for p in pages])
    if not pages:
        codes = {entry["status"] for entry in attempts}
        reason = next((code for code in ("invalid_page_selection", "encrypted_pdf", "tool_timeout")
                       if code in codes), None)
        if not reason:
            reason = ("no_usable_text_backend" if codes <= {"dependency_unavailable", "tool_unavailable"}
                      else "extraction_failed")
        index.update(status="failed", issues=[{"code": reason}])
        save_json(index_path, index)
        say({"status": "failed", "index": str(index_path), "attempts": attempts})
        return 2

    data_dir = out / "pages"
    data_dir.mkdir(exist_ok=True)
    index["reading_order_file"] = "reading-order.txt"
    save_json(index_path, index)
    lines = [geometric_lines(page) for page in pages]
    edges = page_edges(pages, lines)
    remaining_ocr = args.ocr_limit
    previous = None
    in_references = False
    with (out / "reading-order.txt").open("w", encoding="utf-8", newline="\n") as text:
        for page, (fragments, normal), edge in zip(pages, lines, edges):
            if previous is None or previous["page"] + 1 != page.number:
                in_references = False
            ocr, remaining_ocr = ingest_ocr(pdf, page, args, out, remaining_ocr)
            layer = "ocr" if ocr and ocr["status"] == "selected" else "native"
            if layer == "ocr":
                fragments, normal = geometric_lines(page)
                edge = page_edges([page], [(fragments, normal)])[0]
            try:
                record, in_references = page_layout(page, fragments, normal, edge, in_references)
            except ValueError as exc:
                record, in_references = page_layout(page, [], normal, {}, False, raw_only=True)
                record["extraction_error"] = str(exc)
                record["flags"].append("layout_failed_raw_words_preserved")
            record["text_layer_used"] = layer
            if ocr:
                record["ocr"] = ocr
            if not record["blocks"]:
                record["status"] = "review" if page.words else "unreadable"
                record["flags"].append("render_for_manual_review")
            elif any(flag in record["flags"] for flag in (
                    "page_extraction_interrupted", "glyph_mapping_review",
                    "ocr_text_requires_visual_check", "bidirectional_text_review",
                    "rotated_or_vertical_text_review", "extractor_emitted_diagnostics",
                    "sparse_text_over_large_image", "check_rows_with_wide_internal_gaps",
                    "inferred_caption_band_review")):
                record["status"] = "review"
            else:
                record["status"] = "extracted"
            source_rel = f"pages/p{page.number:04d}.json"
            save_json(out / source_rel, record)
            index["pages"].append(layout_summary(record, source_rel))
            candidate = continuation(previous, record)
            if candidate:
                index["possible_page_continuations"].append(candidate)
            text.write(f"=== PDF page {page.number} [{record['status']}] ===\n")
            for block in record["blocks"]:
                if block["kind"] not in MARGINS:
                    text.write(f"[{block['id']} {block['kind']}]\n{block['text']}\n\n")
            if not record["blocks"]:
                text.write(f"Manual review: {', '.join(record['flags'])}\n\n")
            text.flush()
            save_json(index_path, index)
            previous = record

    counts = Counter(p["status"] for p in index["pages"])
    if counts["unreadable"] == len(pages):
        status = "indeterminate"
    elif counts["unreadable"] or counts["review"]:
        status = "partial"
    else:
        status = "success"
    index.update(status=status, page_status_counts=dict(counts))
    save_json(index_path, index)
    say({"status": status, "index": str(index_path), "physical_page_count": count,
         "selected_page_count": len(pages), "page_status_counts": dict(counts)})
    return 0


def page_entries(index_path: Path, spec: str | None):
    index = read_json(index_path)
    wanted = set(choose_pages(spec, index["page_count"])) if spec else None
    for entry in index["pages"]:
        if wanted is None or entry["page"] in wanted:
            yield read_json(index_path.parent / entry["file"])


def find(args) -> int:
    regex = re.compile(args.query if args.regex else re.escape(" ".join(args.query.split())), re.I)
    matches = []
    for page in page_entries(args.index, args.pages):
        for block in page["blocks"]:
            space_normalized = " ".join(block["text"].split())
            if args.kind and block["kind"] != args.kind:
                continue
            match = regex.search(space_normalized)
            if not match:
                continue
            before, after = max(0, match.start() - 90), min(len(space_normalized), match.end() + 150)
            matches.append({
                "page": page["page"], "pdf_page_label": page["pdf_page_label"],
                "id": block["id"], "kind": block["kind"], "bbox": block["bbox"],
                "preview": space_normalized[before:after], "page_flags": page["flags"],
            })
            if len(matches) >= args.limit:
                say(matches)
                return 0
    say(matches)
    return 0


def show(args) -> int:
    spec = str(args.page)
    if args.block:
        match = re.fullmatch(r"P(\d+)-B\d+", args.block)
        if not match:
            raise ValueError("Block ID must have the form P0001-B001")
        spec = match[1]
    page = next(page_entries(args.index, spec), None)
    if page is None:
        raise ValueError("That physical page was not extracted in this run")
    if args.block:
        block = next((b for b in page["blocks"] if b["id"] == args.block), None)
        if not block:
            raise ValueError(f"Block {args.block} absent in this run")
        id_set = {i for line in block["lines"] for i in line["word_ids"]}
        block_words = [w for w in page["words_in_backend_order"] if w["id"] in id_set]
        say({"page": page["page"], "pdf_page_label": page["pdf_page_label"],
             "text_layer": page["text_layer_used"], "flags": page["flags"],
             "block": block, **({"words_in_backend_order": block_words} if args.words else {})})
    else:
        if not args.words:
            page.pop("words_in_backend_order", None)
            if "ocr" in page:
                page["ocr"].pop("words_in_other_layer_order", None)
        say(page)
    return 0


def render(args) -> int:
    out = args.out.resolve()
    if out.suffix.lower() != ".png":
        raise ValueError("--out must name a PNG file")
    if out.resolve() == args.pdf.resolve():
        raise ValueError("Render output and input must be different files")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pdf-render-", dir=out.parent) as tmp:
        staged = Path(tmp) / "page.png"
        engine = render_page(args.pdf.resolve(), args.page, staged, args.dpi, args.timeout)
        if args.bbox:
            from PIL import Image
            x0, y0, x1, y1 = args.bbox
            if not 0 <= x0 < x1 or not 0 <= y0 < y1:
                raise ValueError("--bbox expects nonnegative x0 top x1 bottom in displayed PDF points")
            scale = args.dpi / 72
            with Image.open(staged) as image:
                px = (int(x0 * scale), int(y0 * scale), min(image.width, round(x1 * scale)),
                      min(image.height, round(y1 * scale)))
                if px[0] >= px[2] or px[1] >= px[3]:
                    raise ValueError("Crop lies outside the rendered page")
                cropped = image.crop(px)
            cropped.save(staged)
        staged.replace(out)
    say({"status": "rendered", "pdf": str(args.pdf.resolve()), "page": args.page, "dpi": args.dpi,
         "bbox_pt": args.bbox, "renderer": engine, "image": str(out)})
    return 0


def positive(value: str) -> int:
    integer = int(value)
    if integer <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return integer


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("extract", help="recover reading order and evidence files")
    run.add_argument("pdf", type=Path)
    run.add_argument("--out", required=True, type=Path)
    run.add_argument("--case-id")
    run.add_argument("--pages", help="physical pages, for example 1-3,8")
    run.add_argument("--backend", choices=("auto", *BACKENDS), default="auto")
    run.add_argument("--timeout", type=positive, default=55, help="subprocess extraction timeout")
    run.add_argument("--ocr", choices=("auto", "off", "all"), default="auto")
    run.add_argument("--ocr-lang", default="eng")
    run.add_argument("--ocr-limit", type=int, default=5)
    run.add_argument("--ocr-timeout", type=positive, default=10, help="timeout per OCR or render subprocess")
    run.set_defaults(handler=parse)

    search = sub.add_parser("find", help="search block text and report page and block anchors")
    search.add_argument("index", type=Path)
    search.add_argument("query")
    search.add_argument("--regex", action="store_true")
    search.add_argument("--kind")
    search.add_argument("--pages")
    search.add_argument("--limit", type=positive, default=12)
    search.set_defaults(handler=find)

    inspect = sub.add_parser("show", help="read a specific page or block")
    inspect.add_argument("index", type=Path)
    target = inspect.add_mutually_exclusive_group(required=True)
    target.add_argument("--page", type=positive)
    target.add_argument("--block")
    inspect.add_argument("--words", action="store_true")
    inspect.set_defaults(handler=show)

    image = sub.add_parser("render", help="render a physical page or rectangular area to PNG")
    image.add_argument("pdf", type=Path)
    image.add_argument("--page", required=True, type=positive)
    image.add_argument("--dpi", type=positive, default=160)
    image.add_argument("--out", required=True, type=Path)
    image.add_argument("--bbox", type=float, nargs=4, metavar=("X0", "TOP", "X1", "BOTTOM"))
    image.add_argument("--timeout", type=positive, default=20)
    image.set_defaults(handler=render)

    args = parser.parse_args()
    if getattr(args, "ocr_limit", 0) < 0:
        parser.error("--ocr-limit must be nonnegative")
    try:
        return args.handler(args)
    except (OSError, ValueError, re.error, KeyError, BackendError, ImportError) as exc:
        say({"status": "failed", "error": getattr(exc, "code", type(exc).__name__), "detail": str(exc)})
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
