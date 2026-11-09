# Contrato de regresión numérica — SEV-01

Responsable del módulo: Sevan. Implementación de cierre en la rama `cierre-semana-13`; revisiones humanas de Rhamses/Gerardo pendientes.

Pregunta: ¿qué monto transaccional estima el modelo a partir del tipo de operación y saldo anterior? El objetivo es `amount`, distinto del score de fraude y de la clasificación crediticia.

## Datos y predictores

Se consume D1 con SHA-256, controles de calidad, esquema y discretización validados. El lector verifica cada fila: ID ordinal, partición, tipos, valores finitos y bins compatibles. Los cortes son train 1–323, validation 324–378, test 379–718 y stress 719–743.

| Entrada o derivada | Tratamiento |
| --- | --- |
| type | Catálogo PaySim de cinco tipos, one-hot dentro del pipeline. |
| oldbalanceOrg | Finito, no negativo, excluye booleanos. |
| log_origin_balance | log1p del saldo; transformación determinista. |
| zero_origin_balance | Marcador de saldo cero. |

`amount`, `amount_bin`, comparaciones que contengan el monto, saldos posteriores, etiquetas, IDs y step no entran en la matriz. El preprocesamiento aprendido se ajusta solo con la muestra de train.

## Ajuste y evaluación

Referencia: mediana de monto por tipo; para un tipo válido ausente del entrenamiento, mediana global. Candidatos: Ridge alpha 1/10 y HistGradientBoostingRegressor (100 iteraciones máximas, 15 hojas, learning_rate 0.1, min_samples_leaf 20, random_state 42). Candidatos ajustados sobre log1p(amount); inversión expm1 y recorte inferior a cero.

Reservorio uniforme por prioridades iid con semilla 42, máximo 200,000 filas de train; se conserva la huella de IDs. Mismo subconjunto para todos los métodos. `max_train_rows=null` usa train completo. No se muestrean validation/test/stress. Selección por menor MAE de validation; tolerancia 1e-9 favorece referencia, Ridge 1, Ridge 10 y boosting en ese orden. No se reajusta con validation.

Métricas en escala original: n, MAE, RMSE, R² y sesgo medio. R² indefinido es null con motivo; stress siempre separado. Se publican errores por tipo y tramo de monto con bordes ajustados por D1 solo en train. Resultados: [reporte generado](resultados-modelo.md).

## Artefactos y HTTP

`artifacts/models/regression/`: model.joblib, metrics.json, predictions.parquet y examples.json. El ID es SHA-256 del archivo joblib. El servicio contrasta identidad, versiones y métricas embebidas; los ejemplos tienen huella vinculada y son una muestra uniforme de hasta 200 filas de test. El Parquet exporta todas las filas de validation/test/stress y las huellas separadas de Silver y D1.

- `POST /api/regression/predict`: cuerpo exacto `{"type":"TRANSFER","oldbalanceOrg":500.0}`.
- `GET /api/regression/model`: identidad, particiones, comparación, muestreo y limitaciones.
- `GET /api/regression/examples?limit=20&offset=0`: limit 1–100, offset >=0; página vacía válida.
- 422 para entradas inválidas, 503 para artefactos ausentes/incompatibles. La API inicia sin modelo.
- Variable `BANKSHIELD_REGRESSION_MODEL`; hermanos resueltos en su carpeta. No se aceptan rutas/modelos desde peticiones ni se entrena por HTTP.
- Página `07_regresion.py`: solo HTTP, resultado persistente, comparación separada por partición, ejemplos y avisos por cambio de modelo/filtros.

```powershell
.venv-pruebas/Scripts/python.exe scripts/train_regression.py --config configs/regression.json
.venv-pruebas/Scripts/python.exe -m unittest discover -s tests/unit -p "test*regression*.py" -v
```

Referencias metodológicas: [TransformedTargetRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.compose.TransformedTargetRegressor.html), [HistGradientBoostingRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html). Las versiones realmente utilizadas figuran en el reporte; no se presupone la versión del sitio web.
