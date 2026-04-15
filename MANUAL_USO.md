# JobPilot AI - Manual corto

## Que hace

JobPilot AI usa tu CV como punto de partida. Al subirlo, intenta detectar tu perfil, buscar vacantes desde fuentes configuradas, calcular compatibilidad y crear una cola de postulaciones.

## Que haces tu

1. Abres la app.
2. Inicias sesion o creas una cuenta.
3. Subes tu CV en PDF o DOCX desde el panel.
4. Revisas el perfil detectado y los datos faltantes utiles.
5. Revisas la cola de postulaciones.
6. Actuas solo sobre las que quedaron en `needs_manual_action`.

## Que hace el sistema solo

Al subir el CV ejecuta este pipeline:

1. `parse_cv`: lee el PDF o DOCX.
2. `infer_profile`: detecta datos del candidato e infiere seniority y roles probables.
3. `collect_jobs`: busca vacantes en fuentes reales configuradas.
4. `match_jobs`: calcula compatibilidad flexible.
5. `create_queue_items`: crea postulaciones en cola para las vacantes compatibles.

Si no hay fuentes reales configuradas, no inventa vacantes. Deja el proceso registrado y muestra que no se recolectaron empleos.

## Estados

- `found`: vacante encontrada.
- `matched`: vacante compatible y agregada a cola.
- `prepared`: formulario o documentos preparados.
- `ready_for_review`: requiere revision antes del envio final.
- `applied`: postulacion enviada o marcada como enviada.
- `failed`: fallo tecnico.
- `needs_manual_action`: necesita que termines algo manualmente, por ejemplo captcha, login, pregunta compleja o restriccion del portal.

## Donde mirar

- **Panel**: flujo principal. Subes CV y ves perfil, faltantes, cola y procesos.
- **Perfil detectado**: datos extraidos o inferidos desde el CV.
- **Cola**: postulaciones, estado, errores, logs y links.
- **Diagnostico**: tareas internas, resultados y errores tecnicos.

## Como terminar una accion manual

1. Entra a la cola.
2. Busca las postulaciones con estado `needs_manual_action`.
3. Abre el link de la vacante.
4. Completa lo que el sistema no pudo resolver.
5. Marca el estado como `applied` si terminaste la postulacion.
