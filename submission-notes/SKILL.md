---
name: evidence-linked-paper-notes
description: Create chapter-aligned, source-linked structured notes from research papers. Use when a task asks to summarize a paper, build a paper card, extract reusable knowledge points, or preserve evidence and limitations; do not replace a task-specific output contract with this skill's example format.
---

# Evidence-linked paper notes

Turn the actual supplied paper and task into compact, reusable notes that follow the paper's structure and let a reader verify each important statement. The task instructions and the original paper are authoritative. This skill supplies a method, not prepared answers.

## Start from the actual inputs

1. Read `/input/task.md` and `/input/case.json`. Identify the requested operation, source files, constraints, and every field/type required by `output_contract`. Inspect `environment/resources.yaml` and resolve bundled paths relative to that file. Do not infer document contents from filenames or challenge labels.
2. Open and read the actual source artifact. For PDFs, use the available text layer first and inspect page renderings where extraction is incomplete, reading order is suspect, or a claim depends on a figure, table, or equation. If text is absent or garbled, use available OCR and label uncertain readings; never silently repair scientific content.
3. Inventory the paper's title, abstract, section hierarchy, figures, tables, equations, references, and visible page numbering. Keep printed page numbers distinct from PDF viewer page indices when they differ.
4. Follow the task's requested scope. If it requests only selected sections or questions, do not imply that the whole paper was reviewed.

## Build notes that retain the argument

Follow the source's actual section order and names. Do not force a generic abstract template onto a paper whose structure or argument differs. Within the requested scope, extract only fields supported by the source:

- **Research question and motivation:** what the authors ask and why, including stated hypotheses or aims.
- **Data and setting:** source, sample/material, time or spatial scope, inclusion criteria, and sample size when reported.
- **Methods and conditions:** design, instruments, model or algorithm, variables, comparison, parameter/settings, and assumptions needed to interpret the result.
- **Findings:** the paper's reported observations or estimates, with exact quantities, units, uncertainty/statistics, and conditions where available.
- **Authors' interpretation and conclusion:** distinguish reported results from the authors' explanation or broader claim.
- **Limitations and boundary conditions:** author-stated limitations, explicit scope restrictions, and unresolved questions. Do not turn an omitted detail into a limitation unless the task asks for a critical appraisal; label that as an observation.
- **Reusable knowledge points:** atomic concepts, methods, assumptions, findings, or definitions. Merge duplicate phrasing only when it has the same meaning and evidence; retain disagreements as separate, attributed claims.

Keep key qualifiers attached to claims: negation, uncertainty, comparison group, causal versus correlational wording, subgroup, time range, units, and boundary conditions. Do not strengthen a claim while shortening it. Label a synthesis or inference as such and link all source statements it combines.

## Evidence anchors

Give each important note a stable local ID and one or more source anchors. Prefer the most precise locator the source supports:

`PDF p. 4 (printed p. 3), §2.1, paragraph 2, sentence 1`  
`Figure 2 caption` · `Table 1, row “Control”, column “Mean”` · `Equation (3)`

Use paragraph/sentence ordinals created during this run when the source has no stable paragraph numbering. State the numbering convention once (for example, paragraphs counted within each section in reading order). Include a short source excerpt or value only when it helps disambiguate the anchor; preserve symbols and do not present a paraphrase as a quotation. For figures, tables, and equations, record the identifier and caption/row/column or equation number; do not claim scientific meaning from a visual element that was not actually inspected.

If two source locations conflict, record both, describe the conflict, and leave resolution open unless the paper resolves it. If a location cannot be established, say so and lower the completion status rather than inventing a page or section.

## Output and contract handling

- The official task and `output_contract` take precedence over the example below. Preserve every required contract field, its required type and nesting, and the required `case_id` in `/app/output/result.json`. Do not rename, omit, or replace contract fields with this skill's preferred labels. Populate only supported values; represent absent, not reported, unclear, or conflicting information as the contract permits.
- Put editable artifacts under `/app/output`; use `/app/work` for intermediate files. Do not include prepared answers for the platform's fixed cases in the submitted Skill package.
- Return a status such as `success`, `partial`, or `unable_to_determine` only if compatible with the contract. Explain partial coverage, missing source material, OCR uncertainty, or unresolved conflict in the contract's uncertainty/notes fields.
- Include source identifiers, evidence anchors, uncertainty, and a concise change/provenance record wherever the contract allows. If the contract has no such field, preserve the contract exactly and put supporting detail in an additional clearly named artifact only when allowed.
- Do not invent a study result, sample size, method setting, citation, software state, benchmark, or evaluation score. Mark it `not reported` only after checking the relevant source scope; otherwise use `not checked` or `unclear`.

## Review before returning

Check the notes against the source and task:

1. Every requested section/field is present, or explicitly marked missing/not reported/uncertain.
2. Every central claim has an anchor that points to the statement supporting it; anchors are not merely broad citations to the whole paper.
3. Numbers, signs, units, variable names, sample sizes, figure/table/equation identifiers, and reference markers match the source.
4. Conclusions retain their population, comparison, assumptions, and uncertainty; association is not rewritten as causation.
5. The note sequence follows the paper's structure, and no section is represented as covered if it was not read.
6. `result.json` is valid JSON and retains all original `output_contract` fields plus `case_id`.

When an input is encrypted, missing, unreadable, scan-only without an available OCR path, or incomplete, report the specific failure and the last source location that could be checked. Do not fill gaps from domain knowledge or another paper unless the task explicitly authorizes external sources.
