# Consultas Cypher de Demo (4-6 requeridas)

Este set esta alineado al modelo actual y al caso de uso de recomendacion/red social.

## Consulta 1 - Top generos por consumo

Objetivo: agregacion por genero con evidencia de interacciones de usuarios.

```cypher
MATCH (u:User)-[:VIEWED|RATED|LIKED]->(m:Movie)-[:HAS_GENRE]->(g:Genre)
RETURN g.name AS genre, count(DISTINCT m) AS movies, count(*) AS interactions
ORDER BY interactions DESC
LIMIT 10;
```

## Consulta 2 - Usuarios mas activos

Objetivo: mostrar actividad social y de contenido por usuario.

```cypher
MATCH (u:User)
OPTIONAL MATCH (u)-[r:VIEWED|RATED|LIKED|WATCHLISTED]->(:Movie)
RETURN u.user_id AS user_id, u.name AS name, count(r) AS total_actions
ORDER BY total_actions DESC
LIMIT 15;
```

## Consulta 3 - Directores mas seguidos por usuarios

Objetivo: demostrar relacion social de afinidad a creadores.

```cypher
MATCH (u:User)-[:FOLLOWS_DIRECTOR]->(d:Director)
RETURN d.director_id AS director_id, d.name AS director, count(u) AS followers
ORDER BY followers DESC
LIMIT 15;
```

## Consulta 4 - Similitud entre dos usuarios (Jaccard)

Objetivo: evidencia del algoritmo base colaborativo del proyecto.

Cambiar U00001 y U00002 por ids reales del dataset.

```cypher
MATCH (u1:User {user_id: 'U00001'})
MATCH (u2:User {user_id: 'U00002'})
OPTIONAL MATCH (u1)-[:LIKED]->(m1:Movie)
OPTIONAL MATCH (u1)-[r1:RATED]->(m1r:Movie)
WHERE r1.rating >= 8
WITH u1, u2, collect(DISTINCT m1.movie_id) + collect(DISTINCT m1r.movie_id) AS set1
OPTIONAL MATCH (u2)-[:LIKED]->(m2:Movie)
OPTIONAL MATCH (u2)-[r2:RATED]->(m2r:Movie)
WHERE r2.rating >= 8
WITH set1, collect(DISTINCT m2.movie_id) + collect(DISTINCT m2r.movie_id) AS set2
WITH apoc.coll.toSet(set1) AS a, apoc.coll.toSet(set2) AS b
RETURN
  size([x IN a WHERE x IN b]) AS intersection,
  size(apoc.coll.toSet(a + b)) AS union_size,
  CASE WHEN size(apoc.coll.toSet(a + b)) = 0
       THEN 0.0
       ELSE toFloat(size([x IN a WHERE x IN b])) / toFloat(size(apoc.coll.toSet(a + b)))
  END AS jaccard_score;
```

Nota: si no tienes APOC habilitado en Aura, usa la version alternativa sin APOC.

```cypher
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
```

## Consulta 5 - Recomendaciones candidatas para un usuario

Objetivo: mostrar peliculas no vistas con senal social de vecinos/amigos.

Cambiar U00001 por id real.

```cypher
MATCH (u:User {user_id: 'U00001'})
MATCH (u)-[:FRIEND_OF]-(f:User)
MATCH (f)-[:LIKED|RATED]->(m:Movie)
WHERE NOT (u)-[:VIEWED|RATED]->(m)
OPTIONAL MATCH (m)-[:HAS_GENRE]->(g:Genre)
RETURN m.movie_id AS movie_id,
       m.title AS title,
       count(DISTINCT f) AS friend_support,
       collect(DISTINCT g.name)[0..3] AS genres
ORDER BY friend_support DESC, m.vote_average DESC
LIMIT 20;
```

## Consulta 6 - Integridad y conectividad basica

Objetivo: evidencia de que no hay nodos aislados (parte de grafo conexo).

```cypher
MATCH (n)
WHERE NOT (n)--()
RETURN labels(n) AS labels, properties(n) AS props
LIMIT 25;
```

Si regresa vacio, no hay nodos aislados.
