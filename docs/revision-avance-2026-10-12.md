# Verificación del avance — 12 de octubre de 2026

> **Registro histórico.** La [revisión del 13 de octubre](revision-avance-2026-10-13.md) reemplaza los estados y pendientes que quedaron desactualizados tras las entregas de Cueva, Angel y la integración local de Gerardo. Este informe conserva las comprobaciones y sus límites originales; sus tareas siguientes no deben utilizarse como lista vigente.

## Alcance y criterio

Revisión del código y documentación de `c588482`, commit que comparten `main`, `origin/main` y la rama local `cueva` después de actualizar el remoto. Se contrastaron las responsabilidades de [plan-desarrollo.md](plan-desarrollo.md) y los criterios de [bases-del-proyecto.md](bases-del-proyecto.md) con scripts, servicios, routers, páginas, pruebas y artefactos disponibles.

**Implementado** significa que existe el recorrido en código y sus pruebas; **reportado** identifica resultados de ejecuciones anteriores documentadas; **verificado hoy** identifica comprobaciones ejecutadas durante esta revisión. Un reporte histórico o una prueba con fixtures no acredita una ejecución completa desde otro clon, revisión cruzada ni demostración visual.

El proyecto tiene tres de seis módulos con servicio, API y página: fraude, crédito y grafos. Segmentación tiene pipeline y análisis, pero un problema metodológico bloquea la aceptación de sus resultados. Pronósticos tiene líneas base evaluadas; reclamos permanece en perfilado. La entrega integral todavía está pendiente.

**Actualización posterior de Cueva, 12 de octubre:** se implementaron asociaciones sencillas, endpoint/página de patrones, revisión técnica de Silver desde fraude y comandos de reproducción/verificación. Consultar el [cierre de entrega](fraude/cierre-entrega.md) para la evidencia más reciente del módulo; el resto de esta revisión conserva el diagnóstico inicial.

**Actualización posterior de Angel, 13 de octubre:** se corrigió el rango de fechas del perfil y se construyó el Silver de reclamos con limpieza de narrativas (ver [contrato](reclamos/contrato-silver.md) y [calidad](reclamos/calidad-silver.md)). Después se entrenó el clasificador de producto y se extrajeron los ejemplos de error (ver [resultados](reclamos/resultados-modelo.md) y [revisión](reclamos/revision-ejemplos.md)). Las filas de Angel siguientes conservan el diagnóstico inicial; falta la lectura humana de los ejemplos, el servicio y la página.

**Actualización posterior de Taco, 13 de octubre:** se cerró el bloqueo metodológico de segmentación: `CLUSTER_COLUMNS` ya no incluye `fraud_rate_received` y una prueba exige independencia de la etiqueta. Se regeneró el [reporte](transacciones/segmentacion.md) (146,629 cuentas, k=2, silueta 0.2305, ARI 0.7280) y se agregaron servicio, router (`api/routers/segments.py`) y página (`dashboard/pages/06_segmentos.py`) con sus pruebas. El diagnóstico de la fila de Taco abajo queda reemplazado por esta actualización; falta la revisión humana cruzada del contrato y la navegación.

## Estado de las etapas

| Etapa del plan | Estado contrastado | Qué falta para cerrarla | Responsables |
| --- | --- | --- | --- |
| 1. Conocer los datos | Perfiles de las tres fuentes; diccionarios y contratos por dominio. | Confirmar procedencia, versión y licencia; semántica original de `loan_status`; corregir fechas de reclamos. | Cueva–Taco: transacciones; Sevan: crédito; Angel: reclamos; todo el equipo participa en fuentes. |
| 2. Preparar los datos | Silver transaccional y crediticio; Gold transaccional y temporal implementados, con controles. | Silver de reclamos; reconstruir derivados ausentes en esta copia y validar trazabilidad. | Taco: Silver/mart/segmentos; Gerardo: Gold temporal; Sevan: crédito; Angel: reclamos. |
| 3. Desarrollar los análisis | Fraude y crédito comparan modelos contra referencias; grafos tiene evaluación exploratoria; segmentación tiene cuantiles/KMeans; temporal compara Naive/Naive estacional. | Corregir entrada etiquetada de segmentación; método principal temporal; NLP; documentar referencia comparable de grafos para el criterio común. | Cada responsable de módulo. |
| 4. Construir la aplicación | Tres routers de dominio y tres páginas reales. | Servicios, endpoints y páginas de segmentos, pronósticos y reclamos; actualizar inicio y revisar navegación. | Taco, Gerardo y Angel implementan su vista; Rhamses–Angel mantienen contrato/navegación. |
| 5. Integrar y entregar | Entorno común, instalador, pruebas y workflow CI existen. | Recorrido de los seis módulos, reproducción desde clon limpio, versiones reproducibles, Docker y evidencia de revisiones cruzadas. | Gerardo–Sevan coordinan reproducción; Rhamses–Angel integración; todos demuestran su módulo. |

