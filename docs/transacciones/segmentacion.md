# Segmentación de cuentas de destino reincidentes

Reporte generado por `scripts/segment_transactions.py`.

## Universo y métodos

- Cuentas reincidentes (>= 10 transacciones recibidas): **146,629**.
- Línea base: cortes por cuantiles de actividad (`n_received`).
- Método principal: KMeans sobre variables estandarizadas; k = **5** elegido por silueta.

## Selección de k

| k | Silueta (muestra) |
| ---: | ---: |
| 2 | 0.2034 |
| 3 | 0.1843 |
| 4 | 0.1565 |
| 5 | 0.2316 |
| 6 | 0.1725 |
| 7 | 0.1481 |

- Silueta del k elegido: **0.2316**.
- Estabilidad (ARI medio en remuestras): **0.3883** (0.367, 0.444, 0.354).

## Perfil de segmentos (KMeans)

| Segmento | Cuentas | n_received | mean_amount | amount_concentration | activity_density | share_cash_out | share_cash_in | share_transfer | fraud_rate |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 14,226 | 15.81 | 194,387 | 0.222 | 1.07 | 0.509 | 0.314 | 0.102 | 0.0000 |
| 1 | 71,229 | 15.17 | 188,098 | 0.192 | 1.06 | 0.562 | 0.355 | 0.083 | 0.0000 |
| 2 | 34,355 | 15.77 | 448,022 | 0.347 | 1.06 | 0.505 | 0.263 | 0.229 | 0.0000 |
| 3 | 2,046 | 16.86 | 353,288 | 0.306 | 1.07 | 0.541 | 0.304 | 0.147 | 0.0661 |
| 4 | 24,773 | 33.17 | 315,306 | 0.179 | 1.27 | 0.509 | 0.312 | 0.171 | 0.0004 |

## Línea base (cuantiles de actividad)

| Segmento | Cuentas | n_received medio | total_received medio | fraud_rate medio |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 29,326 | 10.44 | 2,665,346 | 0.0012 |
| 1 | 29,326 | 12.64 | 3,297,133 | 0.0011 |
| 2 | 29,325 | 15.66 | 4,136,742 | 0.0010 |
| 3 | 29,326 | 20.55 | 5,684,009 | 0.0010 |
| 4 | 29,326 | 32.89 | 10,479,447 | 0.0007 |

## Limitaciones

- Las cuentas que reciben una sola vez (la mayoría del dataset) quedan fuera de la segmentación; el resultado describe solo cuentas activas.
- PaySim es una simulación; los segmentos no representan clientes reales.
- La silueta se calcula sobre una muestra por costo computacional.
- Las etiquetas de fraude se usan solo para perfilar, no como variable de agrupamiento.
