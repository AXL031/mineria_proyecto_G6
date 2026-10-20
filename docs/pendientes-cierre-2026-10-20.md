# Pendientes vigentes y contratos de cierre — 20 de octubre de 2026

Este es el punto de entrada vigente para continuar BankShield. Reemplaza las listas de trabajo del 9, 12 y 13 de octubre cuando se contradigan. Los documentos anteriores conservan evidencia histórica; sus porcentajes no se trasladan al alcance ampliado. Este documento asigna trabajo futuro: no declara implementadas las ampliaciones.

## Objetivo y evidencia de partida

Contraste con `ENTREGABLES DE PROYECTO (1).pdf`, facilitado por Cueva el 20 de octubre: semanas 7, 10, 13 y 16. Copia consultada: `C:/Users/axel.cueva/Downloads/ENTREGABLES DE PROYECTO (1).pdf`; esa ruta personal no es una dependencia del software ni debe incluirse en scripts. Las tecnologías de la sección 22 son sugeridas. El ejemplo de clientes/ventas de la sección 26 se adapta justificadamente al dominio financiero. Las técnicas enumeradas en los entregables sí deben acreditarse.

Ya existen seis módulos con servicio/API/página: fraude, crédito, grafos, pronósticos, segmentos y reclamos. Los artefactos locales fueron preparados; los registros del 13 de octubre documentan 238 pruebas y 48 comprobaciones reales. Son resultados históricos, no pruebas ejecutadas para esta planificación. Hay cambios locales sin commit, entre ellos reclamos y scripts de demo: preservarlos, inspeccionarlos e integrarlos con revisión; no reconstruirlos como si faltaran.

## Prioridades y reparto

- **P0 — cobertura técnica:** regresión numérica explícita y descubrimiento automático de asociaciones. La regresión figura como entregable independiente; ampliar asociaciones evita depender únicamente de reglas manuales. Los algoritmos concretos siguientes son decisiones internas del equipo, no imposiciones del PDF.
- **P1 — cierre acordado:** comparación de grafos, integración de las ampliaciones, pruebas, reproducción, fuentes y aceptación humana.
- **P2 — mejora recomendada:** historial del desempeño de modelos y mantenimiento. Se agrega al backlog por acuerdo de esta revisión, sin convertirla en condición adicional del PDF. Docker/Compose queda como empaquetado opcional, salvo otro acuerdo expreso del curso/equipo.

| Responsable | IDs y próxima entrega | Encargo detallado | Revisión de otra pareja |
| --- | --- | --- | --- |
| Cueva | CUE-01 asociaciones completas; CUE-02 aceptación de datos/segmentos y fuente PaySim | [Cueva](encargos/cueva.md) | Sevan revisa minería y evaluación; Taco valida datos. |
| Taco | TAC-01 datos y discretización compartidos; TAC-02 cierre de segmentos/trazabilidad | [Taco](encargos/taco.md) | Gerardo revisa particiones; Cueva acepta contrato. |
| Sevan | SEV-01 regresión completa; SEV-02 cierre crediticio; SEV-03 entorno con Gerardo | [Sevan](encargos/sevan.md) | Rhamses revisa API y evaluación; Gerardo valida reproducción. |
| Rhamses | RHA-01 comparación de grafos; RHA-02 cierre HTTP/navegación con Angel | [Rhamses](encargos/rhamses.md) | Cueva revisa comparación; Angel valida interfaz. |
| Gerardo | GER-01 reproducción y versiones; GER-02 monitoreo recomendado; GER-03 aceptación temporal | [Gerardo](encargos/gerardo.md) | Taco revisa reproducción; Sevan revisa métricas. |
| Angel | ANG-01 integración central y verificación; ANG-02 aceptación NLP; ANG-03 matriz de entregables | [Angel](encargos/angel.md) | Gerardo revisa integración; Rhamses valida navegación. |

El responsable implementa y prueba su entrega completa. El revisor aporta aceptación, no asume silenciosamente su implementación. Un agente puede preparar evidencia técnica; la aceptación humana debe ser confirmada por la persona y quedar pendiente hasta entonces.

