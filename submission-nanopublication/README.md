# Evidence-bound Nanopublications

Challenge: `product-arena-09-0e8befd4`.

This Agent skill focuses on a concrete nanopublication task: splitting scientific prose into atomic claims, binding each claim to its smallest sufficient evidence passage, and retaining source provenance for review and reuse.

## Contents

- `SKILL.md` — task workflow, evidence rules, output-contract handling, and RDF/TriG guidance.
- `references/field-dictionary.md` — reusable claim, evidence, provenance, and uncertainty field definitions.
- `references/claim-patterns.jsonl` — 20 explicitly synthetic patterns for claim splitting and evidence boundaries.
- `examples/claim-record.example.json` — explicitly synthetic claim record, not a platform answer.
- `examples/synthetic-nanopublication.trig` — explicitly synthetic four-graph TriG example.
- `GITHUB_URL.txt` — public repository folder link required by the challenge.

## Use

Install this directory as a skill or pass its `SKILL.md` to the Agent. Provide the actual challenge input directory. The Agent reads `task.md`, `case.json`, `environment/resources.yaml`, and the actual source artifacts, then follows the task's `output_contract`.

At Harbor runtime, treat `/input` as read-only, use `/app/work` for intermediates, and write deliverables to `/app/output`. Preserve every original output-contract field and `case_id` in `result.json`. Do not put precomputed case answers in the skill package.

## Method and boundaries

The workflow distinguishes author-reported claims, interpretations, and extractor-derived normalizations; preserves qualifiers; anchors each key claim to a short evidence passage and a precise page/section/figure/table/equation location; and reports conflicts or missing evidence explicitly. For a requested standard nanopublication, use the four named RDF graphs in TriG (head, assertion, provenance, publication info) and comply with the [Nanopublication Guidelines](https://nanopub.net/docs/guidelines/). The 20 claim patterns are synthetic method examples, not findings or benchmark cases.

The skill does not assign truth beyond the source, infer unseen figure content, mint unverifiable identifiers/signatures, or publish to a nanopublication network. JSON claim records are a task-friendly representation, not standard nanopublication RDF. PDF visual inspection and OCR depend on tools installed by the target runtime. The platform supplies the fixed evaluation cases; this package contains examples only.
