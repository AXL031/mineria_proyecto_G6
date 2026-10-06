# Perfil de calidad — PaySim

## Fuente

- Archivo: `PS_20174392719_1491204439457_log.csv`
- Tamaño: 493,534,783 bytes
- SHA-256: `16910F90577B0D981BF8FF289714510BB89BC71BFF7D3F220F024E287E4EEA6B`
- Filas: 6,362,620
- Columnas: 11

## Controles principales

| Control | Resultado |
| --- | --- |
| `expected_header` | OK |
| `no_missing_columns` | OK |
| `no_extra_columns` | OK |
| `no_null_or_blank_values` | OK |
| `numeric_columns_parse` | OK |
| `numeric_columns_are_finite` | OK |
| `known_transaction_types` | OK |
| `steps_are_positive_integers` | OK |
| `continuous_step_range` | OK |
| `amounts_are_non_negative` | OK |
| `fraud_flags_are_binary` | OK |

## Valores nulos o vacíos

| Columna | Cantidad |
| --- | ---: |
| `step` | 0 |
| `type` | 0 |
| `amount` | 0 |
| `nameOrig` | 0 |
| `oldbalanceOrg` | 0 |
| `newbalanceOrig` | 0 |
| `nameDest` | 0 |
| `oldbalanceDest` | 0 |
| `newbalanceDest` | 0 |
| `isFraud` | 0 |
| `isFlaggedFraud` | 0 |

## Tipos de transacción

| Tipo | Cantidad | Porcentaje |
| --- | ---: | ---: |
| `CASH_OUT` | 2,237,500 | 35.166% |
| `PAYMENT` | 2,151,495 | 33.815% |
| `CASH_IN` | 1,399,284 | 21.992% |
| `TRANSFER` | 532,909 | 8.376% |
| `DEBIT` | 41,432 | 0.651% |

## Distribución de `amount`

| Métrica | Valor |
| --- | ---: |
| Mínimo | 0.00 |
| Promedio | 179,861.90 |
| Mediana | 74,871.94 |
| Percentil 95 | 518,634.20 |
| Percentil 99 | 1,615,979.47 |
| Percentil 99.9 | 8,956,797.68 |
| Máximo | 92,445,516.64 |
| Montos negativos | 0 |
| Montos iguales a cero | 16 |

## Etiquetas

| Campo | Valor 0 | Valor 1 |
| --- | ---: | ---: |
| `isFraud` | 6,354,407 | 8,213 |
| `isFlaggedFraud` | 6,362,604 | 16 |

## Cobertura temporal

| Métrica | Valor |
| --- | ---: |
| Step mínimo | 1 |
| Step máximo | 743 |
| Steps distintos | 743 |
| Steps ausentes | 0 |
| Inicio del tramo final compuesto solo por fraude | 719 |

### Últimos 10 steps

| Step | Transacciones | Monto total | Fraudes | Tasa de fraude |
| ---: | ---: | ---: | ---: | ---: |
| 734 | 8 | 27,827,406.36 | 8 | 100.000% |
| 735 | 12 | 3,155,523.32 | 12 | 100.000% |
| 736 | 14 | 32,530,967.34 | 14 | 100.000% |
| 737 | 10 | 9,560,119.88 | 10 | 100.000% |
| 738 | 10 | 2,883,702.98 | 10 | 100.000% |
| 739 | 10 | 16,587,831.36 | 10 | 100.000% |
| 740 | 6 | 7,632,963.58 | 6 | 100.000% |
| 741 | 22 | 87,828,992.99 | 22 | 100.000% |
| 742 | 14 | 14,323,735.20 | 14 | 100.000% |
| 743 | 8 | 17,519,825.50 | 8 | 100.000% |

## Duplicados

Se detectaron **0** filas duplicadas mediante hash de las 11 columnas. El método permite comparar registros entre bloques sin cargar el CSV completo como texto en memoria.

## Puntos para revisión

- Confirmar con los responsables de Silver cualquier regla de eliminación o corrección antes de modificar datos derivados.
- Investigar el cambio de comportamiento del tramo final antes de definir entrenamiento y prueba.
- Mantener los valores extremos de monto hasta determinar si son errores o resultados válidos de la simulación.

El perfilado es de solo lectura y no modifica el archivo Bronze.