## Reglas comunes para cualquier agente

1. Leer este documento y el encargo individual antes de editar. Inspeccionar `git status --short`, instrucciones locales y código actual. Conservar los cambios ajenos. No hacer reset, descartar archivos, forzar pushes ni sobrescribir artefactos de otros experimentos.
2. Mantener originales Bronze inmutables y fuentes independientes. No inventar un enlace entre cuentas PaySim, solicitantes de crédito y reclamos CFPB.
3. Usar Python 3.12 y las dependencias actuales. Las tareas no requieren migrar a React, una base SQL o deep learning. Evitar dependencias nuevas si la implementación acotada cabe en las ya instaladas.
4. Procesamiento y entrenamiento en scripts offline; los GET sirven artefactos preparados. Ninguna consulta del panel debe entrenar modelos o regenerar millones de filas.
5. Guardar datos generados en `data/gold/`, modelos en `artifacts/models/` y evidencia en `artifacts/reports/`. No añadir esos binarios a Git. Versionar código, configuración, contratos y un resumen de resultados.
6. Artefactos nuevos: `schema_version`, fecha UTC, commit si está disponible, indicador de árbol con cambios, fuente/formato/SHA-256, configuración, cortes, filas por partición, semilla, versiones y limitaciones. Un commit con cambios locales no identifica por sí solo todo el código ejecutado: adjuntar resumen de diferencias o huella de fuentes del experimento.
7. Inferencia y evaluación deben usar el mismo pipeline guardado. `model_id` es SHA-256 del archivo de modelo; `analysis_id` identifica el contenido/configuración de un análisis no ligado a un predictor. Verificar identidades al combinar archivos.
8. JSON estricto: sin NaN ni Infinity; métricas indefinidas como `null` y motivo. Nunca reemplazar una métrica indefinida por cero para aparentar buen resultado.
9. Nuevas entradas HTTP: rechazar campos extra, números no finitos, tipos desconocidos y negativos cuando corresponda. Contratos nuevos: 422 entrada inválida, 404 recurso inexistente, 503 artefacto ausente/incompatible. Esto no exige reescribir todos los contratos históricos.
10. No prometer una mejora de rendimiento. Una referencia que gana debe permanecer seleccionada. No ajustar parámetros después de ver prueba; documentar resultados desfavorables.
11. Pruebas con `unittest` y fixtures pequeños; HTTP con `TestClient` y páginas con AppTest según los patrones actuales. CI no descarga ni entrena el Bronze completo. La demo integral sí necesita los originales completos y artefactos reales.
12. Actualizar el estado por ID con evidencia, comandos y limitaciones. Las tareas comienzan pendientes. No marcar pruebas, fuentes, aceptación de personas, CI remoto o ejecución en otra PC como aprobados sin evidencia.

## Contrato D1: tabla analítica compartida

**Propietario: Taco. Consumidores: Cueva y Sevan.** Especificación en [TAC-01](encargos/taco.md).

| Elemento | Contrato acordado |
| --- | --- |
| Entrada | Silver transaccional completo y su reporte de calidad; verificar procedencia y huella. |
| Salida | `data/gold/analytics/transactions.parquet`. No sustituye el mart existente de segmentos. |
| Columnas | `row_id`, `step`, `type`, `amount`, `oldbalanceOrg`, `isFraud`, `partition`, `amount_bin`, `origin_balance_bin`. |
| Identidad de fila | `row_id`: posición ordinal de fila, base 1, en el Silver de entrada, antes de filtrar. Solo identifica filas; nunca predictor. |
| Metadatos | `artifacts/reports/analytics/dataset.json` y `artifacts/reports/analytics/discretization.json`. |
| Huellas | `source_sha256` identifica el Silver original; `dataset_sha256`, el Parquet D1; `discretization_sha256`, el esquema de bins. Conservar estas distinciones en los reportes consumidores. |
| Particiones nuevas | train: steps 1–323; validation: 324–378; test: 379–718; stress: 719–743. Sin mezcla de filas ni muestreo del test. |
| Discretización | Terciles separados de `amount` y `oldbalanceOrg`, ajustados solo con train; bordes repetidos se colapsan. Rangos extremos abiertos para aplicar a otros periodos. |

