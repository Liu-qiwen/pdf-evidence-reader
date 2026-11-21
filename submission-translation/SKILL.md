---
name: scholarly-translation-evidence
description: Translate scientific papers or specified passages into source-aligned bilingual text. Maintain a consistent glossary, segment coverage, and references, numbers, and formulae; attach source locators and flag uncertainty. Use for academic translation, not for summary-only requests.
---

# Scholarly Translation with Evidence

Translate only the scope and into the target language requested by the case. Produce a faithful, reviewable translation linked to its source. Do not replace translation with summary or silently repair incomplete source text.

## 1. Read the case contract

In the evaluation environment, read `/input/case.json`, the provided `task.md`, and the actual source files. Record `case_id`, requested source range, source and target languages, output files, and every original `output_contract` field. If `environment/resources.yaml` is present, resolve resources from its declared paths. Do not infer scientific facts from a case label or filename.

Preserve the required output contract exactly. Include its original fields and `case_id` in `/app/output/result.json`; use the contract's types, names, enumerations, and nesting. Put bilingual alignment, glossary, evidence, uncertainties, status, and change notes in the fields the contract provides. If it is strict and has no such fields, keep `result.json` contract-compliant and put permitted supporting material in a separate file under `/app/output`; link it only when the contract allows. Never substitute a demo translation for a fixed case.

## 2. Establish source units and evidence

Inspect the actual document before translating. Use the available PDF/text reader and render a page when extraction order, columns, a table, a caption, a footnote, or a formula is ambiguous. Preserve source order and the task's inclusion/exclusion boundary.

Create a coverage ledger before translating. Give each in-scope paragraph, heading, list item, caption, table header/cell, footnote, and requested reference entry a stable unit ID, for example `P0007.S02` for a sentence. Each unit retains its exact source text and a locator with source filename plus the strongest available anchors: physical PDF page, section heading, paragraph/sentence ID, table/figure/equation number, or source character range. Distinguish physical page from printed page when both are available.

For long documents, divide work at section and paragraph boundaries to fit the available context. Carry the approved glossary, current section, and a short adjacent-context note between chunks. Context overlap is for interpretation only; emit each source unit once. Mark every ledger unit translated, intentionally excluded by the task, partially readable, or blocked. Do not silently skip gaps.

## 3. Build and enforce the terminology ledger

Before the main pass, identify recurring domain terms, abbreviations, named methods, and terms whose translation affects scientific meaning. Record source form, preferred target form, concise context/definition, first source locator, and decision state (`provisional` or `locked`). Apply user-provided terminology first. Lock a choice after checking its context; use it consistently in title, abstract, body, captions, tables, and conclusion. Record justified context-specific alternatives explicitly rather than drifting silently. Expand an abbreviation at its first in-scope occurrence when the source does so; preserve the source abbreviation and capitalization thereafter.

## 4. Translate without changing scientific claims

Translate sentence by sentence within each source unit. Preserve:

- negation, modality, hedging, scope, comparison groups, conditions, causal and concessive links, and antecedents;
- all numerical values, signs, ranges, percentages, units, significant notation, variable names, subscripts/superscripts, Greek letters, and equation numbers;
- citation markers and figure/table/section references, keeping each marker adjacent to the claim it supports;
- paragraph, list, heading, caption, and table row/column relationships.

Use formal target-language prose without adding explanations as if they came from the source. Keep citations and bibliography entries unchanged unless the task explicitly requests their translation. For tables, translate headers and cells while keeping each cell associated with its original row and column. For formulas, preserve the expression and translate only surrounding prose unless asked otherwise.

When the source is damaged, ambiguous, or unreadable, preserve the readable span and mark the exact unit and location as partial or uncertain. Do not guess a missing word, number, term, or formula. Separate translator notes from translated text.

## 5. Verify coverage and meaning

Compare the coverage ledger with the requested source range. Check for missing, duplicated, reordered, or partially translated units. Scan the full target text against the locked terminology ledger. Compare source and target unit by unit for numbers, signs, units, abbreviations, citations, equation/figure/table references, negation, modality, and conditions. Recheck antecedents and causal/concessive relations against neighboring sentences. Use extraction checks as aids, not proof of semantic correctness. Record any unresolved items and what a human should inspect.

## 6. Write outputs and status

Create `/app/work` for temporary indexes and ledgers and `/app/output` for deliverables. Save a contract-compliant partial `result.json` early when translation is long, then update it as units are checked. Report the actual state as success, partial, indeterminate, or the contract's equivalent, with an honest reason. Preserve source locators, uncertainty, and material corrections. A translation is complete only for the declared scope; do not imply full-paper coverage when the task asked for or only supports an excerpt.

When the case does not impose a different structure, use a bilingual alignment table or JSON array with one record per source unit: `unit_id`, `kind`, exact `source_text`, `target_text`, `locator`, term decisions where relevant, and uncertainty/review notes. Keep glossary decisions and a concise verification summary. Follow the exact case contract whenever it differs.

## Limits and handoff

This skill guides translation and evidence alignment; it does not itself OCR or semantically decode an image-only formula. Use available installed tools and visually verify the affected region. If the file, pages, fonts, language data, or parsing tool are unavailable, state the observed limitation and affected scope, preserve completed units, and identify the precise manual handoff. Never fabricate source text, benchmark scores, or runtime state.
