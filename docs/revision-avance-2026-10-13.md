# Avance y pendientes del equipo — 13 de octubre de 2026

## Alcance y evidencia

Estado del código integrado en `55d81d0`: incluye los PR #13 de Cueva y #14 de Angel, y la integración de los tres commits nuevos de Gerardo. La actualización de documentación se prepara sobre esa integración para publicarse directamente en `main` por indicación de Cueva. No se incluye trabajo de otros integrantes sin subir.

La suite de la integración pasó: **213 pruebas en 41.246 segundos**, con Python 3.12 y concurrencia numérica limitada a dos hilos. Log local excluido de Git: `artifacts/reports/integracion-gerardo-2026-10-13-tests.txt`. Se resolvió el conflicto en `docs/plan-desarrollo.md` conservando los avances de Angel y Gerardo. Las pruebas no sustituyen una demo completa con datos reales ni una reproducción de los seis módulos desde clon limpio.

## Resumen actual

| Integrante | Avance estimado | Cambios implementados | Próxima entrega |
| --- | ---: | --- | --- |
| Cueva | 95% | Fraude temporal, patrones descriptivos, servicio/API/página y reproducción aislada. | Registrar aceptación cruzada y apoyar la revisión del contrato de segmentación. |
| Sevan | 90% | Silver de crédito, modelo calibrado, explicaciones, servicio/API/página. | Reconstruir los artefactos de crédito para la demo y cerrar revisión de fuente y reproducción. |
| Rhamses | 85% | Grafos, indicadores, patrones, evaluación de alertas, consultas API y página mediante HTTP. | Cerrar comparación con una referencia y navegación compartida; validar una demo acotada. |
| Gerardo | 85% | Gold temporal, backtesting, Holt-Winters comparado, monitoreo histórico, servicio/API/página. | Reconstruir Gold/monitoreo aquí, validar visualmente y coordinar reproducción/Docker. |
| Angel | 70% | Fechas corregidas, Silver/texto limpio, clasificador de producto y ejemplos de error. | Revisar ejemplos y entregar servicio/API/página de reclamos con navegación. |
| Taco | 55% | Silver y mart Gold transaccional, variables por destino, cuantiles y KMeans evaluados. | Corregir el uso de etiqueta en agrupamiento, regenerar resultados y entregar servicio/API/página. |

**Estimación global orientativa: alrededor de 80%.** Es el promedio redondeado de las estimaciones individuales, con un margen aproximado de cinco puntos. Considera preparación de datos, análisis evaluado, aplicación y reproducción; no es una medición de horas, número de commits ni una rúbrica formal del curso. El cierre exige cumplir los criterios siguientes, aunque la estimación sea alta.

## Cueva — fraude y patrones

**Implementado:** perfil/contrato, variables anteriores a la operación, referencia y clasificador, cortes temporales y umbral en validación, análisis de errores, patrones descriptivos, predicción/métricas/patrones por API y página. El [cierre de entrega](fraude/cierre-entrega.md) documenta reconstrucción completa en una copia aislada, métricas reproducidas y 14 comprobaciones HTTP/página.

**Pendientes:**

1. Registrar revisión humana cruzada y aceptación del contrato transaccional/API/navegación con Taco y Rhamses–Angel.
2. Revisar con Taco que la segmentación use solo comportamiento, dejando fraude para descripción posterior.
3. Aportar evidencia de procedencia/licencia de PaySim y participar en la demo integrada.

**Aceptación:** revisión y decisiones registradas, contrato consistente y recorrido de fraude reproducible junto con los demás módulos. Atribuciones individuales y reglas aprendidas adicionales son ampliaciones; los patrones descriptivos ya están implementados.

## Sevan — crédito y explicabilidad

**Implementado:** perfil, Silver, contrato de variables, referencias y boosting, calibración, umbral por coste, explicaciones por oclusión, API y página. Los [resultados documentados](credito/resultados-modelo.md) incluyen ROC-AUC 0.8886 y AP 0.7968; no se reentrenó el modelo en esta revisión.

**Pendientes:**

