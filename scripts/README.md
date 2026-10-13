# Scripts

Comandos reproducibles de ingesta, transformación, entrenamiento y evaluación. Cada comando deberá indicar entradas, salidas y forma de ejecución.

## Entrega completa de fraude

`powershell -ExecutionPolicy Bypass -File scripts/reproduce_fraud.ps1` prepara el entorno y reconstruye perfil, Silver, modelo, errores, asociaciones y comprobación HTTP/página. Guarda una ejecución separada en `artifacts/reports/fraud-reproduction/`. Ver [alcance, evidencia y demostración](../docs/fraude/cierre-entrega.md).

`analyze_fraud_patterns.py` analiza seis reglas descriptivas predefinidas, por partición temporal, sobre el Silver exacto registrado en el modelo. `verify_fraud_delivery.py --model ruta/model.joblib` comprueba predicciones, métricas y patrones en la página contra una API HTTP temporal y los errores de modelo ausente/conexión. Ninguno cambia el umbral ni entrena el clasificador.

## Construcción de Silver transaccional

`build_silver.py` lee el CSV PaySim de Bronze en bloques, aplica los controles
de calidad del [contrato Silver](../docs/transacciones/contrato-silver.md) y
escribe el Parquet tipado en Silver, sin modificar el original.

```powershell
python -m pip install -r requirements/transactions.txt
python scripts/build_silver.py
```

Entradas y salidas predeterminadas (definidas en `configs/transactions.json`):

- Entrada: `data/bronze/transactions/PS_20174392719_1491204439457_log.csv`.
- Parquet generado: `data/silver/transactions/transactions.parquet`.
- Reporte JSON: `artifacts/reports/transactions_silver.json`.
- Resumen generado: `docs/transacciones/calidad-silver.md`.

La ejecución completa espera la huella SHA-256 del inventario y 6,362,620
filas. Para una verificación rápida sobre una muestra:

```powershell
python scripts/build_silver.py --limit 100000
```

Ese informe se identifica como `first_rows_sample`. Opciones adicionales en
`python scripts/build_silver.py --help`.

## Perfilado transaccional

`profile_transactions.py` revisa el CSV PaySim por bloques y genera un reporte
JSON junto con un resumen Markdown, sin modificar Bronze.

```powershell
python -m pip install -r requirements/forecast.txt
python scripts/profile_transactions.py
```

Entradas y salidas predeterminadas:

- Entrada: `data/bronze/transactions/PS_20174392719_1491204439457_log.csv`.
- JSON generado: `artifacts/reports/transactions_profile.json`.
- Resumen generado: `docs/pronosticos/calidad-paysim.md`.

El tamaño de bloque se puede ajustar:

```powershell
python scripts/profile_transactions.py --chunksize 250000
```

## Construcción de Gold temporal

`build_forecast_gold.py` consume el Parquet Silver y genera una serie regular
con una fila por `step`, sin modificar las capas de entrada.

```powershell
python -m pip install -e ".[forecast]"
python scripts/build_forecast_gold.py
```

Entradas y salidas predeterminadas (definidas en `configs/forecast.json`):

- Entrada: `data/silver/transactions/transactions.parquet`.
- Gold: `data/gold/forecast/transactions_hourly.parquet`.
- Reporte JSON: `artifacts/reports/forecast_gold.json`.
- Resumen: `docs/pronosticos/calidad-gold.md`.

El esquema, las fórmulas y los controles se describen en el
[contrato Gold temporal](../docs/pronosticos/contrato-gold.md).

## Construcción del mart transaccional Gold

`build_gold_transactions.py` consume el Parquet Silver y genera el mart
analítico con una fila por transacción, sin modificar las capas de entrada. Es
distinto del Gold temporal: no agrega por `step`.

```powershell
.venv-pruebas/Scripts/python.exe scripts/build_gold_transactions.py
```

Entradas y salidas predeterminadas (definidas en `configs/transactions_gold.json`):

- Entrada: `data/silver/transactions/transactions.parquet`.
- Gold: `data/gold/transactions/transactions_mart.parquet`.
- Reporte JSON: `artifacts/reports/transactions_gold.json`.
- Resumen: `docs/transacciones/calidad-gold.md`.

El esquema, los roles de columna y los controles se describen en el
[contrato del mart transaccional](../docs/transacciones/contrato-gold.md).

## Segmentación de cuentas destino

`segment_transactions.py` consume el mart transaccional Gold y agrupa cuentas
reincidentes (>= 10 transacciones recibidas) con KMeans sobre variables de
comportamiento, comparado con una línea base por cuantiles de actividad. El
agrupamiento **no usa la etiqueta de fraude**; `fraud_rate` solo perfila el
segmento ya formado.

```powershell
.venv-pruebas/Scripts/python.exe scripts/segment_transactions.py
```

Entradas y salidas predeterminadas (definidas en `configs/segments.json`):

