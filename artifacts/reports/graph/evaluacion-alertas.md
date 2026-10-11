# Evaluación de alertas de grafos contra etiquetas de fraude

Informe generado por `scripts/evaluate_graph_alerts.py`.  Los datos
provienen de PaySim (simulación); los resultados son exploratorios.

- Aristas analizadas: 50,000.
- Transacciones fraudulentas: 100 (0.2000%).

## Evaluación por patrón individual

| Patrón | Cuentas marcadas | Con fraude | Precisión (cuenta) | Fraudes cubiertos | Cobertura |
| --- | ---: | ---: | ---: | ---: | ---: |
| high_fanout | 0 | 0 | 0.0000% | 0 | 0.0000% |
| high_fanin | 3,107 | 65 | 2.0921% | 66 | 66.0000% |
| net_flow_anomaly | 7,850 | 89 | 1.1338% | 71 | 71.0000% |
| high_value_edge | 870 | 23 | 2.6437% | 15 | 15.0000% |

## Evaluación combinada (múltiples indicadores)

| Mín. patrones | Cuentas | Con fraude | Precisión (cuenta) | Fraudes cubiertos | Cobertura | Precisión (txn) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 8,065 | 97 | 1.2027% | 79 | 79.0000% | 0.3150% |
| 2 | 2,892 | 57 | 1.9710% | 58 | 58.0000% | 0.2553% |

## Ejemplos de casos

### Verdaderos positivos (alerta + fraude real)

| Cuenta | Tipo | Patrones | Fraudes (origen) | Fraudes (destino) |
| --- | --- | --- | ---: | ---: |
| `C803116137` | cliente | high_fanin, net_flow_anomaly | 0 | 1 |
| `C932583850` | cliente | high_fanin, net_flow_anomaly | 0 | 1 |
| `C716083600` | cliente | high_fanin, net_flow_anomaly | 0 | 1 |
| `C766681183` | cliente | high_fanin, net_flow_anomaly | 0 | 1 |
| `C991505714` | cliente | high_fanin, net_flow_anomaly | 0 | 1 |

### Falsos positivos (alerta sin fraude real)

| Cuenta | Tipo | Patrones | Nº patrones |
| --- | --- | --- | ---: |
| `C1223591088` | cliente | high_fanin, net_flow_anomaly | 2 |
| `C755355682` | cliente | high_fanin, net_flow_anomaly | 2 |
| `C1916720513` | cliente | high_fanin, net_flow_anomaly | 2 |
| `C1721246982` | cliente | high_fanin, net_flow_anomaly | 2 |
| `C1674899618` | cliente | high_fanin, net_flow_anomaly | 2 |

## Interpretación y limitaciones

- **Cobertura** mide qué fracción de las transacciones fraudulentas
  involucran al menos una cuenta detectada por el patrón.
- **Precisión a nivel de cuenta** mide qué fracción de las cuentas
  detectadas tiene al menos una transacción fraudulenta.
- Los patrones son exploratorios y basados en percentiles estáticos.
  Un patrón con alta cobertura pero baja precisión genera muchas
  alertas falsas.
- Los umbrales requieren calibración con datos reales y revisión
  de expertos de dominio.
- La evaluación no mide predicción: no hay separación temporal
  ni partición de prueba.  Es una asociación cruzada, no una
  estimación de desempeño predictivo.
- `isFraud` es una etiqueta del simulador; en producción real,
  las etiquetas de fraude pueden estar incompletas o sesgadas.