1. Reconstruir Silver/modelo en esta copia y ensayar predicción, métricas y explicación mediante API/página.
2. Confirmar `loan_status`, procedencia y licencia con la fuente original; distinguir ese respaldo de la copia en OpenML.
3. Cerrar con Gerardo formato de métricas, versiones y reconstrucción de artefactos; registrar revisión cruzada.
4. Revisar navegación con Rhamses–Angel y conservar las limitaciones de partición aleatoria sin fecha/cliente y del uso de edad.

**Aceptación:** otro integrante puede reconstruir el modelo y demostrar la página; etiqueta y fuente documentadas, revisión registrada. Recomendar un monto de crédito no forma parte del MVP actual: faltan datos y política para hacerlo.

## Rhamses — grafos y navegación compartida

**Implementado:** red dirigida, indicadores de cuentas/conexiones, patrones y reporte de alertas, servicios/endpoints de resumen, cuenta, subgrafo y ranking; página mediante HTTP, límite de 500 nodos y caché que respeta la muestra. La evaluación documentada usa 50,000 transacciones; no acredita la red completa ni una evaluación predictiva temporal.

**Pendientes:**

1. Documentar una referencia comparable de alertas y contrastar cobertura, precisión y límites del método.
2. Ensayar consultas y subgrafos con una muestra real acotada; registrar aceptación desde otro entorno.
3. Cerrar con Angel contratos HTTP, navegación y estados de artefacto ausente para las páginas pendientes.
4. Corregir con Angel la portada: evitar anunciar comunidades sin implementación y representar los seis módulos con su estado real.

**Aceptación:** comparación y limitaciones documentadas, consultas demostrables y navegación coherente. Comunidades y evaluación temporal de red son ampliaciones posteriores.

## Gerardo — pronósticos, monitoreo y reproducción

**Implementado:** Gold por `step`, exploración, cuatro ventanas de backtesting de horizonte 24 sobre steps 1–718; Naive, Naive estacional y tres configuraciones Holt-Winters. [Holt-Winters no mejora el MAE](pronosticos/resultados-holt-winters.md), por lo que Naive permanece seleccionado. El [monitoreo](pronosticos/resultados-monitoreo.md) compara 694–718 con 719–743 y detecta cambios en seis indicadores. Servicio, endpoints `/api/forecast/projection` y `/api/forecast/monitoring`, página `04_pronosticos.py` y pruebas ya están integrados localmente.

**Pendientes:**

1. Registrar la aceptación humana cruzada de la integración; la publicación directa en `main` fue solicitada por Cueva y no sustituye esa revisión.
2. Reconstruir Gold y reporte de monitoreo en esta copia; ensayar cantidad/monto, horizontes y estados de error en API/página.
3. Registrar comprobación visual del recorrido y revisión de evaluación con Sevan.
4. Coordinar entorno común, versiones, comando de reproducción y Docker/Compose cuando esté completo el recorrido de los seis módulos.

**Aceptación:** artefactos reconstruibles, demo temporal real y reproducción integral documentada. No hace falta volver a implementar Holt-Winters ni monitoreo: existen. Los cambios detectados son históricos en una simulación y los intervalos de la página son descriptivos, sin cobertura calibrada.

## Angel — reclamos, NLP y navegación

**Implementado:** perfil con rango cronológico corregido (2011-12-01 a 2016-04-25), Silver de 555,957 filas, 66,806 narrativas y limpieza de censuras. Referencia trivial, Naive Bayes y TF-IDF/regresión logística para producto. [Prueba cronológica](reclamos/resultados-modelo.md): macro-F1 0.728 frente a 0.668 y 0.037; [ejemplos de error](reclamos/revision-ejemplos.md) extraídos y comentados.

**Pendientes:**

1. Confirmar mediante lectura humana los ejemplos de error y registrar conclusiones y limitaciones.
2. Crear servicio, endpoints y página de reclamos con predicción/análisis, tendencias y ejemplos permitidos; manejar ausencia del modelo.
3. Reconstruir Silver/modelo para la demostración de esa página y documentar sus comandos.
4. Cerrar navegación, contrato HTTP y portada con Rhamses; cada responsable implementa su propia vista.
5. Aportar confirmación de procedencia/licencia de CFPB y revisión cruzada.

