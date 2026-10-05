# Perfil de PaySim — módulo de fraude

Informe generado por `scripts/profile_fraud.py`. Los originales no se modifican.

- Archivo: `PS_20174392719_1491204439457_log.csv`.
- SHA-256: `16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b`.
- Alcance: `complete_file`; registros leídos: 6,362,620.
- Registros válidos: 6,362,620; inválidos: 0.
- Fraudes: 8,213; operaciones etiquetadas como no fraudulentas: 6,354,407.
- Prevalencia de fraude en registros válidos: 0.129082%.

## Fraude por tipo

| Tipo | Registros válidos | Fraudes | Prevalencia |
| --- | ---: | ---: | ---: |
| CASH_IN | 1,399,284 | 0 | 0.000000% |
| CASH_OUT | 2,237,500 | 4,116 | 0.183955% |
| DEBIT | 41,432 | 0 | 0.000000% |
| PAYMENT | 2,151,495 | 0 | 0.000000% |
| TRANSFER | 532,909 | 4,097 | 0.768799% |

## Calidad

| Columna | Valores ausentes |
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

Incidencias detectadas: `{}`.

## Rangos numéricos de registros válidos

| Campo | Mínimo | Máximo | Media |
| --- | ---: | ---: | ---: |
| `amount` | 0.0 | 92445516.64 | 179861.90354912292 |
| `oldbalanceOrg` | 0.0 | 59585040.37 | 833883.1040744851 |
| `newbalanceOrig` | 0.0 | 49585040.37 | 855113.6685785672 |
| `oldbalanceDest` | 0.0 | 356015889.35 | 1100701.6665196999 |
| `newbalanceDest` | 0.0 | 356179278.92 | 1224996.3982020712 |

## Cobertura de simulación

Se observan 743 pasos distintos, desde 1 hasta 743. El JSON contiene los recuentos y fraudes de cada paso. `step` no representa una fecha calendario.

Hay 320 pasos que contienen únicamente fraude (3,620 registros). El último paso con operaciones no fraudulentas es 718. Antes de fijar los cortes temporales hay que revisar clases y prevalencia por partición. No se eliminarán periodos en función de sus etiquetas para mejorar métricas.

## Límites del perfil

Los recuentos por tipo, etiqueta, paso y rangos excluyen registros inválidos. La ausencia de incidencias no demuestra que no haya duplicados: este perfil no mide duplicados exactos, cuentas únicas ni cuantiles. La procedencia y licencia siguen pendientes de confirmación.

## Uso para modelado

Consultar el [contrato de variables](contrato-variables.md). Usar `step` para separar periodos y comprobar fraude en cada partición antes de entrenar. La etiqueta queda fuera de las variables; los saldos posteriores y `isFlaggedFraud` también se excluyen del primer modelo.
