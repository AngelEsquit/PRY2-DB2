# Validación Post Carga

- Fecha: 2026-05-03 11:58:18
- Estado: **PASS**
- Base de datos: `de905a51`

## Resumen

- Total de nodos: 13828
- Total de relaciones: 215854

## Conteo de nodos

- Movie: 4803
- User: 2200
- Genre: 19
- Director: 2350
- Language: 37
- Collection: 4419

## Conteo de relaciones

- DIRECTED: 4803
- HAS_GENRE: 12113
- IN_LANGUAGE: 4803
- CONTAINS: 32226
- VIEWED: 72530
- RATED: 39967
- PREFERS: 6668
- FRIEND_OF: 21984
- WATCHLISTED: 11150
- LIKED: 8665
- FOLLOWS_DIRECTOR: 7518
- CREATED: 4419

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
- Director (< 5 props): 1
- Language (< 5 props): 0
- Collection (< 5 props): 0

### Relaciones con menos propiedades de las requeridas

- DIRECTED (< 3 props): 60
- HAS_GENRE (< 3 props): 56
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
- Nodos restantes: 13827
- Alcanzables desde seed: 13827
- No alcanzables desde seed: 0

## Conclusión

La carga cumple la validación formal básica post carga.

### Observaciones no críticas
- Nodos Director con menos de 5 propiedades: 1
- Relaciones DIRECTED con menos de 3 propiedades: 60
- Relaciones HAS_GENRE con menos de 3 propiedades: 56
