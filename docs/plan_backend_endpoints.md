# Planeación funcional del backend y endpoints

## 1. Objetivo de esta planeación

Definir qué decisiones tomará el sistema de recomendación y convertirlas en endpoints de negocio concretos, para implementar el backend por fases sin perder alineación con el modelo de grafo.

## 2. Qué debe hacer el sistema

## 2.1 Decisiones principales del motor

- Identificar el perfil de gusto de cada usuario a partir de señales explícitas e implícitas.
- Priorizar contenido nuevo y relevante para cada usuario.
- Evitar recomendar contenido ya visto o ya calificado por el usuario.
- Permitir filtros por idioma, género y popularidad mínima.
- Explicar cada recomendación con razones legibles.

## 2.2 Señales de entrada (grafo)

- Señales explícitas: RATED, PREFERS, LIKED.
- Señales implícitas: VIEWED (progress), WATCHLISTED, FOLLOWS_DIRECTOR.
- Contexto de contenido: HAS_GENRE, IN_LANGUAGE, DIRECTED.
- Contexto social: FRIEND_OF y afinidad entre usuarios.

## 2.3 Reglas de negocio iniciales

- Excluir películas con VIEWED o RATED por el usuario objetivo.
- Subir puntaje si coincide con géneros preferidos y con idioma favorito.
- Subir puntaje si el director es seguido por el usuario.
- Subir puntaje por evidencia social (usuarios similares o amigos que interactuaron positivamente).
- Devolver top N ordenado por score final.

## 2.4 Algoritmo Data Science: Jaccard

Se adopta Jaccard como base colaborativa del motor para cumplir el criterio de algoritmo de data science de la rubrica.

Definicion:

- Para dos usuarios A y B, la similitud Jaccard se calcula sobre conjuntos de peliculas de interes.
- Conjunto sugerido para MVP: peliculas con `LIKED` y/o `RATED >= 8`.

Formula:

- $J(A,B) = \frac{|S_A \cap S_B|}{|S_A \cup S_B|}$

Uso en el motor:

- Encontrar usuarios vecinos con mayor Jaccard respecto al usuario objetivo.
- Extraer peliculas candidatas desde vecinos similares que el usuario objetivo no haya visto/calificado.
- Combinar score colaborativo (Jaccard) con score de contenido (genero/idioma/director).

Salida esperada para evidencia academica:

- score final por pelicula.
- desglose de contribucion colaborativa y de contenido.
- razones de recomendacion (ejemplo: "3 usuarios similares la calificaron alto").

## 3. Casos de uso backend

- Caso 1: Obtener recomendaciones personalizadas para un usuario.
- Caso 2: Consultar y administrar watchlist del usuario.
- Caso 3: Consultar historial de likes del usuario.
- Caso 4: Consultar y administrar colecciones creadas por usuario.
- Caso 5: Buscar usuarios similares para soporte de recomendación social.
- Caso 6: Consultar películas similares para recomendaciones contextuales.

## 4. Catálogo de endpoints planeados

## 4.1 Recomendación principal

### GET /recommendations/{user_id}

Propósito:
- Obtener lista personalizada de películas recomendadas.

Query params:
- top_k (default 20)
- min_score (opcional)
- language (opcional)
- genre (opcional)
- min_jaccard (opcional, default 0.1)
- max_neighbors (opcional, default 30)
- include_reasons (default true)

Response base:
- user_id
- generated_at
- algorithm: "hybrid_jaccard_v1"
- items: movie_id, title, score, jaccard_score, content_score, reasons[]

Errores:
- 404 si el usuario no existe.
- 400 si parámetros son inválidos.

## 4.2 Perfil y explicación de recomendaciones

### GET /users/{user_id}/recommendation-profile

Propósito:
- Exponer cómo el sistema interpreta el perfil de gusto actual del usuario.

Response base:
- top_genres
- top_languages
- followed_directors
- social_affinity_summary

### GET /recommendations/{user_id}/explanations/{movie_id}

Propósito:
- Explicar por qué una película fue recomendada a ese usuario.

Response base:
- score_breakdown
- matched_genres
- matched_language
- social_signals
- director_signal

## 4.3 Interacciones del usuario

### GET /users/{user_id}/watchlist
### POST /users/{user_id}/watchlist
### DELETE /users/{user_id}/watchlist/{movie_id}

Propósito:
- Consultar, agregar y eliminar pendientes.

### GET /users/{user_id}/likes
### POST /users/{user_id}/likes
### DELETE /users/{user_id}/likes/{movie_id}

Propósito:
- Consultar, agregar y eliminar likes.

## 4.4 Colecciones

### GET /users/{user_id}/collections
### POST /users/{user_id}/collections
### PATCH /users/{user_id}/collections/{collection_id}
### DELETE /users/{user_id}/collections/{collection_id}

Propósito:
- Gestionar colecciones del usuario.

### POST /users/{user_id}/collections/{collection_id}/movies
### DELETE /users/{user_id}/collections/{collection_id}/movies/{movie_id}

Propósito:
- Gestionar contenido de cada colección.

## 4.5 Similaridad

### GET /users/{user_id}/similar-users

Propósito:
- Retornar usuarios similares para análisis y señales colaborativas.

Query params:
- top_k (default 10)
- min_similarity (opcional)

Response base:
- items: similar_user_id, similarity_score, shared_signals[]

### GET /movies/{movie_id}/similar

Propósito:
- Retornar películas similares por contenido y comportamiento.

Query params:
- top_k (default 10)
- by (content, collaborative, hybrid)

Response base:
- items: movie_id, score, reasons[]

## 5. Fases de implementación

## Fase 1 (MVP funcional)

- GET /recommendations/{user_id}
- GET /users/{user_id}/watchlist
- GET /users/{user_id}/likes
- GET /users/{user_id}/collections

Objetivo:
- Entregar valor principal de recomendacion con lectura de señales ya cargadas y Jaccard operativo en produccion.

## Fase 2 (gestión de interacciones)

- POST y DELETE de watchlist
- POST y DELETE de likes
- CRUD de colecciones y contenido de colecciones

Objetivo:
- Permitir retroalimentación del usuario y actualización dinámica de señales.

## Fase 3 (explicabilidad y similaridad)

- GET /users/{user_id}/recommendation-profile
- GET /recommendations/{user_id}/explanations/{movie_id}
- GET /users/{user_id}/similar-users
- GET /movies/{movie_id}/similar

Objetivo:
- Hacer trazable el resultado del motor y mejorar exploración de contenido.

Entregable extra de esta fase:

- endpoint de explicacion debe mostrar vecinos Jaccard que influyeron en cada recomendacion.

## 6. Contratos y estándares transversales

- Respuestas paginadas en listados largos (items, total, skip, limit).
- Errores con formato consistente: code, message, details.
- Trazabilidad mínima: request_id por respuesta.
- Validaciones de entrada para user_id, movie_id, collection_id y parámetros numéricos.

## 7. Criterios de aceptación para cerrar Pendiente 1

- Existe documento de planeación aprobado con alcance y fases.
- Todos los endpoints de negocio del MVP están definidos con propósito, entrada y salida.
- Esta acordada la estrategia inicial de score hibrido con Jaccard y exclusiones.
- Se identifica claramente qué endpoints son de lectura y cuáles de escritura.
- Existe definicion explicita de formula Jaccard, parametros de control y evidencia esperada en respuesta.

## 8. Próximo paso inmediato

Diseñar la especificación técnica del endpoint principal GET /recommendations/{user_id}, incluyendo:

- fórmula de score inicial,
- consulta Cypher base,
- esquema de respuesta,
- casos de prueba mínimos.
