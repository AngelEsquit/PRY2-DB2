import os
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase


NODE_QUERIES = OrderedDict(
    [
        ("Movie", "MATCH (n:Movie) RETURN count(n) AS c"),
        ("User", "MATCH (n:User) RETURN count(n) AS c"),
        ("Genre", "MATCH (n:Genre) RETURN count(n) AS c"),
        ("Director", "MATCH (n:Director) RETURN count(n) AS c"),
        ("Language", "MATCH (n:Language) RETURN count(n) AS c"),
        ("Collection", "MATCH (n:Collection) RETURN count(n) AS c"),
    ]
)

REL_QUERIES = OrderedDict(
    [
        ("DIRECTED", "MATCH ()-[r:DIRECTED]->() RETURN count(r) AS c"),
        ("HAS_GENRE", "MATCH ()-[r:HAS_GENRE]->() RETURN count(r) AS c"),
        ("IN_LANGUAGE", "MATCH ()-[r:IN_LANGUAGE]->() RETURN count(r) AS c"),
        ("CONTAINS", "MATCH ()-[r:CONTAINS]->() RETURN count(r) AS c"),
        ("VIEWED", "MATCH ()-[r:VIEWED]->() RETURN count(r) AS c"),
        ("RATED", "MATCH ()-[r:RATED]->() RETURN count(r) AS c"),
        ("PREFERS", "MATCH ()-[r:PREFERS]->() RETURN count(r) AS c"),
        ("FRIEND_OF", "MATCH ()-[r:FRIEND_OF]-() RETURN count(r) AS c"),
        ("WATCHLISTED", "MATCH ()-[r:WATCHLISTED]->() RETURN count(r) AS c"),
        ("LIKED", "MATCH ()-[r:LIKED]->() RETURN count(r) AS c"),
        ("FOLLOWS_DIRECTOR", "MATCH ()-[r:FOLLOWS_DIRECTOR]->() RETURN count(r) AS c"),
        ("CREATED", "MATCH ()-[r:CREATED]->() RETURN count(r) AS c"),
    ]
)

CHECK_QUERIES = OrderedDict(
    [
        (
            "movies_without_genre",
            "MATCH (m:Movie) WHERE NOT (m)-[:HAS_GENRE]->(:Genre) RETURN count(m) AS c",
        ),
        (
            "movies_without_director",
            "MATCH (m:Movie) WHERE NOT (:Director)-[:DIRECTED]->(m) RETURN count(m) AS c",
        ),
        (
            "users_without_interactions",
            "MATCH (u:User) WHERE NOT (u)-[:VIEWED|RATED|PREFERS|FRIEND_OF]-() RETURN count(u) AS c",
        ),
        (
            "isolated_nodes",
            "MATCH (n) WHERE NOT (n)--() RETURN count(n) AS c",
        ),
        (
            "collections_without_creator",
            "MATCH (c:Collection) WHERE NOT (:User)-[:CREATED]->(c) RETURN count(c) AS c",
        ),
        (
            "collections_without_movies",
            "MATCH (c:Collection) WHERE NOT (c)-[:CONTAINS]->(:Movie) RETURN count(c) AS c",
        ),
    ]
)

MIN_NODE_PROPS = OrderedDict(
    [
        ("Movie", 5),
        ("User", 5),
        ("Genre", 5),
        ("Director", 5),
        ("Language", 5),
        ("Collection", 5),
    ]
)

MIN_REL_PROPS = OrderedDict(
    [
        ("DIRECTED", 3),
        ("HAS_GENRE", 3),
        ("IN_LANGUAGE", 3),
        ("CONTAINS", 3),
        ("VIEWED", 3),
        ("RATED", 3),
        ("PREFERS", 3),
        ("FRIEND_OF", 3),
        ("WATCHLISTED", 3),
        ("LIKED", 3),
        ("FOLLOWS_DIRECTOR", 3),
        ("CREATED", 3),
    ]
)


def run_scalar(session, query: str):
    return session.run(query).single()["c"]


def count_nodes_below_property_threshold(session, label: str, min_props: int) -> int:
    query = f"""
    MATCH (n:{label})
    WHERE size(keys(n)) < $min_props
    RETURN count(n) AS c
    """
    return session.run(query, min_props=min_props).single()["c"]


