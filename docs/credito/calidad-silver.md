# Calidad Silver de crédito — Sevan

Fuente Bronze SHA-256: `ce3c6d2167717bf1627d1c0c81cbccd28323cd4aa7b96d542599366d5ff6aac8`. Parquet SHA-256: `e0980b5eb868a0d639509ed0fb200920a7560419be056e687e9d6c58dcc68087`.

| Concepto | Filas |
| --- | ---: |
| Bronze | 32,581 |
| Rechazadas por validez | 7 |
| Duplicados exactos eliminados | 165 |
| **Silver** | **32,409** |

Motivos de rechazo: `age_out_of_range`: 5, `emp_length_impossible`: 2.

Los rechazos son valores imposibles (p. ej. edad de 123–144 años o antigüedad laboral mayor que la edad); no se imputan. Los nulos de `person_emp_length` y `loan_int_rate` se conservan con indicador `*_missing`. `loan_percent_income` se recalcula como `loan_amnt / person_income`.

## Controles

| Control | Resultado |
| --- | --- |
| `expected_header` | aprobado |
| `row_accounting` | aprobado |
| `no_exact_duplicates_in_silver` | aprobado |
| `labels_binary` | aprobado |
| `row_ids_unique` | aprobado |
| `ratio_matches_amount_over_income` | aprobado |

Tasa de clase positiva en Silver: 21.87%.
