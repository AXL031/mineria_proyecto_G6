# Comparación de alertas de red frente a una referencia por volumen

Documento generado por `scripts/evaluate_graph_alerts.py` desde `artifacts/reports/graph/comparison.json`; no transcribir cifras a mano. Datos de PaySim (simulación). Evaluación exploratoria y retrospectiva sobre la misma muestra observada.

- Análisis: `graph-comparison-72f834d1af957e50` (esquema 1).
- Fuente SHA-256: `16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b`.
- Límite solicitado: 50000; filas leídas: 50,000; steps 1–9.
- Regla de muestreo: Prefijo del archivo: las primeras N filas en su orden original. No es una muestra aleatoria ni se afirma que sea representativa del dataset.
- Huella de las filas usadas: `e3247d51e65a61ce3e330420ab5713e6f42df01af42b7353c37f00128d8036cb`.
- Transacciones fraudulentas etiquetadas: 100.
- Universo: 78,499 cuentas (56,587 clientes, 21,912 comercios); 199 cuentas positivas.
- Presupuestos solicitados: [10, 50, 100]; efectivos: [10, 50, 100].
- Percentiles fijados: fan-out 95.0, fan-in 95.0, flujo neto 95.0.

## Métodos

- **Red:** pattern_count desc, pagerank desc, account_id asc.
- **Referencia por volumen:** total_amount_sent + total_amount_received desc, account_id asc.
- Ambos usan el mismo universo, los mismos nodos y aristas, y ninguna etiqueta de fraude para ordenar.

## k = 10 (solicitado: [10])

| Métrica | Nivel | Red | Referencia por volumen | Diferencia (red − referencia) |
| --- | --- | --- | --- | --- |
| Cuentas seleccionadas | cuenta | 10 | 10 | – |
| Cuentas positivas seleccionadas | cuenta | 0 | 1 | – |
| Precisión de cuentas | cuenta | 0.0000% (0/10) | 10.0000% (1/10) | -10.00 pp |
| Recall de cuentas positivas | cuenta | 0.0000% (0/199) | 0.5025% (1/199) | -0.50 pp |
| Transacciones cubiertas | transacción | 612 | 577 | – |
| Transacciones fraudulentas cubiertas | transacción | 0 | 1 | – |
| Precisión de transacciones cubiertas | transacción | 0.0000% (0/612) | 0.1733% (1/577) | -0.17 pp |
| Cobertura de fraude | transacción | 0.0000% (0/100) | 1.0000% (1/100) | -1.00 pp |

## k = 50 (solicitado: [50])

| Métrica | Nivel | Red | Referencia por volumen | Diferencia (red − referencia) |
| --- | --- | --- | --- | --- |
| Cuentas seleccionadas | cuenta | 50 | 50 | – |
| Cuentas positivas seleccionadas | cuenta | 5 | 6 | – |
| Precisión de cuentas | cuenta | 10.0000% (5/50) | 12.0000% (6/50) | -2.00 pp |
| Recall de cuentas positivas | cuenta | 2.5126% (5/199) | 3.0151% (6/199) | -0.50 pp |
| Transacciones cubiertas | transacción | 2,249 | 2,097 | – |
| Transacciones fraudulentas cubiertas | transacción | 5 | 6 | – |
| Precisión de transacciones cubiertas | transacción | 0.2223% (5/2,249) | 0.2861% (6/2,097) | -0.06 pp |
| Cobertura de fraude | transacción | 5.0000% (5/100) | 6.0000% (6/100) | -1.00 pp |

## k = 100 (solicitado: [100])

| Métrica | Nivel | Red | Referencia por volumen | Diferencia (red − referencia) |
| --- | --- | --- | --- | --- |
| Cuentas seleccionadas | cuenta | 100 | 100 | – |
| Cuentas positivas seleccionadas | cuenta | 7 | 10 | – |
| Precisión de cuentas | cuenta | 7.0000% (7/100) | 10.0000% (10/100) | -3.00 pp |
| Recall de cuentas positivas | cuenta | 3.5176% (7/199) | 5.0251% (10/199) | -1.51 pp |
| Transacciones cubiertas | transacción | 3,495 | 3,178 | – |
| Transacciones fraudulentas cubiertas | transacción | 7 | 8 | – |
| Precisión de transacciones cubiertas | transacción | 0.2003% (7/3,495) | 0.2517% (8/3,178) | -0.05 pp |
| Cobertura de fraude | transacción | 7.0000% (7/100) | 8.0000% (8/100) | -1.00 pp |

## Limitaciones

- Evaluación exploratoria y retrospectiva sobre la misma muestra observada; no es una predicción temporal ni evidencia sobre la red completa.
- La muestra es un prefijo del archivo, no una muestra aleatoria; no se afirma que sea representativa del dataset.
- Los datos provienen de PaySim (simulación); isFraud es una etiqueta del simulador y los resultados no describen fraude real.
- Los rankings no usan etiquetas de fraude; las etiquetas solo se emplean para medir las cuentas ya seleccionadas. combine_suspicion_indicators incluye fraud_count con fines descriptivos y no se usa como puntaje.
- No se selecciona el k ganador según el fraude observado y no se exige que el método de red supere a la referencia por volumen.
- Los percentiles de los indicadores están fijados en la configuración antes de evaluar y no se calibran con las etiquetas.
- Comunidades y evaluación predictiva temporal de grafos quedan fuera de esta comparación.

## Versiones

- python: 3.12.14
- pandas: 3.0.6
- numpy: 2.5.3
- networkx: 3.7
- schema_version: 1