def count_relationships_below_property_threshold(session, rel_type: str, min_props: int) -> int:
    query = f"""
    MATCH ()-[r:{rel_type}]-()
    WHERE size(keys(r)) < $min_props
    RETURN count(r) AS c
    """
    return session.run(query, min_props=min_props).single()["c"]


def pick_seed_node(session):
    record = session.run(
        """
        MATCH (seed)
        OPTIONAL MATCH (seed)-[r]-()
        WITH seed, count(r) AS degree
        ORDER BY degree DESC
        LIMIT 1
        RETURN labels(seed) AS labels, properties(seed) AS props, degree
        """
    ).single()
    return record


def connectivity_check(session):
    seed_record = pick_seed_node(session)
    if not seed_record:
        return {"seed_labels": [], "seed_repr": "<no seed node>", "total_others": 0, "reachable_others": 0, "unreachable_others": 0}

    seed_labels = seed_record["labels"]
    seed_props = seed_record["props"]
    seed_repr = seed_props.get("movie_id") or seed_props.get("user_id") or seed_props.get("name") or "seed"

    result = session.run(
        """
        MATCH (seed)
        OPTIONAL MATCH (seed)-[r]-()
        WITH seed, count(r) AS degree
        ORDER BY degree DESC
        LIMIT 1
        MATCH (n)
            WHERE elementId(n) <> elementId(seed)
        OPTIONAL MATCH p = shortestPath((seed)-[*]-(n))
        RETURN
            count(n) AS total_others,
            sum(CASE WHEN p IS NULL THEN 0 ELSE 1 END) AS reachable_others,
            sum(CASE WHEN p IS NULL THEN 1 ELSE 0 END) AS unreachable_others
        """
    ).single()

    return {
        "seed_labels": seed_labels,
        "seed_repr": seed_repr,
        "total_others": result["total_others"],
        "reachable_others": result["reachable_others"],
        "unreachable_others": result["unreachable_others"],
    }


