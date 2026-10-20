# Pruebas y reproducción local

> **Estado vigente — 20 de octubre:** los seis módulos existentes y sus artefactos locales están preparados. Regresión, asociaciones descubiertas y comparación de grafos requieren implementación según [pendientes y contratos](pendientes-cierre-2026-10-20.md). Los scripts actuales todavía no preparan/verifican esas ampliaciones. El historial del desempeño es recomendado; Docker/Compose es opcional. Gerardo mantiene preparación/entorno y Angel la verificación integrada.

Los comandos se ejecutan en PowerShell desde la raíz. La [revisión histórica del 13 de octubre](revision-avance-2026-10-13.md) y [demo-local.md](demo-local.md) documentan 238 pruebas y 48 comprobaciones posteriores de las seis capacidades. Esos logs no certifican el alcance ampliado ni reproducción integral en otra PC. Los apartados de evidencia histórica al final conservan sus fechas y límites originales.

## Qué se puede probar hoy

| Componente | Verificación disponible | Límite actual |
| --- | --- | --- |
| Fraude | Perfil, entrenamiento desde Bronze/Silver, scoring, patrones, API/página y comandos de reproducción/verificación. | Modelos locales presentes; aceptación humana cruzada y fuentes pendientes. Reproducción aislada documentada en el cierre de entrega. |
| Grafos | Ingesta, métricas, patrones, servicios, API y página conectada mediante HTTP. | Demo con muestra acotada y referencia comparable por cerrar; no acredita la red completa. |
| Transacciones | Silver, mart Gold, segmentación independiente de etiqueta, servicio/API/página; artefactos locales preparados. | Aceptación cruzada y reproducción; D1 nuevo de TAC-01 pendiente. |
| Temporal | Gold, backtesting, Holt-Winters comparado, monitoreo histórico y API/página; artefactos locales preparados. | Aceptación visual/reproducción; historial de desempeño P2 aún no implementado. Naive sigue seleccionado por MAE. |
| Reclamos | Silver/texto, clasificador, tendencias, ejemplos, servicio/API/página y artefactos locales preparados. | Lectura humana cruzada, fuente/condiciones de uso y reproducción pendientes. |
| Crédito | Silver, modelo calibrado, explicaciones y API/página; artefactos locales preparados. | Semántica/fuente original, aceptación y reproducción pendientes. |
| Ampliaciones | Especificaciones y encargos del 20 de octubre. | Regresión, asociaciones descubiertas y comparación de grafos no se declaran implementadas por existir el plan. |

## Bloqueos y responsables

| Prioridad | Falta o problema | Acción y responsable |
| --- | --- | --- |
| P0 | Regresión numérica y minería automática de asociaciones. | Taco prepara D1; Sevan implementa regresión; Cueva descubre/evalúa reglas. |
| P1 | Comparación de alertas de grafos. | Rhamses compara red/referencia con igual universo y k y agrega consulta/vista. |
| P1 | Preparación y verificación ampliadas. | Gerardo integra DAG/identidades; Angel registra routers, navegación y checks de las siete páginas. |
| P1 | Versiones y reproducción integral. | Gerardo–Sevan validan lock y entorno nuevo; todos reproducen su módulo en el segundo entorno. |
| Transversal | Fuentes, semántica crediticia, lectura NLP y aceptación. | Conservar tareas humanas de los seis encargos y registrar evidencia real. |
| P2 recomendado | Historial del desempeño y empaquetado opcional. | Gerardo desarrolla historial si se incorpora; Docker solo si se conserva como entregable. |

Fraude/API/página, caché por muestra de grafos, fechas de reclamos, Silver/NLP, método/monitoreo temporal y corrección/API/página de segmentos ya tienen implementación. No volver a asignarlos como tareas nuevas. Los detalles de aceptación por integrante están en la guía vigente del 20 de octubre.

## 1. Preparar el entorno

Requiere Python 3.11 o posterior; usar 3.12 para aproximarse al entrenamiento inicial de fraude. Verificar el intérprete antes de crear el entorno. Si `python` apunta al alias de Microsoft Store y falla, usar la ruta de un Python instalado o `py -3.12` si el lanzador está disponible.

```powershell
py -3.12 --version
powershell -ExecutionPolicy Bypass -File scripts/setup_env.ps1
```

El script crea el entorno si no existe, exige Python 3.12, instala
`requirements/common.txt`, ejecuta `pip check` y la suite completa. Se detiene
si un paso falla. Admite `-PythonExecutable 'C:\ruta\python.exe'` cuando no
existe el lanzador `py`, y `-SkipTests` para instalar sin verificar la suite.
`ExecutionPolicy Bypass` solo afecta ese proceso de PowerShell.

