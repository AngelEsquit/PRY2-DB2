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

## Consulta 4 - Similitud entre usuarios (Jaccard)

Objetivo: mostrar similitud de gustos entre dos usuarios usando Jaccard sobre peliculas vistas/valoradas.

```cypher
// 1. Buscamos pares de usuarios que compartan al menos una película
MATCH (u1:User)-[:LIKED|RATED]->(m:Movie)<-[:LIKED|RATED]-(u2:User)
WHERE id(u1) < id(u2) // Evita duplicados (A-B y B-A) y compararse consigo mismo

// 2. Obtenemos las listas de películas de cada uno para el cálculo
MATCH (u1)-[:LIKED|RATED]->(m1:Movie)
WITH u1, u2, collect(DISTINCT m1.movie_id) AS a
MATCH (u2)-[:LIKED|RATED]->(m2:Movie)
WITH u1, u2, a, collect(DISTINCT m2.movie_id) AS b

// 3. Calculamos intersección y unión
WITH u1, u2, a, b, [x IN a WHERE x IN b] AS inter
WITH u1, u2, 
     size(inter) AS intersection, 
     (size(a) + size([x IN b WHERE NOT x IN a])) AS union_size

// 4. Calculamos el score y filtramos
WITH u1, u2, intersection, union_size,
     toFloat(intersection) / toFloat(union_size) AS jaccard_score
WHERE jaccard_score > 0

RETURN u1.user_id AS UserA, u2.user_id AS UserB, jaccard_score
ORDER BY jaccard_score DESC
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
