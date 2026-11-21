# Evidence-linked Literature Knowledge Graph — 阅读15｜文献知识图谱构建

Challenge: `product-arena-10-760d1a0b`.

This skill focuses on evidence-grounded graph construction from research papers, with conservative cross-paper entity alignment and executable queries. It is designed to preserve separate source identity, conditions, and evidence rather than merge similar labels into unsupported facts.

## Files

- `SKILL.md` — extraction, alignment, provenance, query, and runtime instructions.
- `references/graph-schema.md` — JSON graph field definitions and evidence requirements.
- `references/query-workflow.md` — supported query syntax and example invocation.
- `examples/synthetic-graph.json` — explicitly synthetic graph fixture; not a platform case.
- `examples/queries.json` — three illustrative queries against that synthetic fixture.
- `scripts/query_graph.py` — standard-library-only graph validation and deterministic query runner.
- `GITHUB_URL.txt` — public repository folder link for this challenge.

## Usage

Install this folder as an Agent skill and provide the actual input package. The Agent reads `task.md`, `case.json`, `environment/resources.yaml`, the corpus manifest, and every original paper source. It builds the graph from source evidence and executes at least three task-relevant queries.

For a JSON graph at `graph.json`, run a query specification with:

```text
python3 scripts/query_graph.py graph.json examples/queries.json --query-id q1
```

The query file is only an interface example. Replace its example questions with queries appropriate to the actual task and run them against the generated graph. The script uses Python's standard library and makes no network calls.

At Harbor runtime, use `/input` for source files, `/app/work` for intermediate files, and `/app/output` for deliverables. Preserve all original output-contract fields and `case_id` in `result.json`; do not submit the synthetic fixture as a case result.

## Limitations

The workflow does not infer missing values from domain knowledge. Entity identity requires evidence, and unresolved candidates remain separate. Formulae, figures, supplementary files, raw clinical/experimental data, or PDF pagination are only available if supplied by the case. JATS paragraph IDs are source anchors, not PDF page numbers. Query results are only as complete as the extracted graph.