Los extras de `pyproject.toml` sirven para validar el conjunto con rangos compatibles. Esta instalación todavía no es un bloqueo exacto de versiones para reproducir las métricas históricas. Para recargar el modelo guardado, comprobar las versiones registradas en `artifacts/models/fraud/metrics.json`; usar `requirements/fraud.txt` en un entorno independiente si hace falta reproducir esa ejecución. No confiar en un `.venv` copiado de otro equipo: debe recrearse si su intérprete base ya no funciona.

`.venv-pruebas/` debe permanecer fuera de Git. No es necesario activar el entorno si se usa su ejecutable explícitamente.

## 2. Comprobar Bronze y ejecutar pruebas

Los CSV usan Git LFS. En un clon nuevo, confirmar que son archivos completos y no punteros; los tamaños y huellas esperados están en [datasets.md](datasets.md).

```powershell
git lfs version
git lfs pull
Get-Item data/bronze/transactions/*.csv, data/bronze/credit/*.csv, data/bronze/complaints/*.csv | Select-Object Name,Length
.venv-pruebas/Scripts/python.exe -m unittest discover -s tests/unit -v
```

La suite requiere todos los módulos importados y permiso de escritura en directorios temporales. Si una restricción del entorno impide escribir allí, usar una carpeta temporal propia y permitida o ejecutar en un entorno local autorizado. Un error por dependencia o permisos no prueba que la lógica del módulo sea incorrecta, pero impide declarar la suite aprobada.

## 3. Probar Silver y Gold sin sustituir reportes completos

La prueba rápida escribe sus salidas en rutas separadas. La muestra de primeras filas solo comprueba el pipeline; no debe usarse para evaluar pronósticos ni representar toda la fuente.

```powershell
.venv-pruebas/Scripts/python.exe scripts/build_silver.py --limit 100000 --output data/silver/smoke/transactions.parquet --quality-json artifacts/reports/smoke/silver.json --quality-markdown artifacts/reports/smoke/silver.md
.venv-pruebas/Scripts/python.exe scripts/build_forecast_gold.py --input data/silver/smoke/transactions.parquet --output data/gold/smoke/transactions_hourly.parquet --quality-json artifacts/reports/smoke/gold.json --quality-markdown artifacts/reports/smoke/gold.md
```

Después, ejecutar el recorrido completo. Estos comandos regeneran los reportes Markdown versionados: revisar el diff antes de guardarlos como una nueva entrega.

```powershell
.venv-pruebas/Scripts/python.exe scripts/build_silver.py
.venv-pruebas/Scripts/python.exe scripts/build_forecast_gold.py
.venv-pruebas/Scripts/python.exe scripts/analyze_forecast_series.py
```

Aceptar cuando Silver conserva 6,362,620 filas para esta fuente, no hay rechazos y pasan sus controles; Gold temporal tiene 743 filas, conserva cantidad/monto/fraudes y no tiene nulos. Comparar con los reportes versionados. Los métodos temporales ya están evaluados; para reconstruir monitoreo y comparación, consultar `scripts/README.md`.

El mart transaccional y la segmentación requieren Silver completo y se reconstruyen así:

```powershell
.venv-pruebas/Scripts/python.exe scripts/build_gold_transactions.py
.venv-pruebas/Scripts/python.exe scripts/segment_transactions.py
```

Estos comandos regeneran reportes versionados: revisar el diff antes de guardar. La configuración está en `configs/segments.json`. Se generan `data/gold/segments/account_segments.parquet` y `artifacts/reports/segments.json`, excluidos de Git. El reporte nuevo documenta 146,629 cuentas, k=2, silueta 0.2305 y ARI 0.7280; fraude queda fuera de `CLUSTER_COLUMNS`.

Con API y panel iniciados, consultar `/api/segments/summary`, `/api/segments/0/accounts?limit=50&offset=0` y una cuenta existente de la respuesta; comprobar perfiles y cuentas en Segmentos. Sin artefactos, la API devuelve 503; recursos desconocidos devuelven 404 y límites inválidos 422. `BANKSHIELD_SEGMENTS_PARQUET` y `BANKSHIELD_SEGMENTS_REPORT` permiten rutas alternativas.

## 4. Probar fraude local

Si hay un modelo compatible disponible:

```powershell
.venv-pruebas/Scripts/python.exe scripts/predict_fraud.py --type TRANSFER --amount 1000 --origin-balance 500
```

Aceptar cuando devuelve `score`, `alert`, `threshold` y `score_is_calibrated=false`. No exigir una alerta específica para ese ejemplo sin contrastar el modelo cargado. Para reconstruir los artefactos en otro clon:

