#!/usr/bin/env python3
"""Validate and query a small evidence-linked literature graph (stdlib only)."""

import argparse
import json
import sys
from pathlib import Path


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as stream:
        return json.load(stream)


def source_ids(record):
    ids = set(record.get("source_ids", []))
    if record.get("source_id"):
        ids.add(record["source_id"])
    for evidence in record.get("evidence", []):
        if evidence.get("source_id"):
            ids.add(evidence["source_id"])
    return ids


def validate_graph(graph):
    errors = []
    sources = {item.get("source_id") for item in graph.get("sources", [])}
    sources.discard(None)
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    node_map = {item.get("id"): item for item in nodes if item.get("id")}

    if len(node_map) != len(nodes):
        errors.append("node IDs are missing or duplicated")
    edge_ids = [item.get("id") for item in edges]
    if None in edge_ids or len(set(edge_ids)) != len(edge_ids):
        errors.append("edge IDs are missing or duplicated")

    for kind, records in (("node", nodes), ("edge", edges)):
        for record in records:
            rid = record.get("id", "<missing-id>")
            evidence = record.get("evidence", [])
            if not evidence:
                errors.append("{} {} has no evidence".format(kind, rid))
            for item in evidence:
                for field in ("source_id", "paragraph_id", "quote"):
                    if not item.get(field):
                        errors.append("{} {} evidence missing {}".format(kind, rid, field))
                sid = item.get("source_id")
                if sid and sources and sid not in sources:
                    errors.append("{} {} cites unknown source {}".format(kind, rid, sid))
    for edge in edges:
        eid = edge.get("id", "<missing-id>")
        for endpoint in ("subject", "object"):
            value = edge.get(endpoint)
            if value not in node_map:
                errors.append("edge {} has dangling {} {}".format(eid, endpoint, value))
    for alignment in graph.get("alignments", []):
        status = alignment.get("status")
        if status not in {"same_entity", "same_concept", "related_but_distinct", "candidate_unresolved", "conflict"}:
            errors.append("alignment has unsupported status {!r}".format(status))
        for node_id in alignment.get("node_ids", []):
            if node_id not in node_map:
                errors.append("alignment references unknown node {}".format(node_id))
        if not alignment.get("evidence"):
            errors.append("alignment {} has no evidence".format(alignment.get("node_ids", [])))
    return errors


def record_matches_source(record, source_id):
    return source_id is None or source_id in source_ids(record)


def resolve_edge(edge, node_map):
    return {
        "edge": edge,
        "subject_node": node_map.get(edge.get("subject")),
        "object_node": node_map.get(edge.get("object")),
    }


def run_query(graph, query):
    kind = query.get("kind")
    source_id = query.get("source_id")
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    node_map = {item.get("id"): item for item in nodes}

    if kind == "nodes_by_type":
        wanted = query.get("node_type")
        if not wanted:
            raise ValueError("nodes_by_type requires node_type")
        results = [n for n in nodes if n.get("type") == wanted and record_matches_source(n, source_id)]
    elif kind == "edges_by_predicate":
        wanted = query.get("predicate")
        if not wanted:
            raise ValueError("edges_by_predicate requires predicate")
        results = [resolve_edge(e, node_map) for e in edges if e.get("predicate") == wanted and record_matches_source(e, source_id)]
    elif kind == "neighbors":
        node_id = query.get("node_id")
        if not node_id:
            raise ValueError("neighbors requires node_id")
        direction = query.get("direction", "both")
        if direction not in {"incoming", "outgoing", "both"}:
            raise ValueError("neighbors direction must be incoming, outgoing, or both")
        predicates = set(query.get("predicates", []))
        results = []
        for edge in edges:
            matches = ((direction in {"outgoing", "both"} and edge.get("subject") == node_id)
                       or (direction in {"incoming", "both"} and edge.get("object") == node_id))
            if matches and (not predicates or edge.get("predicate") in predicates) and record_matches_source(edge, source_id):
                results.append(resolve_edge(edge, node_map))
    elif kind == "alignments_by_status":
        wanted = query.get("status")
        if not wanted:
            raise ValueError("alignments_by_status requires status")
        required_sources = set(query.get("source_ids", []))
        results = []
        for alignment in graph.get("alignments", []):
            evidence_sources = source_ids(alignment)
            linked_nodes = [node_map.get(nid) for nid in alignment.get("node_ids", [])]
            for node in linked_nodes:
                if node:
                    evidence_sources.update(source_ids(node))
            if alignment.get("status") == wanted and required_sources.issubset(evidence_sources):
                results.append(alignment)
    else:
        raise ValueError("unsupported query kind: {!r}".format(kind))

    return {"query_id": query.get("id"), "kind": kind, "result_count": len(results), "results": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("graph", help="path to evidence-graph JSON")
    parser.add_argument("queries", help="path to JSON array of query specifications")
    parser.add_argument("--query-id", help="run only the query with this id")
    parser.add_argument("--validate-only", action="store_true", help="validate graph structure without running queries")
    args = parser.parse_args()

    try:
        graph = load_json(args.graph)
        queries = load_json(args.queries)
        if not isinstance(queries, list):
            raise ValueError("query file must contain a JSON array")
        errors = validate_graph(graph)
        if errors:
            print(json.dumps({"valid": False, "errors": errors}, ensure_ascii=False, indent=2))
            return 2
        if args.validate_only:
            print(json.dumps({"valid": True, "node_count": len(graph.get("nodes", [])), "edge_count": len(graph.get("edges", []))}, ensure_ascii=False, indent=2))
            return 0
        selected = [q for q in queries if not args.query_id or q.get("id") == args.query_id]
        if args.query_id and not selected:
            raise ValueError("query id not found: {}".format(args.query_id))
        results = [run_query(graph, query) for query in selected]
        print(json.dumps({"valid": True, "queries": results}, ensure_ascii=False, indent=2))
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
