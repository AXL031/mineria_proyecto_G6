# Diccionario de las fuentes originales y tablas analíticas

Responsables: Cueva–Taco (PaySim), Sevan (crédito), Angel (reclamos); Gerardo revisa tiempo/particiones y Rhamses identidades de red. Consolidación: ANG-03. Actualización técnica: 9 de noviembre de 2026.

Las tres fuentes son independientes: no hay una clave de cliente común. Los tipos de esta página son los tipos analíticos esperados, no una afirmación sobre tipos nativos del CSV. Los vacíos y rechazos se cuantifican en los reportes de cada Silver.

## PaySim: una fila por transacción simulada

6,362,620 filas, 11 columnas; original inmutable en `data/bronze/transactions/`. La unidad monetaria no está verificada. Diccionario ampliado: [fuente PaySim](pronosticos/fuente-paysim.md). Fuente pública de referencia: [publicación PaySim](https://www.kaggle.com/datasets/ealaxi/paysim1).

| Campo original | Tipo / dominio | Significado y unidad | Uso / ausencia |
| --- | --- | --- | --- |
| step | entero 1–743 | Hora simulada; sin fecha calendario. | Partición/orden temporal; cero nulos observados. |
| type | categoría | CASH_IN, CASH_OUT, DEBIT, PAYMENT, TRANSFER. | Predictor y agregación; cero nulos. |
| amount | decimal ≥0 | Monto de la operación; moneda desconocida. | Predictor de fraude y objetivo de regresión; cero nulos. |
| nameOrig | texto | ID de cuenta origen; prefijo C. | Identidad de grafo, nunca predictor de regresión; cero nulos. |
| oldbalanceOrg | decimal ≥0 | Saldo anterior del origen; misma unidad de amount. | Predictor disponible antes del evento, sujeto a limitaciones del simulador; cero nulos. |
| newbalanceOrig | decimal ≥0 | Saldo posterior del origen. | Descripción/auditoría; excluido de decisiones anteriores al evento; cero nulos. |
| nameDest | texto | ID destino; C cuenta, M comercio. | Grafos y agregados de segmentación; cero nulos. |
| oldbalanceDest | decimal ≥0 | Saldo anterior de destino. | Descriptivo; saldos de comercios pueden figurar como cero, no como ausencia. |
| newbalanceDest | decimal ≥0 | Saldo posterior de destino. | Descriptivo; no predictor previo. |
| isFraud | entero 0/1 | Etiqueta generada por simulación; 1 fraude. | Objetivo de clasificación/consecuente de asociaciones; no predictor ni variable de clustering. |
| isFlaggedFraud | entero 0/1 | Marca de una regla preexistente; no es la etiqueta real. | Auditoría; no predictor de los modelos acordados. |

Los saldos pueden reflejar el mecanismo de cancelación de fraude del simulador; sus asociaciones fuertes no acreditan fraude bancario real. No se oculta esta limitación para mejorar la interpretación de las métricas.

## Crédito: una fila por registro de préstamo/solicitud

32,581 filas originales, 12 columnas. No hay fecha ni ID de cliente. [Contrato](credito/contrato-variables.md), [perfil](credito/perfil-credito.md) y [calidad](credito/calidad-silver.md). Catálogo de referencia: [Credit Risk Dataset de Lao Tse](https://www.kaggle.com/datasets/laotse/credit-risk-dataset).

| Campo original | Tipo / dominio | Significado y unidad | Uso / ausencia |
| --- | --- | --- | --- |
| person_age | entero | Edad en años; Silver admite 18–100. | Predictor; variable sensible; cinco edades rechazadas. |
| person_income | decimal >0 | Ingreso declarado; moneda y periodo de la copia requieren confirmación. | Predictor y denominador de razón monto/ingreso. |
| person_home_ownership | categoría | RENT, MORTGAGE, OWN, OTHER. | Predictor; no representa titularidad de una cuenta PaySim. |
| person_emp_length | decimal ≥0 | Antigüedad laboral en años. | 895 vacíos en Bronze; imputación aprendida con train e indicador de ausencia; dos valores imposibles rechazados. |
| loan_intent | categoría | Finalidad: PERSONAL, EDUCATION, MEDICAL, VENTURE, HOMEIMPROVEMENT, DEBTCONSOLIDATION. | Predictor. |
| loan_grade | categoría A–G | Grado asignado por prestamista. | Excluido del modelo principal por disponibilidad posterior. |
| loan_amnt | decimal >0 | Monto solicitado/registrado; moneda no verificada. | Predictor; no es una recomendación de límite. |
| loan_int_rate | decimal | Tasa de interés publicada; escala porcentual de la fuente. | 3,116 vacíos; excluida del modelo principal, incluida solo en variante descriptiva comparativa. |
| loan_status | entero 0/1 | Catálogo público: 0 sin impago, 1 impago. | Objetivo; correspondencia/procedencia exacta de la copia pendiente, por eso el producto conserva «impago asumido». |
| loan_percent_income | decimal | Razón monto/ingreso. | Silver la recalcula desde loan_amnt/person_income; no copiar inconsistencias originales. |
| cb_person_default_on_file | categoría Y/N | Registro de incumplimiento previo. | Predictor conocido previamente; distinto del resultado actual loan_status. |
| cb_person_cred_hist_length | entero ≥0 | Longitud del historial crediticio en años. | Predictor con controles de coherencia respecto de edad. |

Silver elimina 165 duplicados exactos y rechaza siete filas inválidas; quedan 32,409. Una división aleatoria estratificada no acredita generalización temporal o a personas nuevas.

## Reclamos: una fila por complaint_id

555,957 filas originales, 18 columnas. Narrativa presente en 66,806 registros (12.02%); los vacíos no se inventan ni se completan con texto sintético. Fuente de referencia: [CFPB](https://www.consumerfinance.gov/data-research/consumer-complaints/), [campos oficiales](https://cfpb.github.io/api/ccdb/fields.html). El contrato de [Silver](reclamos/contrato-silver.md) enumera por separado las variables derivadas.

| Campo original | Tipo / dominio | Significado | Uso / ausencia |
| --- | --- | --- | --- |
| date_received | fecha | Fecha de recepción por CFPB. | Obligatoria; tendencia/partición; fechas imposibles rechazadas. |
| product | categoría | Producto identificado por el consumidor. | Objetivo del clasificador NLP; no equivale a resolución. |
| sub_product | categoría/texto | Subproducto dependiente de product. | Nulable; no todos los productos tienen subproducto. |
| issue | categoría/texto | Problema declarado por consumidor. | Descripción; requerido por fuente de trabajo. |
| sub_issue | categoría/texto | Detalle del problema. | Nulable; no todos los problemas tienen detalle. |
| consumer_complaint_narrative | texto | Relato publicado con consentimiento y anonimización. | Nulable; solo el subconjunto con texto elegible entra a NLP. |
| company_public_response | texto | Respuesta pública opcional de empresa. | Nulable; información posterior, no entrada del clasificador de producto. |
| company | categoría/texto | Empresa objeto del reclamo. | Agregación; volumen bruto no mide calidad ajustada por tamaño de empresa. |
| state | texto | Estado de dirección del consumidor. | Nulable; no une personas entre fuentes. |
| zipcode | texto | Código postal, a veces enmascarado. | Nulable; conservar texto y ceros iniciales. |
| tags | texto | Indicadores como persona mayor o militar. | Nulable; marcadores descriptivos, no identidades. |
| consumer_consent_provided | categoría/texto | Estado del consentimiento para publicar narrativa. | Nulable; no inferirlo por ausencia de texto. |
| submitted_via | categoría/texto | Canal de envío del reclamo. | Agregación descriptiva. |
| date_sent_to_company | fecha | Fecha de envío a empresa. | Puede ser nula si no se interpreta; diferencias negativas se marcan, no se corrigen silenciosamente. |
| company_response_to_consumer | categoría/texto | Tipo de respuesta al consumidor. | Resultado posterior al reclamo. |
| timely_response | Yes/No | Respuesta dentro del plazo de referencia de la fuente. | Silver convierte a booleano; no predictor previo. |
| consumer_disputed? | Yes/No | Disputa del consumidor a la respuesta, campo histórico. | Resultado posterior; no se extrapola al catálogo actual de CFPB. |
| complaint_id | entero | Identificador único del reclamo. | Clave y control de duplicados; no ID de cliente. |

La referencia actual de CFPB no conserva necesariamente todos los campos históricos de esta copia 2011–2016. Se documenta esa diferencia. No se publican narrativas originales nuevas ni identificadores personales como parte de esta revisión.

## Derivados y contratos

| Tabla/artefacto | Grano / claves | Contrato |
| --- | --- | --- |
| Silver transaccional | Una transacción, mismas 11 columnas y orden. | [Silver](transacciones/contrato-silver.md). |
| Gold transaccional | Una transacción con variables derivadas; saldos posteriores descriptivos. | [Gold](transacciones/contrato-gold.md). |
| D1 | Una transacción; row_id ordinal base 1 del Silver, partición y bins de train. | [Analítico](transacciones/contrato-analitico.md). |
| Gold temporal | Una fila por step; conteos, montos y fraude descriptivo. | [Temporal](pronosticos/contrato-gold.md). |
| Segmentos | Una cuenta destino con al menos diez recepciones. | [Segmentación](transacciones/segmentacion.md). |
| Regresión | Entradas type/oldbalanceOrg; salida amount estimado. | [Regresión](regresion/contrato-variables.md). |
| Asociaciones | Una regla con evaluaciones por partición. | [Asociaciones](fraude/asociaciones-descubiertas.md). |

Los row_id del Silver de reclamos son base 0; los de D1 son base 1. No son claves compartidas y nunca se unen entre dominios.
