# Cierre técnico hasta la tercera presentación — 9 de noviembre de 2026

Rama: `cierre-semana-13`, iniciada desde `de6bbe2` del remoto. Se conserva el reparto académico por integrante, aunque la implementación pendiente se realiza en esta rama común. No se atribuyen revisiones humanas, trabajo en otras PCs o CI nuevo sin evidencia.

## Resultado y alcance

Se implementaron las dos capacidades faltantes del alcance acordado: CUE-01 (asociaciones descubiertas) y SEV-01 (regresión numérica). Se completó la comparación cuantitativa de clustering y se integraron las siete páginas, las capacidades HTTP, la preparación y el verificador. La documentación académica ahora tiene matriz de los 19 entregables con encargados, diccionario de 41 campos originales, nueve fichas de indicadores, metodología y guion de exposición.

La cobertura técnica no equivale a aprobación integral del docente: quedan confirmaciones de procedencia histórica/condiciones de las copias y aceptaciones humanas, detalladas al final. Docker y GER-02 son P2 y no se declaran implementados.

## Evidencia ejecutada en este equipo

| Verificación | Resultado observado | Evidencia local, excluida de Git |
| --- | --- | --- |
| Dependencias | `pip check`: sin conflictos. | Entorno `.venv-pruebas`, Python 3.12.14. |
| Suite completa ampliada | **365 pruebas aprobadas**, 61.888 s. | `artifacts/reports/cierre-semana13-tests.log`. |
| Contratos finales del preparador | 16 pruebas aprobadas, 7.130 s; incluyen disponibilidad full y versión 2 de reportes temporales. | `artifacts/reports/cierre-preparation-tests.log`. |
| Primera preparación integral | **17 etapas construidas**, historial P2 omitido explícitamente; 710.771 s (11 min 50.771 s). | `artifacts/reports/cierre-preparation-first.json`; logs en `artifacts/reports/demo/runs/af71885279054daabdbc0f3a484d3350/`. |
| Preparador final con síntesis académica | **17 etapas reutilizadas**, tres construidas (baselines, comparación temporal y síntesis), una P2 omitida; 12.753 s. | `artifacts/reports/demo/preparation-manifest.json`, corrida `ba4f3ef47a7d4a198bc6190b18326ddc`. |
| API + panel aislados + páginas | **71 comprobaciones aprobadas** por HTTP real/AppTest, incluidas las siete páginas. Procesos propios detenidos al terminar. | `artifacts/reports/cierre-delivery-check.json`, `cierre-delivery.log`, `cierre-api.log` y `cierre-panel.log`. |
| Grafos en entorno común | Repetidas corridas de 10,000 y 50,000 filas con Python 3.12.14, pandas 3.0.6, NumPy 2.5.3, NetworkX 3.7. | `artifacts/reports/graph/comparison*.json` y resúmenes versionados. |
| Evidencia académica | Nueve indicadores y 30 filas comparativas generadas desde reportes reales, con huellas de entradas. | `artifacts/reports/academic/summary.json`. |

La primera suite intermedia de esta implementación pasó 362 pruebas; se añadieron tres casos antes de la suite completa de 365. Se corrigió durante el desarrollo una colisión entre keys de botones y resultados de session_state en la página de regresión; las pruebas de página e integración pasan tras la corrección. Las advertencias actuales de TestClient, Streamlit y series cortas no causaron fallos. AppTest no sustituye una revisión visual humana.

Los artefactos registran UTC, versiones, fuente Silver, D1 y bins, configuración, particiones, muestreo y huellas de fuentes de código. El commit base junto con `tree_dirty=true` no identifica por sí solo los cambios ejecutados; las huellas de código distinguen la implementación. Los recibos del preparador también registran el conjunto de código/configuración/entradas utilizado.

### Recursos observados

El mayor RSS de etapa observado en la reconstrucción fue 2,460,037,120 bytes (~2.29 GiB), en segmentos. Asociaciones: 467,070,976 bytes; regresión: 606,101,504 bytes. Es una suma RSS aproximada del proceso y sus hijos, muestreada por el preparador; puede contar memoria compartida más de una vez. No es un mínimo de RAM garantizado ni un benchmark independiente.

El preparador verificó datos/modelos ya presentes antes de reutilizarlos en la segunda ejecución. La reconstrucción desde originales en esta misma carpeta no se describe como un clon limpio, otra PC o aprobación de una segunda persona.

## Resultados principales