Los cortes son decisiones del nuevo experimento y no modifican las métricas históricas de fraude. Allí el test llegaba a 743; aquí se separa su cierre anómalo como stress. Todo reporte debe indicar esa diferencia. Stress se informa aparte y no selecciona modelos, bins, reglas ni umbrales.

`amount_bin` se usa para asociaciones; está prohibido como predictor del monto en regresión. Los agentes pueden desarrollar con un fixture que cumpla D1 mientras Taco prepara el archivo real; no deben sustituirlo silenciosamente por datos sintéticos al declarar una demo real.

## Contratos de servicios y propiedad de archivos

| Capacidad | Artefactos principales | HTTP nuevo | Archivos compartidos/propietario |
| --- | --- | --- | --- |
| Asociaciones | `artifacts/models/associations/rules.json` | `GET /api/fraud/associations` | Cueva: router/página de fraude y servicio propio. Preservar `/api/fraud/patterns`. |
| Regresión | `artifacts/models/regression/model.joblib`, `metrics.json`, `predictions.parquet` | `POST /api/regression/predict`, `GET /api/regression/model`, `GET /api/regression/examples` | Sevan: router nuevo y `dashboard/pages/07_regresion.py`. Angel registra el router central. |
| Comparación de redes | `artifacts/reports/graph/comparison.json` | `GET /api/graphs/evaluation` | Rhamses: router/página de grafos y evaluador. |
| Historial recomendado | `artifacts/reports/monitoring/runs/<run_id>.json` | `GET /api/monitoring/runs`, `GET /api/monitoring/runs/{run_id}` | Gerardo: router nuevo y ampliación de página temporal. Angel registra router central cuando exista. |
| Integración | manifiesto de capacidades y verificación integral | raíz `/` y OpenAPI | Angel: `api/main.py`, `dashboard/app.py`, `scripts/verify_demo.py`. |
| Preparación/entorno | manifiesto de preparación y dependencias validadas | no aplica | Gerardo: `scripts/prepare_demo.py`, `scripts/setup_env.ps1`, `requirements/*`, `pyproject.toml`, `.github/workflows/tests.yml`. |

Los endpoints anteriores son futuros: no anunciarlos como disponibles hasta integrarlos y verificarlos. Los contratos precisos de cuerpo/respuesta y pruebas están en cada encargo. Cada propietario agrega sus pruebas de módulo. Angel agrega las de integración, sin trasladar toda la carga de pruebas a Angel.

Cambios en un archivo de otro propietario: enviar un parche concreto para integración o coordinar una edición secuencial. No dejar implementaciones paralelas de un mismo router o preparación. Cueva conserva la página 01, Rhamses la 03, Gerardo la 04, Angel la 05 y Sevan la nueva 07; Taco conserva la 06. La portada central es de Angel.

## Secuencia de trabajo y dependencias

### Instrucción lista para entregar a cada agente

> Lee `docs/pendientes-cierre-2026-10-20.md` y `docs/encargos/<integrante>.md` (sustituye `<integrante>` por el nombre en minúsculas). Inspecciona el estado local y preserva cambios ajenos. Implementa los IDs de tu encargo por prioridad y sus pruebas/criterios de aceptación, respetando los contratos y la propiedad de archivos. Si una dependencia aún no existe, avanza con un fixture explícito del contrato y registra que la corrida real sigue pendiente. No marques trabajo de otra persona, revisión humana, publicación o reproducción externa como realizado sin evidencia. Entrega cambios revisables, comandos, resultados reales y pendientes; actualiza los checklists sin presentar P2 como obligación del PDF.

### Orden acordado

