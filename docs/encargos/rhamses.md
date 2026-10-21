# Encargo de Rhamses — comparación de grafos y contratos HTTP

Estado inicial: pendiente. Leer [contratos y prioridades](../pendientes-cierre-2026-10-20.md). La red, indicadores, patrones, API, consultas acotadas y página HTTP ya existen. No reconstruir estos módulos ni volver a introducir caché que ignore el límite de muestra.

## RHA-01 — comparación justa de alertas de red (P1)

### Resultado esperado

Comparar el ranking de indicadores de red con una referencia por volumen, usando el mismo universo y el mismo número de cuentas seleccionadas. La evaluación es exploratoria sobre la misma muestra observada, no una predicción temporal ni evidencia sobre la red completa.

### Archivos

- Crear `src/bankshield/evaluation/graph.py` para rankings, presupuestos y métricas, separado del código de presentación.
- Ampliar `scripts/evaluate_graph_alerts.py` con `--comparison-output` y `--comparison-markdown`; conservar flags y reporte de evaluación históricos.
- Agregar configuración `comparison` a `configs/graph.json`.
- Ampliar `src/bankshield/services/graph.py`, `api/routers/graphs.py` y `dashboard/pages/03_redes.py`.
- Crear `tests/unit/test_graph_comparison.py`; ampliar pruebas de API/página de grafos.
- Crear `docs/grafos/comparacion-alertas.md`.

### Comparación fijada

1. Leer una única muestra con el lector existente. Guardar fuente SHA-256, número real de filas, límite solicitado, steps mínimo/máximo, regla de muestreo y huella de las filas usadas. Default de demo: primeras 10000 filas; corrida adicional documentada: primeras 50000. No afirmar que el prefijo sea representativo del dataset.
2. Universo: todas las cuentas origen/destino de esas aristas, en ambos métodos. Excluir ninguna por conocer si tiene fraude. Registrar tipos de cuenta y límites de la población.
3. Método de red: ordenar todo el universo por número de indicadores activos (`pattern_count`) descendente, luego PageRank descendente y account_id ascendente. Cuentas sin indicador tienen cero y permanecen en el universo. Percentiles de indicadores: valores de configuración fijados antes de evaluar.
4. Referencia: `total_amount_sent + total_amount_received` descendente y account_id ascendente, con los mismos nodos y aristas. No usar `fraud_count`, `isFraud`, `isFlaggedFraud` o resultados evaluados para ordenar ninguno de los métodos.
5. Presupuestos solicitados por defecto: 10, 50 y 100 cuentas. Si N es menor, k efectivo es min(k,N); eliminar presupuestos efectivos duplicados en el reporte, conservando cuáles se solicitaron. Ambos métodos deben devolver exactamente k cuentas distintas para cada presupuesto efectivo.
6. Positivo a nivel cuenta: aparece como origen o destino de al menos una transacción etiquetada fraude en esa muestra. Conjunto de transacciones cubiertas: aquellas cuyo origen **o** destino pertenece a la selección; contar cada fila una sola vez, aunque ambos extremos estén seleccionados.
7. Métricas por método/k: cuentas seleccionadas, cuentas positivas seleccionadas, precisión de cuentas, recall de cuentas positivas, transacciones cubiertas, transacciones fraudulentas cubiertas, precisión de transacciones cubiertas y cobertura de fraude. Guardar numeradores/denominadores, no solo porcentajes.
8. Métrica sin positivos o sin transacciones cubiertas: null con motivo. Comparar diferencias a igual k; no seleccionar el k ganador según fraude observado. No exigir que el método de red gane.
9. Eliminar cualquier uso accidental de etiquetas en desempates/rankings. `combine_suspicion_indicators` actualmente incluye `fraud_count` para descripción: no usarlo como score de comparación. Conservar esa distinción en la documentación.

### Reporte, HTTP y página

Salida: `artifacts/reports/graph/comparison.json`, con schema_version, analysis_id, fuente/muestra/configuración, universo, presupuestos solicitados/efectivos, rankings seleccionados, métricas, limitaciones y versiones. Guardar comparación Markdown desde el mismo contenido; no transcribir cifras manualmente.

`GET /api/graphs/evaluation?limit=10000` carga el reporte preparado, no ejecuta análisis. Variable `BANKSHIELD_GRAPH_COMPARISON`. `limit` 1000–500000 debe coincidir con el tamaño de muestra solicitado que consta en el reporte, no solo con filas efectivas. Si difiere, 503 con indicación de regenerar para esa muestra, sin servir resultados de otro universo. No sobrescribir el reporte por una consulta. Conservar las rutas existentes de cuenta/subgrafo/top.

Respuesta mínima: schema_version, analysis_id, simulation_data=true, scope="sample_retrospective", sample, universe_size, comparisons, limitations. El panel muestra muestra/periodo, tabla red vs referencia por k, métricas con sus niveles cuenta/transacción y las limitaciones. Si falta comparación, conservar operativas las otras consultas y mostrar aviso específico.

### Pruebas necesarias

- Fixture de aristas con resultados manuales para ambos rankings, precisión y cobertura.
- Transacción con ambos extremos seleccionados se cuenta una vez; cuentas únicas aunque aparezcan en varias aristas.
- Cambiar solo etiquetas conserva universo, scores, orden y k; sí puede cambiar las métricas.
- Empates resueltos por ID; casos N<k, sin cuentas con indicadores, sin fraudes y muestra vacía.
- API distingue reporte ausente, versión incompatible y límite distinto; no carga/recalcula el grafo para servir el reporte.
- AppTest mantiene muestra en consultas y muestra comparación correcta; preservar regresiones de subgrafo/HTML existentes.

Comando objetivo, una vez ampliado el script:

```powershell
.venv-pruebas/Scripts/python.exe scripts/evaluate_graph_alerts.py --limit 10000 --comparison-output artifacts/reports/graph/comparison.json --comparison-markdown docs/grafos/comparacion-alertas.md
.venv-pruebas/Scripts/python.exe -m unittest discover -s tests/unit -p "test*graph*.py" -v
```

**Aceptación:** reporte real, rankings independientes de etiquetas, igualdad de universo/k, métricas auditables y consulta API/panel sin confundir muestras. Cueva revisa la evaluación; Angel revisa la interfaz. Entregar a Gerardo CLI/salidas y a Angel casos de integración.

## RHA-02 — aceptación HTTP y navegación (P1)

- [ ] Revisar con Angel navegación de seis módulos existentes más regresión. Las reglas descubiertas se integran en fraude y no necesitan una página adicional.
- [ ] Revisar router y página de regresión de Sevan: validación, identidad del modelo, 503 sin artefacto y predicción persistente.
- [ ] Acordar con Angel estados de error consistentes en las capacidades nuevas, sin cambiar contratos existentes por accidente.
- [ ] Registrar demo acotada de redes en el segundo entorno y revisión humana real de los contratos/navegación.
- [ ] Mantener límites actuales de muestra/subgrafos y el HTML embebido sin archivos compartidos ni descargas de bibliotecas durante la demo.

Comunidades y evaluación predictiva temporal de grafos siguen fuera de este cierre. Si se amplían después, necesitan un protocolo propio; no se consideran resueltas mediante esta comparación retrospectiva.
