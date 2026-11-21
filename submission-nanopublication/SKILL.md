---
name: evidence-bound-nanopublications
description: Extract atomic, source-grounded scientific claims and bind each to precise evidence and provenance. Use when a task asks for nanopublications, claim-level knowledge units, evidence-linked assertions, or RDF export; follow the task's output contract and do not label custom JSON as standard nanopublication RDF.
---

# Evidence-bound nanopublications

Create small, independently checkable scientific claims whose evidence and source history can be followed back to the supplied material. The task and actual source files are authoritative. This skill gives a workflow and vocabulary; it contains no answers to the platform's fixed cases.

## 1. Inspect the task and source

1. Read `/input/task.md` and `/input/case.json`. Extract the requested claim scope, required fields, serialization format, and every field/type in `output_contract`. Inspect `environment/resources.yaml`; resolve bundled files relative to it. Do not infer scientific facts from filenames, abstracts in metadata, or challenge labels.
2. Inventory the actual source artifacts. Read the original paper/document. For PDF text, retain the PDF page index and printed page label separately when they differ. Inspect rendered pages for evidence that depends on a figure, table, equation, layout, or uncertain OCR. If the source cannot be read, report that limitation instead of substituting another source.
3. Record source metadata only when present or verified: title, authors, publication year, DOI/other identifier, version, URL, and source-file identifier. Mark unknown fields as not reported/unknown using the task's allowed representation.

## 2. Extract atomic claims

Represent one independently assessable proposition per claim. Split conjunctions, lists of findings, and mixed result-plus-interpretation statements when the parts can be judged separately. Keep inseparable conditions attached to the claim. Preserve:

- the original subject and relation direction;
- polarity, modality, uncertainty, comparison, population, time scope, and boundary conditions;
- quantities, units, signs, variable names, and statistical qualifiers;
- whether the statement is an author-reported result, an author interpretation, or an extractor-derived normalization.

Prefer a short faithful statement over a broad paraphrase. Do not turn correlation into causation, a subgroup result into a general result, or an author's hypothesis into a finding. Keep the original-language wording or a faithful quotation when useful. If normalizing to subject–predicate–object form would lose meaning, preserve the claim as text and mark the structured relation as unavailable rather than inventing one.

## 3. Bind the smallest sufficient evidence

For each claim, identify the smallest source passage that still supports it. Store an exact excerpt when the output format allows it and a precise locator, for example:

- `PDF p. 6 (printed p. 5), §3.2, paragraph 2, sentence 1`;
- `Figure 2 caption, PDF p. 7`;
- `Table 1, row “Treatment”, column “Mean change”`;
- `Equation (4), PDF p. 8`.

Define paragraph/sentence numbering locally if the source does not number them. Verify quotations against the source text; check the page rendering when OCR, symbols, columns, or table cells are uncertain. Do not cite an entire paper as evidence for a specific claim. Distinguish evidence relations such as `supports`, `contradicts`, and `qualifies`; do not mark an indirect inference as direct support. If evidence is insufficient or conflicting, retain the claim as unresolved/qualified per the contract and say why.

Confidence must have an inspectable basis, such as direct textual support, clear structured value, indirect inference, OCR uncertainty, or conflicting passages. Do not invent calibrated probabilities or imply independent scientific replication.

## 4. Build provenance and serialize honestly

When the task requests a standard Nanopublication, serialize RDF in TriG using the four named graphs described by the Nanopublication Guidelines:

1. **Head graph:** one nanopublication type declaration and links to exactly one assertion, provenance, and publication-info graph.
2. **Assertion graph:** the atomic claim, expressed as RDF triples when the entities and relation can be mapped faithfully; otherwise preserve a literal claim plus the supported structured fields required by the task.
3. **Provenance graph:** link the assertion graph to its source and record the evidence excerpt, locator, evidence relation, and extraction/derivation agent or method when known.
4. **Publication-info graph:** metadata about this nanopublication, such as the actual creator and creation time when available.

Use distinct graph URIs. The provenance graph must refer to the assertion graph; publication info must refer to the nanopublication. Do not claim that custom JSON is TriG or a standard nanopublication. If the task requires JSON or another schema, use that exact schema and export TriG only as an additional artifact when requested or clearly allowed.

Do not mint a Trusty URI, checksum-based identifier, digital signature, ORCID, DOI, author, license, or timestamp unless it is actually available or computed by an appropriate tool. Use a clearly marked local identifier where a stable external identity is unavailable. Never imply that a nanopublication has been published to a network merely because it was serialized.

## 5. Respect the runtime contract

- `/input` is the source; `/app/work` is for intermediates; deliverables belong under `/app/output`.
- Preserve **all** original `output_contract` fields, types, and nesting in `/app/output/result.json`, and include the required `case_id`. Do not replace the platform schema with this skill's example or add unsupported required fields.
- Include requested claim records, source metadata, evidence and uncertainty. Report honest status and limits, and add a concise change/provenance record wherever the contract allows.
- A missing source, unreadable scan, unavailable OCR, claim without support, or source conflict must be reported distinctly. Mark `not reported` only after checking the relevant source scope; use `not checked`, `unclear`, or the contract's equivalent otherwise.
- Do not include prepared answers, benchmark results, or formal case outputs in the skill package. The platform supplies and evaluates its fixed cases.

## 6. Final review

Before returning, verify that:

1. Each claim is atomic enough to assess and retains its conditions, qualifiers, and direction.
2. Each key claim has a minimal, genuinely supporting excerpt and a usable source locator.
3. Claim text, subject/relation/object, evidence relation, and source metadata do not contradict one another.
4. Unknown, not reported, unreadable, conflicting, and inferred values are distinguished.
5. The serialization parses in the required format and preserves every output-contract field and `case_id`.
6. No external identifier, signature, publication status, or benchmark score has been fabricated.

If a claim spans prose and a figure/table, link every needed evidence fragment and state which part each fragment supports. If the visual cannot be inspected, do not assert its content from the caption alone.

For field meanings and controlled values, consult `references/field-dictionary.md`. For common compound-sentence and evidence-boundary patterns, consult `references/claim-patterns.jsonl`; its records are synthetic illustrations, not scientific findings or answers.