## Cueva — fraude supervisado y patrones

| Compromiso del plan | Estado y evidencia |
| --- | --- |
| Perfilar PaySim y etiqueta | Implementado: `scripts/profile_fraud.py`, `ingestion/fraud_dataset.py`, `docs/fraude/perfil-paysim.md`. |
| Definir variables y evitar fuga | Implementado: `features/fraud.py`, `docs/fraude/contrato-variables.md`; excluye etiquetas y saldos posteriores de predictores. |
| Línea base y clasificador | Implementado: `models/fraud.py`, `scripts/train_fraud.py`; DummyClassifier y HistGradientBoostingClassifier. |
| Umbral y evaluación temporal | Implementado/reportado: cortes 323/378; AP 0.961840, precisión 0.796634, recall 0.992511; ejemplos TP/FP/FN/TN en `scripts/analyze_fraud_errors.py`. No se reentrenó el CSV completo hoy. |
| Servicio y página | Implementado: `services/fraud.py`, `api/routers/fraud.py`, `dashboard/pages/01_fraude.py`; predicción y métricas por HTTP. |
| Asociaciones y explicaciones | Asociaciones sencillas implementadas posteriormente: seis antecedentes fijos evaluados por partición, endpoint y consulta en página. Condiciones/errores disponibles; atribuciones individuales siguen como ampliación. Ver cierre de entrega. |

**Estado posterior:** revisión técnica de Silver desde fraude realizada a solicitud de Cueva; disponibilidad del saldo anterior y reproducción documentadas; asociaciones y página comprobadas. Falta registrar aceptación humana cruzada del equipo y confirmar fuente/licencia. La reproducción aislada y sus límites se detallan en el cierre de entrega.

## Sevan — riesgo crediticio y explicabilidad

| Compromiso del plan | Estado y evidencia |
| --- | --- |
| Perfil y semántica | Parcial: `ingestion/credit_profile.py`, `docs/credito/perfil-credito.md`; 1 = impago respaldado por copia, sin confirmación de fuente original. |
| Limpieza y variables | Implementado/reportado: `transforms/silver_credit.py`, `features/credit.py`; 32,409 filas Silver, 7 rechazos y 165 duplicados. Modelo principal excluye grado/tasa fijados por el prestamista. |
| Referencias y modelo | Implementado: `models/credit.py`; prior, logística y boosting, con variante comparativa con pricing. |
| Calibración y explicaciones | Implementado/reportado: calibración sigmoide, umbral por coste y oclusión; ROC-AUC 0.8886, AP 0.7968, Brier 0.0871 y ECE 0.0118 en el reporte histórico. |
| Servicio y página | Implementado: `services/credit.py`, `api/routers/credit.py`, `dashboard/pages/02_credito.py`. |
| Limitaciones sobre monto | Documentado: la API no recomienda monto; faltan exposición, pérdidas, plazo y política. |

**Siguiente entrega:** confirmar etiqueta/procedencia/licencia, regenerar Silver/modelo en esta copia para una demo, cerrar plantilla de métricas con Gerardo y revisión de navegación con Rhamses–Angel. Documentar la partición aleatoria sin fecha/cliente y el uso de edad. La recomendación de límite no es un pendiente del MVP salvo exigencia del curso.

## Rhamses — grafos de transacciones

