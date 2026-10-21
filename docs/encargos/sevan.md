# Encargo de Sevan — regresión numérica y cierre crediticio

Estado inicial: pendiente. Leer [contratos y prioridades](../pendientes-cierre-2026-10-20.md) y [D1/Taco](taco.md). El modelo de crédito, calibración, explicaciones, API y página ya existen; la regresión numérica será una capacidad nueva y separada de la regresión logística.

## SEV-01 — estimación del monto transaccional (P0)

### Pregunta y alcance fijados

Estimar `amount` a partir de `type` y `oldbalanceOrg` en PaySim. Sirve para estudiar montos esperados y errores de estimación, no para fijar límites crediticios ni producir una alerta de fraude. Si los predictores resultan poco informativos, documentar el resultado y conservar la referencia ganadora; no cambiar el objetivo después de inspeccionar test.

### Archivos

- Crear `configs/regression.json`, `src/bankshield/features/regression.py`, `src/bankshield/models/regression.py` y `src/bankshield/services/regression.py`.
- Crear `scripts/train_regression.py`, `api/routers/regression.py` y `dashboard/pages/07_regresion.py`.
- Crear pruebas `test_regression_features.py`, `test_regression_training.py`, `test_api_regression.py` y `test_regression_dashboard.py`.
- Crear `docs/regresion/contrato-variables.md` y `docs/regresion/resultados-modelo.md`.
- Entregar a Angel el router para registrarlo en `api/main.py`; no modificar el archivo central simultáneamente.

### Variables y evaluación

1. Consumir D1 validado; usar las particiones nuevas comunes. Objetivo: `amount`. Entrada pública exacta: `type` y `oldbalanceOrg`.
2. Ingeniería permitida: codificación de tipo, saldo, `log1p(oldbalanceOrg)` y marcador de saldo cero. **Prohibidos:** `amount`, `amount_bin`, cocientes/comparaciones que contengan amount, saldos posteriores, etiquetas, IDs y step como predictor. No reutilizar `build_fraud_feature_frame`, porque contiene el objetivo y sus derivados.
3. Referencia: mediana de monto de train por tipo, con mediana global para categorías sin observaciones en la muestra de entrenamiento. Tipos fuera del catálogo PaySim siguen siendo entrada inválida de la API.
4. Candidatos: Ridge con alpha=1 y con alpha=10; `HistGradientBoostingRegressor` con max_iter=100, max_leaf_nodes=15, learning_rate=0.1, min_samples_leaf=20, random_state=42. Fijar escalado/one-hot dentro del pipeline. Para los candidatos, ajustar `log1p(amount)` y convertir con `expm1`; recortar predicciones a cero como regla de dominio fijada antes de evaluar. Reportar métricas finales en escala original, no solo logarítmica.
5. Para acotar recursos: `max_train_rows=200000`, reservorio uniforme con semilla 42 solo en train; misma muestra para referencia y candidatos. Registrar algoritmo, filas disponibles/usadas y huella de los row_id seleccionados. Permitir `null` para usar todo train. No balancear por fraude ni muestrear validation/test/stress.
6. Ajustar transformadores y modelos solo en esa muestra de train. Seleccionar menor MAE de validation; empate numérico dentro de tolerancia 1e-9 favorece referencia, luego Ridge alpha=1, Ridge alpha=10 y boosting. No reentrenar sobre validation en v1, para conservar exactamente el artefacto evaluado.
7. Evaluar validation/test/stress completos por bloques. Métricas: n, MAE, RMSE, R², sesgo medio `mean(prediction-actual)`, por conjunto y tipo. R² con varianza cero o n insuficiente: null y motivo. Presentar stress separado de test.
8. Analizar errores por tipo y tramo de monto; cortes de análisis fijados con train. No usar los resultados de prueba para cambiar hiperparámetros. No exigir que el modelo complejo gane.

### Artefactos y exportación para Gerardo

Guardar en `artifacts/models/regression/`:

- `model.joblib`: pipeline/referencia seleccionada, configuración y metadatos de evaluación/variables/versiones. Validar compatibilidad al cargar; no deserializar archivos aportados por usuarios.
- `metrics.json`: copia de consulta vinculada al SHA-256 de `model.joblib`; el servicio verifica coincidencia y no mezcla métricas de otro modelo.
- `predictions.parquet`: row_id, step, partition, type, actual, prediction, model_id, source_sha256, dataset_sha256. Las dos últimas huellas identifican Silver y D1 respectivamente. Exportar todas las filas de validation/test/stress, sin usarlas para reajuste. Actual/prediction finitos y no negativos; un registro por row_id. Esta tabla es la entrada del monitoreo recomendado de Gerardo.
- `examples.json`: muestra determinista de hasta 200 filas de test, semilla 42, con los mismos campos y model_id. No escoger solo aciertos; explicar que son ejemplos, no toda la prueba.

