import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from neo4j import GraphDatabase
from pydantic import BaseModel, Field


load_dotenv()


# --- Validacion de nombres para evitar inyeccion en Cypher ---

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


def normalize_string_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        if "|" in value:
            return [v.strip() for v in value.split("|") if v.strip()]
        return [value.strip()] if value.strip() else []
    return [str(value).strip()] if str(value).strip() else []


# --- Verificaciones de existencia de nodos de negocio ---

def require_user(session, user_id: str):
    row = session.run(
        "MATCH (u:User {user_id: $uid}) RETURN u.user_id AS uid", uid=user_id
    ).single()
    if not row:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")


def require_movie(session, movie_id: str):
    row = session.run(
        "MATCH (m:Movie {movie_id: $mid}) RETURN m.movie_id AS mid", mid=movie_id
    ).single()
    if not row:
        raise HTTPException(status_code=404, detail=f"Movie '{movie_id}' not found")


# ============================================================
# MODELOS - CRUD GENERICO
# ============================================================

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


# ============================================================
# MODELOS - ENDPOINTS DE NEGOCIO
# ============================================================

class CollectionCreateRequest(BaseModel):
    name: str
    description: Optional[str] = ""


class CollectionUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class FriendRequest(BaseModel):
    friend_id: str
    closeness: float = Field(default=0.5, ge=0.0, le=1.0)


# ============================================================
# CONEXION A NEO4J
# ============================================================

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

if not NEO4J_URI or not NEO4J_USERNAME or not NEO4J_PASSWORD:
    raise RuntimeError("Missing Neo4j env vars. Check .env")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

app = FastAPI(title="Neo4j Social Recommender API", version="2.0.0")


# ============================================================
# SALUD
# ============================================================

@app.get("/health")
def health():
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run("RETURN 1 AS ok").single()["ok"]
    return {"status": "ok", "db": result}


# ============================================================
# CRUD GENERICO - NODOS
# ============================================================

@app.post("/nodes", tags=["nodes"])
def create_node(payload: CreateNodeRequest):
    labels = [sanitize_identifier(lbl, "label") for lbl in payload.labels]
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


@app.get("/nodes/{label}/{id_property}/{id_value}", tags=["nodes"])
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


@app.post("/nodes/search", tags=["nodes"])
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


@app.post("/nodes/aggregate", tags=["nodes"])
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
            MATCH (n:{label}) {where_clause}
            RETURN n.{group_by} AS group_value, count(n) AS value
            ORDER BY value DESC
            """
        else:
            field = sanitize_identifier(payload.field or "", "property name")
            query = f"""
            MATCH (n:{label}) {where_clause}
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


@app.patch("/nodes/properties/add-one", tags=["nodes"])
def add_node_properties_one(payload: NodePropertyOneRequest):
    return _run_node_property_set(payload.selector, payload.properties)


@app.patch("/nodes/properties/update-one", tags=["nodes"])
def update_node_properties_one(payload: NodePropertyOneRequest):
    return _run_node_property_set(payload.selector, payload.properties)


@app.patch("/nodes/properties/add-many", tags=["nodes"])
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
    MATCH (n:{label}) {where_clause}
    SET n += $props
    RETURN count(n) AS affected
    """
    with driver.session(database=NEO4J_DATABASE) as session:
        affected = session.run(query, **params).single()["affected"]
    return {"affected": affected}


@app.patch("/nodes/properties/update-many", tags=["nodes"])
def update_node_properties_many(payload: NodePropertyManyRequest):
    return add_node_properties_many(payload)


@app.delete("/nodes/properties/delete-one", tags=["nodes"])
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


@app.delete("/nodes/properties/delete-many", tags=["nodes"])
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
    MATCH (n:{label}) {where_clause}
    FOREACH(k IN $keys | SET n[k] = null)
    RETURN count(n) AS affected
    """
    with driver.session(database=NEO4J_DATABASE) as session:
        affected = session.run(query, **params).single()["affected"]
    return {"affected": affected}


@app.delete("/nodes/delete-one", tags=["nodes"])
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


