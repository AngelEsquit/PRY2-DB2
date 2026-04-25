# Pendientes de Backend (PRY2-DB2)

## Estado actual (ya implementado)

- API FastAPI funcional con CRUD genérico para nodos y relaciones.
- Validación básica de identificadores para evitar inyección en labels/propiedades/tipos de relación.
- Endpoint de salud (`GET /health`).
- Conexión directa a Neo4j AuraDB mediante driver oficial.

## Lo que falta en backend (priorizado)

## Prioridad alta

### 1) Endpoints de negocio del caso de uso (recomendación)

Falta exponer una capa de negocio específica para el motor de recomendación. Hoy la API es genérica CRUD.

Implementar endpoints alineados al plan por fases:

- Fase 1 (MVP):
	- `GET /recommendations/{user_id}`
	- `GET /users/{user_id}/watchlist`
	- `GET /users/{user_id}/likes`
	- `GET /users/{user_id}/collections`
- Fase 2 (gestión de interacciones):
	- `POST/DELETE /users/{user_id}/watchlist`
	- `POST/DELETE /users/{user_id}/likes`
	- CRUD de colecciones y contenido de colección
- Fase 3 (similaridad y explicabilidad):
	- `GET /users/{user_id}/similar-users`
	- `GET /movies/{movie_id}/similar`
	- `GET /users/{user_id}/recommendation-profile`
	- `GET /recommendations/{user_id}/explanations/{movie_id}`

### 2) Algoritmo de recomendación integrado en API

Falta implementar la lógica de recomendación dentro del backend (no solo estructura de datos).

Mínimo esperado:

- Estrategia híbrida simple: contenido + colaborativo (Jaccard).
- Exclusión de contenido ya visto/rateado por usuario.
- Parámetros de control (`top_k`, `min_jaccard`, `max_neighbors`, filtros por idioma/género).
- Respuesta explicable (por qué se recomendó cada item).

Definición concreta para este pendiente:

- Jaccard es la base colaborativa del sistema.
- Fórmula: J(A,B) = |S_A ∩ S_B| / |S_A ∪ S_B|.
- Conjunto sugerido para MVP: películas con `LIKED` y/o `RATED >= 8`.
- El endpoint principal debe devolver score híbrido (`score`, `jaccard_score`, `content_score`).

### 3) Capa de servicios y repositorios

Toda la lógica está concentrada en `app/main.py`. Falta separar responsabilidades.

Propuesta mínima:

- `app/api/` (routers)
- `app/services/` (reglas de negocio)
- `app/repositories/` (Cypher y acceso a datos)
- `app/schemas/` (request/response models)

Beneficio: mantenibilidad, pruebas más simples y menor acoplamiento.

Alcance ajustado:

- Separación mínima para endpoints de recomendación primero.
- No es necesario migrar todo el CRUD genérico en la primera iteración.

### 4) Pruebas automatizadas del backend

No hay pruebas en el repositorio para la API.

Agregar:

- Tests de integración para `GET /recommendations/{user_id}`.
- Tests de integración para `GET /users/{user_id}/watchlist`, `GET /users/{user_id}/likes` y `GET /users/{user_id}/collections`.
- Tests de regresión para CRUD crítico.
- Fixtures de datos y entorno de prueba.
- Validación de códigos HTTP, payload y casos de error.

## Prioridad media (versión simple)

### 7) Contratos de respuesta mínimos

Se mantiene una versión ligera solo para mejorar la presentación y consistencia del backend.

Agregar únicamente:

- Modelos de respuesta para `GET /recommendations/{user_id}`.
- Modelos de respuesta para `GET /users/{user_id}/similar-users`.
- Campos mínimos en recomendaciones: `algorithm`, `score`, `jaccard_score`, `content_score`, `reasons`.
- Ejemplos mínimos en OpenAPI para ambos endpoints.

No incluye estandarización completa de errores ni documentación extensa.

---

## Siguiente entrega recomendada (backend mínimo viable)

1. Crear módulo de recomendación con endpoint `GET /recommendations/{user_id}`.
2. Implementar Jaccard en ese endpoint con salida híbrida (`score`, `jaccard_score`, `content_score`).
3. Agregar endpoints de apoyo de Fase 1 (`watchlist`, `likes`, `collections`).
4. Añadir tests de integración para recomendaciones y endpoints de apoyo.
5. Separar en forma mínima `main.py` para recomendación (router + service + repository) y definir contratos de respuesta mínimos.

Con eso ya tendrías un backend alineado al caso de uso, no solo CRUD técnico.
