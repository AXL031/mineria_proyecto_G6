# Contrato de datos Silver — Taco

## Alcance de esta entrega

`scripts/build_silver.py` convierte el CSV de Bronze en un Parquet tipado en
`data/silver/transactions/transactions.parquet` (compresión snappy), con
controles de calidad y un reporte que registra recuentos antes y después.
Bronze permanece intacto; la transformación se ejecuta solo con código
reproducible.

- Reporte de la ejecución completa: [calidad-silver.md](calidad-silver.md)
  (JSON en `artifacts/reports/transactions_silver.json`).
- Inventario y huella de la fuente: [datasets.md](../datasets.md).

## Esquema de salida

Grano: **una fila por transacción**, mismas 11 columnas de Bronze, en su orden
original.

| Columna | Tipo Parquet | Regla de validación |
| --- | --- | --- |
| `step` | `int64` | Entero no negativo. No es una fecha calendario. |
| `type` | `string` | Pertenece a `PAYMENT`, `TRANSFER`, `CASH_OUT`, `DEBIT`, `CASH_IN`. |
| `amount` | `float64` | Finito y no negativo. |
| `nameOrig` | `string` | No nulo ni vacío. |
| `oldbalanceOrg` | `float64` | Finito y no negativo. |
| `newbalanceOrig` | `float64` | Finito y no negativo. |
| `nameDest` | `string` | No nulo ni vacío. |
| `oldbalanceDest` | `float64` | Finito y no negativo. |
| `newbalanceDest` | `float64` | Finito y no negativo. |
| `isFraud` | `int8` | Binario (0/1). Etiqueta; queda fuera de los predictores. |
| `isFlaggedFraud` | `int8` | Binario (0/1). Solo auditoría hasta verificar su origen. |

El reporte registra, además de los recuentos, la huella SHA-256 del Parquet
(`output.sha256`) y la del CSV de origen (`source.sha256`), de modo que
cualquier consumidor pueda vincular el Parquet regenerado con el reporte y con
la fuente.

## Controles aplicados

1. Cabecera exacta del esquema PaySim y descarte de referencias Git LFS.
2. Verificación de la huella SHA-256 del CSV contra la registrada en el
   inventario; si no coincide, la construcción se detiene.
3. Por fila: nulos o vacíos, tipos numéricos finitos, montos no negativos,
   `step` entero, etiquetas binarias y `type` conocido.
4. Recuentos de filas de Bronze, filas de Silver y rechazos **por causa**
   (`missing:*`, `invalid:*`, `negative:*`) en el reporte.
5. Duplicados exactos medidos con hash de 64 bits sobre las 11 columnas.
6. Cuentas únicas origen/destino y cuantiles de `amount` (p25–p99.9).
7. Cobertura de `step`: mínimo, máximo, distintos y ausentes.

Las filas rechazadas se **excluyen de Silver** y quedan registradas; nunca se
corrigen ni eliminan desde Bronze.

## Integración con fraude (dupla Cueva–Taco)

`train_fraud(..., input_format="silver")` consume este Parquet y exige, antes
de entrenar, que el reporte cumpla el contrato:

| Requisito | Campo verificado | Valor en la ejecución completa |
| --- | --- | --- |
| Alcance completo | `scope == "complete_file"` | `complete_file` |
| Sin rechazos | `counts.rejected_rows == 0` | `0` |
| Recuentos conservados | `counts.bronze_rows == counts.silver_rows == filas del perfil` | `6,362,620` |
| Controles aprobados | `quality_checks` incluye `expected_header`, `source_sha256_matches`, `no_rejected_rows`, `no_exact_duplicate_rows`, `steps_are_contiguous`, todos en `True` | todos `True` |
| Fuente de Bronze | `source.sha256` == huella del perfil de fraude | `16910F90…EA6B` |
| Parquet vigente | `output.sha256` == huella del archivo leído | `47C786D9…E46C` |

La ejecución completa reproducida en `train_fraud` desde Silver (AP 0.961840,
precisión 0.796634, recall 0.992511) es la evidencia del lado de fraude.
Revisión verificada desde el lado transaccional contra la implementación; la
confirmación explícita de Axel (Cueva) queda pendiente para cerrar el punto
1 de prioridades del plan.

## Decisiones acordadas

- **Duplicados:** se conservan (`policy: kept`) porque la fuente no tiene
  identificador de transacción. El control `no_exact_duplicate_rows` se aprueba
  porque la ejecución completa no detecta duplicados exactos (0 filas); si en
  el futuro aparecieran, el entrenamiento desde Silver se detendría y habría que
  revisar la política antes de continuar.
- **Etiquetas en Silver:** `isFraud` e `isFlaggedFraud` se mantienen para
  evaluación; la lista de predictores la gobierna el
  [contrato de variables de fraude](../fraude/contrato-variables.md).
- Los controles no corrigen valores extremos de monto: se reportan y se
  conservan hasta decidir si son errores o resultados válidos de la simulación.

## Reproducción

```powershell
# Entorno común del equipo (Python 3.12) + suite completa:
powershell -ExecutionPolicy Bypass -File scripts/setup_env.ps1

.venv-pruebas/Scripts/python.exe scripts/build_silver.py --limit 100000   # muestra de verificación
.venv-pruebas/Scripts/python.exe scripts/build_silver.py                  # dataset completo
.venv-pruebas/Scripts/python.exe -m unittest discover -s tests/unit -p "test_silver*.py" -v
```

La ejecución completa espera 6,362,620 filas y la huella registrada en
`configs/transactions.json`. `--limit` marca el informe como
`first_rows_sample`; un informe de muestra no se presenta como evaluación del
dataset completo.

## Límites

- PaySim es una simulación: `step` no es fecha calendario y los resultados no
  representan operaciones bancarias reales.
- `data/silver/` queda fuera de Git; cada integrante regenera el Parquet con
  el comando anterior.
- Esta entrega cubre Bronze → Silver. El mart analítico en Gold y la
  segmentación son las siguientes entregas del módulo.