| Compromiso del plan | Estado y evidencia |
| --- | --- |
| Red origen → destino | Implementado: `ingestion/graph_dataset.py`, `features/graph.py`; construcción dirigida desde muestras. No se acredita aquí carga de la red completa. |
| Indicadores | Implementado: métricas, grados, flujos y centralidad. |
| Patrones y evaluación | Implementado/reportado: `features/graph_patterns.py`, `scripts/evaluate_graph_alerts.py`; reporte con 50,000 transacciones y 100 fraudes. Cobertura combinada de un patrón 79%, precisión por cuenta 1.2027%. No es evaluación predictiva temporal. |
| Consultas y API | Implementado: `services/graph.py`, `api/routers/graphs.py`; resumen, cuenta, subgrafo, ranking y patrones. Caché respeta tamaño de muestra. |
| Vista manejable y simulación | Implementado: `dashboard/pages/03_redes.py` consume HTTP; extracción limitada a 500 nodos y pruebas asociadas. |

**Siguiente entrega:** cerrar contrato y navegación compartidos con Angel, comprobar el recorrido con datos reales acotados y revisar evidencia de aceptación desde otro clon. Para cumplir el criterio común de comparación, documentar una referencia de alertas y su comparación. Comunidades y partición temporal son ampliaciones; la portada anuncia comunidades aunque no se encontró implementación correspondiente.

## Taco — pipeline transaccional y segmentación

| Compromiso del plan | Estado y evidencia |
| --- | --- |
| Ingesta y Silver | Implementado y artefacto local presente: `transforms/silver_transactions.py`, `scripts/build_silver.py`; reporte completo de 6,362,620 filas. |
| Mart Gold | Implementado/reportado: `transforms/gold_transactions.py`, `scripts/build_gold_transactions.py`; una fila por transacción, conservación de montos/etiquetas y controles. Gold temporal es otra tabla. |
| Variables de comportamiento | Implementado: `features/segments.py`; destinos con al menos 10 operaciones recibidas. Adaptación razonable frente a poca repetición de orígenes. |
| Agrupamiento y evaluación | Implementado con bloqueo: `models/segments.py`, `scripts/segment_transactions.py`; cuantiles y MiniBatchKMeans, elección de k por silueta y remuestreo ARI. Reporte: 146,629 cuentas, k=5, silueta 0.2316, ARI medio 0.3883. Estas cifras requieren regeneración por el problema descrito abajo. |
| Servicio y página | Implementado (13 de octubre): `services/segments.py`, `api/routers/segments.py`, `dashboard/pages/06_segmentos.py`; consulta por segmento mediante HTTP con manejo de artefacto ausente (503). Pruebas nuevas de servicio/API y de página. |

**Bloqueo metodológico (resuelto el 13 de octubre):** `CLUSTER_COLUMNS` incluía `fraud_rate_received`; ya se excluyó y una prueba exige que cambiar solo `isFraud` no altere la matriz ni las etiquetas. La etiqueta se conserva solo para perfilar. Reporte regenerado en [segmentación](transacciones/segmentacion.md).

**Siguiente entrega:** revisión humana cruzada del contrato con Cueva y de la navegación con Rhamses–Angel; verificar el recorrido completo desde un clon limpio. Ampliaciones (comunidades, partición temporal) quedan fuera del alcance actual.

## Gerardo — pronósticos, monitoreo y reproducción

| Compromiso del plan | Estado y evidencia |
| --- | --- |
| Gold temporal y exploración | Implementado/reportado: `transforms/temporal_transactions.py`, `features/temporal.py`, scripts de Gold/exploración; 743 steps y tramo final solo fraude desde 719. |
| Referencia y método principal | Parcial: `models/forecast.py` solo tiene Naive y Naive estacional. Holt-Winters está propuesto, sin implementación. |
| Backtesting | Implementado/reportado: `evaluation/forecast.py`, `scripts/evaluate_forecast_baselines.py`; cuatro ventanas, horizonte 24, steps 1–718; MAE/RMSE/sMAPE. Naive seleccionado por MAE; referencia estacional competitiva para cantidad. |
| Monitoreo de distribuciones | Pendiente: periodo 719–743 reservado en configuración; no se encontró implementación de deriva ni reporte de monitoreo. Reservar el periodo no ejecuta el análisis. |
| Servicio y página temporal | Pendiente: no existen servicio/router/página temporal. |
| Reproducción y Docker | Parcial: instalador, entorno común y CI presentes; sin Docker/Compose ni lock común validado. No se acredita instalación en un segundo entorno/clon. |

