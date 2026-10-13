# Monitoreo histórico de cambios transaccionales

Comparación descriptiva generada por `scripts/monitor_forecast_shift.py`.
No representa monitoreo en producción ni una alerta bancaria real.

## Ventanas

- Referencia: steps 694–718.
- Observada: steps 719–743.
- Ambas ventanas contienen 25 steps consecutivos.

## Cambios principales

| Indicador | Referencia | Observado | Cambio | Alerta |
| --- | ---: | ---: | ---: | --- |
| Transacciones | 16,760 | 296 | -98.23 % | Sí |
| Monto total | 2,587,983,402.59 | 468,962,836.94 | -81.88 % | Sí |
| Monto promedio | 154,414.28 | 1,584,333.91 | +926.03 % | Sí |
| Tasa de fraude | 1.6945% | 100.0000% | +98.31 pp | Sí |

## Distribuciones

- Distancia de variación total de montos: 0.4169 (alerta: sí).
- Distancia de variación total de tipos: 0.6035 (alerta: sí).

Los valores de distancia van de 0 (misma distribución) a 1 (distribuciones sin solapamiento). Para los montos se utilizan intervalos definidos por cuantiles de la ventana de referencia.

### Mezcla por tipo

| Tipo | Referencia | Observado | Cambio porcentual |
| --- | ---: | ---: | ---: |
| CASH_IN | 21.30% | 0.00% | -21.30 pp |
| CASH_OUT | 30.45% | 50.00% | +19.55 pp |
| DEBIT | 1.50% | 0.00% | -1.50 pp |
| PAYMENT | 37.54% | 0.00% | -37.54 pp |
| TRANSFER | 9.21% | 50.00% | +40.79 pp |

## Resultado

Estado: **change_detected** con 6 indicadores fuera de los umbrales descriptivos.

El tramo 719–743 contiene exclusivamente transacciones etiquetadas como fraude y una actividad mucho menor. El resultado demuestra que el método detecta un cambio histórico evidente del simulador; no demuestra capacidad para anticipar deriva futura.

## Umbrales descriptivos

| Indicador | Umbral absoluto |
| --- | ---: |
| `transaction_count_relative_change` | 0.5000 |
| `total_amount_relative_change` | 0.5000 |
| `average_amount_relative_change` | 0.5000 |
| `amount_distribution_tvd` | 0.2000 |
| `type_mix_tvd` | 0.2000 |
| `fraud_rate_absolute_change` | 0.2000 |

## Limitaciones

- La comparación es histórica y no observa lotes futuros en producción.
- Los umbrales son descriptivos y no fueron calibrados con incidentes reales.
- PaySim es una simulación y el tramo observado pertenece a su cierre anómalo.
