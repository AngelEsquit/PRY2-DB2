import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase


def main():
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env")

    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USERNAME")
    pwd = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    if not uri or not user or not pwd:
        raise ValueError("Missing NEO4J_URI, NEO4J_USERNAME or NEO4J_PASSWORD in .env")

    driver = GraphDatabase.driver(uri, auth=(user, pwd))

    with driver.session(database=database) as session:
        drama_count = session.run(
            "MATCH (g:Genre {name: 'Drama'}) RETURN count(g) AS c"
        ).single()["c"]
        if drama_count == 0:
            raise RuntimeError("Drama genre not found. Expected it to already exist in the graph.")

        unknown_director = session.run(
            """
            MERGE (d:Director {director_id: 'UNKNOWN_DIRECTOR'})
            SET d.name = 'Unknown Director'
            RETURN d.director_id AS director_id
            """
        ).single()["director_id"]

        fill_genre_result = session.run(
            """
            MATCH (m:Movie)
            WHERE NOT (m)-[:HAS_GENRE]->(:Genre)
            WITH m
            MATCH (g:Genre {name: 'Drama'})
            MERGE (m)-[r:HAS_GENRE]->(g)
            SET r.source = 'fallback',
                r.last_updated = date()
            RETURN count(m) AS affected
            """
        ).single()["affected"]

        fill_director_result = session.run(
            """
            MATCH (m:Movie)
            WHERE NOT (:Director)-[:DIRECTED]->(m)
            WITH m
            MATCH (d:Director {director_id: 'UNKNOWN_DIRECTOR'})
            MERGE (d)-[r:DIRECTED]->(m)
            SET r.source = 'fallback',
                r.last_updated = date()
            RETURN count(m) AS affected
            """
        ).single()["affected"]

        print(f"Drama genre found: {drama_count}")
        print(f"Fallback director: {unknown_director}")
        print(f"Movies updated with fallback genre: {fill_genre_result}")
        print(f"Movies updated with fallback director: {fill_director_result}")

    driver.close()


if __name__ == "__main__":
    main()
