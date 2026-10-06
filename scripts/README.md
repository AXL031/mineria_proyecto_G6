# Scripts

Comandos reproducibles de ingesta, transformación, entrenamiento y evaluación. Cada comando deberá indicar entradas, salidas y forma de ejecución.

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