1. **Datos y contratos:** Taco entrega D1 y fixtures; Sevan/Cueva desarrollan contra ese contrato. Rhamses trabaja en su comparación de forma independiente. Angel prepara pruebas de contratos y navegación con respuestas simuladas explícitas en tests.
2. **Capacidades P0:** Cueva entrega asociaciones y Sevan regresión, con scripts, artefactos reales, pruebas y página. Cada uno conserva sus contratos existentes.
3. **Integración P1:** Rhamses entrega comparación; Angel registra routers y navegación; Gerardo integra preparación y fija entorno; equipo ejecuta pruebas y demo. Aceptaciones de fuentes/contratos en paralelo.
4. **Reproducción P1:** una segunda persona recrea entorno y derivados desde otro clon con LFS; registrar recursos, tiempos, versiones y logs. Corregir la primera causa que falle y repetir la fase afectada.
5. **Mejoras P2:** historial de desempeño por lotes y, si se mantiene como entregable, Docker/Compose. Estas mejoras no bloquean cerrar los requisitos que ya estén acreditados; informar su estado aparte.

## Comandos y evidencias

Disponibles hoy, desde la raíz en PowerShell:

```powershell
git lfs pull
powershell -ExecutionPolicy Bypass -File scripts/setup_env.ps1
.venv-pruebas/Scripts/python.exe -m unittest discover -s tests/unit -v
.venv-pruebas/Scripts/python.exe scripts/prepare_demo.py
powershell -ExecutionPolicy Bypass -File scripts/start_demo.ps1
.venv-pruebas/Scripts/python.exe scripts/verify_demo.py
powershell -ExecutionPolicy Bypass -File scripts/stop_demo.ps1
```

Objetivos de CLI **por implementar**, con `--help`, errores accionables y salida no cero en fallo:

```powershell
.venv-pruebas/Scripts/python.exe scripts/build_analytics_transactions.py --config configs/analytics.json
.venv-pruebas/Scripts/python.exe scripts/mine_associations.py --config configs/associations.json
.venv-pruebas/Scripts/python.exe scripts/train_regression.py --config configs/regression.json
.venv-pruebas/Scripts/python.exe scripts/evaluate_graph_alerts.py --limit 10000 --comparison-output artifacts/reports/graph/comparison.json
# P2, después de generar predicciones reales de regresión:
.venv-pruebas/Scripts/python.exe scripts/monitor_model_performance.py --config configs/model_monitoring.json
```

Cada agente entrega: lista de cambios, comando reproducible, resultado de pruebas relevantes, limitaciones y pendientes humanos. Los logs de ejecución deben indicar fecha/entorno; no reciclar los números 238/48 como si probaran el alcance ampliado.

## Checklist de cierre compartido

- [ ] D1 completo, controles aprobados y procedencia vinculada a Silver.
- [ ] Regresión numérica con referencia, evaluación independiente, artefacto, HTTP y panel.
- [ ] Asociaciones descubiertas automáticamente, selección sin test y evaluación posterior.
- [ ] Comparación de grafos con igual universo y presupuesto de alertas.
- [ ] Preparación y verificación recorren las seis capacidades existentes y regresión.
- [ ] Pruebas relevantes y suite completa aprobadas para la revisión final del código.
- [ ] Reproducción integral desde otro clon/entorno, con LFS y evidencia de recursos/tiempos.
- [ ] Fuentes y condiciones de uso de los tres CSV; semántica original de `loan_status`.
- [ ] Aceptaciones cruzadas y lectura humana de errores registradas.
- [ ] Cambios locales revisados e integrados; CI remoto comprobado cuando se publique.
- [ ] Matriz requisito → evidencia y material final coherentes con resultados reales.
- [ ] P2: historial de desempeño, si se implementa; informar estado sin confundirlo con monitoreo histórico ya existente.
- [ ] P2: Docker/Compose, solo si se conserva dentro de la entrega acordada.

Los dos últimos puntos son opcionales respecto de este contraste del PDF. Las revisiones documentales no requieren reentrenar módulos que no hayan cambiado.