**Aceptación:** página conectada a la API con resultados reales y manejo de errores, revisión de ejemplos registrada y navegación coherente. Corregir fechas, construir Silver y entrenar el clasificador ya no son pendientes de implementación.

## Taco — datos transaccionales y segmentación

**Implementado:** Bronze → Silver con tipos y controles, reporte completo de 6,362,620 filas, mart Gold por transacción, variables de destinos con al menos diez operaciones, referencia de cuantiles, MiniBatchKMeans, selección por silueta y estabilidad ARI.

**Bloqueo vigente:** `src/bankshield/models/segments.py` incluye `fraud_rate_received` en `CLUSTER_COLUMNS`. La etiqueta influye en los grupos; las métricas/perfiles actuales deben regenerarse antes de aceptar la segmentación.

**Pendientes:**

1. Excluir fraude y sus derivados de la matriz; conservarlos únicamente para describir los segmentos después del ajuste.
2. Añadir una comprobación de que cambiar solo etiquetas no altera la matriz ni los segmentos, manteniendo comportamiento y semilla.
3. Regenerar agrupamientos, métricas y perfiles; explicar su estabilidad y contrastar la referencia de cuantiles.
4. Implementar servicio, endpoints y página para consultar cuentas y segmentos, con manejo de artefactos ausentes.
5. Cerrar aceptación del contrato Silver/Gold con Cueva y reconstruir derivados para la demo.

**Aceptación:** agrupamiento independiente de etiquetas, evidencia regenerada y consulta real desde API/página. Los grupos no deben presentarse como categorías de riesgo validadas.

## Orden de cierre del proyecto

| Prioridad | Trabajo | Responsable y apoyo | Evidencia de cierre |
| --- | --- | --- | --- |
| 1 | Preparar crédito/pronósticos para demo y registrar aceptación de integración | Gerardo–Sevan; equipo revisa integración | Artefactos reconstruidos, recorrido visual y aceptación registrados. |
| 1 | Corregir segmentación y regenerar evaluación | Taco; Cueva revisa contrato | Independencia de etiquetas comprobada y métricas/perfiles nuevos. |
| 2 | Entregar API/página de segmentos | Taco; Rhamses–Angel revisan HTTP | Consulta por cuenta/segmento con datos reales y errores manejados. |
| 2 | Entregar API/página de reclamos y revisión humana | Angel; revisión de otra pareja | Predicción/análisis desde página y lectura de errores registrada. |
| 2 | Cerrar referencia de grafos, portada y contratos | Rhamses–Angel; cada módulo participa | Evaluación comparable y navegación de seis módulos coherente. |
| 3 | Reproducción, versiones, Docker y demo integral | Gerardo–Sevan coordinan; todos ejecutan su módulo | Clon limpio con LFS, seis recorridos, suite aprobada e instrucciones ejecutables. |
| Transversal | Procedencia/licencia y revisiones cruzadas | Los seis integrantes | Fuentes, decisiones y aceptación registradas. |

No se fijan fechas ni se cambia el reparto acordado. La prioridad refleja dependencias y preparación para presentar.

## Disponibilidad local y límites de la revisión

Hay cuatro páginas implementadas: fraude, crédito, redes y pronósticos. Segmentos y reclamos todavía no tienen servicio/API/página. En esta copia hay modelos de fraude y fraude-Silver; no se encontraron el modelo de crédito, el Gold temporal ni el JSON de monitoreo. Esa ausencia exige reconstrucción para la demo, no volver a implementar sus módulos. Los derivados/modelos quedan fuera de Git.

La suite aprobada comprueba contratos y lógica, con fixtures en varios módulos. No se reentrenaron todos los modelos, no se regeneraron todos los pipelines, no se verificó una demo visual de los cuatro módulos en esta revisión ni se comprobó el CI remoto. La [revisión del 12 de octubre](revision-avance-2026-10-12.md) se conserva como evidencia histórica; este documento reemplaza sus pendientes cuando contradicen las entregas actuales.
