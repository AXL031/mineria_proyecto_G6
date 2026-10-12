# Perfil del dataset crediticio — Sevan

Fuente: `credit_risk_dataset.csv` (1,804,682 bytes), SHA-256 `ce3c6d2167717bf1627d1c0c81cbccd28323cd4aa7b96d542599366d5ff6aac8`. Generado por `scripts/profile_credit.py`; no modifica Bronze.

## Resumen

- Filas: **32,581**; columnas: 12.
- Duplicados exactos: **165**.
- `loan_status`: 0 = 25,473; 1 = 7,108 (21.82% positivos).
- No hay fecha ni clave de cliente: la separación temporal o por cliente no es posible.

## Semántica de `loan_status`

El archivo no incluye diccionario. Se **asume** que 1 significa impago/default y 0 préstamo al corriente, coherente con la tasa por grado (A≈10 % … G≈98 %) y con la tasa positiva de 21.8 %. Una copia del dataset en OpenML (api.openml.org/d/43454) documenta 0 = sin impago y 1 = impago y reporta los mismos 895 nulos en `person_emp_length`. Es una fuente secundaria: no confirma procedencia ni licencia. Hasta verificarlo con la fuente original, el módulo habla de «clase positiva = impago asumido».

## Valores faltantes

| Columna | Faltantes | % |
| --- | ---: | ---: |
| `person_emp_length` | 895 | 2.75% |
| `loan_int_rate` | 3,116 | 9.56% |

Tasa de clase positiva con `loan_int_rate` ausente: 20.67% frente a 21.94% con valor. La ausencia es informativa, así que se conserva un indicador en vez de descartar filas.

## Valores implausibles

- Edad mayor de 100 años: 5.
- Antigüedad laboral mayor que edad − 14: 2.
- Filas rechazadas por las reglas de validez de Silver: **7** (age_out_of_range: 5, emp_length_impossible: 2).
- `loan_percent_income` difiere más de 0.01 de `loan_amnt / person_income` en 388 filas (máx. 0.093); Silver recalcula la razón.

## Grado y tasa: ¿variables disponibles al decidir?

`loan_grade` y `loan_int_rate` las fija el prestamista **después** de evaluar el riesgo del solicitante. La tasa se solapa por grado y refleja el riesgo ya estimado, de modo que usarlas para «decidir» sería circular. El modelo principal las excluye y una variante comparativa las incluye.

| Grado | Filas | Tasa positiva | Tasa mín. | Tasa máx. | Tasa ausente |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 10,777 | 9.96% | 5.42 | 9.63 | 1,003 |
| B | 10,451 | 16.28% | 6.00 | 12.69 | 1,056 |
| C | 6,458 | 20.73% | 6.00 | 16.11 | 630 |
| D | 3,626 | 59.05% | 6.00 | 18.49 | 312 |
| E | 964 | 64.42% | 6.00 | 20.69 | 83 |
| F | 241 | 70.54% | 15.01 | 22.06 | 27 |
| G | 64 | 98.44% | 17.34 | 23.22 | 5 |

## Estrategia de partición

Sin fecha ni cliente, se usa una partición **aleatoria estratificada** 70/15/15 con semilla fija, después de eliminar duplicados exactos para que una misma fila no caiga en dos particiones. Limitación: no mide generalización temporal ni a clientes nuevos, y no se puede descartar que una misma persona aparezca varias veces con valores distintos. La métrica de prueba se reporta una sola vez, con modelo, calibración y umbral ya congelados.
