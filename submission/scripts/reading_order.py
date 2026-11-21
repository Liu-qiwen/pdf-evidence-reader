"""Layout recovery with stable word evidence and non-destructive role hints."""

from __future__ import annotations

import bisect
import re
import statistics as stats
import unicodedata as ud
from collections import defaultdict
from dataclasses import dataclass

from pdf_backend import Box, Page, Word, suspect

CAPTION = re.compile(
    r"^\s*(fig(?:ure)?\.?|tab(?:le)?\.?|图|表)\s*[A-Z]?\s*[.．]?\s*"
    r"(?:\d+(?:[.-]\d+)*[a-z]?|[一二三四五六七八九十]+)(?![A-Za-z0-9])",
    re.I,
)
STANDARD_HEAD = re.compile(
    r"^(abstract|summary|keywords|introduction|background|related work|materials and methods|"
    r"methods|methodology|experimental setup|experiments?|results(?: and discussion)?|discussion|"
    r"conclusions?|limitations|references|bibliography|acknowledg(?:e)?ments?|supplementary material|"
    r"appendix(?: [A-Z0-9])?|摘要|关键词|引言|绪论|背景|相关工作|材料与方法|实验方法|方法|"
    r"实验|结果|讨论|结果与讨论|结论|致谢|参考文献|附录[ A-Z0-9]*)[.。]?$",
    re.I,
)
NUMBERED_HEAD = re.compile(r"^(?:\d+(?:\.\d+){0,4}[.)]?|[IVX]{1,6}\.)\s+(\D.{1,85})$")
REFERENCE_HEAD = re.compile(r"^(?:\d+(?:\.\d+)*\.?\s+)?(?:references|bibliography|参考文献)[.。]?$", re.I)
ABSTRACT_HEAD = re.compile(r"^\s*(?:abstract|摘要)(?:\s*[:：—–.-]|\s*$)", re.I)
PAGE_MARK = re.compile(r"(?:[-–—]\s*)?(?:p(?:age)?\.?\s*)?\d{1,5}(?:\s*[-–—])?", re.I)
LABEL_ONLY = re.compile(r"[(（]\d+(?:[.-]\d+)*[)）]$")
FOOTNOTE_START = re.compile(r"^(?:[*†‡§¶]|[⁰¹²³⁴⁵⁶⁷⁸⁹]+|\d{1,2}[.)]?\s+[A-Za-z\u3400-\u9fff])")


@dataclass
class Line:
    row: int
    ids: list[int]
    box: Box
    text: str

    @property
    def y(self) -> float:
        return (self.box[1] + self.box[3]) / 2

    @property
    def height(self) -> float:
        return self.box[3] - self.box[1]


def box_union(boxes: list[Box]) -> Box:
    return (
        min(b[0] for b in boxes), min(b[1] for b in boxes),
        max(b[2] for b in boxes), max(b[3] for b in boxes),
    )


def box_json(box: Box) -> list[float]:
    return [round(value, 2) for value in box]


