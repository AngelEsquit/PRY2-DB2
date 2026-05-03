# PRY2-DB2 - Neo4j Recommender Backend

Proyecto de Bases de Datos 2: backend con FastAPI y Neo4j, y frontend Vite+React.

## Estructura relevante

- `app/`: API FastAPI (endpoints CRUD, recomendaciones, etc.).
- `data/clean/`: CSV limpios usados para carga.
- `scripts/`: scripts para preprocesado, generación, carga y validación.
- `frontend/`: aplicación Vite + React (UI mínima).

## Requisitos

- Python 3.10+ (3.13 recomendado)
- Node.js + npm
- Neo4j (local o AuraDB)

## Variables de entorno

Colocar un archivo `.env` en la raíz con como mínimo:

- `NEO4J_URI` (ej: bolt://localhost:7687 o neo4j+s://...)
- `NEO4J_USERNAME`
- `NEO4J_PASSWORD`
- `NEO4J_DATABASE` (opcional, por defecto `neo4j`)
- `CORS_ALLOWED_ORIGINS` (opcional, comas separadas; por defecto se permiten orígenes locales de dev)
- `VITE_API_URL` (opcional para el frontend)

Ejemplo mínimo `.env`:

NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=changeme

## Quick start (local)

1. Crear y activar entorno Python

	 - Windows PowerShell:
		 ```powershell
		 python -m venv .venv
		 .\.venv\Scripts\Activate.ps1
		 pip install -r requirements.txt
		 ```

	 - macOS / Linux:
		 ```bash
		 python -m venv .venv
		 source .venv/bin/activate
		 pip install -r requirements.txt
		 ```

2. Levantar backend (FastAPI + Uvicorn)

	 ```bash
	 python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
	 ```

	 - Documentación Swagger: http://127.0.0.1:8000/docs
	 - Health: `GET /health`

3. Cargar datos (modo verificación / dry-run)

	 ```bash
	 python scripts/load_clean_data_to_neo4j.py --data-dir data/clean --dry-run
	 ```

	 - El `--dry-run` imprime los conteos preparados y los controles básicos sin escribir en la BD.
	 - Para realizar la carga real, ejecutar sin `--dry-run`.

4. Validar post-carga

	 ```bash
	 python scripts/validate_post_load.py
	 ```

	 - Genera `validation_post_load_report.md` y devuelve `PASS`/`FAIL` según la rúbrica técnica.

5. Levantar frontend

	 ```bash
	 cd frontend
	 npm install
	 # Exportar VITE_API_URL si no está en .env del frontend
	 npm run dev
	 ```

## Checklist demostrable (mapa desde la rúbrica a comandos / evidencia)

- **Entorno reproducible:**
	- Evidencia: ejecutar `python -m uvicorn app.main:app --reload` y `npm run dev` funciona.

- **Carga de datos y volumen (>=5000 nodos):**
	- Cómo demostrar: `python scripts/load_clean_data_to_neo4j.py --data-dir data/clean --dry-run` muestra conteos; `python scripts/validate_post_load.py` confirma `Total de nodos >= 5000` y escribe `validation_post_load_report.md`.

- **Nodos y labels (múltiples labels):**
	- Cómo demostrar: `MATCH (n) RETURN distinct labels(n)` en Neo4j Browser o ejecutar `python scripts/validate_post_load.py` y revisar conteo por label en el reporte.

- **Relaciones y tipos (varios tipos):**
	- Cómo demostrar: `python scripts/validate_post_load.py` imprime conteos por tipo de relación (DIRECTED, HAS_GENRE, VIEWED, RATED, PREFERS, FRIEND_OF, etc.).

- **Propiedades y tipos heterogéneos:**
	- Cómo demostrar: usar `POST /nodes/search` o ejecutar consultas Cypher (ej: `MATCH (m:Movie) RETURN m.title, m.release_date, m.popularity LIMIT 5`) para mostrar fechas, números, listas y booleanos.

- **CRUD funcional vía API:**
	- Cómo demostrar:
		- Crear nodo: `curl -X POST http://localhost:8000/nodes -H 'Content-Type: application/json' -d '{"label":"Test","props":{"test_id":1,"name":"x"}}'`
		- Leer: `GET /nodes/Test/test_id/1`
		- Actualizar propiedades: `PATCH /nodes/properties/update-one`
		- Borrar: `DELETE /nodes/delete-one`

- **Agregaciones y búsqueda:**
	- Cómo demostrar: `POST /nodes/aggregate` con payload de agregación; `POST /nodes/search` para búsquedas por propiedad/regex.

- **Algoritmo de recomendación:**
	- Cómo demostrar: `GET /recommendations/{user_id}` (ej: `curl http://localhost:8000/recommendations/1`) y mostrar JSON de recomendaciones.

- **Integridad post-carga:**
	- Cómo demostrar: `python scripts/validate_post_load.py` — revisa películas sin género/director, usuarios sin interacciones, nodos aislados, colecciones sin creador o películas. El script falla (exit code != 0) si hay problemas.

- **Conectividad del grafo (seed reachable):**
	- Cómo demostrar: revisar la sección `## Conectividad` en `validation_post_load_report.md` generada por `validate_post_load.py`.

## Donde mirar / archivos útiles

- Carga y generación de datos: `scripts/load_clean_data_to_neo4j.py`
- Validación post-carga: `scripts/validate_post_load.py` (genera `validation_post_load_report.md`)
- API principal: `app/main.py`
- Frontend API client: `frontend/src/services/api.js` (usa `VITE_API_URL`)

---

Si quieres, puedo:

- Ejecutar `--dry-run` aquí y pegar los conteos.
- Ejecutar la carga real (necesita credenciales Neo4j activas en `.env`).
- Empezar un pequeño script que ejecute todas las comprobaciones y genere un informe listo para la exposición.

