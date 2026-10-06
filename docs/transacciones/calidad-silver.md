# Reporte de calidad — Silver transaccional

Archivo generado por `scripts/build_silver.py`; se regenera con cada
construcción de Silver. Los originales de Bronze no se modifican.

## Fuente y salida

- Entrada: `PS_20174392719_1491204439457_log.csv`
- Tamaño: 493,534,783 bytes
- SHA-256: `16910F90577B0D981BF8FF289714510BB89BC71BFF7D3F220F024E287E4EEA6B`
- Huella esperada coincide: True
- Salida: `data\silver\transactions\transactions.parquet` (Parquet, compresión snappy)
- Alcance: `complete_file`

## Recuentos

| Métrica | Valor |
| --- | ---: |
| Filas de Bronze | 6,362,620 |
| Filas en Silver | 6,362,620 |
| Filas rechazadas | 0 |

### Rechazos por causa

| Causa | Filas |
| --- | ---: |
| _(sin rechazos)_ | 0 |

## Controles

| Control | Resultado |
| --- | --- |
| `expected_header` | OK |
| `source_sha256_matches` | OK |
| `no_rejected_rows` | OK |
| `no_exact_duplicate_rows` | OK |
| `steps_are_contiguous` | OK |

## Duplicados y cuentas

- Filas exactas duplicadas en Silver: **0** (política: kept; Hash pandas de 64 bits sobre las 11 columnas de Silver.)
- Cuentas origen únicas: 6,353,307
- Cuentas destino únicas: 2,722,362
- Cuentas únicas (unión): 9,073,900

## Distribución de `amount` en Silver

| Métrica | Valor |
| --- | ---: |
| Mínimo | 0.00 |
| Promedio | 179,861.90 |
| Máximo | 92,445,516.64 |
| Percentil 25 | 13,389.57 |
| Percentil 50 | 74,871.94 |
| Percentil 75 | 208,721.48 |
| Percentil 95 | 518,634.20 |
| Percentil 99 | 1,615,979.47 |
| Percentil 99.9 | 8,956,797.68 |

## Cobertura por `step`

| Métrica | Valor |
| --- | ---: |
| Step mínimo | 1 |
| Step máximo | 743 |
| Steps distintos | 743 |
| Steps ausentes | 0 |

## Fraude por tipo de transacción

| Tipo | Filas | Fraudes | Monto total |
| --- | ---: | ---: | ---: |
| `CASH_IN` | 1,399,284 | 0 | 236,367,391,912.46 |
| `CASH_OUT` | 2,237,500 | 4,116 | 394,412,995,224.49 |
| `DEBIT` | 41,432 | 0 | 227,199,221.28 |
| `PAYMENT` | 2,151,495 | 0 | 28,093,371,138.37 |
| `TRANSFER` | 532,909 | 4,097 | 485,291,987,263.17 |

## Límites

- `step` es un paso de simulación de PaySim, no una fecha calendario.
- Los datos provienen de una simulación; los resultados no representan
  operaciones bancarias reales.
- Las filas rechazadas se excluyen de Silver y quedan registradas por causa
  en este reporte; Bronze permanece intacto.
- Los duplicados exactos se conservan por política mientras el equipo no
  defina una regla de eliminación: no existe identificador de transacción
  en la fuente.
