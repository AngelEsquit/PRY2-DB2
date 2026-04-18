# ETAPA 02 - Diseño del Grafo


## 1) Diagrama

```mermaid
graph TD
    classDef userProfile fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#01579b;
    classDef movieContent fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#e65100;
    classDef metadata fill:#f3e5f5,stroke:#4a148c,stroke-width:2px,color:#4a148c;
    classDef social fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px,color:#1b5e20;

    subgraph User_Core [Núcleo de Usuario]
        U[User: user_id, name, age, country, register_date, premium, favorite_languages, preferred_genres]:::userProfile
    end

    subgraph Media_Core [Núcleo de Contenido]
        M[Movie: movie_id, title, original_language, release_date, runtime, budget, revenue, vote_average, popularity]:::movieContent
        C[Collection: collection_id, name, created_at, public, followers_count]:::social
    end

    subgraph Attributes [Atributos y Taxonomía]
        G[Genre: name]:::metadata
        D[Director: director_id, name]:::metadata
        L[Language: code, name, region, family, rtl]:::metadata
    end

    %% Relaciones de interacción y preferencia
    U ==>|VIEWED| M
    U -.->|RATED| M
    U -.->|PREFERS| G
    U ---|FRIEND_OF| U
    M -->|HAS_GENRE| G
    D -->|DIRECTED| M

    %% Relaciones de organización y afinidad
    M -->|IN_LANGUAGE| L
    U -.->|WATCHLISTED| M
    U -.->|LIKED| M
    U -.->|FOLLOWS_DIRECTOR| D
    U ==>|CREATED| C
    C -->|CONTAINS| M

    linkStyle default stroke:#555,stroke-width:1px;
```

## 2) Labels y propiedades

### User
- `user_id`: string
- `name`: string
- `age`: integer
- `country`: string
- `register_date`: date
- `premium`: boolean
- `favorite_languages`: list<string>
- `preferred_genres`: list<string>

### Movie
- `movie_id`: string
- `title`: string
- `original_language`: string
- `original_title`: string
- `release_date`: date
- `runtime`: float
- `budget`: integer
- `revenue`: integer
- `vote_average`: float
- `popularity`: float

### Genre
- `name`: string
- `description`: string
- `popularity_index`: float
- `active`: boolean
- `created_at`: date

### Director
- `director_id`: string
- `name`: string
- `nationality`: string
- `birth_date`: date
- `active`: boolean

### Language
- `code`: string
- `name`: string
- `region`: string
- `family`: string
- `rtl`: boolean

### Collection
- `collection_id`: string
- `name`: string
- `created_at`: date
- `public`: boolean
- `followers_count`: integer

## 3) Tipos de relación

1. `VIEWED` (User -> Movie)
2. `RATED` (User -> Movie)
3. `PREFERS` (User -> Genre)
4. `FRIEND_OF` (User <-> User)
5. `HAS_GENRE` (Movie -> Genre)
6. `DIRECTED` (Director -> Movie)
7. `IN_LANGUAGE` (Movie -> Language)
8. `WATCHLISTED` (User -> Movie)
9. `LIKED` (User -> Movie)
10. `FOLLOWS_DIRECTOR` (User -> Director)
11. `CONTAINS` (Collection -> Movie)
12. `CREATED` (User -> Collection)