# Contrato Silver de reclamos — Angel

Define la tabla `data/silver/complaints/complaints.parquet`, generada desde `data/bronze/complaints/consumer_complaints.csv` con:

```powershell
.venv-pruebas/Scripts/python.exe scripts/build_silver_complaints.py
```

El comando escribe además `artifacts/reports/complaints/silver_quality.json` y [calidad-silver.md](calidad-silver.md). El Parquet y el JSON quedan fuera de Git. Código: `src/bankshield/transforms/silver_complaints.py` y `src/bankshield/features/text_cleaning.py`.

**Grano:** una fila por reclamo (`complaint_id`). Este archivo no se une con transacciones ni crédito: no hay llave común.

## Reglas de validez

Se **rechaza** una fila, con motivo registrado en el reporte, si:

| Motivo | Condición |
| --- | --- |
| `missing:complaint_id` / `invalid:complaint_id` | Identificador vacío o no numérico. |
| `missing:date_received` / `invalid:date_received` | Fecha vacía o que no es `MM/DD/YYYY` (ni `YYYY-MM-DD`) real, p. ej. `13/45/2015`. |
| `missing:product` | Producto vacío. |

Un `complaint_id` repetido no se rechaza: se conserva la primera aparición y se cuenta como duplicado eliminado.

**No se rechazan, solo se marcan:** envío a la empresa anterior a la recepción (`sent_before_received`), código postal con formato inusual (`zipcode_format_valid`) y narrativas idénticas (`narrative_is_repeated`).

## Columnas

| Columna | Tipo | Descripción |
| --- | --- | --- |
| `row_id` | int64 | Posición de la fila en Bronze (0 = primera fila de datos). |
| `complaint_id` | int64 | Identificador único. |
| `date_received`, `date_sent_to_company` | datetime | Fechas interpretadas; `date_sent_to_company` queda nula si no es interpretable. |
| `days_to_send` | Int64 | `date_sent_to_company − date_received` en días; puede ser negativo. |
| `sent_before_received` | bool | `days_to_send < 0`. |
| `product`, `issue`, `company`, `company_response_to_consumer`, `submitted_via` | texto | Sin espacios sobrantes; nunca vacíos salvo que Bronze lo permita. |
| `sub_product`, `sub_issue`, `company_public_response`, `state`, `consumer_consent_provided` | texto, nulable | Vacío en Bronze → nulo. |
| `zipcode` | texto, nulable | Se conserva como texto (hay códigos enmascarados como `123XX`). |
| `zipcode_format_valid` | bool | `True` si es de 5 dígitos o `123XX`. |
| `timely_response`, `consumer_disputed` | boolean | `Yes`/`No` → `True`/`False`. |
| `is_older_american`, `is_servicemember` | bool | Derivadas de `tags`. |
| `has_narrative` | bool | Hay narrativa del consumidor. |
| `narrative` | texto, nulable | Original, solo recortado. |
| `narrative_clean` | texto, nulable | Versión limpia (ver abajo); nula si no hay narrativa. |
| `redaction_count` | int64 | Fechas, montos y rachas de `X` censurados en el original. |
| `clean_word_count` | int64 | Palabras de `narrative_clean`. |
| `narrative_is_repeated` | bool | La misma narrativa aparece en más de un reclamo (plantillas o reclamos duplicados). |

`consumer_disputed` es un resultado posterior al reclamo: no debe usarse como predictor de nada que ocurra antes de la disputa.

## Limpieza del texto

`narrative_clean` se obtiene en este orden: (1) sustituir censura por marcadores, (2) colapsar espacios y saltos de línea, (3) pasar a minúsculas.

| Censura en el original | Ejemplos | Marcador |
| --- | --- | --- |
| Monto | `{$27.00}`, `{$1,250.50}` | `<monto>` |
| Fecha con componentes censurados | `XX/XX/XXXX`, `XXXX/XXXX/2015`, `XX/XX/15` | `<fecha>` |
| Racha de `X` (mayúscula o minúscula) | `XXXX`, `XXXXXXXX`, `XXXX,`, `xxxxxxxxxxx` | `<censurado>` |

Una fecha sin ninguna `X` (`05/12/2015`) es un dato visible y se deja intacta. Las palabras que contienen `x` (por ejemplo `MAXX` o `xxl`) no se tocan. Las `x` en minúscula son las que los propios consumidores escriben para ocultar números de cuenta (22 narrativas); se tratan igual que la censura de la CFPB.

## Decisiones

- **Marcadores en lugar de borrar la censura.** Se conserva la señal de que había una fecha o un monto; el paso de NLP decide si los ignora.
- **Sin stopwords ni stemming en Silver.** Eso pertenece al vectorizador del modelo, que debe ajustarse solo con entrenamiento para no filtrar información de prueba.
- **Las narrativas repetidas se conservan** y se marcan: al partir en entrenamiento y prueba conviene agruparlas para que el mismo texto no caiga en ambos lados.
- **Cobertura:** solo una minoría de reclamos tiene narrativa (ver [perfil](perfil-complaints.md)); los análisis de texto se limitan a ese subconjunto y no representan a todos los reclamos.

## Controles que hacen fallar el comando

`expected_header`, `row_accounting` (Bronze = Silver + rechazadas + duplicadas), `complaint_ids_unique`, `row_ids_unique`, `dates_received_valid`, `narrative_accounting` (las narrativas de Bronze se reparten sin pérdida entre Silver, rechazadas y duplicadas), `clean_text_only_with_narrative` y `no_residual_redaction`. El reporte registra además las huellas SHA-256 del CSV y del Parquet.