**Siguiente entrega:** reconstruir Gold, implementar y comparar Holt-Winters contra ambas referencias en las mismas ventanas, documentar selección y limitaciones; después servicio y página. Añadir comparación histórica de distribuciones con límites explícitos, sin presentarla como monitoreo de lotes futuros. Coordinar con Sevan artefactos/versiones y finalmente empaquetado reproducible.

## Angel — reclamos, NLP y navegación

| Compromiso del plan | Estado y evidencia |
| --- | --- |
| Perfil y cobertura | Implementado/reportado: `ingestion/complaints_profile.py`, `scripts/profile_complaints.py`; 555,957 reclamos y 66,806 narrativas (12.02%). Las marcas `XXXX` se cuentan; no existe todavía un pipeline de limpieza del texto. |
| Limpieza estructurada/texto | Implementado posteriormente: Silver con tipos, marcas de calidad y `narrative_clean`; fechas del perfil corregidas (13 de octubre). Inicialmente pendiente. |
| Línea base y método NLP | Implementado posteriormente (13 de octubre): referencia trivial, Naive Bayes y TF-IDF con regresión logística para predecir `product`. Los tópicos quedan fuera. Inicialmente pendiente. |
| Evaluación y ejemplos | Parcial (13 de octubre): prueba cronológica con macro-F1 0.728 frente a 0.668 y 0.037; ejemplos extraídos y comentados, pero la lectura humana de la revisión sigue pendiente. Inicialmente pendiente. |
| Servicio y página de reclamos | Pendiente: no existen servicio/router/página de reclamos. |
| Navegación con Rhamses | Parcial: portal y tres páginas existen; portada omite segmentos, marca crédito en desarrollo y navegación solo menciona fraude/redes. |

**Siguiente entrega:** parsear/validar fechas y cubrir cruce de años; regenerar perfil. Construir Silver estructurado y texto limpio respetando las narrativas disponibles. Fijar una tarea NLP, comparar línea base y método principal, registrar métricas y ejemplos; después servicio, API y página. Actualizar portada y contrato de navegación con Rhamses sin asumir la implementación de vistas de otros responsables.

## Orden de trabajo y criterios de aceptación

| Orden | Trabajo concreto | Responsable principal / apoyo | Aceptación |
| --- | --- | --- | --- |
| 1 | Corregir uso de etiqueta en segmentación (**hecho el 13 de octubre**) | Taco / Cueva revisa contrato | Matriz sin fraude/derivados, comprobación de independencia de etiquetas, reporte y perfiles regenerados. |
| 1 | Corregir fechas y crear Silver de reclamos | Angel / Taco apoya patrón de calidad | Tipos fecha, prueba entre años, rango correcto, recuentos/rechazos trazables y texto procesado. |
| 1 | Cerrar revisiones de contratos y actualizar estado documental | Cueva–Taco, Sevan–Gerardo, Rhamses–Angel | Confirmaciones y decisiones registradas; resumen del plan/guía/portada coherentes con el código. |
| 2 | Entregar segmento de aplicación (**hecho el 13 de octubre**) | Taco / Rhamses–Angel revisan HTTP | Consulta de cuentas/perfiles desde página mediante API y manejo de artefacto ausente. |
| 2 | Completar método temporal | Gerardo / Sevan revisa evaluación | Modelo principal comparado en las cuatro ventanas sin fuga; elección y errores documentados. |
| 2 | Implementar NLP | Angel / revisión de otra pareja | Línea base y método principal, evaluación independiente y ejemplos documentados. |
| 3 | Completar vistas temporal y reclamos | Gerardo y Angel / Rhamses apoya contratos | Cada vista consume su endpoint con datos/resultados reales y errores manejados. |
| 3 | Añadir comparación histórica de distribuciones | Gerardo / Sevan | Periodos comparables, métricas/límites y reporte; sin prometer monitoreo futuro. |
| 4 | Reproducir y empaquetar seis módulos | Gerardo–Sevan / todos | Clon/entorno limpio, LFS, derivados/modelos reconstruidos, suite, API/panel, demo y Docker documentados. |