| Capacidad / encargado | Resultado defendible | Límite |
| --- | --- | --- |
| D1 / Taco | 6,362,620 filas, nueve controles, cero excluidas. SHA-256 `A4C6F55EC8DBB5351B8F2B6F5B8BE59E8C4C4696FBC4815F22B6CDC1234960EA`. | Cuatro particiones; stress no selecciona métodos. |
| Asociaciones / Cueva | Apriori acotado examinó 60 candidatos y congeló 18 reglas por validation. La unión cubre 3,611 de 3,710 fraudes de test D1 (97.3315%). | Las reglas dependen de la simulación; la igualdad monto/saldo puede reflejar sus mecanismos, no fraude bancario generalizable. |
| Regresión / Sevan | Mediana por tipo gana por MAE de validation y permanece seleccionada. En test: MAE 109,127.8246; RMSE 354,977.9572; R² 0.199430. | Moneda no verificada; no alerta ni recomendación crediticia. |
| Exportación de regresión / Sevan | 980,416 validation + 918,321 test + 296 stress = 1,899,033 predicciones; 200 ejemplos uniformes de test. | Solo 200 ejemplos no resumen toda la prueba; archivo completo se exporta para auditoría. |
| Clustering / Taco | KMeans: silueta 0.230484, ARI 0.728025. Cuantiles: silueta 0.120737, ARI 0.993067. | KMeans separa mejor en el espacio evaluado; cuantiles son más estables. k se eligió con KMeans. |
| Series / Gerardo | Naive conserva menor MAE de cantidad (1,366.9375) que Holt-Winters aditivo (4,518.2212). | Error relativo alto; horas simuladas, no fechas bancarias reales. |
| Grafos / Rhamses | Prefijo 10,000, k=100: red cubre 7/68 fraudes; volumen 9/68. En 50,000: red 7/100; volumen 8/100. | La referencia gana en esos casos; evaluación retrospectiva y no representativa de toda la red. |
| Integración/evidencia / Angel | Siete módulos y capacidades explícitas, KPIs, matriz, diccionario, guion y verificador full. | Cada dueño conserva responsabilidad académica; ninguna revisión humana se presume realizada. |

Los resultados completos se generan desde [asociaciones](fraude/asociaciones-descubiertas.md), [regresión](regresion/resultados-modelo.md), [clustering](transacciones/segmentacion.md), [grafos](grafos/comparacion-alertas.md) y [síntesis comparativa](evaluacion-comparativa.md). No se suman coberturas de reglas solapadas ni se comparan métricas de tareas distintas como si midieran lo mismo.

## Comandos de reproducción

Desde la raíz en PowerShell, con Python 3.12 y los tres originales completos:

```powershell
git lfs pull
powershell -ExecutionPolicy Bypass -File scripts/setup_env.ps1 -UseLock
.venv-pruebas/Scripts/python.exe -m unittest discover -s tests/unit -v
.venv-pruebas/Scripts/python.exe scripts/prepare_demo.py --scope full
.venv-pruebas/Scripts/python.exe scripts/verify_local_delivery.py
.venv-pruebas/Scripts/python.exe scripts/build_academic_evidence.py
```

`verify_local_delivery.py` usa puertos libres, arranca API/panel sin ventana, ejecuta verificación y detiene solo su árbol de procesos. No reemplaza `artifacts/reports/demo/processes.json` de otra demo. Para uso interactivo: `scripts/start_demo.ps1`, `verify_demo.py --profile full` y `scripts/stop_demo.ps1`.

La preparación predeterminada ahora es full. `--scope current`/`--profile current` permiten el recorrido histórico de seis módulos, pero no acreditan asociaciones/regresión/comparación. `--include-model-monitoring` exige el P2 si se implementa; su ausencia no se oculta como éxito.

## Pendientes que no se pueden firmar mediante código

| Pendiente | Encargado |
| --- | --- |
| Confirmar origen/fecha de descarga y condiciones de uso de la copia PaySim. | Cueva–Taco. |
| Confirmar correspondencia de la copia crediticia con el catálogo original; la definición pública de loan_status ya está localizada, pero el producto mantiene el supuesto hasta vincular la copia. | Sevan. |
| Confirmar procedencia histórica de la copia CFPB y leer humanamente errores/confusiones NLP. | Angel. |
| Revisar asociaciones, regresión, comparación de grafos y navegación. | Sevan/Taco, Rhamses/Gerardo y Cueva/Angel según cada encargo. |
| Revisar visualmente la demo y aceptar los contratos. | Equipo. |
| Reproducir el alcance ampliado en otro clon/entorno y, cuando corresponda, otra PC/persona. | Gerardo coordina; todos reproducen su etapa. |
| Publicar esta rama y comprobar su CI remoto si se decide compartirla. | Equipo; sin push/merge realizado en este cierre. |
| Acordar fecha académica y ensayar exposición con el guion. | Equipo; Angel consolida. |

La [matriz](matriz-entregables.md) conserva estos límites: la implementación técnica hasta semana 13 está disponible, y el cierre académico integral depende de esas comprobaciones humanas y de fuentes. Los avances previos de semana 16 no se usan para sustituir requisitos de las semanas 7/10/13.
