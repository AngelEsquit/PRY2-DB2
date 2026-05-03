# CineGraph Frontend

Frontend elegante para el proyecto PRY2-DB2. Está hecho con React + Vite y se conecta al backend FastAPI con Neo4j.

## Requisitos

- Node.js instalado
- Backend corriendo en `http://localhost:8000`
- Base de datos Neo4j cargada

## Instalación

```bash
npm install
```

## Configuración

Crea un archivo `.env` en la raíz del frontend:

```bash
VITE_API_URL=http://localhost:8000
```

## Ejecutar

```bash
npm run dev
```

Luego abre la URL que muestre Vite, normalmente:

```bash
http://localhost:5173
```

## Funciones incluidas

- Catálogo de películas desde `/nodes/search`
- Selección de usuario activo
- Recomendaciones personalizadas desde `/recommendations/{user_id}`
- Detalle de película desde `/movies/{movie_id}`
- Películas similares desde `/movies/{movie_id}/similar`
- Likes
- Watchlist
- Colecciones
- Amigos y perfil social

## Nota sobre CORS

Si el navegador bloquea las peticiones, agrega CORS en FastAPI:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