Variable de entorno de servicio: `BANKSHIELD_REGRESSION_MODEL`; las rutas hermanas de métricas/ejemplos se resuelven desde la carpeta de ese artefacto y deben coincidir en identidad.

### Contrato HTTP y página

`POST /api/regression/predict`:

```json
{"type": "TRANSFER", "oldbalanceOrg": 500.0}
```

Respuesta mínima:

```json
{
  "model_id": "<sha256>",
  "target": "amount",
  "prediction": 0.0,
  "selected_model": "<modelo seleccionado>",
  "simulation_data": true,
  "limitations": ["Estimación académica; no constituye una alerta de fraude."]
}
```

El cero del ejemplo es ilustrativo del tipo de dato, no un resultado esperado. No inventar moneda ni intervalos de confianza. Tipo válido, saldo finito no negativo y campos exactos. GET `/api/regression/model` devuelve identidad, variables, selección, particiones, comparación y limitaciones del mismo artefacto. GET `/api/regression/examples?limit=20&offset=0`: limit 1–100, offset >=0, total y filas de `examples.json`, validando model_id. 422 inválido; 503 faltante/incompatible; 200 con página vacía fuera del total.

Página 07: formulario de tipo/saldo; predicción persistente; comparación de candidatos en validation/test claramente diferenciadas; MAE/RMSE y gráfico real vs estimado de ejemplos; advertencias sobre simulación, moneda y stress. Consumir HTTP, sin cargar joblib ni calcular entrenamiento desde Streamlit. Angel integra enlace/portada, no implementa el modelo por Sevan.

### Pruebas y aceptación

- Cambiar amount, bins de monto, etiquetas o campos posteriores sin cambiar type/saldo no cambia la matriz de predictores.
- Train/validation/test/stress disjuntos; muestra determinista solo en train; transformadores no aprenden de validation/test.
- Referencia y métricas contrastadas con cálculos manuales; selección usa validation aunque otro candidato gane en test.
- Serializar/cargar reproduce predicciones; cambiar modelo rompe identidad con métricas/ejemplos antiguos y provoca 503.
- Casos saldo cero, tipo válido sin filas en train, NaN/Infinity, negativos, booleanos como números y campos extra.
- API, paginación y AppTest de predicción/evaluación; el backend puede iniciar sin modelo.
- Corrida real D1 completa, predicciones exportadas y memoria/tiempo registrados; comparación sin cifras inventadas.

Comandos objetivo:

```powershell
.venv-pruebas/Scripts/python.exe scripts/train_regression.py --config configs/regression.json
.venv-pruebas/Scripts/python.exe -m unittest discover -s tests/unit -p "test*regression*.py" -v
```

**Aceptación:** capacidad numérica independiente de clasificación/series, datos sin fuga, evaluación y artefactos coherentes, endpoint y página funcionales. Rhamses revisa contrato/evaluación y Gerardo reproduce. Entregar a Angel casos de uso/errores y a Gerardo CLI/salidas y predicciones.

## SEV-02 — cierre crediticio (P1)

- [ ] Confirmar `loan_status` con fuente original y registrar respaldo, procedencia y condiciones de uso en inventario/contrato. La copia OpenML no sustituye esa confirmación; si no se encuentra, conservar explícita la semántica asumida.
- [ ] Revisar predicción, calibración, umbral y explicaciones por oclusión en API/página con los artefactos ya preparados.
- [ ] Registrar aceptación de evaluación con Gerardo y navegación con Rhamses–Angel. Mantener límites de partición aleatoria, edad y falta de fecha/cliente.
- [ ] No agregar recomendación de monto de crédito: la regresión de este encargo estima transacciones, no una política de préstamos.

## SEV-03 — revisiones y entorno (P1)

- [ ] Revisar minería/evaluación de Cueva, especialmente selección sin test y soporte conjunto.
- [ ] Proporcionar a Gerardo dependencias realmente utilizadas y versiones del artefacto; revisar el conjunto fijado con `pip check`.
- [ ] Reconstruir crédito/regresión desde el clon limpio sin copiar entornos ni modelos y registrar resultados.
- [ ] Revisar, si se implementa GER-02, que las métricas de desempeño pertenezcan al mismo modelo y no se confundieran con deriva de datos.
