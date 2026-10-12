# Contrato de variables de crédito — Sevan

Complementa el [perfil](perfil-credito.md), la [calidad Silver](calidad-silver.md) y los [resultados](resultados-modelo.md). El código vive en `src/bankshield/features/credit.py`.

## Decisión que apoya el modelo

Estimar la probabilidad de **impago asumido** (`loan_status = 1`) de una solicitud de préstamo en el momento de la solicitud. El significado de `loan_status` no está documentado en la fuente; hasta confirmarlo, API y página lo declaran como no confirmado.

## Variables

| Variable | Tipo | Uso | Nota |
| --- | --- | --- | --- |
| `person_age` | entero 18–100 | predictor | Variable sensible: revisar antes de cualquier uso real. |
| `person_income` | positivo | predictor | Fuente de `loan_percent_income`. |
| `person_emp_length` | ≥ 0, opcional | predictor | 2.75 % ausente; el modelo la acepta nula. |
| `loan_amnt` | positivo | predictor | |
| `loan_percent_income` | derivada | predictor | Se recalcula como `loan_amnt / person_income`. |
| `cb_person_cred_hist_length` | entero ≥ 0 | predictor | |
| `person_home_ownership`, `loan_intent`, `cb_person_default_on_file` | categóricas | predictores | Categorías cerradas; valores desconocidos se rechazan. |
| `loan_grade`, `loan_int_rate` | categórica / numérica | **excluidas** del modelo principal | Las fija el prestamista tras evaluar el riesgo; solo entran en la variante comparativa `with_pricing`. |
| `loan_status` | etiqueta | objetivo | Nunca forma parte de la matriz de variables. |

## Reglas de validez (Silver y API)

- Edad entre 18 y 100; ingreso y monto positivos.
- `person_emp_length` ≤ edad − 14; historial crediticio ≤ edad − 13.
- Categorías dentro del vocabulario conocido; etiqueta binaria.
- Filas inválidas se rechazan y cuentan en el reporte (7 en el CSV actual); no se imputan.
- Duplicados exactos se eliminan antes de particionar (165).

## Partición, calibración y umbral

Aleatoria estratificada 70/15/15 con semilla 42 (no hay fecha ni cliente). Modelo y calibración sigmoide se ajustan con entrenamiento y validación; el umbral minimiza FP×1 + FN×5 sobre la probabilidad calibrada en validación; la prueba se lee una sola vez. Los costes son supuestos académicos.

## Explicación individual

La API devuelve hasta cinco factores por **oclusión**: cambio en la probabilidad al sustituir cada variable por la mediana o moda de entrenamiento. Describe al modelo, no establece causalidad, y al mover una sola variable a la vez puede subestimar efectos que dependen de varias (p. ej. monto e ingreso a través de `loan_percent_income`).

## Monto de crédito

El servicio **no recomienda montos ni límites** (`credit_limit_recommended` siempre nulo). Una probabilidad de impago no determina un monto óptimo: faltan pérdida en caso de impago, plazo, margen, costo de fondeo y respuesta de la demanda. Una política de límites requeriría esos datos y una regla explícita, como máxima razón monto/ingreso o pérdida esperada acotada, validada con el área de riesgo.

## Interfaz

`POST /api/credit/predict` acepta solo los campos de solicitud (rechaza `loan_grade`, `loan_int_rate` y cualquier campo extra). `GET /api/credit/model` devuelve métricas, particiones, versiones y límites embebidos en el mismo artefacto. El modelo se indica con `BANKSHIELD_CREDIT_MODEL` (por defecto `artifacts/models/credit/model.joblib`).
