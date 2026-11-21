# Query workflow

`scripts/query_graph.py` is a small deterministic query runner for the local JSON graph schema. It uses Python 3 and the standard library only. It never fetches sources or creates entities.

## Query specification

A query file is a JSON array of objects. The first query must have a unique `id` and a supported `kind`:

```json
[
  {"id":"q1","kind":"nodes_by_type","node_type":"method","source_id":"paper-A"},
  {"id":"q2","kind":"edges_by_predicate","predicate":"evaluates_on","source_id":"paper-A"},
  {"id":"q3","kind":"alignments_by_status","status":"candidate_unresolved"}
]
```

Supported query kinds:

- `nodes_by_type`: `node_type` required; optional `source_id`.
- `edges_by_predicate`: `predicate` required; optional `source_id`.
- `neighbors`: `node_id` required; optional `direction` (`outgoing`, `incoming`, `both`), `predicates` (array), and `source_id`.
- `alignments_by_status`: `status` required; optional `source_ids` (array; every listed source must appear in the alignment evidence or node records).

Run one query and save its JSON result:

```text
python3 scripts/query_graph.py /app/work/graph.json /app/work/queries.json --query-id q1
```

Run all queries in the query file by omitting `--query-id`. The result includes matching graph records and evidence as stored. Review that the evidence actually supports the answer; the script checks structure and filters records, not scientific entailment.

## Choosing real queries

For a multi-paper case, select at least three distinct questions based on `task.md`, such as (1) methods and tasks within each source, (2) evidence-backed relations for a requested metric or result, and (3) cross-paper alignments/conflicts. Do not hard-code case-specific labels. If two values cannot be fairly compared because the samples, datasets, measures, or conditions differ, return them separately and explain the incompatibility.
