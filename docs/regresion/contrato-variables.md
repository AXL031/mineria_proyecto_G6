# Contrato de variables de la regresión del monto (SEV-01)

Propietario: Sevan. Entrada: tabla D1 de Taco ([contrato analítico](../transacciones/contrato-analitico.md)).

**Pregunta:** estimar `amount` a partir de `type` y `oldbalanceOrg` en PaySim. Sirve para estudiar montos
esperados y errores de estimación; no fija límites crediticios ni produce una alerta de fraude.

## Entrada pública (exacta)

| Campo | Regla |
| --- | --- |
| `type` | `PAYMENT`, `TRANSFER`, `CASH_OUT`, `DEBIT` o `CASH_IN`; otro valor es 422. |
| `oldbalanceOrg` | Número finito y no negativo; booleanos, cadenas, NaN/Infinity y campos extra son 422. |

## Predictores del modelo

`type`, `oldbalanceOrg`, `log_oldbalance = log1p(oldbalanceOrg)` y `zero_balance` (1 si el saldo es 0).
Implementado en `src/bankshield/features/regression.py`; no reutiliza `build_fraud_feature_frame`.

**Prohibidos como predictor:** `amount`, `amount_bin`, cocientes que contengan el monto, saldos posteriores,
`isFraud`, `row_id`, `step`. Una prueba verifica que cambiar esos campos no cambia la matriz de predictores.

## Particiones y muestra de entrenamiento

Las de D1: `train` 1–323, `validation` 324–378, `test` 379–718, `stress` 719–743 (solo fraude, informado aparte).
La muestra de entrenamiento (`max_train_rows = 200000`, `null` usa todo train) es uniforme sin reemplazo con
`numpy.random.default_rng(42)`, solo dentro de train; se registran filas disponibles/usadas y la huella SHA-256
de los `row_id` elegidos. Validation, test y stress no se muestrean ni se balancean.

## Artefactos (`artifacts/models/regression/`)

| Archivo | Contenido |
| --- | --- |
| `model.joblib` | Modelo seleccionado, configuración, variables, versiones y metadatos de evaluación. |
| `metrics.json` | Consulta vinculada al SHA-256 de `model.joblib` (`model_sha256`). |
| `predictions.parquet` | `row_id, step, partition, type, actual, prediction, model_id, source_sha256, dataset_sha256` para todas las filas de validation/test/stress. Entrada del monitoreo de Gerardo. |
| `examples.json` | 200 filas aleatorias de test (semilla 42), no solo aciertos. |

El servicio rechaza (503) un modelo cuyo `metrics.json` o `examples.json` pertenezcan a otra identidad.
Variable de entorno: `BANKSHIELD_REGRESSION_MODEL`. No se deserializan archivos aportados por usuarios.

## HTTP

- `POST /api/regression/predict` → `model_id`, `target`, `prediction`, `selected_model`, `simulation_data`, `limitations`.
- `GET /api/regression/model` → identidad, variables, selección, particiones, comparación y limitaciones.
- `GET /api/regression/examples?limit=20&offset=0` → `limit` 1–100, `offset` ≥ 0; página vacía fuera de rango.

El router vive en `api/routers/regression.py`. **Pendiente de Angel:** registrarlo en `api/main.py`
(`app.include_router(regression_router, prefix="/api")`) y enlazar la página 07 desde la portada.
