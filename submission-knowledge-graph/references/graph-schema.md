# Evidence graph schema

This is the default graph representation for this skill. A task's `output_contract` takes precedence; map these concepts to its required schema without dropping provenance.

## Top-level JSON object

| Key | Type | Meaning |
|---|---|---|
| `schema_version` | string | Version of this local representation, e.g. `evidence-graph/v1`. |
| `sources` | array | One record per actual paper/source artifact. |
| `nodes` | array | Paper-local entities, claims, conditions, and other task-relevant objects. |
| `edges` | array | Directed, typed, evidence-backed relations. |
| `alignments` | array | Cross-paper identity/concept decisions, including non-merges and unresolved candidates. |
| `queries` | array | Actual query specifications, results, and evidence references when the task permits. |
| `uncertainties` | array | Missing, unreadable, conflicting, or non-comparable information. |

## Source record

Each source record should include the actual `source_id`, DOI when present, title, authors, publication year, version, license, and source-file hash from the manifest or source package. Preserve unknowns as unknown. Do not copy metadata from one paper to another merely because it is the root record.

## Node record

Recommended fields: `id`, `type`, `label`, `canonical_label` (only if justified), `surface_forms`, `source_ids`, `evidence`, and optional `attributes`/`status`.

Every substantive node has at least one evidence object:

```json
{
  "source_id": "the specific paper ID",
  "paragraph_id": "JATS paragraph ID or supplied locator",
  "quote": "short exact source text",
  "role": "defines|mentions|reports|describes"
}
```

Keep paper-specific model instances, samples, datasets, cohorts, and experimental materials as distinct nodes unless evidence explicitly establishes identity.

## Edge record

Recommended fields: `id`, `subject`, `predicate`, `object`, `source_id`, `qualifiers`, `evidence`, and optional `evidence_relation`/`status`.

Every substantive edge has source-local evidence with `source_id`, `paragraph_id`, and an exact short `quote`. Preserve relation direction, scope, polarity, comparison, and conditions. Use separate edges for different papers or different conditions. A cross-paper alignment is not a scientific result edge.

## Alignment record

Use one of `same_entity`, `same_concept`, `related_but_distinct`, `candidate_unresolved`, or `conflict`. Include the local node IDs, rationale, evidence from each relevant source, and the decision author/recorded time only if known. Label-based string similarity alone is not sufficient evidence to merge.

## Query record

Record `query_id`, human-readable question, executable query specification, actual result node/edge IDs, evidence references, and an empty-result or comparability note when relevant. Never populate results before executing the query against the graph.
