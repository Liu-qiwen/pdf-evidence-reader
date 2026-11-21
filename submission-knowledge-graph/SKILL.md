---
name: evidence-linked-literature-graph
description: Build an evidence-linked, queryable knowledge graph from one or more research papers. Use when a task asks to extract scientific entities and relations, align entities across papers, preserve source evidence, or run graph queries; keep paper-specific conditions and provenance separate and follow the task's output contract.
---

# Evidence-linked literature graph

Build a compact graph from the actual supplied papers, with every substantive node and edge traceable to its own source passage. The task, source files, and `output_contract` are authoritative. This skill describes a workflow, not a prepared graph or case answer.

## 1. Inspect the input package

1. Read `/input/task.md`, `/input/case.json`, and `environment/resources.yaml`. Resolve bundled paths relative to the resource manifest. Read the actual input files; do not rely on labels or metadata summaries as substitutes for the papers.
2. If `corpus-manifest.json` is present, use it to create a separate source record for each DOI, title, author list, license, version, and source hash. Do not propagate the root paper's DOI/title/authors to another paper. Cross-check with each paper's own front matter.
3. Treat `material.json` as an index only. Read `primary-material.json` and every separate paper file, including any publisher XML when needed to inspect linearized formulae. Use JATS `paragraph_id` anchors when supplied. If the package has no PDF, do not invent PDF page numbers; if no image/appendix/raw data is supplied, do not infer their contents.
4. Inventory the task's required entity types, relation types, queries, file formats, and all `output_contract` fields before constructing the graph.

## 2. Extract entities and evidence

Create nodes only for entities supported by the paper: for example, researchers, materials, methods, tasks/datasets, metrics, conditions, samples, and claims/results. Preserve the source's surface form and a cautious canonical label. Each substantive node needs one or more evidence records containing:

- `source_id`: the identifier of the specific paper that supports this occurrence;
- `paragraph_id`: the supplied JATS paragraph ID or the most precise available source locator;
- `quote`: a short exact passage from that source;
- optionally, the local role, section, or evidence note when required.

If no passage can be found, do not create a factual node; if the task requires a candidate, mark it unresolved and say why. Distinguish author-created work from a paper's citation or discussion of someone else's work.

## 3. Add conservative, directed relations

Use one directed edge per source-supported relation. Every substantive edge must carry its own source-specific evidence (`source_id`, `paragraph_id`, exact short quote), relation label, and qualifiers/conditions. Keep relationship direction faithful to the text. Distinguish at least:

- `uses` / `applies_to` / `measures` / `evaluates_on` for methods, tasks, materials, or metrics;
- `reports` / `supports` / `contradicts` / `qualifies` for claims and results;
- `compares_with` / `outperforms` only when the comparison and scope are explicit.

Do not turn co-occurrence, a citation, a hypothesis, or a cross-paper similarity into a direct scientific relation. Attach sample, model, dataset, metric, time, and experimental conditions to the edge or to linked condition nodes; do not merge findings with incompatible conditions. Record source-internal conflicts as separate, attributed edges or claims with a conflict marker rather than choosing a winner without evidence.

## 4. Align entities without collapsing distinct objects

Keep a paper-local entity identity distinct from a cross-paper concept alignment. Normalize capitalization, spelling, acronym, or full-name variants only when the source itself or strong contextual evidence establishes identity. Record each cross-paper decision as `same_entity`, `same_concept`, `related_but_distinct`, `candidate_unresolved`, or `conflict`, with a rationale and source-specific evidence.

String similarity or a shared generic label is only a candidate-generation clue. The same method/material term does not establish that two papers used the same physical sample, model instance, dataset, cohort, or experimental conditions. Do not force aliases to merge. Preserve separate paper-local IDs, and include non-merge/conflict decisions when they affect interpretation.

## 5. Run useful, evidence-returning queries

Select at least three distinct queries that answer the task's actual questions. Run them against the graph, not from memory. Queries should cover useful views such as:

1. entities and supported relations within each source;
2. methods/materials/tasks/metrics and the claims linked to them;
3. cross-source alignments, disagreements, or candidate comparisons, with comparability limits.

Use the bundled `scripts/query_graph.py` for deterministic basic queries over the JSON graph. It supports `nodes_by_type`, `edges_by_predicate`, `neighbors`, and `alignments_by_status`; see `references/query-workflow.md` for query syntax. Save each actual query, its result, and evidence anchors. An empty result is a valid result and should be reported as such. Do not claim a query was executed unless it was run against the generated graph.

## 6. Deliverables and runtime contract

- Preserve every original `output_contract` field, type, and nesting and include `case_id` in `/app/output/result.json`. Do not replace the platform schema with this skill's example schema.
- Put editable artifacts under `/app/output` and intermediates under `/app/work`. When allowed by the contract, write a machine-readable graph (JSON with `nodes`, `edges`, `sources`, `alignments`) and query records with actual results and evidence. Keep additional artifact names clear and stable.
- Each query result must retain source IDs, paragraph IDs, and short evidence quotations for substantive nodes/edges. Include entity merge/non-merge decisions and unresolved conflicts where applicable.
- Report status, coverage, source limitations, missing inputs, uncertainty, and change/provenance information in the contract's fields. The input revision may have no PDF pagination; use supplied JATS paragraph IDs and do not call them PDF page numbers.
- Do not fabricate source metadata, entities, relationships, scientific values, software state, benchmark scores, or query results. The platform provides the fixed cases and comparison; do not include prepared case answers in this skill package.

## 7. Review before returning

Check that every substantive node and edge has source-local evidence; IDs resolve; edge direction and qualifiers match the quotation; paper-specific DOI/author metadata remains separate; entity alignments have written evidence; comparisons do not blend different samples or conditions; and at least three queries were actually executed with their results. Mark unsupported, missing, conflicting, and non-comparable information explicitly rather than filling gaps from domain knowledge.