La procedencia/licencia de los CSV sigue abierta para todo el equipo, con los propietarios de cada dominio recopilando la evidencia. No hay fechas comprometidas en el plan: este orden es una propuesta basada en dependencias, no un calendario acordado ni una reasignación del reparto.

## Documentación que requiere actualización

- El resumen del plan fechado el 9 de octubre mezcla entregas del 11 y todavía dice que redes llama directamente a servicios; el código actual llama a la API.
- Los pendientes de Taco presentaban Gold/segmentación como trabajo futuro y la corrección metodológica de la etiqueta; ya están implementados y la independencia de la etiqueta se verificó el 13 de octubre (ver la actualización de Taco arriba).
- Los pendientes de Gerardo aún presentan definición de horizonte y comparación de referencias como futuros; ya hay horizonte 24 y backtesting.
- `docs/pruebas-reproduccion.md` afirma que fraude carece de API/página, Silver falta y la caché de grafos no respeta el límite. Esas afirmaciones quedaron desactualizadas. Sus instrucciones deben revisarse junto con la prueba desde un clon limpio.
- La portada marcaba crédito en desarrollo y ofrecía detección de comunidades no implementada; además omitía segmentación. **Resuelto el 13 de octubre (Taco):** la portada ya incluye segmentación.
- `docs/transacciones/contrato-gold.md` todavía anunciaba la segmentación como siguiente entrega. **Resuelto el 13 de octubre (Taco).**

## Validación de esta revisión

- Python local 3.12.14; `pip check`: sin dependencias rotas.
- Inventario local: CSV de los tres dominios presentes, Silver transaccional y modelos fraude/fraude-silver presentes. No se encontraron Gold temporal/transaccional, derivados de segmentos ni Silver/modelo de crédito en esta copia. Su ausencia local no implica ausencia de implementación: están excluidos de Git y deben reconstruirse.
- Suite completa ejecutada hoy: **157 pruebas aprobadas en 19.716 segundos**, con Python 3.12.14 y concurrencia numérica limitada a dos hilos. Las ejecuciones restringidas iniciales se interrumpieron; la ejecución final fuera de esas restricciones terminó con código 0. Log local: `artifacts/reports/verificacion-avance-2026-10-12-tests.txt`. Hubo avisos de deprecación de TestClient y de NumPy en series pequeñas, sin fallos.
- Se recalcularon los SHA-256 de los tres CSV: coinciden con `docs/datasets.md`. Silver transaccional tiene **6,362,620 filas**; su SHA-256 coincide con el reporte local de calidad y sus cinco controles figuran aprobados. Se verificaron filas/huella, sin repetir toda la transformación.
- API comprobada en proceso mediante `TestClient`, sin servidor HTTP externo: estado, métricas de fraude y predicción con el modelo real `fraud-silver` devolvieron 200; resumen de grafo desde el CSV con límite solicitado de 1,000 devolvió 200. Esto no acredita la navegación visual ni la red completa. Crédito devuelve 503 porque falta su modelo local: es ausencia del artefacto, no de la implementación.
- Problema de fechas reproducido: entradas `12/31/2014` y `01/01/2015` producen mínimo `01/01/2015` y máximo `12/31/2014`, inversos al orden cronológico.
- Problema de segmentación reproducido: con el mismo comportamiento y cambiando solo `isFraud` a cero, cambia la matriz de agrupamiento. La suite existente pasa porque no exige independencia de etiquetas.
- Evidencia JSON local: `artifacts/reports/verificacion-avance-2026-10-12.json`. Tanto el log como el JSON están excluidos de Git; este informe conserva el resultado y el alcance de las comprobaciones.
- No se reentrenaron todos los modelos ni se regeneraron los pipelines completos; tampoco se realizó demo visual de navegador, clon limpio ni comprobación del resultado de CI en GitHub.

El cierre de un módulo necesita completar sus compromisos y verificar su aceptación. No se asigna un porcentaje global: contar archivos, commits o casillas mezclaría tareas de esfuerzo y alcance diferentes.
