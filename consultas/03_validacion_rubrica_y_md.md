# Validacion de Cumplimiento: Codigo vs Rubrica


## Validacion contra Rubrica

### Modelado de datos

1. Caso de uso adecuado.
- Estado: Cumple.
- Evidencia: modelo orientado a recomendacion/social con usuarios, peliculas, preferencias, amistad, likes, watchlist y colecciones.

2. Minimo 5 labels y 5 propiedades por label.
- Estado: Cumple en codigo de carga actualizado.
- Labels: Movie, User, Genre, Director, Language, Collection.
- Validador reforzado para verificar minimos de propiedades.

3. Minimo 10 tipos de relaciones y 3 propiedades por tipo.
- Estado: Cumple en codigo de carga actualizado.
- Tipos: DIRECTED, HAS_GENRE, IN_LANGUAGE, CONTAINS, VIEWED, RATED, PREFERS, FRIEND_OF, WATCHLISTED, LIKED, FOLLOWS_DIRECTOR, CREATED.
- Validador reforzado para verificar minimos de propiedades.

4. Tipos de datos (String, Float, Integer, Boolean, List, Date).
- Estado: Cumple.
- Evidencia en nodos y relaciones cargadas.

### Set de datos

5. Carga desde CSV.
- Estado: Cumple.
- Scripts de generacion, limpieza y carga por CSV.

6. Datos previamente cargados en BD.
- Estado: No verificable en esta sesion por conexion Aura pendiente.

7. Minimo 5000 nodos.
- Estado: Cumple por volumen preparado.
- Dry-run muestra volumen total muy superior a 5000.

8. Grafo conexo.
- Estado: No verificable en esta sesion por conexion Aura pendiente.
- Existe script de validacion post carga para comprobarlo.

### Aplicacion funcional

9. Crear nodos con 1 label, 2+ labels y 5+ propiedades.
- Estado: Cumple.
- Endpoint generico /nodes con lista de labels y propiedades.

10. Visualizacion de nodos (uno, muchos, agregadas).
- Estado: Cumple.
- Endpoints GET /nodes/{...}, POST /nodes/search, POST /nodes/aggregate.

11. Gestion de propiedades en nodos (add/update/delete one/many).
- Estado: Cumple.

12. Crear relacion entre nodos con 3+ propiedades.
- Estado: Cumple.
- Endpoint /relationships permite propiedades y la carga base ya maneja 3+ por tipo.

13. Gestion de propiedades en relaciones (add/update/delete one/many).
- Estado: Cumple.

14. Eliminacion de nodos one/many.
- Estado: Cumple.

15. Eliminacion de relaciones one/many.
- Estado: Cumple.

16. Consultas Cypher (4-6) y 2 por integrante.
- Estado: Cumple con entregables creados en carpeta consultas.
- Evidencia: archivos 01_consultas_cypher_demo.md y 02_reparto_consultas_por_integrante.md.
