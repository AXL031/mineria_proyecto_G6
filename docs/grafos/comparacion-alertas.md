# Comparación de alertas de red frente a una referencia por volumen

Documento generado por `scripts/evaluate_graph_alerts.py` desde `artifacts/reports/graph/comparison.json`; no transcribir cifras a mano. Datos de PaySim (simulación). Evaluación exploratoria y retrospectiva sobre la misma muestra observada.

- Análisis: `graph-comparison-13195a22452c53df` (esquema 1).
- Fuente SHA-256: `16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b`.
- Límite solicitado: 10000; filas leídas: 10,000; steps 1–7.
- Regla de muestreo: Prefijo del archivo: las primeras N filas en su orden original. No es una muestra aleatoria ni se afirma que sea representativa del dataset.
- Huella de las filas usadas: `1c7abe80e069318c9df332ccf23a1dfe81be8d570e33f8d7a5813ae6315e67da`.
- Transacciones fraudulentas etiquetadas: 68.
- Universo: 16,397 cuentas (10,932 clientes, 5,465 comercios); 135 cuentas positivas.
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
| Recall de cuentas positivas | cuenta | 0.0000% (0/135) | 0.7407% (1/135) | -0.74 pp |
| Transacciones cubiertas | transacción | 458 | 401 | – |
| Transacciones fraudulentas cubiertas | transacción | 0 | 1 | – |
| Precisión de transacciones cubiertas | transacción | 0.0000% (0/458) | 0.2494% (1/401) | -0.25 pp |
| Cobertura de fraude | transacción | 0.0000% (0/68) | 1.4706% (1/68) | -1.47 pp |

## k = 50 (solicitado: [50])

| Métrica | Nivel | Red | Referencia por volumen | Diferencia (red − referencia) |
| --- | --- | --- | --- | --- |
| Cuentas seleccionadas | cuenta | 50 | 50 | – |
| Cuentas positivas seleccionadas | cuenta | 4 | 9 | – |
| Precisión de cuentas | cuenta | 8.0000% (4/50) | 18.0000% (9/50) | -10.00 pp |
| Recall de cuentas positivas | cuenta | 2.9630% (4/135) | 6.6667% (9/135) | -3.70 pp |
| Transacciones cubiertas | transacción | 1,575 | 1,481 | – |
| Transacciones fraudulentas cubiertas | transacción | 4 | 7 | – |
| Precisión de transacciones cubiertas | transacción | 0.2540% (4/1,575) | 0.4727% (7/1,481) | -0.22 pp |
| Cobertura de fraude | transacción | 5.8824% (4/68) | 10.2941% (7/68) | -4.41 pp |

## k = 100 (solicitado: [100])

| Métrica | Nivel | Red | Referencia por volumen | Diferencia (red − referencia) |
| --- | --- | --- | --- | --- |
| Cuentas seleccionadas | cuenta | 100 | 100 | – |
| Cuentas positivas seleccionadas | cuenta | 7 | 13 | – |
| Precisión de cuentas | cuenta | 7.0000% (7/100) | 13.0000% (13/100) | -6.00 pp |
| Recall de cuentas positivas | cuenta | 5.1852% (7/135) | 9.6296% (13/135) | -4.44 pp |
| Transacciones cubiertas | transacción | 2,261 | 2,035 | – |
| Transacciones fraudulentas cubiertas | transacción | 7 | 9 | – |
| Precisión de transacciones cubiertas | transacción | 0.3096% (7/2,261) | 0.4423% (9/2,035) | -0.13 pp |
| Cobertura de fraude | transacción | 10.2941% (7/68) | 13.2353% (9/68) | -2.94 pp |

## Limitaciones

- Evaluación exploratoria y retrospectiva sobre la misma muestra observada; no es una predicción temporal ni evidencia sobre la red completa.
- La muestra es un prefijo del archivo, no una muestra aleatoria; no se afirma que sea representativa del dataset.
- Los datos provienen de PaySim (simulación); isFraud es una etiqueta del simulador y los resultados no describen fraude real.
- Los rankings no usan etiquetas de fraude; las etiquetas solo se emplean para medir las cuentas ya seleccionadas. combine_suspicion_indicators incluye fraud_count con fines descriptivos y no se usa como puntaje.
- No se selecciona el k ganador según el fraude observado y no se exige que el método de red supere a la referencia por volumen.
- Los percentiles de los indicadores están fijados en la configuración antes de evaluar y no se calibran con las etiquetas.
- Comunidades y evaluación predictiva temporal de grafos quedan fuera de esta comparación.

## Versiones

- python: 3.10.12
- pandas: 2.3.3
- numpy: 2.2.6
- networkx: 3.4.2
- schema_version: 1
