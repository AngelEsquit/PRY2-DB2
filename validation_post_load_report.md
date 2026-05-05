# Validación Post Carga

- Fecha: 2026-05-05 16:38:53
- Estado: **PASS**
- Base de datos: `de905a51`

## Resumen

- Total de nodos: 13836
- Total de relaciones: 215876

## Conteo de nodos

- Movie: 4803
- User: 2200
- Genre: 20
- Director: 2350
- Language: 37
- Collection: 4426

## Conteo de relaciones

- DIRECTED: 4803
- HAS_GENRE: 12114
- IN_LANGUAGE: 4803
- CONTAINS: 32234
- VIEWED: 72530
- RATED: 39967
- PREFERS: 6668
- FRIEND_OF: 21984
- WATCHLISTED: 11151
- LIKED: 8670
- FOLLOWS_DIRECTOR: 7518
- CREATED: 4426

## Controles de integridad

- movies_without_genre: 0
- movies_without_director: 0
- users_without_interactions: 0
- isolated_nodes: 0
- collections_without_creator: 0
- collections_without_movies: 0

## Validación de propiedades mínimas

### Nodos con menos propiedades de las requeridas

- Movie (< 5 props): 0
- User (< 5 props): 0
- Genre (< 5 props): 0
- Director (< 5 props): 0
- Language (< 5 props): 0
- Collection (< 5 props): 0

### Relaciones con menos propiedades de las requeridas

- DIRECTED (< 3 props): 0
- HAS_GENRE (< 3 props): 0
- IN_LANGUAGE (< 3 props): 0
- CONTAINS (< 3 props): 0
- VIEWED (< 3 props): 0
- RATED (< 3 props): 0
- PREFERS (< 3 props): 0
- FRIEND_OF (< 3 props): 0
- WATCHLISTED (< 3 props): 0
- LIKED (< 3 props): 0
- FOLLOWS_DIRECTOR (< 3 props): 0
- CREATED (< 3 props): 0

## Conectividad

- Seed elegido: English ['Language']
- Nodos restantes: 13835
- Alcanzables desde seed: 13835
- No alcanzables desde seed: 0

## Conclusión

La carga cumple la validación formal básica post carga.
