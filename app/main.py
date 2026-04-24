import os
import re
from typing import Any, Dict, List, Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from neo4j import GraphDatabase
from pydantic import BaseModel, Field


load_dotenv()


def sanitize_identifier(name: str, kind: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise HTTPException(status_code=400, detail=f"Invalid {kind}: {name}")
    return name


def check_props(props: Dict[str, Any], field_name: str = "properties") -> Dict[str, Any]:
    if props is None:
        return {}
    if not isinstance(props, dict):
        raise HTTPException(status_code=400, detail=f"{field_name} must be an object")
    for key in props.keys():
        sanitize_identifier(key, "property name")
    return props


class NodeSelector(BaseModel):
    label: str
    id_property: str
    id_value: Any


class CreateNodeRequest(BaseModel):
    labels: List[str] = Field(min_length=1)
    properties: Dict[str, Any] = Field(default_factory=dict)


class SearchNodesRequest(BaseModel):
    label: Optional[str] = None
    filters: Dict[str, Any] = Field(default_factory=dict)
    skip: int = 0
    limit: int = 50


class AggregateNodesRequest(BaseModel):
    label: str
    operation: Literal["count", "avg", "sum", "min", "max"]
    field: Optional[str] = None
    group_by: Optional[str] = None
    filters: Dict[str, Any] = Field(default_factory=dict)


class NodePropertyOneRequest(BaseModel):
    selector: NodeSelector
    properties: Dict[str, Any] = Field(default_factory=dict)


class NodePropertyManyRequest(BaseModel):
    label: str
    filters: Dict[str, Any] = Field(default_factory=dict)
    properties: Dict[str, Any] = Field(default_factory=dict)


class NodePropertyDeleteOneRequest(BaseModel):
    selector: NodeSelector
    property_keys: List[str] = Field(min_length=1)


class NodePropertyDeleteManyRequest(BaseModel):
    label: str
    filters: Dict[str, Any] = Field(default_factory=dict)
    property_keys: List[str] = Field(min_length=1)


class DeleteNodeOneRequest(BaseModel):
    selector: NodeSelector
    detach: bool = True


class DeleteNodeManyRequest(BaseModel):
    label: str
    filters: Dict[str, Any] = Field(default_factory=dict)
    detach: bool = True


class RelationshipCreateRequest(BaseModel):
    start: NodeSelector
    end: NodeSelector
    rel_type: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class RelationshipSelector(BaseModel):
    start: NodeSelector
    end: NodeSelector
    rel_type: str
    direction: Literal["outgoing", "incoming", "undirected"] = "outgoing"
    relationship_match_properties: Dict[str, Any] = Field(default_factory=dict)


class RelationshipPropertyOneRequest(BaseModel):
    selector: RelationshipSelector
    properties: Dict[str, Any] = Field(default_factory=dict)


class RelationshipPropertyDeleteOneRequest(BaseModel):
    selector: RelationshipSelector
    property_keys: List[str] = Field(min_length=1)


class RelationshipPropertyManyRequest(BaseModel):
    start_label: str
    end_label: str
    rel_type: str
    direction: Literal["outgoing", "incoming", "undirected"] = "outgoing"
    start_filters: Dict[str, Any] = Field(default_factory=dict)
    end_filters: Dict[str, Any] = Field(default_factory=dict)
    relationship_filters: Dict[str, Any] = Field(default_factory=dict)
    properties: Dict[str, Any] = Field(default_factory=dict)


class RelationshipPropertyDeleteManyRequest(BaseModel):
    start_label: str
    end_label: str
    rel_type: str
    direction: Literal["outgoing", "incoming", "undirected"] = "outgoing"
    start_filters: Dict[str, Any] = Field(default_factory=dict)
    end_filters: Dict[str, Any] = Field(default_factory=dict)
    relationship_filters: Dict[str, Any] = Field(default_factory=dict)
    property_keys: List[str] = Field(min_length=1)


class DeleteRelationshipOneRequest(BaseModel):
    selector: RelationshipSelector


class DeleteRelationshipManyRequest(BaseModel):
    start_label: str
    end_label: str
    rel_type: str
    direction: Literal["outgoing", "incoming", "undirected"] = "outgoing"
    start_filters: Dict[str, Any] = Field(default_factory=dict)
    end_filters: Dict[str, Any] = Field(default_factory=dict)
    relationship_filters: Dict[str, Any] = Field(default_factory=dict)


NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

if not NEO4J_URI or not NEO4J_USERNAME or not NEO4J_PASSWORD:
    raise RuntimeError("Missing Neo4j env vars. Check .env")


driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

app = FastAPI(title="Neo4j CRUD API", version="1.0.0")


@app.get("/health")
def health():
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run("RETURN 1 AS ok").single()["ok"]
    return {"status": "ok", "db": result}


@app.post("/nodes")
def create_node(payload: CreateNodeRequest):
    labels = [sanitize_identifier(l, "label") for l in payload.labels]
    props = check_props(payload.properties)
    label_part = ":".join(labels)

    query = f"""
    CREATE (n:{label_part})
    SET n += $props
    RETURN elementId(n) AS element_id, labels(n) AS labels, properties(n) AS properties
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        row = session.run(query, props=props).single()

    return dict(row)


@app.get("/nodes/{label}/{id_property}/{id_value}")
def get_one_node(label: str, id_property: str, id_value: str):
    label = sanitize_identifier(label, "label")
    id_property = sanitize_identifier(id_property, "property name")

    query = f"""
    MATCH (n:{label})
    WHERE n.{id_property} = $id_value
    RETURN elementId(n) AS element_id, labels(n) AS labels, properties(n) AS properties
    LIMIT 1
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        row = session.run(query, id_value=id_value).single()

    if not row:
        raise HTTPException(status_code=404, detail="Node not found")

    return dict(row)


@app.post("/nodes/search")
def search_nodes(payload: SearchNodesRequest):
    params: Dict[str, Any] = {"skip": payload.skip, "limit": payload.limit}

    match_part = "MATCH (n)"
    if payload.label:
        label = sanitize_identifier(payload.label, "label")
        match_part = f"MATCH (n:{label})"

    where_parts = []
    for idx, (key, value) in enumerate(payload.filters.items()):
        key = sanitize_identifier(key, "property name")
        p = f"f{idx}"
        where_parts.append(f"n.{key} = ${p}")
        params[p] = value

    where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    query = f"""
    {match_part}
    {where_clause}
    RETURN elementId(n) AS element_id, labels(n) AS labels, properties(n) AS properties
    SKIP $skip LIMIT $limit
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        rows = [dict(r) for r in session.run(query, **params)]

    return {"count": len(rows), "items": rows}


@app.post("/nodes/aggregate")
def aggregate_nodes(payload: AggregateNodesRequest):
    label = sanitize_identifier(payload.label, "label")
    op = payload.operation

    if op != "count" and not payload.field:
        raise HTTPException(status_code=400, detail="field is required for avg/sum/min/max")

    params: Dict[str, Any] = {}
    where_parts = []
    for idx, (key, value) in enumerate(payload.filters.items()):
        key = sanitize_identifier(key, "property name")
        p = f"f{idx}"
        where_parts.append(f"n.{key} = ${p}")
        params[p] = value
    where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    if payload.group_by:
        group_by = sanitize_identifier(payload.group_by, "property name")
        if op == "count":
            query = f"""
            MATCH (n:{label})
            {where_clause}
            RETURN n.{group_by} AS group_value, count(n) AS value
            ORDER BY value DESC
            """
        else:
            field = sanitize_identifier(payload.field or "", "property name")
            query = f"""
            MATCH (n:{label})
            {where_clause}
            RETURN n.{group_by} AS group_value, {op}(n.{field}) AS value
            ORDER BY value DESC
            """
    else:
        if op == "count":
            query = f"MATCH (n:{label}) {where_clause} RETURN count(n) AS value"
        else:
            field = sanitize_identifier(payload.field or "", "property name")
            query = f"MATCH (n:{label}) {where_clause} RETURN {op}(n.{field}) AS value"

    with driver.session(database=NEO4J_DATABASE) as session:
        rows = [dict(r) for r in session.run(query, **params)]

    return {"items": rows}


def _run_node_property_set(selector: NodeSelector, props: Dict[str, Any]) -> Dict[str, Any]:
    label = sanitize_identifier(selector.label, "label")
    id_property = sanitize_identifier(selector.id_property, "property name")
    props = check_props(props)

    query = f"""
    MATCH (n:{label})
    WHERE n.{id_property} = $id_value
    SET n += $props
    RETURN elementId(n) AS element_id, labels(n) AS labels, properties(n) AS properties
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        row = session.run(query, id_value=selector.id_value, props=props).single()

    if not row:
        raise HTTPException(status_code=404, detail="Node not found")

    return dict(row)


@app.patch("/nodes/properties/add-one")
def add_node_properties_one(payload: NodePropertyOneRequest):
    return _run_node_property_set(payload.selector, payload.properties)


@app.patch("/nodes/properties/update-one")
def update_node_properties_one(payload: NodePropertyOneRequest):
    return _run_node_property_set(payload.selector, payload.properties)


@app.patch("/nodes/properties/add-many")
def add_node_properties_many(payload: NodePropertyManyRequest):
    label = sanitize_identifier(payload.label, "label")
    props = check_props(payload.properties)

    params: Dict[str, Any] = {"props": props}
    where_parts = []
    for idx, (key, value) in enumerate(payload.filters.items()):
        key = sanitize_identifier(key, "property name")
        p = f"f{idx}"
        where_parts.append(f"n.{key} = ${p}")
        params[p] = value

    where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    query = f"""
    MATCH (n:{label})
    {where_clause}
    SET n += $props
    RETURN count(n) AS affected
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        affected = session.run(query, **params).single()["affected"]

    return {"affected": affected}


@app.patch("/nodes/properties/update-many")
def update_node_properties_many(payload: NodePropertyManyRequest):
    return add_node_properties_many(payload)


@app.delete("/nodes/properties/delete-one")
def delete_node_properties_one(payload: NodePropertyDeleteOneRequest):
    label = sanitize_identifier(payload.selector.label, "label")
    id_property = sanitize_identifier(payload.selector.id_property, "property name")
    keys = [sanitize_identifier(k, "property name") for k in payload.property_keys]

    query = f"""
    MATCH (n:{label})
    WHERE n.{id_property} = $id_value
    FOREACH(k IN $keys | SET n[k] = null)
    RETURN elementId(n) AS element_id, labels(n) AS labels, properties(n) AS properties
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        row = session.run(query, id_value=payload.selector.id_value, keys=keys).single()

    if not row:
        raise HTTPException(status_code=404, detail="Node not found")

    return dict(row)


@app.delete("/nodes/properties/delete-many")
def delete_node_properties_many(payload: NodePropertyDeleteManyRequest):
    label = sanitize_identifier(payload.label, "label")
    keys = [sanitize_identifier(k, "property name") for k in payload.property_keys]

    params: Dict[str, Any] = {"keys": keys}
    where_parts = []
    for idx, (key, value) in enumerate(payload.filters.items()):
        key = sanitize_identifier(key, "property name")
        p = f"f{idx}"
        where_parts.append(f"n.{key} = ${p}")
        params[p] = value

    where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    query = f"""
    MATCH (n:{label})
    {where_clause}
    FOREACH(k IN $keys | SET n[k] = null)
    RETURN count(n) AS affected
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        affected = session.run(query, **params).single()["affected"]

    return {"affected": affected}


@app.delete("/nodes/delete-one")
def delete_node_one(payload: DeleteNodeOneRequest):
    label = sanitize_identifier(payload.selector.label, "label")
    id_property = sanitize_identifier(payload.selector.id_property, "property name")
    delete_kw = "DETACH DELETE" if payload.detach else "DELETE"

    query = f"""
    MATCH (n:{label})
    WHERE n.{id_property} = $id_value
    WITH n LIMIT 1
    {delete_kw} n
    RETURN count(*) AS affected
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        affected = session.run(query, id_value=payload.selector.id_value).single()["affected"]

    if affected == 0:
        raise HTTPException(status_code=404, detail="Node not found")

    return {"affected": affected}


@app.delete("/nodes/delete-many")
def delete_node_many(payload: DeleteNodeManyRequest):
    label = sanitize_identifier(payload.label, "label")
    delete_kw = "DETACH DELETE" if payload.detach else "DELETE"

    params: Dict[str, Any] = {}
    where_parts = []
    for idx, (key, value) in enumerate(payload.filters.items()):
        key = sanitize_identifier(key, "property name")
        p = f"f{idx}"
        where_parts.append(f"n.{key} = ${p}")
        params[p] = value

    where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    query = f"""
    MATCH (n:{label})
    {where_clause}
    WITH collect(n) AS nodes
    FOREACH(node IN nodes | {delete_kw} node)
    RETURN size(nodes) AS affected
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        affected = session.run(query, **params).single()["affected"]

    return {"affected": affected}


def _relationship_pattern(direction: str) -> str:
    if direction == "outgoing":
        return "-[r:{rel_type}]->"
    if direction == "incoming":
        return "<-[r:{rel_type}]-"
    return "-[r:{rel_type}]-"


@app.post("/relationships")
def create_relationship(payload: RelationshipCreateRequest):
    start_label = sanitize_identifier(payload.start.label, "label")
    end_label = sanitize_identifier(payload.end.label, "label")
    start_id_prop = sanitize_identifier(payload.start.id_property, "property name")
    end_id_prop = sanitize_identifier(payload.end.id_property, "property name")
    rel_type = sanitize_identifier(payload.rel_type, "relationship type")
    props = check_props(payload.properties)

    query = f"""
    MATCH (a:{start_label}), (b:{end_label})
    WHERE a.{start_id_prop} = $start_id_value AND b.{end_id_prop} = $end_id_value
    CREATE (a)-[r:{rel_type}]->(b)
    SET r += $props
    RETURN elementId(r) AS rel_element_id, type(r) AS rel_type, properties(r) AS properties
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        row = session.run(
            query,
            start_id_value=payload.start.id_value,
            end_id_value=payload.end.id_value,
            props=props,
        ).single()

    if not row:
        raise HTTPException(status_code=404, detail="Start or end node not found")

    return dict(row)


def _match_relationship_one(selector: RelationshipSelector) -> tuple[str, Dict[str, Any]]:
    start_label = sanitize_identifier(selector.start.label, "label")
    end_label = sanitize_identifier(selector.end.label, "label")
    start_id_prop = sanitize_identifier(selector.start.id_property, "property name")
    end_id_prop = sanitize_identifier(selector.end.id_property, "property name")
    rel_type = sanitize_identifier(selector.rel_type, "relationship type")

    params: Dict[str, Any] = {
        "start_id_value": selector.start.id_value,
        "end_id_value": selector.end.id_value,
    }

    pattern = _relationship_pattern(selector.direction).format(rel_type=rel_type)

    where_parts = [f"a.{start_id_prop} = $start_id_value", f"b.{end_id_prop} = $end_id_value"]

    rel_match_props = check_props(selector.relationship_match_properties, "relationship_match_properties")
    for idx, (key, value) in enumerate(rel_match_props.items()):
        p = f"rp{idx}"
        where_parts.append(f"r.{key} = ${p}")
        params[p] = value

    where_clause = " AND ".join(where_parts)

    match = f"MATCH (a:{start_label}){pattern}(b:{end_label}) WHERE {where_clause}"
    return match, params


@app.patch("/relationships/properties/add-one")
def add_relationship_properties_one(payload: RelationshipPropertyOneRequest):
    match, params = _match_relationship_one(payload.selector)
    props = check_props(payload.properties)
    params["props"] = props

    query = f"""
    {match}
    WITH r LIMIT 1
    SET r += $props
    RETURN elementId(r) AS rel_element_id, type(r) AS rel_type, properties(r) AS properties
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        row = session.run(query, **params).single()

    if not row:
        raise HTTPException(status_code=404, detail="Relationship not found")

    return dict(row)


@app.patch("/relationships/properties/update-one")
def update_relationship_properties_one(payload: RelationshipPropertyOneRequest):
    return add_relationship_properties_one(payload)


@app.delete("/relationships/properties/delete-one")
def delete_relationship_properties_one(payload: RelationshipPropertyDeleteOneRequest):
    match, params = _match_relationship_one(payload.selector)
    keys = [sanitize_identifier(k, "property name") for k in payload.property_keys]
    params["keys"] = keys

    query = f"""
    {match}
    WITH r LIMIT 1
    FOREACH(k IN $keys | SET r[k] = null)
    RETURN elementId(r) AS rel_element_id, type(r) AS rel_type, properties(r) AS properties
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        row = session.run(query, **params).single()

    if not row:
        raise HTTPException(status_code=404, detail="Relationship not found")

    return dict(row)


def _match_relationship_many(
    start_label: str,
    end_label: str,
    rel_type: str,
    direction: str,
    start_filters: Dict[str, Any],
    end_filters: Dict[str, Any],
    relationship_filters: Dict[str, Any],
) -> tuple[str, Dict[str, Any]]:
    start_label = sanitize_identifier(start_label, "label")
    end_label = sanitize_identifier(end_label, "label")
    rel_type = sanitize_identifier(rel_type, "relationship type")

    pattern = _relationship_pattern(direction).format(rel_type=rel_type)
    params: Dict[str, Any] = {}
    where_parts = []

    for idx, (k, v) in enumerate(check_props(start_filters, "start_filters").items()):
        p = f"s{idx}"
        where_parts.append(f"a.{k} = ${p}")
        params[p] = v

    for idx, (k, v) in enumerate(check_props(end_filters, "end_filters").items()):
        p = f"e{idx}"
        where_parts.append(f"b.{k} = ${p}")
        params[p] = v

    for idx, (k, v) in enumerate(check_props(relationship_filters, "relationship_filters").items()):
        p = f"r{idx}"
        where_parts.append(f"r.{k} = ${p}")
        params[p] = v

    where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    match = f"MATCH (a:{start_label}){pattern}(b:{end_label}) {where_clause}"
    return match, params


@app.patch("/relationships/properties/add-many")
def add_relationship_properties_many(payload: RelationshipPropertyManyRequest):
    match, params = _match_relationship_many(
        payload.start_label,
        payload.end_label,
        payload.rel_type,
        payload.direction,
        payload.start_filters,
        payload.end_filters,
        payload.relationship_filters,
    )

    params["props"] = check_props(payload.properties)

    query = f"""
    {match}
    SET r += $props
    RETURN count(r) AS affected
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        affected = session.run(query, **params).single()["affected"]

    return {"affected": affected}


@app.patch("/relationships/properties/update-many")
def update_relationship_properties_many(payload: RelationshipPropertyManyRequest):
    return add_relationship_properties_many(payload)


@app.delete("/relationships/properties/delete-many")
def delete_relationship_properties_many(payload: RelationshipPropertyDeleteManyRequest):
    match, params = _match_relationship_many(
        payload.start_label,
        payload.end_label,
        payload.rel_type,
        payload.direction,
        payload.start_filters,
        payload.end_filters,
        payload.relationship_filters,
    )

    keys = [sanitize_identifier(k, "property name") for k in payload.property_keys]
    params["keys"] = keys

    query = f"""
    {match}
    FOREACH(k IN $keys | SET r[k] = null)
    RETURN count(r) AS affected
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        affected = session.run(query, **params).single()["affected"]

    return {"affected": affected}


@app.delete("/relationships/delete-one")
def delete_relationship_one(payload: DeleteRelationshipOneRequest):
    match, params = _match_relationship_one(payload.selector)

    query = f"""
    {match}
    WITH r LIMIT 1
    DELETE r
    RETURN count(*) AS affected
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        affected = session.run(query, **params).single()["affected"]

    if affected == 0:
        raise HTTPException(status_code=404, detail="Relationship not found")

    return {"affected": affected}


@app.delete("/relationships/delete-many")
def delete_relationship_many(payload: DeleteRelationshipManyRequest):
    match, params = _match_relationship_many(
        payload.start_label,
        payload.end_label,
        payload.rel_type,
        payload.direction,
        payload.start_filters,
        payload.end_filters,
        payload.relationship_filters,
    )

    query = f"""
    {match}
    DELETE r
    RETURN count(*) AS affected
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        affected = session.run(query, **params).single()["affected"]

    return {"affected": affected}
