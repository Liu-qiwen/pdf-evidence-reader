#!/usr/bin/env python3
"""Create a small original PDF for the invocation example; no dependencies."""

import argparse
from pathlib import Path


def line(x, y, size, text):
    quoted = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return f"BT /F1 {size} Tf {x} {y} Td ({quoted}) Tj ET"


def demo(out):
    left = [
        "The left column starts the procedure.",
        "Read its notes from top to bottom.",
        "The sample has a deliberately short name.",
        "The listing finishes with this sentence.",
    ]
    right = [
        "The sample label is R-27.",
        "Record the label with this block ID.",
        "This row is a little lower than the left row.",
        "The right column ends at this sentence.",
    ]
    page1 = [
        line(55, 762, 8, "DEMONSTRATION NOTES"),
        line(109, 720, 22, "Reading order demonstration"),
        line(226, 691, 11, "M. Example, Demo Lab"),
        line(55, 660, 10, "Abstract: An original miniature PDF with a full-width title and two text columns."),
        line(55, 624, 12, "1 Setup"),
        line(322, 621, 12, "2 Observation"),
    ]
    for i, (a, b) in enumerate(zip(left, right)):
        page1.extend((line(322, 602 - i*14, 10, b), line(55, 605 - i*14, 10, a)))
    page1.extend([
        "0.6 G 55 419 498 109 re S 0 G",
        line(55, 400, 10, "Figure 1. This full-width caption marks the boundary between two reading bands in the example."),
        line(55, 369, 12, "3 Follow-up"),
        line(322, 366, 12, "4 Notes"),
    ])
    lower = [
        ("After the caption, read this lane first.", "Then resume in the right-hand lane."),
        ("The order remains stable within this lane.", "The two lanes are independent."),
        ("This sentence belongs to the follow-up.", "The lower band also ends on the right."),
    ]
    for i, (a, b) in enumerate(lower):
        page1.extend((line(322, 348 - i*14, 10, b), line(55, 351 - i*14, 10, a)))
    page1.extend([line(55, 92, 8, "* An example footnote retained on the first page."),
                  line(301, 25, 8, "17")])
    page2 = [
        line(55, 762, 8, "DEMONSTRATION NOTES"),
        line(55, 703, 12, "References"),
        line(55, 676, 10, "[1] Example, M. Demonstration notes."),
        line(301, 25, 8, "18"),
    ]
    pages = [page1, page2]
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>",
               b"<< /Type /Pages /Kids [4 0 R 6 0 R] /Count 2 >>",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    for i, commands in enumerate(pages):
        stream = ("\n".join(commands) + "\n").encode("ascii")
        content_id = 5 + 2*i
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {content_id} 0 R "
            "/Resources << /Font << /F1 3 0 R >> >> >>".encode("ascii")
        )
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"endstream")
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(data))
        data.extend(f"{i} 0 obj\n".encode("ascii") + obj + b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets[1:]:
        data.extend(f"{offset:010} 00000 n \n".encode("ascii"))
    data.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    demo(parser.parse_args().output)