- Entrada: `data/gold/transactions/transactions_mart.parquet`.
- Salida: `data/gold/segments/account_segments.parquet`.
- Reporte JSON: `artifacts/reports/segments.json`.
- Resumen: `docs/transacciones/segmentacion.md`.

Los límites están en el [reporte de segmentación](../docs/transacciones/segmentacion.md).
La API expone `GET /api/segments/summary` y
`GET /api/segments/{segmento}/accounts` para la página de segmentos.

## Exploración de la serie temporal

`analyze_forecast_series.py` calcula estadísticas del periodo operativo,
autocorrelaciones y gráficos de cantidad, monto y ciclo simulado de 24 horas.

```powershell
python -m pip install -e ".[forecast]"
python scripts/analyze_forecast_series.py
```

El reporte se escribe en `docs/pronosticos/exploracion-serie.md`; los gráficos
y el JSON reproducible permanecen localmente dentro de `artifacts/`.

## Evaluación de líneas base de pronóstico

`evaluate_forecast_baselines.py` compara Naive y Naive estacional sobre las
cuatro ventanas temporales definidas en `configs/forecast.json`. Ambos modelos
usan exactamente los mismos periodos y se evalúan con MAE, RMSE y sMAPE para
cantidad de transacciones y monto total.

```powershell
python -m pip install -e ".[forecast]"
python scripts/evaluate_forecast_baselines.py
```

La entrada predeterminada es
`data/gold/forecast/transactions_hourly.parquet`. El reporte reproducible se
guarda en `artifacts/reports/forecast_baselines.json` y permanece fuera de Git.
La definición completa del experimento se encuentra en
`docs/pronosticos/protocolo-evaluacion.md`.

## Pipeline de crédito

Los tres scripts usan los valores predeterminados de `configs/credit.json` y no modifican Bronze.

```powershell
.venv-pruebas/Scripts/python.exe scripts/profile_credit.py
.venv-pruebas/Scripts/python.exe scripts/build_silver_credit.py
.venv-pruebas/Scripts/python.exe scripts/train_credit.py
```

- `profile_credit.py`: lee `data/bronze/credit/credit_risk_dataset.csv`; escribe `artifacts/reports/credit/credit_profile.json` y `docs/credito/perfil-credito.md`.
- `build_silver_credit.py`: rechaza valores imposibles, elimina duplicados exactos y recalcula `loan_percent_income`; escribe `data/silver/credit/credit.parquet`, `artifacts/reports/credit/silver_quality.json` y `docs/credito/calidad-silver.md`.
- `train_credit.py`: verifica el Parquet contra su reporte, entrena, calibra, elige el umbral en validación y evalúa la prueba una sola vez; escribe `artifacts/models/credit/` y `docs/credito/resultados-modelo.md`.

El esquema y las decisiones están en el [contrato de variables](../docs/credito/contrato-variables.md).

## Pipeline de reclamos

Los dos scripts no modifican Bronze y usan rutas predeterminadas.

```powershell
.venv-pruebas/Scripts/python.exe scripts/profile_complaints.py
.venv-pruebas/Scripts/python.exe scripts/build_silver_complaints.py
```

- `profile_complaints.py`: lee `data/bronze/complaints/consumer_complaints.csv`; escribe `artifacts/reports/complaints/complaints_profile.json` y `docs/reclamos/perfil-complaints.md`. Interpreta las fechas antes de calcular el rango.
- `build_silver_complaints.py`: rechaza filas sin identificador, fecha o producto válidos, conserva el primer `complaint_id` repetido y sustituye la censura de las narrativas por marcadores; escribe `data/silver/complaints/complaints.parquet`, `artifacts/reports/complaints/silver_quality.json` y `docs/reclamos/calidad-silver.md`. Termina con error si falla algún control de calidad.

El esquema y las decisiones están en el [contrato Silver de reclamos](../docs/reclamos/contrato-silver.md).

Clasificador de producto y revisión de ejemplos (usan `configs/complaints.json` y requieren el Silver y su reporte de calidad):

```powershell
.venv-pruebas/Scripts/python.exe scripts/train_complaints.py
.venv-pruebas/Scripts/python.exe scripts/analyze_complaints_errors.py
```

- `train_complaints.py`: verifica el Parquet contra su reporte, parte cronológicamente, entrena la referencia trivial, Naive Bayes y TF-IDF con regresión logística, elige C en validación y evalúa la prueba una vez; escribe `artifacts/models/complaints/` y `docs/reclamos/resultados-modelo.md`. Tarda unos 2.5 minutos.
- `analyze_complaints_errors.py`: reconstruye la partición de prueba del modelo guardado y extrae pares confundidos, errores de mayor confianza y casi-duplicados; escribe `artifacts/reports/complaints/error_examples.json` y `docs/reclamos/revision-ejemplos.md`. Conserva el texto escrito a mano bajo el marcador `<!-- OBSERVACIONES -->`.
