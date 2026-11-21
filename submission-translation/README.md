# Scholarly Translation with Evidence

Target challenge: `product-arena-01-5a9928c1` — `阅读03｜文献翻译`. The downloaded challenge package contains the prompt/configuration but no case datasets; the fixed original cases are supplied to the evaluator at runtime. Challenge metadata marks scoring as human-review-only, so this package makes no score or turnaround-time claims.

This Skill turns a specified scientific-paper range into a faithful, reviewable translation. Its focus is paragraph/sentence alignment, consistent technical terminology, and preservation of scientific relations and source locators. It does not provide prewritten answers for the platform's fixed cases.

## Contents

- `SKILL.md` — agent instructions and Harbor runtime workflow.
- `scripts/check_alignment.py` — optional structural checker for an alignment sidecar; it does not judge translation quality.
- `examples/minimal-example.md` — synthetic invocation and illustrative output, not a formal case result.
- `GITHUB_URL.txt` — intended public repository and file path; the work must be pushed before this location is publicly verifiable.

## Invocation

Install this folder as a Skill so its `SKILL.md` is discoverable. In the Playground Harbor runtime, the evaluator installs it at `/skills/weekly-skill`. The agent must read `/input/case.json`, the provided `task.md`, and the actual source file before acting. It should create temporary files under `/app/work` and deliver the original `output_contract` fields plus `case_id` in `/app/output/result.json`.

The target language and translation range come from the case. When no output schema is imposed, a bilingual unit list is a useful default. A unit should keep its stable ID, exact source, translation, and locator. A glossary entry should record source term, chosen translation, context, decision status, and evidence location. Do not force this default onto a strict case schema.

## Method

1. Read task boundaries and contract; inspect the real file and preserve reading order.
2. Segment the requested source into stable paragraph/sentence units and make a coverage ledger with page, section, block, or table/caption locators.
3. Establish a context-aware glossary and lock preferred translations before translating the full range.
4. Translate each source unit once, carrying approved terms and local context across long-document chunks.
5. Compare source and target for meaning, qualifiers, negation, numbers, units, references, formulas, and coverage; mark unclear source spans instead of guessing.
6. Write contract-compliant outputs and report genuine partial completion, uncertainty, and corrections.

## Optional alignment checker

Python 3.10+ standard library only. Run:

```sh
python3 scripts/check_alignment.py path/to/alignment.json
```

The checker expects a JSON object with a `segments` array. Each segment has `id`, `source_text`, `target_text`, and a `locator` object containing a non-empty `file` and at least one additional locator field such as `page`, `section`, `paragraph_id`, or `table_id`. It rejects duplicate IDs and empty source/target text. Optional `status: "untranslated"` units may omit `target_text` only when they include a non-empty `reason`. It checks structure and traceability only; an agent or reviewer must still assess translation accuracy, terminology, and claim preservation.

Use this sidecar only when the case contract permits it. The platform's `result.json` contract takes priority.

## Minimal example

See [examples/minimal-example.md](examples/minimal-example.md). Its sentence is synthetic and demonstrates the interface only; it is not from a platform case and must not be presented as a benchmark result.

## Dependencies and limits

The Skill itself requires no network service or external translation API. The optional checker requires Python 3.10 or newer and only Python's standard library. PDF reading/rendering depends on tools already available in the agent's evaluation image; the Skill does not bundle OCR, licensed fonts, or a PDF parser. If a page is image-only or extraction is ambiguous, use available rendering/OCR tools and mark unverified spans for human review.

No formal fixed-case outputs, baseline scores, speed claims, or evaluation results are included in this package. The platform supplies and runs the three cases and comparison conditions.
