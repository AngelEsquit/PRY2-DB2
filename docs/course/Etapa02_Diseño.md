# ETAPA 02 - Diseño del Grafo

## 0) Caso de Uso: Motor de Recomendación

Descripcion: Sistema de recomendación de peliculas basado en similitud colaborativa (Jaccard) que analiza preferencias de usuarios similares para sugerir contenido personalizado.

Flujo:
1. Calcular similitud Jaccard entre peliculas calificadas/favoritas de usuarios
2. Identificar usuarios con gustos similares
3. Recomendar peliculas que usuarios similares han visto/calificado positivamente pero que el usuario objetivo aun no ha visto
4. Filtrar por preferencias de contenido (generos, idiomas, directores)

Valor: Personalizacion basada en red social + analisis de contenido

---

## 1) Diagrama

\\\mermaid
graph TD
    classDef userProfile fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#01579b;
    classDef movieContent fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#e65100;
    classDef metadata fill:#f3e5f5,stroke:#4a148c,stroke-width:2px,color:#4a148c;
    classDef social fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px,color:#1b5e20;

    subgraph User_Core [Nucleo de Usuario]
        U[User: user_id, name, age, country, register_date, premium, favorite_languages, preferred_genres]:::userProfile
    end

    subgraph Media_Core [Nucleo de Contenido]
        M[Movie: movie_id, title, original_language, release_date, runtime, budget, revenue, vote_average, popularity]:::movieContent
        C[Collection: collection_id, name, created_at, public, followers_count]:::social
    end

    subgraph Attributes [Atributos y Taxonomia]
        G[Genre: name]:::metadata
        D[Director: director_id, name]:::metadata
        L[Language: code, name, region, family, rtl]:::metadata
    end

    %% Relaciones de interaccion y preferencia
    U ==>|VIEWED| M
    U -.->|RATED| M
    U -.->|PREFERS| G
    U ---|FRIEND_OF| U
    M -->|HAS_GENRE| G
    D -->|DIRECTED| M

    %% Relaciones de organizacion y afinidad
    M -->|IN_LANGUAGE| L
    U -.->|WATCHLISTED| M
    U -.->|LIKED| M
    U -.->|FOLLOWS_DIRECTOR| D
    U ==>|CREATED| C
    C -->|CONTAINS| M

    linkStyle default stroke:#555,stroke-width:1px;
\\\

## 2) Labels y propiedades

### User
- user_id: string
- name: string
- age: integer
- country: string
- register_date: date
- premium: boolean
- favorite_languages: list<string>
- preferred_genres: list<string>

### Movie
- movie_id: string
- title: string
- original_language: string
- original_title: string
- release_date: date
- runtime: float
- budget: integer
- revenue: integer
- vote_average: float
- popularity: float

### Genre
- name: string
- description: string
- popularity_index: float
- active: boolean
- created_at: date

### Director
- director_id: string
- name: string
- nationality: string
- birth_date: date
- active: boolean

### Language
- code: string
- name: string
- region: string
- family: string
- rtl: boolean

### Collection
- collection_id: string
- name: string
- created_at: date
- public: boolean
- followers_count: integer

## 3) Tipos de relacion

1. VIEWED (User -> Movie)
2. RATED (User -> Movie)
3. PREFERS (User -> Genre)
4. FRIEND_OF (User <-> User)
5. HAS_GENRE (Movie -> Genre)
6. DIRECTED (Director -> Movie)
7. IN_LANGUAGE (Movie -> Language)
8. WATCHLISTED (User -> Movie)
9. LIKED (User -> Movie)
10. FOLLOWS_DIRECTOR (User -> Director)
11. CONTAINS (Collection -> Movie)
12. CREATED (User -> Collection)

### Propiedades de Relaciones (Minimo 3 por tipo)

VIEWED: view_date (date), device (string), progress (float)
RATED: rating (float: 1-10), rating_date (date), comment (string)
PREFERS: weight (float: 0-1), last_updated (date), source (string)
FRIEND_OF: since_date (date), closeness (float: 0-1), interactions (integer)
HAS_GENRE: order (integer), relevance (float), created_at (date)
DIRECTED: role (string), is_primary (boolean), contributed_years (integer)
IN_LANGUAGE: is_original (boolean), subtitled (boolean), dubbed (boolean)
WATCHLISTED: added_date (date), priority (integer), notes (string)
LIKED: liked_date (date), like_strength (float: 0-1), reason (string)
FOLLOWS_DIRECTOR: since_date (date), notification_enabled (boolean), followers_count (integer)
CONTAINS: position (integer), added_date (date), note (string)
CREATED: created_at (date), is_public (boolean), description (string)

---

## 4) Cobertura de Tipos de Datos - RUBRICA

Requisito: Implementacion de todos los tipos de datos (String, Float, Integer, Boolean, List, Date)

STRING: Movie.title, User.name, Director.name, RATED.comment, PREFERS.source, DIRECTED.role, WATCHLISTED.notes

FLOAT: Movie.vote_average, Movie.popularity, Movie.runtime, Genre.popularity_index, RATED.rating, PREFERS.weight, LIKED.like_strength, HAS_GENRE.relevance

INTEGER: Movie.budget, Movie.revenue, Movie.vote_count, User.age, Collection.followers_count, FRIEND_OF.interactions, HAS_GENRE.order, WATCHLISTED.priority, CONTAINS.position

BOOLEAN: User.premium, Director.active, Language.rtl, Genre.active, Collection.public, DIRECTED.is_primary, IN_LANGUAGE.is_original, FOLLOWS_DIRECTOR.notification_enabled, CREATED.is_public

LIST: User.favorite_languages, User.preferred_genres, Director.style_tags

DATE: User.register_date, Movie.release_date, Director.birth_date, Genre.created_at, Collection.created_at, VIEWED.view_date, RATED.rating_date, FRIEND_OF.since_date, CONTAINS.added_date, FOLLOWS_DIRECTOR.since_date

---

## 5) Validacion Contra Rubrica

✓ Caso de uso adecuado: MOTOR DE RECOMENDACION con Jaccard similitud

✓ 5+ labels con 5+ propiedades: 6 labels (User, Movie, Genre, Director, Language, Collection)

✓ 10+ tipos de relaciones con 3+ propiedades: 12 tipos con propiedades documentadas

✓ Todos los tipos de datos: String, Float, Integer, Boolean, List, Date
