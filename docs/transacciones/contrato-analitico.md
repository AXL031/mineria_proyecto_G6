# Contrato de la tabla analítica compartida (D1)

Este documento describe la tabla que consumen la minería de asociaciones
(CUE-01) y la regresión numérica (SEV-01). Fue construida por Taco y verificada
sobre el Silver transaccional completo. **No reemplaza** al mart de segmentos
(`data/gold/transactions/transactions_mart.parquet`) ni al Gold temporal de
pronósticos: es una tabla derivada, con su propio contrato.

- Propietario: Taco.
- Consumidores: Cueva (asociaciones) y Sevan (regresión).
- Especificación de origen: [encargo TAC-01](../encargos/taco.md) y
  [contrato D1](../pendientes-cierre-2026-10-20.md).

## Comando reproducible

```powershell
.venv-pruebas/Scripts/python.exe scripts/build_analytics_transactions.py --config configs/analytics.json
```

El comando exige el reporte de calidad Silver completo, sin rechazos y con
huellas coincidentes. Cualquier desviación detiene la construcción con un
mensaje accionable y sin publicar un archivo parcial.

## Entradas y salidas

| Elemento | Ruta predeterminada | Notas |
| --- | --- | --- |
| Entrada | `data/silver/transactions/transactions.parquet` | Una fila por transacción; no se modifica. |
| Reporte de calidad exigido | `artifacts/reports/transactions_silver.json` | `scope = complete_file`, 0 rechazos, controles aprobados y `output.sha256` igual al Parquet. |
| Salida | `data/gold/analytics/transactions.parquet` | Snappy, una fila por transacción del Silver. |
| Metadatos del dataset | `artifacts/reports/analytics/dataset.json` | Recuentos, controles y huellas. |
| Metadatos de discretización | `artifacts/reports/analytics/discretization.json` | Bordes, etiquetas y recuentos por bin. |

`data/` y `artifacts/` están excluidos de Git: cada integrante reconstruye D1
con el comando anterior.

## Esquema

| Columna | Tipo | Rol | Uso |
| --- | --- | --- | --- |
| `row_id` | `int64` | Identidad | Posición ordinal base 1 en el Silver de entrada. Nunca es predictor. |
| `step` | `int64` | Contexto | Paso de simulación (1–743). Puede usarse para agrupar o particionar; no como predictor en la regresión. |
| `type` | `string` | Predictor | Uno de `PAYMENT`, `TRANSFER`, `CASH_OUT`, `DEBIT`, `CASH_IN`. |
| `amount` | `float64` | Objetivo / predictor | Monto de la operación. Es el objetivo de la regresión y un predictor del clasificador de fraude. |
| `oldbalanceOrg` | `float64` | Predictor | Saldo del origen antes de la operación. |
| `isFraud` | `int8` | Etiqueta | Solo evaluación y consecuente de asociaciones. Nunca antecedente ni predictor. |
| `partition` | `string` | Metadato | `train`, `validation`, `test` o `stress`. |
| `amount_bin` | `string` | Predictor categórico (asociaciones) | `b0`, `b1` o `b2` según los terciles de `amount` en `train`. **Prohibido** como predictor del monto. |
| `origin_balance_bin` | `string` | Predictor categórico | `b0`, `b1` o `b2` según los terciles de `oldbalanceOrg` en `train`. |

## Particiones

Los cortes son decisiones de este experimento y no modifican las métricas
históricas de fraude.

| Partición | Steps | Filas verificadas | Fraudes |
| --- | --- | ---: | ---: |
| `train` | 1–323 | 4,463,587 | 3,643 |
| `validation` | 324–378 | 980,416 | 564 |
| `test` | 379–718 | 918,321 | 3,710 |
| `stress` | 719–743 | 296 | 296 |

Cada fila pertenece exactamente a una partición. La asignación usa solo `step`:
no se equilibra por clase, no se muestrea y no se inspecciona `isFraud`.

**Diferencia con el clasificador de fraude.** El entrenamiento histórico de
fraude usa `test` 379–743 y reporta 918,617 filas de prueba. Aquí ese tramo se
divide: `test` 379–718 (918,321) y `stress` 719–743 (296). La diferencia de 296
filas corresponde únicamente al tramo final, en el que solo hay fraude. Cualquier
comparación con las métricas históricas debe indicar ese cambio.

`stress` se informa aparte y **no** selecciona modelos, hiperparámetros, bins,
reglas ni umbrales.

## Discretización

1. Los terciles se calculan con `numpy.quantile` (interpolación lineal) sobre los
   valores de `train` únicamente. No hay muestreo oculto.
2. Se conservan solo los cortes estrictamente interiores al rango de `train`
   (`min < corte < max`) y se colapsan los repetidos.
3. Los intervalos son cerrados a la derecha:
   `(-inf, c1]`, `(c1, c2]`, `(c2, +inf)`. El valor `0.0` pertenece a `b0`.
4. Los extremos abiertos se representan como `null` en los metadatos, nunca como
   `Infinity`.