def text_height(words: list[Word]) -> float:
    heights = sorted(w.box[3] - w.box[1] for w in words)
    middle = heights[len(heights)//5: (4*len(heights))//5 + 1]
    return max(3., stats.median(middle)) if middle else 10.


def compose(row: int, ids: list[int], words: list[Word]) -> Line:
    ids = sorted(ids, key=lambda k: (words[k].box[0], k))
    parts = [words[ids[0]].text]
    for prev, current in zip(ids, ids[1:]):
        before, after = words[prev], words[current]
        # PDF word boundaries are geometric. Avoid inserting spaces between adjacent CJK glyphs.
        near = after.box[0] - before.box[2] <= .25 * (after.box[3] - after.box[1])
        wide = ud.east_asian_width(before.text[-1]) in {"W", "F"}
        next_wide = ud.east_asian_width(after.text[0]) in {"W", "F"}
        parts.append(("" if near and wide and next_wide else " ") + after.text)
    return Line(row, ids, box_union([words[k].box for k in ids]), "".join(parts))


def geometric_lines(page: Page) -> tuple[list[Line], float]:
    words = page.words
    normal = text_height(words)
    grouped: list[tuple[float, float, list[int]]] = []
    by_height = sorted(range(len(words)), key=lambda k: (
        (words[k].box[1] + words[k].box[3]) / 2, words[k].box[0], k
    ))
    for k in by_height:
        _, y0, _, y1 = words[k].box
        y, height = (y0 + y1) / 2, y1 - y0
        for center, ref, ids in reversed(grouped[-4:]):
            if abs(y - center) <= max(1.6, .34 * min(height, ref, normal)):
                ids.append(k)
                break
        else:
            grouped.append((y, height, [k]))
    output = []
    gap = max(5.5, min(11., .90 * normal))
    for row, (_, _, ids) in enumerate(grouped, start=1):
        ids.sort(key=lambda k: (words[k].box[0], k))
        chunk = [ids[0]]
        edge = words[ids[0]].box[2]
        for k in ids[1:]:
            if words[k].box[0] - edge >= gap:
                output.append(compose(row, chunk, words))
                chunk = []
            chunk.append(k)
            edge = max(edge, words[k].box[2])
        output.append(compose(row, chunk, words))
    return output, normal


def side(line: Line, x: float, margin: float = 2.) -> int:
    if line.box[0] >= x - margin:
        return 1
    if line.box[2] <= x + margin:
        return -1
    return 0


def near_count(first: list[float], second: list[float], radius: float) -> int:
    second = sorted(second)
    count = 0
    for y in first:
        k = bisect.bisect_left(second, y - radius)
        count += k < len(second) and second[k] <= y + radius
    return count


def cut_evidence(lines: list[Line], x: float, anchor: float, normal: float, span: float):
    left = [line for line in lines if side(line, x) == -1]
    right = [line for line in lines if side(line, x) == 1]
    anchored = sum(abs(line.box[0] - anchor) <= max(4., .65 * normal) for line in right)
    if min(len(left), len(right)) < 3 or anchored < 3:
        return None
    if anchored < .35 * len(right):
        return None
    if any(max(line.box[2] - line.box[0] for line in lane) < .15 * span for lane in (left, right)):
        return None
    ly, ry = [line.y for line in left], [line.y for line in right]
    if min(max(ly) - min(ly), max(ry) - min(ry)) < 2 * normal:
        return None
    radius = max(9., 1.5 * normal)
    pairs = min(near_count(ly, ry, radius), near_count(ry, ly, radius))
    if pairs < max(3, .36 * min(len(left), len(right))):
        return None
    return {"x": round(x, 2), "left_fragments": len(left), "right_fragments": len(right),
            "aligned_fragments": pairs, "right_margin_repetitions": anchored}


def infer_cut(lines: list[Line], low: float, high: float, normal: float):
    span = high - low
    # Short numeric cells, equation labels and footnote markers cannot establish columns.
    prose = [line for line in lines
             if line.box[2] - line.box[0] >= max(14., .055 * span)
             and sum(c.isalpha() for c in line.text) >= 7]
    anchors: list[list[float]] = []
    for x in sorted(line.box[0] for line in prose if low + .17*span < line.box[0] < high - .14*span):
        if anchors and x - anchors[-1][0] <= max(4., .60 * normal):
            anchors[-1].append(x)
        else:
            anchors.append([x])
    best_score, best = 0., None
    for group in anchors:
        if len(group) < 3:
            continue
        anchor = stats.median(group)
        x = round(anchor - max(2.5, min(5., .38 * normal)), 2)
        crossing = {line.row for line in prose if side(line, x) == 0}
        runs: list[list[Line]] = [[]]
        last_bridge = None
        for line in prose:
            if line.row in crossing:
                if last_bridge != line.row and runs[-1]:
                    runs.append([])
                last_bridge = line.row
            else:
                runs[-1].append(line)
        samples = runs
        if 0 < len(crossing) <= max(2, .09 * len(prose)):
            samples = [*runs, [line for line in prose if line.row not in crossing]]
        for sample in samples:
            evidence = cut_evidence(sample, x, anchor, normal, span)
            if evidence:
                score = (evidence["aligned_fragments"] +
                         .32 * min(evidence["left_fragments"], evidence["right_fragments"]) +
                         .23 * evidence["right_margin_repetitions"])
                if score > best_score:
                    best_score, best = score, (evidence, score)
    return best


def infer_gutters(lines: list[Line], normal: float) -> list[dict]:
    if not lines:
        return []
    low = min(line.box[0] for line in lines)
    high = max(line.box[2] for line in lines)
    cut = infer_cut(lines, low, high, normal)
    if not cut:
        return []
    first, _ = cut
    x = first["x"]
    alternatives = [
        infer_cut([line for line in lines if side(line, x) == -1], low, x, normal),
        infer_cut([line for line in lines if side(line, x) == 1], x, high, normal),
    ]
    alternatives = [candidate for candidate in alternatives if candidate and candidate[1] >= 5.]
    if not alternatives:
        return [first]
    second, _ = max(alternatives, key=lambda pair: pair[1])
    return sorted([first, second], key=lambda item: item["x"])


def margin_zone(line: Line, page: Page) -> str | None:
    if line.box[3] <= .082 * page.height:
        return "header"
    if line.box[1] >= .918 * page.height:
        return "footer"
    return None


def page_edges(pages: list[Page], layouts: list[tuple[list[Line], float]]) -> list[dict[int, str]]:
    repeated = defaultdict(list)
    output: list[dict[int, str]] = [{} for _ in pages]
    for i, (page, (lines, _)) in enumerate(zip(pages, layouts)):
        for j, line in enumerate(lines):
            zone = margin_zone(line, page)
            if not zone:
                continue
            text = " ".join(line.text.casefold().split())
            if PAGE_MARK.fullmatch(text):
                center = (line.box[0] + line.box[2]) / 2
                if abs(center - .5*page.width) < .09*page.width or center >= .83*page.width:
                    output[i][j] = "page_number_candidate"
            elif len(text) >= 4 and not (ABSTRACT_HEAD.match(text) or STANDARD_HEAD.fullmatch(text)
                                         or CAPTION.match(text)):
                signature = re.sub(r"\s+(?:[|·•]\s*|page\s+)\d{1,5}$", "", text)
                repeated[(zone, signature)].append((i, j, line.y / page.height, line.height))
    for (zone, _), members in repeated.items():
        for i, j, y, height in members:
            matched = any(i != k and abs(y - other_y) <= .018 and abs(height - h) <= .25 * max(height, h)
                          for k, _, other_y, h in members)
            if matched:
                output[i][j] = f"running_{zone}_candidate"
    return output


def fragments_by_row(lines: list[Line]):
    rows = defaultdict(list)
    for line in lines:
        rows[line.row].append(line)
    return rows


def image_breaks(rows: list[list[Line]], cuts: list[float], page: Page, normal: float) -> dict[int, Box]:
    boundaries = {}
    if not cuts:
        return boundaries
    for image in page.images:
        x0, top, x1, bottom = image
        if (x1-x0 < .50*page.width or bottom-top > .78*page.height or
                not (x0 + 10 < cuts[0] <= cuts[-1] < x1 - 10)):
            continue
        before = any(max(line.box[3] for line in row) <= top + 2 for row in rows)
        following = next((row for row in rows if min(line.box[1] for line in row) >= bottom - 2), None)
        if before and following:
            boundaries[following[0].row] = image
    return boundaries


def caption_breaks(rows: list[list[Line]], cuts: list[float], crossing: set[int],
                   images: dict[int, Box], normal: float) -> tuple[set[int], set[int]]:
    image_captions, gap_captions = set(), set()
    if not cuts:
        return image_captions, gap_captions
    for i, row in enumerate(rows):
        if len(row) != 1 or row[0].row in crossing or not CAPTION.match(row[0].text):
            continue
        line = row[0]
        if line.row in images and line.box[1] - images[line.row][3] <= 2.5 * normal:
            image_captions.add(line.row)
            continue
        if not 0 < i < len(rows) - 1:
            continue
        gap = line.box[1] - max(previous.box[3] for previous in rows[i - 1])
        if gap < max(28., 3.5 * normal):
            continue
        # A short caption after page-wide whitespace is a weak bridge unless both
        # neighboring bands contain text in every inferred column.
        lane_sets = [{
            bisect.bisect_right(cuts, (item.box[0] + item.box[2]) / 2)
            for nearby in window if nearby[0].row not in crossing for item in nearby
            if sum(c.isalpha() for c in item.text) >= 7
        } for window in (rows[max(0, i-6):i], rows[i+1:i+7])]
        if all(len(lanes) == len(cuts) + 1 for lanes in lane_sets):
            gap_captions.add(line.row)
    return image_captions, gap_captions


def reading_groups(body: list[Line], gutters: list[dict], page: Page, normal: float):
    cuts = [item["x"] for item in gutters]
    crossing = {line.row for line in body if any(side(line, x, 3.) == 0 for x in cuts)}
    rows = list(fragments_by_row(body).values())
    images = image_breaks(rows, cuts, page, normal)
    image_captions, gap_captions = caption_breaks(rows, cuts, crossing, images, normal)
    bridge_rows = crossing | image_captions | gap_captions
    groups = []
    band = []
    for fragments in rows:
        row = fragments[0].row
        if (row in bridge_rows or row in images) and band:
            groups.append((False, band))
            band = []
        if row in bridge_rows:
            groups.append((True, fragments))
        else:
            band.extend(fragments)
    if band:
        groups.append((False, band))

    result = []
    for is_bridge, lines in groups:
        lanes = defaultdict(lambda: defaultdict(list))
        for line in lines:
            center = (line.box[0] + line.box[2]) / 2
            lane = None if is_bridge else bisect.bisect_right(cuts, center) + 1
            lanes[lane][line.row].extend(line.ids)
        for lane, rows in sorted(lanes.items()):
            result.append((lane, [compose(row, ids, page.words) for row, ids in sorted(rows.items())]))
    return result, {
        "crossing_rows": sorted(crossing),
        "raster_breaks": [{"row": row, "image_bbox": box_json(bbox)} for row, bbox in images.items()],
        "inferred_caption_rows": sorted(gap_captions),
    }


def line_role(line: Line, page: Page, normal: float, first_abstract: Line | None,
              title: set[int], in_references: bool) -> tuple[str, int | None]:
    text = line.text.strip()
    match = CAPTION.match(text)
    if match:
        label = match[1].casefold()
        return ("table_caption_candidate" if label.startswith("tab") or label == "表"
                else "figure_caption_candidate"), None
    if ABSTRACT_HEAD.match(text):
        bare = bool(re.fullmatch(r"(?:abstract|摘要)[.。:]?", text, re.I))
        return ("heading_candidate", 1) if bare else ("abstract_candidate", None)
    if line.row in title:
        return "title_candidate", None
    if first_abstract and line.y < first_abstract.y and line.box[1] >= .055*page.height:
        return "front_matter_candidate", None
    if STANDARD_HEAD.fullmatch(text) or REFERENCE_HEAD.fullmatch(text):
        return "heading_candidate", 1
    if line.box[1] >= .78*page.height and line.height <= .90*normal and FOOTNOTE_START.match(text):
        return "footnote_candidate", None
    numbered = NUMBERED_HEAD.fullmatch(text)
    if numbered and not in_references and not text.endswith((".", "?", "。", "？")):
        label = text.split()[0].rstrip(".)")
        return "heading_candidate", 1 + label.count(".")
    if LABEL_ONLY.search(text) and (LABEL_ONLY.fullmatch(text) or re.search(r"[=∑∫√≤≥≈±∂]", text)):
        return "equation_candidate", None
    xs = [page.words[k].box for k in line.ids]
    gaps = sum(right[0] - left[2] >= max(9., 1.1 * normal) for left, right in zip(xs, xs[1:]))
    if gaps >= 2 and sum(c.isdigit() for c in text) >= 2:
        return "table_row_candidate", None
    return ("reference_candidate" if in_references else "paragraph"), None


def new_block(previous: Line, line: Line, normal: float, role: str) -> bool:
    if role in {"heading_candidate", "equation_candidate", "table_row_candidate"}:
        return True
    if line.y - previous.y > max(1.65 * normal, 1.45 * max(previous.height, line.height)):
        return True
    if role == "reference_candidate" and re.match(r"^\s*(?:\[\d+\]|\d+[.)])\s+", line.text):
        return True
    if role in {"figure_caption_candidate", "table_caption_candidate", "footnote_candidate",
                "title_candidate", "front_matter_candidate", "abstract_candidate"}:
        return False
    indentation = line.box[0] - previous.box[0]
    return indentation > max(7., .75 * normal) and previous.text.rstrip().endswith((".", "。", ")", "”"))


def page_layout(page: Page, fragments: list[Line], normal: float, edge: dict[int, str],
                in_references: bool, raw_only: bool = False) -> tuple[dict, bool]:
    body = [line for i, line in enumerate(fragments) if i not in edge]
    gutters = infer_gutters(body, normal)
    groups, boundaries = reading_groups(body, gutters, page, normal)
    first_abstract = next((line for _, lines in groups for line in lines
                           if page.number == 1 and ABSTRACT_HEAD.match(line.text)
                           and line.box[1] <= .60 * page.height), None)
    title = set()
    if page.number == 1:
        top = first_abstract.y if first_abstract else .26 * page.height
        candidates = [line for _, lines in groups for line in lines if
                      .055 * page.height <= line.y < top and line.height >= 1.24 * normal]
        if candidates:
            largest = max(line.height for line in candidates)
            title = {line.row for line in candidates if line.height >= .91 * largest}

    blocks = []
    for lane, lines in groups:
        current = None
        caption_kind = None
        for line in lines:
            role, level = line_role(line, page, normal, first_abstract, title, in_references)
            if role == "heading_candidate":
                in_references = bool(REFERENCE_HEAD.fullmatch(line.text)) or (
                    in_references and not STANDARD_HEAD.fullmatch(line.text))
            if current and caption_kind and role == "paragraph":
                last = current[3][-1]
                if (0 < line.y - last.y <= 1.4 * normal and
                        abs(line.height - last.height) <= .18 * max(line.height, last.height)
                        and abs(line.box[0] - last.box[0]) < 2.1 * normal):
                    role = caption_kind
            if (not current or role != current[0] or new_block(current[3][-1], line, normal, role)
                    or CAPTION.match(line.text)):
                current = (role, lane, level, [line])
                blocks.append(current)
            else:
                current[3].append(line)
            caption_kind = role if role in {"table_caption_candidate", "figure_caption_candidate",
                                            "footnote_candidate"} else None
    if blocks:
        body_bottom = max((line.box[3] for kind, _, _, lines in blocks if kind != "footnote_candidate"
                           for line in lines), default=0.)
        bottom_notes = [block for block in blocks
                        if block[0] == "footnote_candidate" and block[3][0].box[1] >= body_bottom]
        if bottom_notes:
            blocks = [block for block in blocks if block not in bottom_notes] + bottom_notes
    blocks.extend((role, None, None, [fragments[i]]) for i, role in edge.items())
    blocks_out = []
    seen = []
    for j, (kind, lane, level, lines) in enumerate(blocks, start=1):
        block_id = f"P{page.number:04d}-B{j:03d}"
        block = {
            "id": block_id, "kind": kind, "column": lane,
            "bbox": box_json(box_union([line.box for line in lines])),
            "text": "\n".join(line.text for line in lines),
            "lines": [{"geometric_row": line.row, "bbox": box_json(line.box),
                       "word_ids": [k + 1 for k in line.ids], "text": line.text} for line in lines],
        }
        if level is not None:
            block["level_candidate"] = level
        blocks_out.append(block)
        seen.extend(k for line in lines for k in line.ids)
    if not raw_only and sorted(seen) != list(range(len(page.words))):
        raise ValueError("Layout lost or duplicated one or more extracted word IDs")

    flags = list(page.flags)
    if any(suspect(word.text) for word in page.words):
        flags.append("glyph_mapping_review")
    if any(word.confidence is not None and word.confidence < 60. for word in page.words):
        flags.append("low_confidence_ocr_words")
    if any(ud.bidirectional(c) in {"R", "AL"} for word in page.words for c in word.text):
        flags.append("bidirectional_text_review")
    if boundaries["inferred_caption_rows"]:
        flags.append("inferred_caption_band_review")
    if not gutters and sum(len(parts) >= 2 for parts in fragments_by_row(body).values()) >= 4:
        flags.append("check_rows_with_wide_internal_gaps")
    tall = sum(word.box[3] - word.box[1] > 3 * normal for word in page.words)
    if tall > max(3, len(page.words) * .04):
        flags.append("rotated_or_vertical_text_review")

    return {
        "page": page.number, "pdf_page_label": page.label,
        "width_pt": round(page.width, 2), "height_pt": round(page.height, 2),
        "backend": page.backend, "flags": flags,
        "layout": {"method": "gutter-bands" if gutters else "geometric-rows",
                   "gutters": gutters, **boundaries,
                   "geometric_rows": [{"row": line.row, "bbox": box_json(line.box),
                                       "word_ids": [k + 1 for k in line.ids]} for line in fragments]},
        "image_regions": [box_json(box) for box in page.images],
        "blocks": blocks_out,
        "words_in_backend_order": word_records(page.words),
        **({"extraction_error": page.error} if page.error else {}),
    }, in_references


def word_records(words: list[Word]) -> list[dict]:
    return [{"id": i, "text": word.text, "bbox": box_json(word.box),
             **({"source_line": word.source_line} if word.source_line is not None else {}),
             **({"confidence": round(word.confidence, 2)} if word.confidence is not None else {})}
            for i, word in enumerate(words, start=1)]
