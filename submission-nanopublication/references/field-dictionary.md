# Claim and evidence field dictionary

This is a reusable field guide. It does not override a challenge's `output_contract`.

## Claim record

| Field | Meaning | Rule |
|---|---|---|
| `claim_id` | Local identifier for one claim | Stable within the output; do not pretend it is a DOI or Trusty URI. |
| `claim_text` | Faithful, independently assessable proposition | Preserve polarity, modality, population, conditions, scope, quantities, and units. |
| `claim_kind` | `author_result`, `author_interpretation`, `author_hypothesis`, `definition`, or `extractor_inference` | Use the closest supported type; explain a custom type if needed. |
| `subject` | Main entity the claim is about | Use a source-defined or resolvable entity where available; otherwise retain text. |
| `predicate` | Relation asserted about the subject | Use a controlled ontology term only when its meaning fits; never guess a relation. |
| `object` | Entity/value related to the subject | Preserve literal values and units when no suitable entity URI exists. |
| `qualifiers` | Conditions and context needed to interpret the claim | Include comparator, subgroup, time, setting, method, statistical qualifier, and limitations as applicable. |
| `source_id` | Paper or source artifact identifier | DOI/URI only if verified; otherwise a local source key. |
| `evidence_ids` | Evidence records supporting, qualifying, or contradicting the claim | Every central claim should link to at least one relevant record or be marked unsupported/unresolved. |

## Evidence record

| Field | Meaning | Rule |
|---|---|---|
| `evidence_id` | Local evidence identifier | Unique within the result. |
| `relation` | `supports`, `contradicts`, `qualifies`, or `mentions` | Describe the actual relation between passage and claim. |
| `excerpt` | Exact source text/value when available | Do not silently normalize OCR, punctuation, numbers, or symbols inside a quotation. |
| `locator` | Source position | Use PDF page index and printed page when different, section/paragraph/sentence, or figure/table/equation and cell/panel. |
| `evidence_mode` | `direct_text`, `table_cell`, `figure_visual`, `equation`, `ocr_uncertain`, or a justified extension | Distinguish direct text from visual reading and inference. |
| `note` | Context needed to assess sufficiency or uncertainty | Explain partial support, contradiction, visual limits, or OCR concerns. |

## Provenance and uncertainty

- **Source provenance:** actual title, authors, venue/year, DOI or other identifier, version, URL, and local artifact key when available.
- **Claim provenance:** source passage(s), extraction method/agent when known, and whether the claim is quoted, normalized, or inferred.
- **Publication provenance:** actual creator and creation time only when known; do not invent personal identifiers or digital signatures.
- **Uncertainty:** separate `not_reported` (searched the relevant source scope), `not_checked`, `unreadable`, `conflicting`, and `inferred` where the output schema permits.
- **Confidence basis:** explain directness and source quality in words. Do not assign numeric probability without a calibrated method specified by the task.

## Standard nanopublication mapping

When TriG is required, map content to four distinct named graphs:

1. Head: nanopublication type and links to the three component graphs.
2. Assertion: one atomic claim, preferably one truth-evaluable statement.
3. Provenance: source and evidence details; this graph refers to the assertion graph.
4. Publication info: metadata about the nanopublication; this graph refers to the nanopublication URI.

See the official [Nanopublication Guidelines](https://nanopub.net/docs/guidelines/) for conformance requirements. JSON field names alone do not make a record a nanopublication.
