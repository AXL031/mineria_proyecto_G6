# Pruebas y reproducción local

Revisión del 9 de octubre de 2026. Complementa el [plan de desarrollo](plan-desarrollo.md). Los comandos se ejecutan en PowerShell desde la raíz del repositorio. Esta guía describe verificaciones pendientes; no certifica una ejecución completa exitosa.

## Qué se puede probar hoy

| Componente | Verificación disponible | Límite actual |
| --- | --- | --- |
| Fraude | Perfil, pruebas unitarias, entrenamiento y scoring por CLI. | Sin endpoint ni página. Artefactos locales excluidos de Git. El entrenamiento lee Bronze. |
| Grafos | Pruebas de ingesta, métricas, patrones y servicios; API y página de redes. | API probada con grafo en memoria; página llama directamente a servicios. Falta recorrido API → panel. |
| Transacciones | Pruebas de Silver y construcción desde CSV. | Parquet local ausente; requiere regeneración. Segmentación pendiente. |
| Temporal | Pruebas de agregación y exploración; construcción Gold y gráficos. | Parquet local ausente; pronóstico y backtesting pendientes. |
| Reclamos | Pruebas y perfilado del CSV. | Rango temporal incorrecto por comparación de cadenas; sin Silver, modelo ni página. |
| Crédito | CSV original disponible. | Sin pipeline ni pruebas propias encontradas. |

## Bloqueos y responsables

| Prioridad | Falta o problema | Acción y responsable |
| --- | --- | --- |
| P0 | Intérprete utilizable y entorno con todas las dependencias. | Cada integrante prepara un entorno aislado; Sevan–Gerardo documentan y validan una instalación común. |
| Resuelto en configuración | `TestClient` necesita `httpx`. | Declarado en el extra `test`, incluido en `requirements/common.txt`; falta verificar instalación y suite completas. |
| P0 | Silver y Gold no existen en esta copia. | Taco ejecuta Silver completo; Gerardo genera Gold y exploración. Verificar controles y recuentos. |
| P1 | Archivos de versiones fijadas no forman un entorno común: `fraud.txt` y `graph.txt` fijan `tzdata==2026.4`, `transactions.txt` fija `tzdata==2026.5`. | Sevan–Gerardo unifican versiones y Python tras validar la suite. No instalar todos los archivos fijados juntos. |
| P1 | API y panel no recorren juntos los datos reales. | Rhamses–Angel conectan redes a la API y añaden una prueba de integración con muestra acotada. |
| P1 | No existe endpoint ni página de fraude. | Cueva implementa ambos y acuerda con Taco el uso de Silver. |
| P1 | Caché de grafos ignora cambios de `limit` tras la primera carga. | Rhamses define caché por muestra o rechaza cambios explícitamente; añade prueba que cambie el límite. |
| P1 | Rango de fechas de reclamos incorrecto. | Angel parsea fechas antes de compararlas, prueba cruce de años y regenera el reporte completo. |
| P2 | Modelos/análisis de crédito, segmentación, pronósticos y NLP incompletos. | Cada responsable completa su siguiente entrega según el plan; todavía no se pueden demostrar los seis módulos finales. |
| P2 | Procedencia/licencia, comando único, Docker y reproducción desde clon limpio pendientes. | Equipo confirma fuentes; Gerardo coordina reproducción y empaquetado después de validar el recorrido local. |

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

Aceptar cuando Silver conserva 6,362,620 filas para esta fuente, no hay rechazos y pasan sus controles; Gold tiene 743 filas, conserva cantidad/monto/fraudes y no tiene nulos. Comparar con los reportes versionados. No existe todavía un pronóstico evaluado.

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

Abrir Swagger en `http://127.0.0.1:8000/docs` y panel en `http://localhost:8501`. Usar una cuenta devuelta por el ranking para consultar cuenta/subgrafo. Confirmar respuesta de error para una cuenta inexistente. La primera consulta de resumen fija hoy la muestra en caché: reiniciar la API antes de probar otro límite hasta corregirlo.

En redes, comprobar KPIs, ranking, subgrafo y filtros de patrones. La página puede funcionar sin la API porque llama directamente a servicios: esto valida dos componentes separados, no la integración API → panel. El endpoint raíz tampoco acredita que todos los módulos anunciados estén implementados.

## Evidencia de esta revisión

- El comando `python` del PATH apuntó a WindowsApps y no pudo iniciar.
- Con el Python incluido en Codex, la suite no pudo completarse: faltaban dependencias (`fastapi`, `joblib`, `pyarrow`, `matplotlib` y `networkx` en verificaciones realizadas) y algunas pruebas encontraron restricciones de escritura temporal.
- Existe `.venv` con Python 3.12 y dependencias de fraude; el intento de ejecutar la suite no produjo resultados y se interrumpió. No se considera un entorno común validado.
- No se instaló un entorno nuevo ni se ejecutó entrenamiento/procesamiento completo durante esta revisión. No se certifican pruebas aprobadas ni funcionamiento visual de la aplicación.

## Criterio para declarar el primer recorrido probado

1. Instalación desde entorno limpio y `pip check` sin conflictos.
2. Suite completa sin errores, con versiones y resultado registrados.
3. CSV completos; Silver y Gold regenerados con controles aprobados.
4. Scoring de fraude con artefacto compatible y metadatos identificados.
5. API de grafos y página de redes demostrables con datos reales acotados.
6. Para declarar el MVP integrado: página de fraude consumiendo su endpoint y contrato de datos revisado Cueva–Taco; integración API → panel revisada Rhamses–Angel.

Los puntos 1–5 permiten probar los componentes existentes; el punto 6 todavía necesita desarrollo. La entrega de los seis módulos requiere además los pendientes individuales del plan.

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
las versiones exactas en `requirements/common-lock.txt` mediante
`pip freeze --exclude-editable`, revisar el archivo y validar su instalación en
un segundo entorno antes de usarlo como contrato común. Hasta entonces, se
comparte una configuración común con rangos, no una reproducción exacta de
paquetes o de las métricas históricas.
