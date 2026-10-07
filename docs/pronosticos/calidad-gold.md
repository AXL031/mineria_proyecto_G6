# Calidad de la tabla Gold temporal

Reporte generado por `scripts/build_forecast_gold.py`.

## Entrada y salida

- Silver: `data\silver\transactions\transactions.parquet`.
- Gold: `data\gold\forecast\transactions_hourly.parquet`.
- Grano: una fila por `step` (hora simulada).

## Recuentos

| Métrica | Valor |
| --- | ---: |
| Transacciones de entrada | 6,362,620 |
| Filas temporales Gold | 743 |
| Steps incorporados con actividad cero | 0 |
| Transacciones representadas en Gold | 6,362,620 |

## Cobertura temporal

| Métrica | Valor |
| --- | ---: |
| Step mínimo | 1 |
| Step máximo | 743 |
| Steps observados en Silver | 743 |
| Steps en Gold | 743 |
| Inicio del tramo final solo fraude | 719 |

## Controles

| Control | Resultado |
| --- | --- |
| `one_row_per_step` | OK |
| `regular_step_sequence` | OK |
| `transaction_count_preserved` | OK |
| `amount_total_preserved` | OK |
| `fraud_count_preserved` | OK |
| `no_null_values` | OK |

## Totales

- Monto total: 1,144,392,944,759.77.
- Transacciones fraudulentas: 8,213.

## Limitaciones

- `step` es una hora simulada, no una fecha calendario.
- Los datos son sintéticos y los montos no tienen una moneda identificada.
- `fraud_count` y `fraud_rate` son variables descriptivas; no se usarán como información futura para predecir volumen.
- El tramo final solo fraude debe analizarse por separado antes del backtesting.