def main():
    load_dotenv()

    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USERNAME")
    pwd = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    missing = [key for key, value in {"NEO4J_URI": uri, "NEO4J_USERNAME": user, "NEO4J_PASSWORD": pwd}.items() if not value]
    if missing:
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")

    root = Path(__file__).resolve().parents[1]
    report_path = root / "validation_post_load_report.md"

    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with driver.session(database=database) as session:
        total_nodes = run_scalar(session, "MATCH (n) RETURN count(n) AS c")
        total_relationships = run_scalar(session, "MATCH ()-[r]->() RETURN count(r) AS c")

        node_counts = OrderedDict((name, run_scalar(session, query)) for name, query in NODE_QUERIES.items())
        rel_counts = OrderedDict((name, run_scalar(session, query)) for name, query in REL_QUERIES.items())
        checks = OrderedDict((name, run_scalar(session, query)) for name, query in CHECK_QUERIES.items())
        node_property_checks = OrderedDict(
            (label, count_nodes_below_property_threshold(session, label, min_props))
            for label, min_props in MIN_NODE_PROPS.items()
        )
        rel_property_checks = OrderedDict(
            (rel_type, count_relationships_below_property_threshold(session, rel_type, min_props))
            for rel_type, min_props in MIN_REL_PROPS.items()
        )
        connectivity = connectivity_check(session)

    driver.close()

    passed = True
    failures = []

    if total_nodes < 5000:
        passed = False
        failures.append(f"Total de nodos menor al mínimo: {total_nodes}")
    if checks["movies_without_genre"] > 0:
        passed = False
        failures.append(f"Películas sin género: {checks['movies_without_genre']}")
    if checks["movies_without_director"] > 0:
        passed = False
        failures.append(f"Películas sin director: {checks['movies_without_director']}")
    if checks["users_without_interactions"] > 0:
        passed = False
        failures.append(f"Usuarios sin interacciones: {checks['users_without_interactions']}")
    if checks["isolated_nodes"] > 0:
        passed = False
        failures.append(f"Nodos aislados: {checks['isolated_nodes']}")
    if checks["collections_without_creator"] > 0:
        passed = False
        failures.append(f"Colecciones sin creador: {checks['collections_without_creator']}")
    if checks["collections_without_movies"] > 0:
        passed = False
        failures.append(f"Colecciones sin películas: {checks['collections_without_movies']}")
    for label, count in node_property_checks.items():
        if count > 0:
            passed = False
            failures.append(f"Nodos {label} con menos de {MIN_NODE_PROPS[label]} propiedades: {count}")
    for rel_type, count in rel_property_checks.items():
        if count > 0:
            passed = False
            failures.append(f"Relaciones {rel_type} con menos de {MIN_REL_PROPS[rel_type]} propiedades: {count}")
    if connectivity["unreachable_others"] > 0:
        passed = False
        failures.append(f"Nodos no alcanzables desde el seed: {connectivity['unreachable_others']}")

    status = "PASS" if passed else "FAIL"

    lines = []
    lines.append("# Validación Post Carga")
    lines.append("")
    lines.append(f"- Fecha: {timestamp}")
    lines.append(f"- Estado: **{status}**")
    lines.append(f"- Base de datos: `{database}`")
    lines.append("")
    lines.append("## Resumen")
    lines.append("")
    lines.append(f"- Total de nodos: {total_nodes}")
    lines.append(f"- Total de relaciones: {total_relationships}")
    lines.append("")
    lines.append("## Conteo de nodos")
    lines.append("")
    for label, count in node_counts.items():
        lines.append(f"- {label}: {count}")
    lines.append("")
    lines.append("## Conteo de relaciones")
    lines.append("")
    for rel, count in rel_counts.items():
        lines.append(f"- {rel}: {count}")
    lines.append("")
    lines.append("## Controles de integridad")
    lines.append("")
    for name, count in checks.items():
        lines.append(f"- {name}: {count}")
    lines.append("")
    lines.append("## Validación de propiedades mínimas")
    lines.append("")
    lines.append("### Nodos con menos propiedades de las requeridas")
    lines.append("")
    for label, count in node_property_checks.items():
        lines.append(f"- {label} (< {MIN_NODE_PROPS[label]} props): {count}")
    lines.append("")
    lines.append("### Relaciones con menos propiedades de las requeridas")
    lines.append("")
    for rel_type, count in rel_property_checks.items():
        lines.append(f"- {rel_type} (< {MIN_REL_PROPS[rel_type]} props): {count}")
    lines.append("")
    lines.append("## Conectividad")
    lines.append("")
    lines.append(f"- Seed elegido: {connectivity['seed_repr']} {connectivity['seed_labels']}")
    lines.append(f"- Nodos restantes: {connectivity['total_others']}")
    lines.append(f"- Alcanzables desde seed: {connectivity['reachable_others']}")
    lines.append(f"- No alcanzables desde seed: {connectivity['unreachable_others']}")
    lines.append("")
    lines.append("## Conclusión")
    lines.append("")
    if passed:
        lines.append("La carga cumple la validación formal básica post carga.")
    else:
        lines.append("La carga necesita ajustes antes de darla por válida.")
        lines.append("")
        lines.append("### Fallos detectados")
        for failure in failures:
            lines.append(f"- {failure}")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Estado: {status}")
    print(f"Total nodos: {total_nodes}")
    print(f"Total relaciones: {total_relationships}")
    for label, count in node_counts.items():
        print(f"[NODE] {label}: {count}")
    for rel, count in rel_counts.items():
        print(f"[REL] {rel}: {count}")
    for name, count in checks.items():
        print(f"[CHECK] {name}: {count}")
    for label, count in node_property_checks.items():
        print(f"[NODE_PROPS] {label} (<{MIN_NODE_PROPS[label]}): {count}")
    for rel_type, count in rel_property_checks.items():
        print(f"[REL_PROPS] {rel_type} (<{MIN_REL_PROPS[rel_type]}): {count}")
    print(
        f"[CONNECTIVITY] seed={connectivity['seed_repr']} labels={connectivity['seed_labels']} "
        f"reachable={connectivity['reachable_others']} unreachable={connectivity['unreachable_others']}"
    )
    print(f"Reporte escrito en: {report_path}")

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
