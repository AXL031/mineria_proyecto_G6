# Scripts

Comandos reproducibles de ingesta, transformación, entrenamiento y evaluación. Cada comando deberá indicar entradas, salidas y forma de ejecución.

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
