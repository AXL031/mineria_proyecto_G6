# Calidad Silver de reclamos — Angel

Fuente Bronze SHA-256: `df219bbcf0e8233f33eb83454ef9b3451adf471db29618acfb36d2dacc40ed3f`. Parquet SHA-256: `ba939fe172c4d938bee3d5266048506eb7c1bc7f79ea2252ff679eeb0dd0ff07`.

| Concepto | Filas |
| --- | ---: |
| Bronze | 555,957 |
| Rechazadas por validez | 0 |
| Duplicados de `complaint_id` eliminados | 0 |
| **Silver** | **555,957** |

No hubo filas rechazadas.

Rango de `date_received`: 2011-12-01 a 2016-04-25.

## Narrativas y marcas de calidad

| Concepto | Valor |
| --- | ---: |
| Narrativas en Bronze | 66,806 |
| Narrativas en Silver | 66,806 |
| Narrativas repetidas exactamente (`narrative_is_repeated`) | 1,868 |
| Elementos censurados reemplazados por marcador | 667,994 |
| Envío anterior a recepción (`sent_before_received`, se conservan) | 7,057 |
| `date_sent_to_company` no interpretable | 0 |
| `zipcode` con formato distinto de 5 dígitos o `123XX` | 197 |

## Controles

| Control | Resultado |
| --- | --- |
| `expected_header` | aprobado |
| `row_accounting` | aprobado |
| `complaint_ids_unique` | aprobado |
| `row_ids_unique` | aprobado |
| `dates_received_valid` | aprobado |
| `narrative_accounting` | aprobado |
| `clean_text_only_with_narrative` | aprobado |
| `no_residual_redaction` | aprobado |
