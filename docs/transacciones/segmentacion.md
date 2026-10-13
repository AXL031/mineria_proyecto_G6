# Segmentación de cuentas de destino reincidentes

Reporte generado por `scripts/segment_transactions.py`.

## Universo y métodos

- Cuentas reincidentes (>= 10 transacciones recibidas): **146,629**.
- Línea base: cortes por cuantiles de actividad (`n_received`).
- Método principal: KMeans sobre variables estandarizadas; k = **2** elegido por silueta.

## Selección de k

| k | Silueta (muestra) |
| ---: | ---: |
| 2 | 0.2305 |
| 3 | 0.2111 |
| 4 | 0.1526 |
| 5 | 0.1738 |
| 6 | 0.1919 |
| 7 | 0.1920 |

- Silueta del k elegido: **0.2305**.
- Estabilidad (ARI medio en remuestras): **0.7280** (0.631, 0.735, 0.818).

## Perfil de segmentos (KMeans)

| Segmento | Cuentas | n_received | mean_amount | amount_concentration | activity_density | share_cash_out | share_cash_in | share_transfer | fraud_rate |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 48,334 | 23.84 | 434,165 | 0.294 | 1.15 | 0.487 | 0.286 | 0.218 | 0.0014 |
| 1 | 98,295 | 15.78 | 194,355 | 0.200 | 1.07 | 0.557 | 0.339 | 0.094 | 0.0008 |

## Línea base (cuantiles de actividad)

| Segmento | Cuentas | n_received medio | total_received medio |
| ---: | ---: | ---: | ---: |
| 0 | 73,315 | 12.18 | 3,155,516 |
| 1 | 73,314 | 24.70 | 7,349,599 |

## Limitaciones

- Las cuentas que reciben una sola vez (la mayoría del dataset) quedan fuera de la segmentación; el resultado describe solo cuentas activas.
- PaySim es una simulación; los segmentos no representan clientes reales.
- La silueta se calcula sobre una muestra por costo computacional.
- Las etiquetas de fraude se usan solo para perfilar, no como variable de agrupamiento.