```powershell
.venv-pruebas/Scripts/python.exe scripts/profile_fraud.py
.venv-pruebas/Scripts/python.exe scripts/train_fraud.py
```

El entrenamiento completo necesita memoria para materializar las particiones. No se ha medido un requisito mínimo de RAM. Un entorno con versiones diferentes puede requerir reentrenamiento y no garantiza cifras idénticas.

## 5. Probar API y panel de redes

Terminal 1:

```powershell
.venv-pruebas/Scripts/python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/
Invoke-RestMethod 'http://127.0.0.1:8000/api/graphs/summary?limit=1000'
Invoke-RestMethod 'http://127.0.0.1:8000/api/graphs/top?top_n=5'
.venv-pruebas/Scripts/python.exe -m streamlit run dashboard/app.py
```

Abrir Swagger en `http://127.0.0.1:8000/docs` y panel en `http://localhost:8501`. Usar una cuenta devuelta por el ranking para consultar cuenta/subgrafo. Confirmar respuesta de error para una cuenta inexistente. La caché actual respeta el límite solicitado; usar el mismo `limit` en resumen, ranking, cuenta, subgrafo y patrones para comparar el mismo universo.

En redes, comprobar KPIs, ranking, subgrafo y filtros de patrones mediante el recorrido HTTP actual. El endpoint raíz por sí solo no acredita artefactos disponibles. La comparación nueva de RHA-01 se incorpora a este recorrido únicamente cuando esté implementada y preparada.

## Evidencia histórica de una revisión anterior a la preparación de demo

- El comando `python` del PATH apuntó a WindowsApps y no pudo iniciar.
- Con el Python incluido en Codex, la suite no pudo completarse: faltaban dependencias (`fastapi`, `joblib`, `pyarrow`, `matplotlib` y `networkx` en verificaciones realizadas) y algunas pruebas encontraron restricciones de escritura temporal.
- Existe `.venv` con Python 3.12 y dependencias de fraude; el intento de ejecutar la suite no produjo resultados y se interrumpió. No se considera un entorno común validado.
- No se instaló un entorno nuevo ni se ejecutó entrenamiento/procesamiento completo durante esta revisión. No se certifican pruebas aprobadas ni funcionamiento visual de la aplicación.

## Criterio histórico del primer recorrido

1. Instalación desde entorno limpio y `pip check` sin conflictos.
2. Suite completa sin errores, con versiones y resultado registrados.
3. CSV completos; Silver y Gold regenerados con controles aprobados.
4. Scoring de fraude con artefacto compatible y metadatos identificados.
5. API de grafos y página de redes demostrables con datos reales acotados.
6. Para declarar el MVP integrado: página de fraude consumiendo su endpoint y contrato de datos revisado Cueva–Taco; integración API → panel revisada Rhamses–Angel.

La preparación posterior resolvió la integración base del punto 6; su reproducción en otro entorno sigue pendiente. Para el cierre ampliado usar el checklist del 20 de octubre: además exige regresión, asociaciones descubiertas y comparación de grafos con evidencia propia.

## Qué compartir por Git y cómo trabajar en equipo

Se comparten `pyproject.toml`, `requirements/common.txt`, el script de instalación,
esta guía y `.github/workflows/tests.yml`. El workflow ejecuta instalación,
`pip check` y pruebas con fixtures pequeños en Windows/Python 3.12: no descarga
los CSV de LFS. No valida la aplicación visual ni el procesamiento completo.
Su primer resultado en GitHub queda pendiente de subir los cambios.

Cada integrante trabaja en una rama y abre un PR a `main`; otra persona revisa
su entrega. Antes de integrar, exigir pruebas de CI aprobadas. El equipo debe
configurar esa protección en GitHub si desea hacerla obligatoria.

Después de integrar estos archivos en `main`, cada integrante ejecuta:

```powershell
git switch main
git pull --ff-only origin main
git lfs pull
powershell -ExecutionPolicy Bypass -File scripts/setup_env.ps1
```

Si hay cambios locales sin guardar, resolverlos antes de cambiar de rama o
actualizar. El script no descarga LFS ni genera Silver/Gold ni entrena modelos;
seguir las secciones anteriores para probar esos recorridos.

Una vez aprobada la suite en un entorno limpio, Sevan–Gerardo pueden registrar
las versiones exactas en `requirements/lock-py312-windows.txt` mediante
`pip freeze --exclude-editable`, revisar el archivo y validar su instalación en
un segundo entorno antes de usarlo como contrato común. Hasta entonces, se
comparte una configuración común con rangos, no una reproducción exacta de
paquetes o de las métricas históricas.