@app.delete("/nodes/delete-many", tags=["nodes"])
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
    MATCH (n:{label}) {where_clause}
    WITH collect(n) AS nodes
    FOREACH(node IN nodes | {delete_kw} node)
    RETURN size(nodes) AS affected
    """
    with driver.session(database=NEO4J_DATABASE) as session:
        affected = session.run(query, **params).single()["affected"]
    return {"affected": affected}


# ============================================================
# CRUD GENERICO - RELACIONES
# ============================================================

def _relationship_pattern(direction: str) -> str:
    if direction == "outgoing":
        return "-[r:{rel_type}]->"
    if direction == "incoming":
        return "<-[r:{rel_type}]-"
    return "-[r:{rel_type}]-"


@app.post("/relationships", tags=["relationships"])
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


@app.patch("/relationships/properties/add-one", tags=["relationships"])
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


@app.patch("/relationships/properties/update-one", tags=["relationships"])
def update_relationship_properties_one(payload: RelationshipPropertyOneRequest):
    return add_relationship_properties_one(payload)


@app.delete("/relationships/properties/delete-one", tags=["relationships"])
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


@app.patch("/relationships/properties/add-many", tags=["relationships"])
def add_relationship_properties_many(payload: RelationshipPropertyManyRequest):
    match, params = _match_relationship_many(
        payload.start_label, payload.end_label, payload.rel_type, payload.direction,
        payload.start_filters, payload.end_filters, payload.relationship_filters,
    )
    params["props"] = check_props(payload.properties)
    query = f"{match} SET r += $props RETURN count(r) AS affected"
    with driver.session(database=NEO4J_DATABASE) as session:
        affected = session.run(query, **params).single()["affected"]
    return {"affected": affected}


@app.patch("/relationships/properties/update-many", tags=["relationships"])
def update_relationship_properties_many(payload: RelationshipPropertyManyRequest):
    return add_relationship_properties_many(payload)


@app.delete("/relationships/properties/delete-many", tags=["relationships"])
def delete_relationship_properties_many(payload: RelationshipPropertyDeleteManyRequest):
    match, params = _match_relationship_many(
        payload.start_label, payload.end_label, payload.rel_type, payload.direction,
        payload.start_filters, payload.end_filters, payload.relationship_filters,
    )
    keys = [sanitize_identifier(k, "property name") for k in payload.property_keys]
    params["keys"] = keys
    query = f"{match} FOREACH(k IN $keys | SET r[k] = null) RETURN count(r) AS affected"
    with driver.session(database=NEO4J_DATABASE) as session:
        affected = session.run(query, **params).single()["affected"]
    return {"affected": affected}


@app.delete("/relationships/delete-one", tags=["relationships"])
def delete_relationship_one(payload: DeleteRelationshipOneRequest):
    match, params = _match_relationship_one(payload.selector)
    query = f"{match} WITH r LIMIT 1 DELETE r RETURN count(*) AS affected"
    with driver.session(database=NEO4J_DATABASE) as session:
        affected = session.run(query, **params).single()["affected"]
    if affected == 0:
        raise HTTPException(status_code=404, detail="Relationship not found")
    return {"affected": affected}


@app.delete("/relationships/delete-many", tags=["relationships"])
def delete_relationship_many(payload: DeleteRelationshipManyRequest):
    match, params = _match_relationship_many(
        payload.start_label, payload.end_label, payload.rel_type, payload.direction,
        payload.start_filters, payload.end_filters, payload.relationship_filters,
    )
    query = f"{match} DELETE r RETURN count(*) AS affected"
    with driver.session(database=NEO4J_DATABASE) as session:
        affected = session.run(query, **params).single()["affected"]
    return {"affected": affected}


# ============================================================
# ALGORITMO JACCARD
# Calcula similitud entre dos usuarios basado en peliculas
# que les gustan o calificaron con 8 o mas.
# Formula: J(A,B) = |A intersect B| / |A union B|
# ============================================================

def _jaccard(set_a: set, set_b: set) -> float:
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def _get_interest_set(session, user_id: str) -> set:
    # Peliculas con LIKED o RATED >= 8 para este usuario
    rows = session.run(
        """
        MATCH (u:User {user_id: $uid})
        OPTIONAL MATCH (u)-[:LIKED]->(m1:Movie)
        OPTIONAL MATCH (u)-[r:RATED]->(m2:Movie)
        WHERE r.rating >= 8
        WITH collect(DISTINCT m1.movie_id) + collect(DISTINCT m2.movie_id) AS ids
        UNWIND ids AS mid
        RETURN DISTINCT mid
        """,
        uid=user_id,
    )
    return {row["mid"] for row in rows if row["mid"]}


def _get_seen_set(session, user_id: str) -> set:
    # Peliculas que el usuario ya vio o califico (se excluyen de recomendaciones)
    rows = session.run(
        """
        MATCH (u:User {user_id: $uid})
        OPTIONAL MATCH (u)-[:VIEWED]->(m1:Movie)
        OPTIONAL MATCH (u)-[:RATED]->(m2:Movie)
        WITH collect(DISTINCT m1.movie_id) + collect(DISTINCT m2.movie_id) AS ids
        UNWIND ids AS mid
        RETURN DISTINCT mid
        """,
        uid=user_id,
    )
    return {row["mid"] for row in rows if row["mid"]}


# ============================================================
# RECOMENDACIONES
# ============================================================

@app.get("/recommendations/{user_id}", tags=["recommendations"])
def get_recommendations(
    user_id: str,
    top_k: int = 20,
    min_jaccard: float = 0.05,
    max_neighbors: int = 30,
    language: Optional[str] = None,
    genre: Optional[str] = None,
    include_reasons: bool = True,
):
    """
    Devuelve una lista personalizada de peliculas recomendadas.
    Usa similitud Jaccard (colaborativo) combinada con preferencias de contenido.
    """
    with driver.session(database=NEO4J_DATABASE) as session:
        require_user(session, user_id)

        # Preferencias del usuario: generos, idiomas y directores seguidos
        pref_row = session.run(
            """
            MATCH (u:User {user_id: $uid})
            OPTIONAL MATCH (u)-[p:PREFERS]->(g:Genre)
            OPTIONAL MATCH (u)-[:FOLLOWS_DIRECTOR]->(d:Director)
            RETURN
                collect(DISTINCT g.name) AS genres,
                u.favorite_languages AS fav_langs,
                collect(DISTINCT d.director_id) AS directors
            """,
            uid=user_id,
        ).single()

        pref_genres = set(pref_row["genres"] or [])
        pref_directors = set(pref_row["directors"] or [])
        pref_langs: set = set(normalize_string_list(pref_row["fav_langs"]))

        interest_set = _get_interest_set(session, user_id)
        seen_set = _get_seen_set(session, user_id)

        # Obtener conjuntos de interes de otros usuarios para calcular Jaccard
        neighbor_rows = session.run(
            """
            MATCH (other:User)
            WHERE other.user_id <> $uid
            OPTIONAL MATCH (other)-[:LIKED]->(ml:Movie)
            OPTIONAL MATCH (other)-[ro:RATED]->(mr:Movie)
            WHERE ro.rating >= 8
            WITH other, collect(DISTINCT ml.movie_id) + collect(DISTINCT mr.movie_id) AS other_ids
            WHERE size(other_ids) > 0
            RETURN other.user_id AS neighbor_id, other_ids
            LIMIT $scan_limit
            """,
            uid=user_id,
            scan_limit=max_neighbors * 6,
        )

        # Filtrar vecinos por similitud minima y ordenar
        neighbors: List[Dict[str, Any]] = []
        for row in neighbor_rows:
            other_set = set(row["other_ids"])
            score = _jaccard(interest_set, other_set)
            if score >= min_jaccard:
                neighbors.append({
                    "user_id": row["neighbor_id"],
                    "jaccard": score,
                    "movies": other_set,
                })

        neighbors.sort(key=lambda x: x["jaccard"], reverse=True)
        neighbors = neighbors[:max_neighbors]

        # Acumular peliculas candidatas desde los vecinos mas similares
        candidate_scores: Dict[str, Dict[str, Any]] = {}
        for neighbor in neighbors:
            for mid in neighbor["movies"]:
                if mid in seen_set:
                    continue
                if mid not in candidate_scores:
                    candidate_scores[mid] = {"jaccard_votes": 0.0, "neighbor_count": 0}
                candidate_scores[mid]["jaccard_votes"] += neighbor["jaccard"]
                candidate_scores[mid]["neighbor_count"] += 1

        if not candidate_scores:
            return {
                "user_id": user_id,
                "generated_at": datetime.utcnow().isoformat(),
                "algorithm": "hybrid_jaccard_v1",
                "total": 0,
                "items": [],
            }

        # Obtener datos de las peliculas candidatas
        movie_rows = session.run(
            """
            UNWIND $ids AS mid
            MATCH (m:Movie {movie_id: mid})
            OPTIONAL MATCH (m)-[:HAS_GENRE]->(g:Genre)
            OPTIONAL MATCH (m)-[:IN_LANGUAGE]->(l:Language)
            OPTIONAL MATCH (d:Director)-[:DIRECTED]->(m)
            RETURN
                m.movie_id AS movie_id,
                m.title AS title,
                m.vote_average AS vote_average,
                collect(DISTINCT g.name) AS genres,
                collect(DISTINCT l.code) AS languages,
                collect(DISTINCT d.director_id) AS directors
            """,
            ids=list(candidate_scores.keys()),
        )

        results = []
        for row in movie_rows:
            mid = row["movie_id"]
            movie_genres = set(row["genres"] or [])
            movie_langs = set(row["languages"] or [])
            movie_directors = set(row["directors"] or [])

            if language and language not in movie_langs:
                continue
            if genre and genre not in movie_genres:
                continue

            jaccard_score = candidate_scores[mid]["jaccard_votes"]
            neighbor_count = candidate_scores[mid]["neighbor_count"]

            # Score de contenido: coincidencia de genero, idioma y director
            matched_genres = pref_genres & movie_genres
            matched_langs = pref_langs & movie_langs
            matched_directors = pref_directors & movie_directors
            content_score = (
                len(matched_genres) * 0.3
                + len(matched_langs) * 0.2
                + len(matched_directors) * 0.5
                + (row["vote_average"] or 0) * 0.05
            )

            # Score final: 60% colaborativo Jaccard + 40% contenido
            final_score = round(jaccard_score * 0.6 + content_score * 0.4, 4)

            reasons = []
            if include_reasons:
                if neighbor_count:
                    reasons.append(f"{neighbor_count} usuarios similares la valoraron alto")
                if matched_genres:
                    reasons.append(f"Coincide con tus generos: {', '.join(matched_genres)}")
                if matched_langs:
                    reasons.append("En tu idioma preferido")
                if matched_directors:
                    reasons.append("Director que sigues")

            results.append({
                "movie_id": mid,
                "title": row["title"],
                "score": final_score,
                "jaccard_score": round(jaccard_score, 4),
                "content_score": round(content_score, 4),
                "vote_average": row["vote_average"],
                "genres": list(movie_genres),
                "reasons": reasons,
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        results = results[:top_k]

    return {
        "user_id": user_id,
        "generated_at": datetime.utcnow().isoformat(),
        "algorithm": "hybrid_jaccard_v1",
        "total": len(results),
        "items": results,
    }


@app.get("/recommendations/{user_id}/explanations/{movie_id}", tags=["recommendations"])
def get_recommendation_explanation(user_id: str, movie_id: str):
    """
    Explica por que una pelicula fue recomendada a un usuario concreto.
    Muestra senales colaborativas (vecinos Jaccard) y de contenido.
    """
    with driver.session(database=NEO4J_DATABASE) as session:
        require_user(session, user_id)
        require_movie(session, movie_id)

        interest_set = _get_interest_set(session, user_id)

        # Vecinos que valoraron positivamente esta pelicula
        neighbor_rows = session.run(
            """
            MATCH (other:User)
            WHERE other.user_id <> $uid
            WITH other
            OPTIONAL MATCH (other)-[:LIKED]->(m1:Movie {movie_id: $mid})
            OPTIONAL MATCH (other)-[ro:RATED]->(m2:Movie {movie_id: $mid})
            WHERE ro.rating >= 8
            WITH other, (m1 IS NOT NULL OR m2 IS NOT NULL) AS liked_it
            WHERE liked_it
            OPTIONAL MATCH (other)-[:LIKED]->(ml:Movie)
            OPTIONAL MATCH (other)-[ro2:RATED]->(mr:Movie)
            WHERE ro2.rating >= 8
            WITH other, collect(DISTINCT ml.movie_id) + collect(DISTINCT mr.movie_id) AS other_ids
            RETURN other.user_id AS neighbor_id, other_ids
            LIMIT 50
            """,
            uid=user_id,
            mid=movie_id,
        )

        influencing = []
        for row in neighbor_rows:
            j = _jaccard(interest_set, set(row["other_ids"]))
            if j > 0:
                influencing.append({"user_id": row["neighbor_id"], "jaccard": round(j, 4)})

        influencing.sort(key=lambda x: x["jaccard"], reverse=True)

        movie_row = session.run(
            """
            MATCH (m:Movie {movie_id: $mid})
            OPTIONAL MATCH (m)-[:HAS_GENRE]->(g:Genre)
            OPTIONAL MATCH (m)-[:IN_LANGUAGE]->(l:Language)
            OPTIONAL MATCH (d:Director)-[:DIRECTED]->(m)
            RETURN
                m.title AS title,
                m.vote_average AS vote_average,
                collect(DISTINCT g.name) AS genres,
                collect(DISTINCT l.code) AS languages,
                collect(DISTINCT d.director_id) AS directors
            """,
            mid=movie_id,
        ).single()

        user_pref = session.run(
            """
            MATCH (u:User {user_id: $uid})
            OPTIONAL MATCH (u)-[:PREFERS]->(g:Genre)
            OPTIONAL MATCH (u)-[:FOLLOWS_DIRECTOR]->(d:Director)
            RETURN
                collect(DISTINCT g.name) AS genres,
                collect(DISTINCT d.director_id) AS directors,
                u.favorite_languages AS fav_langs
            """,
            uid=user_id,
        ).single()

        pref_genres = set(user_pref["genres"] or [])
        pref_directors = set(user_pref["directors"] or [])
        pref_langs: set = set(normalize_string_list(user_pref["fav_langs"]))

        movie_genres = set(movie_row["genres"] or [])
        movie_langs = set(movie_row["languages"] or [])
        movie_directors = set(movie_row["directors"] or [])

    return {
        "user_id": user_id,
        "movie_id": movie_id,
        "title": movie_row["title"],
        "score_breakdown": {
            "collaborative_neighbors": len(influencing),
            "genre_match_count": len(pref_genres & movie_genres),
            "language_match_count": len(pref_langs & movie_langs),
            "director_match_count": len(pref_directors & movie_directors),
            "vote_average": movie_row["vote_average"],
        },
        "matched_genres": list(pref_genres & movie_genres),
        "matched_languages": list(pref_langs & movie_langs),
        "matched_directors": list(pref_directors & movie_directors),
        "social_signals": influencing[:10],
    }


@app.get("/users/{user_id}/recommendation-profile", tags=["recommendations"])
def get_recommendation_profile(user_id: str):
    """
    Muestra como el sistema interpreta el perfil de gusto de un usuario.
    """
    with driver.session(database=NEO4J_DATABASE) as session:
        require_user(session, user_id)

        row = session.run(
            """
            MATCH (u:User {user_id: $uid})
            OPTIONAL MATCH (u)-[p:PREFERS]->(g:Genre)
            OPTIONAL MATCH (u)-[:FOLLOWS_DIRECTOR]->(d:Director)
            OPTIONAL MATCH (u)-[:FRIEND_OF]-(friend:User)
            RETURN
                u.favorite_languages AS fav_langs,
                collect(DISTINCT {genre: g.name, weight: p.weight}) AS genre_prefs,
                collect(DISTINCT d.name) AS followed_directors,
                count(DISTINCT friend) AS friend_count
            """,
            uid=user_id,
        ).single()

        genre_prefs = sorted(
            [gp for gp in (row["genre_prefs"] or []) if gp.get("genre")],
            key=lambda x: x.get("weight") or 0,
            reverse=True,
        )

    return {
        "user_id": user_id,
        "top_genres": genre_prefs[:5],
        "top_languages": normalize_string_list(row["fav_langs"]),
        "followed_directors": row["followed_directors"] or [],
        "social_affinity_summary": {"friend_count": row["friend_count"]},
    }


# ============================================================
# USUARIOS SIMILARES Y PELICULAS SIMILARES
# ============================================================

@app.get("/users/{user_id}/similar-users", tags=["similarity"])
def get_similar_users(user_id: str, top_k: int = 10, min_similarity: float = 0.05):
    """
    Retorna usuarios similares usando Jaccard sobre peliculas de interes.
    """
    with driver.session(database=NEO4J_DATABASE) as session:
        require_user(session, user_id)
        interest_set = _get_interest_set(session, user_id)

        rows = session.run(
            """
            MATCH (other:User)
            WHERE other.user_id <> $uid
            OPTIONAL MATCH (other)-[:LIKED]->(ml:Movie)
            OPTIONAL MATCH (other)-[ro:RATED]->(mr:Movie)
            WHERE ro.rating >= 8
            WITH other, collect(DISTINCT ml.movie_id) + collect(DISTINCT mr.movie_id) AS other_ids
            WHERE size(other_ids) > 0
            RETURN other.user_id AS user_id, other.name AS name, other_ids
            LIMIT 300
            """,
            uid=user_id,
        )

        results = []
        for row in rows:
            other_set = set(row["other_ids"])
            score = _jaccard(interest_set, other_set)
            if score >= min_similarity:
                shared = list(interest_set & other_set)
                results.append({
                    "user_id": row["user_id"],
                    "name": row["name"],
                    "similarity_score": round(score, 4),
                    "shared_count": len(shared),
                    "shared_movies_sample": shared[:5],
                })

        results.sort(key=lambda x: x["similarity_score"], reverse=True)

    return {"user_id": user_id, "total": len(results[:top_k]), "items": results[:top_k]}


@app.get("/movies/{movie_id}", tags=["movies"])
def get_movie(movie_id: str):
    """
    Retorna el detalle de una pelicula por movie_id.
    """
    with driver.session(database=NEO4J_DATABASE) as session:
        row = session.run(
            """
            MATCH (m:Movie {movie_id: $mid})
            OPTIONAL MATCH (m)-[:HAS_GENRE]->(g:Genre)
            OPTIONAL MATCH (m)-[:IN_LANGUAGE]->(l:Language)
            OPTIONAL MATCH (d:Director)-[:DIRECTED]->(m)
            RETURN
                m.movie_id AS movie_id,
                m.title AS title,
                m.original_title AS original_title,
                m.overview AS overview,
                m.release_date AS release_date,
                m.runtime AS runtime,
                m.original_language AS original_language,
                m.status AS status,
                m.vote_average AS vote_average,
                m.vote_count AS vote_count,
                m.popularity AS popularity,
                m.budget AS budget,
                m.revenue AS revenue,
                collect(DISTINCT g.name) AS genres,
                collect(DISTINCT l.code) AS languages,
                collect(DISTINCT d.name) AS directors
            """,
            mid=movie_id,
        ).single()

    if not row:
        raise HTTPException(status_code=404, detail=f"Movie '{movie_id}' not found")

    return dict(row)


@app.get("/movies/{movie_id}/similar", tags=["similarity"])
def get_similar_movies(movie_id: str, top_k: int = 10):
    """
    Retorna peliculas similares por genero (Jaccard) y director compartido.
    """
    with driver.session(database=NEO4J_DATABASE) as session:
        require_movie(session, movie_id)

        base_row = session.run(
            """
            MATCH (m:Movie {movie_id: $mid})
            OPTIONAL MATCH (m)-[:HAS_GENRE]->(g:Genre)
            OPTIONAL MATCH (d:Director)-[:DIRECTED]->(m)
            RETURN collect(DISTINCT g.name) AS genres, collect(DISTINCT d.director_id) AS directors
            """,
            mid=movie_id,
        ).single()

        base_genres = set(base_row["genres"] or [])
        base_directors = set(base_row["directors"] or [])

        rows = session.run(
            """
            MATCH (m:Movie {movie_id: $mid})-[:HAS_GENRE]->(g:Genre)<-[:HAS_GENRE]-(other:Movie)
            WHERE other.movie_id <> $mid
            OPTIONAL MATCH (other)-[:HAS_GENRE]->(og:Genre)
            OPTIONAL MATCH (od:Director)-[:DIRECTED]->(other)
            WITH other,
                 collect(DISTINCT og.name) AS other_genres,
                 collect(DISTINCT od.director_id) AS other_directors
            RETURN
                other.movie_id AS movie_id,
                other.title AS title,
                other.vote_average AS vote_average,
                other_genres,
                other_directors
            LIMIT 150
            """,
            mid=movie_id,
        )

        results = []
        for row in rows:
            other_genres = set(row["other_genres"] or [])
            other_directors = set(row["other_directors"] or [])
            genre_score = _jaccard(base_genres, other_genres)
            director_bonus = 0.3 if base_directors & other_directors else 0.0
            score = round(genre_score * 0.7 + director_bonus, 4)
            results.append({
                "movie_id": row["movie_id"],
                "title": row["title"],
                "score": score,
                "vote_average": row["vote_average"],
                "shared_genres": list(base_genres & other_genres),
                "same_director": bool(base_directors & other_directors),
            })

        results.sort(key=lambda x: x["score"], reverse=True)

    return {"movie_id": movie_id, "total": len(results[:top_k]), "items": results[:top_k]}


# ============================================================
# WATCHLIST
# ============================================================

@app.get("/users/{user_id}/watchlist", tags=["interactions"])
def get_watchlist(user_id: str, skip: int = 0, limit: int = 50):
    with driver.session(database=NEO4J_DATABASE) as session:
        require_user(session, user_id)
        rows = session.run(
            """
            MATCH (u:User {user_id: $uid})-[w:WATCHLISTED]->(m:Movie)
            RETURN
                m.movie_id AS movie_id,
                m.title AS title,
                m.vote_average AS vote_average,
                coalesce(w.added_at, w.added_date) AS added_at,
                w.priority AS priority
            ORDER BY coalesce(w.added_at, w.added_date) DESC
            SKIP $skip LIMIT $limit
            """,
            uid=user_id, skip=skip, limit=limit,
        )
        items = [dict(r) for r in rows]
    return {"user_id": user_id, "total": len(items), "items": items}


@app.post("/users/{user_id}/watchlist", tags=["interactions"])
def add_to_watchlist(user_id: str, movie_id: str, priority: int = 1):
    with driver.session(database=NEO4J_DATABASE) as session:
        require_user(session, user_id)
        require_movie(session, movie_id)
        session.run(
            """
            MATCH (u:User {user_id: $uid}), (m:Movie {movie_id: $mid})
            MERGE (u)-[w:WATCHLISTED]->(m)
            SET w.added_at = date(),
                w.added_date = date(),
                w.priority = $priority,
                w.source = coalesce(w.source, 'manual'),
                w.last_updated = date()
            """,
            uid=user_id, mid=movie_id, priority=priority,
        )
    return {"user_id": user_id, "movie_id": movie_id, "status": "added"}


@app.delete("/users/{user_id}/watchlist/{movie_id}", tags=["interactions"])
def remove_from_watchlist(user_id: str, movie_id: str):
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(
            """
            MATCH (u:User {user_id: $uid})-[w:WATCHLISTED]->(m:Movie {movie_id: $mid})
            DELETE w
            RETURN count(w) AS affected
            """,
            uid=user_id, mid=movie_id,
        ).single()
    if not result or result["affected"] == 0:
        raise HTTPException(status_code=404, detail="Entry not found in watchlist")
    return {"user_id": user_id, "movie_id": movie_id, "status": "removed"}


# ============================================================
# LIKES
# ============================================================

@app.get("/users/{user_id}/likes", tags=["interactions"])
def get_likes(user_id: str, skip: int = 0, limit: int = 50):
    with driver.session(database=NEO4J_DATABASE) as session:
        require_user(session, user_id)
        rows = session.run(
            """
            MATCH (u:User {user_id: $uid})-[lk:LIKED]->(m:Movie)
            RETURN
                m.movie_id AS movie_id,
                m.title AS title,
                m.vote_average AS vote_average,
                coalesce(lk.liked_at, lk.liked_date) AS liked_at,
                lk.source AS source
            ORDER BY coalesce(lk.liked_at, lk.liked_date) DESC
            SKIP $skip LIMIT $limit
            """,
            uid=user_id, skip=skip, limit=limit,
        )
        items = [dict(r) for r in rows]
    return {"user_id": user_id, "total": len(items), "items": items}


@app.post("/users/{user_id}/likes", tags=["interactions"])
def add_like(user_id: str, movie_id: str):
    with driver.session(database=NEO4J_DATABASE) as session:
        require_user(session, user_id)
        require_movie(session, movie_id)
        session.run(
            """
            MATCH (u:User {user_id: $uid}), (m:Movie {movie_id: $mid})
            MERGE (u)-[lk:LIKED]->(m)
            SET lk.liked_at = date(),
                lk.liked_date = date(),
                lk.source = 'manual',
                lk.last_updated = date()
            """,
            uid=user_id, mid=movie_id,
        )
    return {"user_id": user_id, "movie_id": movie_id, "status": "liked"}


@app.delete("/users/{user_id}/likes/{movie_id}", tags=["interactions"])
def remove_like(user_id: str, movie_id: str):
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(
            """
            MATCH (u:User {user_id: $uid})-[lk:LIKED]->(m:Movie {movie_id: $mid})
            DELETE lk
            RETURN count(lk) AS affected
            """,
            uid=user_id, mid=movie_id,
        ).single()
    if not result or result["affected"] == 0:
        raise HTTPException(status_code=404, detail="Like not found")
    return {"user_id": user_id, "movie_id": movie_id, "status": "removed"}


# ============================================================
# COLECCIONES
# ============================================================

@app.get("/users/{user_id}/collections", tags=["collections"])
def get_collections(user_id: str):
    with driver.session(database=NEO4J_DATABASE) as session:
        require_user(session, user_id)
        rows = session.run(
            """
            MATCH (u:User {user_id: $uid})-[cr:CREATED]->(c:Collection)
            OPTIONAL MATCH (c)-[:CONTAINS]->(m:Movie)
            RETURN
                c.collection_id AS collection_id,
                c.name AS name,
                c.description AS description,
                coalesce(cr.created_at, cr.created_date) AS created_at,
                count(m) AS movie_count
            ORDER BY coalesce(cr.created_at, cr.created_date) DESC
            """,
            uid=user_id,
        )
        items = [dict(r) for r in rows]
    return {"user_id": user_id, "total": len(items), "items": items}


@app.post("/users/{user_id}/collections", tags=["collections"])
def create_collection(user_id: str, payload: CollectionCreateRequest):
    collection_id = f"COL_{uuid.uuid4().hex[:12].upper()}"
    with driver.session(database=NEO4J_DATABASE) as session:
        require_user(session, user_id)
        session.run(
            """
            MATCH (u:User {user_id: $uid})
            CREATE (c:Collection {
                collection_id: $cid,
                name: $name,
                description: $desc,
                created_at: date()
            })
            CREATE (u)-[cr:CREATED {created_at: date(), title: 'custom', public: false, source: 'user'}]->(c)
            """,
            uid=user_id,
            cid=collection_id,
            name=payload.name,
            desc=payload.description or "",
        )
    return {
        "user_id": user_id,
        "collection_id": collection_id,
        "name": payload.name,
        "status": "created",
    }


@app.patch("/users/{user_id}/collections/{collection_id}", tags=["collections"])
def update_collection(user_id: str, collection_id: str, payload: CollectionUpdateRequest):
    updates: Dict[str, Any] = {}
    if payload.name is not None:
        updates["name"] = payload.name
    if payload.description is not None:
        updates["description"] = payload.description
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")
    with driver.session(database=NEO4J_DATABASE) as session:
        require_user(session, user_id)
        result = session.run(
            """
            MATCH (u:User {user_id: $uid})-[:CREATED]->(c:Collection {collection_id: $cid})
            SET c += $updates
            RETURN c.collection_id AS collection_id, c.name AS name, c.description AS description
            """,
            uid=user_id, cid=collection_id, updates=updates,
        ).single()
    if not result:
        raise HTTPException(status_code=404, detail="Collection not found or not owned by user")
    return dict(result)


@app.delete("/users/{user_id}/collections/{collection_id}", tags=["collections"])
def delete_collection(user_id: str, collection_id: str):
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(
            """
            MATCH (u:User {user_id: $uid})-[:CREATED]->(c:Collection {collection_id: $cid})
            DETACH DELETE c
            RETURN count(*) AS affected
            """,
            uid=user_id, cid=collection_id,
        ).single()
    if not result or result["affected"] == 0:
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"status": "deleted", "collection_id": collection_id}


@app.post("/users/{user_id}/collections/{collection_id}/movies", tags=["collections"])
def add_movie_to_collection(user_id: str, collection_id: str, movie_id: str):
    with driver.session(database=NEO4J_DATABASE) as session:
        require_user(session, user_id)
        require_movie(session, movie_id)
        result = session.run(
            """
            MATCH (u:User {user_id: $uid})-[:CREATED]->(c:Collection {collection_id: $cid})
            MATCH (m:Movie {movie_id: $mid})
            MERGE (c)-[cn:CONTAINS]->(m)
            SET cn.added_date = date(),
                cn.added_by = $uid,
                cn.position = 0
            RETURN c.collection_id AS collection_id
            """,
            uid=user_id, cid=collection_id, mid=movie_id,
        ).single()
    if not result:
        raise HTTPException(status_code=404, detail="Collection not found or not owned by user")
    return {"collection_id": collection_id, "movie_id": movie_id, "status": "added"}


@app.delete("/users/{user_id}/collections/{collection_id}/movies/{movie_id}", tags=["collections"])
def remove_movie_from_collection(user_id: str, collection_id: str, movie_id: str):
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(
            """
            MATCH (u:User {user_id: $uid})-[:CREATED]->(c:Collection {collection_id: $cid})
                  -[cn:CONTAINS]->(m:Movie {movie_id: $mid})
            DELETE cn
            RETURN count(cn) AS affected
            """,
            uid=user_id, cid=collection_id, mid=movie_id,
        ).single()
    if not result or result["affected"] == 0:
        raise HTTPException(status_code=404, detail="Movie not found in collection")
    return {"collection_id": collection_id, "movie_id": movie_id, "status": "removed"}


# ============================================================
# AMIGOS
# ============================================================

@app.get("/users/{user_id}/friends", tags=["social"])
def get_friends(user_id: str, skip: int = 0, limit: int = 50):
    with driver.session(database=NEO4J_DATABASE) as session:
        require_user(session, user_id)
        rows = session.run(
            """
            MATCH (u:User {user_id: $uid})-[f:FRIEND_OF]-(friend:User)
            RETURN
                friend.user_id AS user_id,
                friend.name AS name,
                f.since_date AS since_date,
                f.closeness AS closeness,
                f.interactions AS interactions
            ORDER BY f.closeness DESC
            SKIP $skip LIMIT $limit
            """,
            uid=user_id, skip=skip, limit=limit,
        )
        items = [dict(r) for r in rows]
    return {"user_id": user_id, "total": len(items), "items": items}


@app.post("/users/{user_id}/friends", tags=["social"])
def add_friend(user_id: str, payload: FriendRequest):
    if user_id == payload.friend_id:
        raise HTTPException(status_code=400, detail="A user cannot be their own friend")
    with driver.session(database=NEO4J_DATABASE) as session:
        require_user(session, user_id)
        require_user(session, payload.friend_id)
        session.run(
            """
            MATCH (u:User {user_id: $uid}), (f:User {user_id: $fid})
            MERGE (u)-[r:FRIEND_OF]-(f)
            SET r.since_date = coalesce(r.since_date, date()),
                r.closeness = $closeness,
                r.interactions = coalesce(r.interactions, 0) + 1,
                r.last_updated = date()
            """,
            uid=user_id, fid=payload.friend_id, closeness=payload.closeness,
        )
    return {"user_id": user_id, "friend_id": payload.friend_id, "status": "added"}


@app.delete("/users/{user_id}/friends/{friend_id}", tags=["social"])
def remove_friend(user_id: str, friend_id: str):
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(
            """
            MATCH (u:User {user_id: $uid})-[r:FRIEND_OF]-(f:User {user_id: $fid})
            DELETE r
            RETURN count(r) AS affected
            """,
            uid=user_id, fid=friend_id,
        ).single()
    if not result or result["affected"] == 0:
        raise HTTPException(status_code=404, detail="Friendship not found")
    return {"user_id": user_id, "friend_id": friend_id, "status": "removed"}