5. Si no quedan cortes interiores, la columna usa un único intervalo `b0`,
   también al aplicarla a las demás particiones.

Bordes verificados en la ejecución completa:

| Columna | Salida | Cortes interiores | Etiquetas |
| --- | --- | --- | --- |
| `amount` | `amount_bin` | 21,649.48 y 157,428.26 | `b0`, `b1`, `b2` |
| `oldbalanceOrg` | `origin_balance_bin` | 28.00 y 51,716.00 | `b0`, `b1`, `b2` |

## Huellas y metadatos

`dataset.json` conserva tres identidades distintas que no deben intercambiarse:

- `source.sha256`: SHA-256 del Parquet Silver de entrada.
- `output.sha256`: SHA-256 del Parquet D1 publicado.
- `discretization.sha256`: huella canónica del esquema de bins (configuración,
  cortes, etiquetas y partición de ajuste), independiente de la fecha.

Además se registran `output.schema_sha256`, el tamaño del archivo, el commit y si
el árbol tenía cambios (`git.tree_dirty`), los recuentos por partición, los
totales de monto y fraude, los conteos por tipo y los controles.

`discretization.json` repite las huellas del dataset y del Silver y añade
`train_min`, `train_max`, `train_rows` y `train_counts` por bin.

## Controles que deben pasar

| Control | Qué verifica |
| --- | --- |
| `silver_contract_approved` | Existe reporte de calidad Silver y se validó. |
| `source_sha256_matches` | El Parquet Silver coincide con su reporte. |
| `one_row_per_silver_row` | Filas de entrada iguales a filas de salida. |
| `row_ids_contiguous` | `row_id` va de 1 a N, sin huecos ni repeticiones. |
| `partitions_cover_all_rows` | La suma de particiones cubre todas las filas. |
| `amount_total_preserved` | La suma de `amount` se conserva (`rtol=1e-12`, `atol=0.01`). |
| `fraud_count_preserved` | El número de fraudes no cambia. |
| `bins_without_nulls` | Ninguna fila queda sin etiqueta de bin. |
| `bins_fitted_on_train_only` | La discretización usó solo `train`. |

Una fila inválida (`step` fuera de 1–743, tipo desconocido, monto o saldo
negativo, etiqueta no binaria o valor ausente) **detiene** la construcción: no se
descarta silenciosamente.

## Resultado verificado (21 de octubre de 2026)

- Silver de entrada: 6,362,620 filas, SHA-256
  `47C786D91FD92D81842BBD83BBA86B5D39FC94F43F9928315884C6E118C2E46C`.
- D1 publicado: 6,362,620 filas, 0 excluidas, 97.9 MiB, SHA-256
  `A4C6F55EC8DBB5351B8F2B6F5B8BE59E8C4C4696FBC4815F22B6CDC1234960EA`.
- Esquema de bins: SHA-256
  `54685F5BDBA5360600B74E4539AB13FB76FAAE2BAD4D062A2CDB60EAB1AD9386`.
- Suma de montos conservada: 1,144,392,944,759.77.
- Fraudes conservados: 8,213.
- Los nueve controles figuran aprobados en `dataset.json`.
- Dos ejecuciones consecutivas con la misma entrada produjeron el mismo SHA-256
  del Parquet y del esquema de bins; la segunda tardó ~21 segundos en este equipo.
- La memoria no se midió con instrumentación: los buffers de cuantiles suman
  ~71 MB (2 columnas × 4,463,587 valores × 8 bytes) más los bloques de 500,000
  filas que se leen por pasada.

## Fixture para desarrollo

Para que otros módulos avancen sin esperar la corrida completa:

```powershell
.venv-pruebas/Scripts/python.exe scripts/build_analytics_transactions.py --write-fixture artifacts/reports/analytics/fixture
```

Genera un Silver mínimo válido, el Parquet D1 y los dos JSON con el esquema
final. El fixture cubre las cuatro particiones y no sustituye a los datos reales
cuando se declara una demostración.

## Pruebas

```powershell
.venv-pruebas/Scripts/python.exe -m unittest discover -s tests/unit -p "test_analytical_transactions.py" -v
```

`tests/unit/test_analytical_transactions.py` cubre bordes 323/324, 378/379 y
718/719, `row_id`, invarianza de bins ante cambios en `test`/`stress`, invarianza
de particiones y bins ante cambios de etiqueta, valores constantes, cortes
repetidos, ceros, valores por encima del máximo de `train`, equivalencia entre
tamaños de bloque y fallo limpio ante reportes o filas inválidas.

## Límites

- Los datos provienen de la simulación PaySim; no representan operaciones reales.
- `step` no es una fecha calendario.
- `row_id` identifica filas y nunca es predictor.
- `amount_bin` describe el monto: está prohibido usarlo para predecir el monto.
- `stress` no se usa para seleccionar nada y se reporta aparte.
- D1 no contiene `nameOrig` ni `nameDest`: no sirve para análisis de redes ni de
  cuentas; para eso están el mart transaccional y los segmentos.
