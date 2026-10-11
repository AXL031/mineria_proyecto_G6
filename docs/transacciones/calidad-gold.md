# Calidad del mart transaccional Gold

Reporte generado por `scripts/build_gold_transactions.py`.

## Entrada y salida

- Silver: `data\silver\transactions\transactions.parquet`.
- Gold: `data\gold\transactions\transactions_mart.parquet`.
- Grano: una fila por transacción.

## Recuentos

| Métrica | Valor |
| --- | ---: |
| Transacciones de entrada | 6,362,620 |
| Filas del mart Gold | 6,362,620 |

## Totales

| Métrica | Valor |
| --- | ---: |
| Monto total | 1,144,392,944,759.77 |
| Transacciones fraudulentas | 8,213 |
| Transacciones marcadas (`isFlaggedFraud`) | 16 |
| Residuos de balance origen distintos de cero | 5,413,997 |
| Residuos de balance destino distintos de cero | 4,736,674 |

## Controles

| Control | Resultado |
| --- | --- |
| `one_row_per_transaction` | OK |
| `predictors_present` | OK |
| `amount_total_preserved` | OK |
| `fraud_count_preserved` | OK |
| `flagged_count_preserved` | OK |
| `no_null_values` | OK |

## Predictores

- Lista gobernada por el contrato de fraude: `type`, `amount`, `oldbalanceOrg`, `amount_to_origin_balance`, `exceeds_origin_balance`.
- `origin_balance_delta` y `destination_balance_delta` son descriptivos: usan saldos posteriores a la operación y quedan fuera de los predictores.

## Limitaciones

- `step` es una hora simulada, no una fecha calendario.
- Los datos son sintéticos y los montos no tienen una moneda identificada.
- Este mart no agrega actividad por `step`; el Gold temporal de pronósticos es una tabla distinta por módulo.
- El mart conserva `isFraud` e `isFlaggedFraud` para evaluación; quedan fuera de cualquier conjunto de predictores.
