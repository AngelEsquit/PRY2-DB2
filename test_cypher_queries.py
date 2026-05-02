#!/usr/bin/env python
"""Test script to execute the 6 demo Cypher queries"""

import os
import sys
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USERNAME") or os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")
database = os.getenv("NEO4J_DATABASE", "neo4j")

if not uri or not user or not password:
    print("ERROR: Missing Neo4j env vars. Required: NEO4J_URI, NEO4J_USERNAME/NEO4J_USER, NEO4J_PASSWORD")
    sys.exit(2)

driver = GraphDatabase.driver(uri, auth=(user, password))

queries = [
    {
        "name": "Query 1: Top genres by consumption",
        "query": """
MATCH (u:User)-[:VIEWED|RATED|LIKED]->(m:Movie)-[:HAS_GENRE]->(g:Genre)
RETURN g.name AS genre, count(DISTINCT m) AS movies, count(*) AS interactions
ORDER BY interactions DESC
LIMIT 10;
        """
    },
    {
        "name": "Query 2: Most active users",
        "query": """
MATCH (u:User)
OPTIONAL MATCH (u)-[r:VIEWED|RATED|LIKED|WATCHLISTED]->(:Movie)
RETURN u.user_id AS user_id, u.name AS name, count(r) AS total_actions
ORDER BY total_actions DESC
LIMIT 15;
        """
    },
    {
        "name": "Query 3: Most followed directors",
        "query": """
MATCH (u:User)-[:FOLLOWS_DIRECTOR]->(d:Director)
RETURN d.director_id AS director_id, d.name AS director, count(u) AS followers
ORDER BY followers DESC
LIMIT 15;
        """
    },
    {
        "name": "Query 4: Jaccard similarity (non-APOC version)",
        "query": """
MATCH (u1:User {user_id: 'U00001'})-[:LIKED|RATED]->(m:Movie)
WITH collect(DISTINCT m.movie_id) AS a
MATCH (u2:User {user_id: 'U00002'})-[:LIKED|RATED]->(m:Movie)
WITH a, collect(DISTINCT m.movie_id) AS b
WITH a, b, [x IN a WHERE x IN b] AS inter
RETURN
  size(inter) AS intersection,
  size(a) + size([x IN b WHERE NOT x IN a]) AS union_size,
  CASE WHEN (size(a) + size([x IN b WHERE NOT x IN a])) = 0
       THEN 0.0
       ELSE toFloat(size(inter)) / toFloat(size(a) + size([x IN b WHERE NOT x IN a]))
  END AS jaccard_score;
        """
    },
    {
        "name": "Query 5: Candidate recommendations for user",
        "query": """
MATCH (u:User {user_id: 'U00001'})
MATCH (u)-[:FRIEND_OF]-(f:User)
MATCH (f)-[:LIKED|RATED]->(m:Movie)
WHERE NOT (u)-[:VIEWED|RATED]->(m)
OPTIONAL MATCH (m)-[:HAS_GENRE]->(g:Genre)
RETURN m.movie_id AS movie_id,
       m.title AS title,
    m.vote_average AS vote_average,
       count(DISTINCT f) AS friend_support,
       collect(DISTINCT g.name)[0..3] AS genres
ORDER BY friend_support DESC, vote_average DESC
LIMIT 20;
        """
    },
    {
        "name": "Query 6: Graph connectivity - Isolated nodes check",
        "query": """
MATCH (n)
WHERE NOT (n)--()
RETURN labels(n) AS labels, count(*) AS count
LIMIT 25;
        """
    },
]

has_errors = False

with driver.session(database=database) as session:
    for idx, q in enumerate(queries, 1):
        print(f"\n{'='*80}")
        print(f"{q['name']}")
        print(f"{'='*80}")
        try:
            result = session.run(q['query'])
            records = list(result)
            if records:
                print(f"Result count: {len(records)}\n")
                for i, record in enumerate(records[:5], 1):
                    print(f"  Row {i}: {dict(record)}")
                if len(records) > 5:
                    print(f"  ... and {len(records) - 5} more rows")
            else:
                print("No results")
        except Exception as e:
            has_errors = True
            print(f"ERROR: {str(e)}")

driver.close()
print(f"\n{'='*80}")
if has_errors:
    print("x One or more queries failed")
    sys.exit(1)

print("✓ All 6 queries executed successfully")
