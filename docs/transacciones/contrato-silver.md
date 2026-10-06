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

## Decisiones pendientes de revisión en dupla

- **Duplicados:** se conservan (`policy: kept`) porque la fuente no tiene
  identificador de transacción; hay que acordar con Axel (Cueva) si alguna
  métrica de su entrenamiento los trata distinto.
- **Etiquetas en Silver:** `isFraud` e `isFlaggedFraud` se mantienen para
  evaluación; la lista de predictores la gobierna el
  [contrato de variables de fraude](../fraude/contrato-variables.md).
- Los controles no corrigen valores extremos de monto: se reportan y se
  conservan hasta decidir si son errores o resultados válidos de la simulación.

## Reproducción

```powershell
python -m pip install -r requirements/transactions.txt
python scripts/build_silver.py --limit 100000   # muestra de verificación
python scripts/build_silver.py                  # dataset completo
python -m unittest discover -s tests/unit -p "test_silver*.py" -v
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
