# Evidence-linked Paper Notes — 阅读10｜文献总结与结构化笔记

Challenge: `product-arena-06-6d8cf72b`.

An Agent skill for turning research papers into chapter-aligned, reusable notes with claim-level evidence anchors. It focuses on the gap between a fluent one-paragraph summary and a note that preserves the paper's structure, conditions, limitations, and traceable sources.

## Files

- `SKILL.md` — the skill entry point and workflow.
- `examples/minimal-example.md` — a short synthetic illustration of the note style. It is not a result from any platform case.
- `GITHUB_URL.txt` — the public repository/folder link required by the challenge.

The skill uses the reading and file tools available in the target Agent runtime. It has no external package dependency and does not require a personal glossary, account, or manual pre-processing. It works with PDFs and other readable paper artifacts; visual/OCR capabilities depend on the evaluator's installed tools.

## Invocation

Install this directory as a skill, or pass it to the Agent as the requested skill directory. Give the Agent the challenge input directory containing `task.md`, `case.json`, and the supplied paper. The skill reads the actual source files and follows the task's output contract; the example is illustrative only.

At Harbor runtime, use `/input` as read-only source, `/app/work` for intermediates, and `/app/output` for deliverables. The actual task's `output_contract` controls the exact `result.json` schema; preserve all its fields and `case_id`.

## Method

1. Read task and case metadata, inspect the resource manifest, and inventory actual source artifacts.
2. Follow the paper's own section sequence and create atomic notes for the requested scope.
3. Attach precise page, section, paragraph/sentence, figure/table, or equation anchors to important claims.
4. Preserve qualifiers, data conditions, units, uncertainty, and the boundary between author claims and synthesis.
5. Mark unreported, unreadable, conflicting, or unverified information explicitly.
6. Check contract completeness and source alignment before returning.

## Scope and limitations

The skill structures and grounds notes; it does not guarantee OCR quality or independently validate the scientific truth of a paper. Scans, encrypted files, image-only figures, ambiguous reading order, or absent page labels may limit anchors. The Agent must report those limits instead of guessing. A note marked `not reported` means the relevant source scope was checked; otherwise use `not checked` or `unclear`.

The downloaded challenge package contains no datasets; the platform supplies the fixed original cases at evaluation time. No benchmark scores or fixed-case answers are included here.
