# PRY2-DB2 - Neo4j Recommender Backend

Proyecto de Bases de Datos 2 orientado a un motor de recomendacion con Neo4j AuraDB.

## Estructura del repositorio

- `app/`: API FastAPI con CRUD para nodos y relaciones.
- `data/`: datasets originales y limpios.
- `scripts/`: generacion, limpieza, carga y validacion de datos.
- `docs/latex/`: documento final en LaTeX y PDF.
- `docs/course/Instrucciones.md`: enunciado del proyecto.

## Requisitos

- Python 3.13+
- Entorno virtual (`.venv`)
- Neo4j AuraDB activo
- MiKTeX (opcional, para compilar el documento)

## Instalacion

```powershell
& "c:/Users/aeeh2/Documents/Universidad/Semestre 7/BasesdeDatos2/PRY2-DB2/.venv/Scripts/python.exe" -m pip install -r requirements.txt
```


## Pipeline de datos

### 1) Generar usuarios e interacciones sinteticas

```powershell
& "c:/Users/aeeh2/Documents/Universidad/Semestre 7/BasesdeDatos2/PRY2-DB2/.venv/Scripts/python.exe" "scripts/generate_synthetic_users_interactions.py" --movies data/movies.csv --outdir data --users 2200 --seed 42
```

### 2) Limpiar datos

```powershell
& "c:/Users/aeeh2/Documents/Universidad/Semestre 7/BasesdeDatos2/PRY2-DB2/.venv/Scripts/python.exe" "scripts/preprocess_data.py"
```

### 3) Cargar en Neo4j AuraDB

```powershell
& "c:/Users/aeeh2/Documents/Universidad/Semestre 7/BasesdeDatos2/PRY2-DB2/.venv/Scripts/python.exe" "scripts/load_clean_data_to_neo4j.py"
```

### 4) Validar post carga

```powershell
& "c:/Users/aeeh2/Documents/Universidad/Semestre 7/BasesdeDatos2/PRY2-DB2/.venv/Scripts/python.exe" "scripts/validate_post_load.py"
```

Si hay peliculas huerfanas (sin genero/director), ejecutar correccion y revalidar:

```powershell
& "c:/Users/aeeh2/Documents/Universidad/Semestre 7/BasesdeDatos2/PRY2-DB2/.venv/Scripts/python.exe" "scripts/fix_post_load_orphans.py"
& "c:/Users/aeeh2/Documents/Universidad/Semestre 7/BasesdeDatos2/PRY2-DB2/.venv/Scripts/python.exe" "scripts/validate_post_load.py"
```

## API CRUD (rubrica)

### Levantar API

```powershell
& "c:/Users/aeeh2/Documents/Universidad/Semestre 7/BasesdeDatos2/PRY2-DB2/.venv/Scripts/python.exe" -m uvicorn app.main:app --reload
```

- Swagger: http://127.0.0.1:8000/docs
- Health: `GET /health`

### Endpoints principales

Nodos:

- `POST /nodes`
- `GET /nodes/{label}/{id_property}/{id_value}`
- `POST /nodes/search`
- `POST /nodes/aggregate`
- `PATCH /nodes/properties/add-one`
- `PATCH /nodes/properties/add-many`
- `PATCH /nodes/properties/update-one`
- `PATCH /nodes/properties/update-many`
- `DELETE /nodes/properties/delete-one`
- `DELETE /nodes/properties/delete-many`
- `DELETE /nodes/delete-one`
- `DELETE /nodes/delete-many`

Relaciones:

- `POST /relationships`
- `PATCH /relationships/properties/add-one`
- `PATCH /relationships/properties/add-many`
- `PATCH /relationships/properties/update-one`
- `PATCH /relationships/properties/update-many`
- `DELETE /relationships/properties/delete-one`
- `DELETE /relationships/properties/delete-many`
- `DELETE /relationships/delete-one`
- `DELETE /relationships/delete-many`

## Documento del proyecto

- Fuente LaTeX: `docs/latex/documento_proyecto.tex`
- PDF: `docs/latex/documento_proyecto.pdf`

Compilar PDF:

```powershell
Set-Location "c:/Users/aeeh2/Documents/Universidad/Semestre 7/BasesdeDatos2/PRY2-DB2/docs/latex"
& "c:/Users/aeeh2/AppData/Local/Programs/MiKTeX/miktex/bin/x64/pdflatex.exe" -interaction=nonstopmode -halt-on-error "documento_proyecto.tex"
```
