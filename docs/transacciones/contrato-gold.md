# Contrato de datos Gold — mart transaccional

## Propósito

El mart transaccional transforma cada transacción de Silver en una fila
analítica lista para consumo y para la segmentación. **No agrega por `step`**:
la serie horaria por `step` es el
[Gold temporal de pronósticos](../pronosticos/contrato-gold.md), un módulo
distinto. La construcción no entrena modelos ni genera predicciones.

## Entrada y salida

- Entrada: `data/silver/transactions/transactions.parquet`.
- Salida: `data/gold/transactions/transactions_mart.parquet`.
- Configuración: `configs/transactions_gold.json`.
- Comando: `python scripts/build_gold_transactions.py`.
- Reporte JSON: `artifacts/reports/transactions_gold.json`.
- Reporte Markdown: `docs/transacciones/calidad-gold.md`.

`data/gold/` y `artifacts/` son derivados locales y no se versionan. Bronze y
Silver permanecen sin modificaciones.

## Grano y esquema

Grano: **una fila por transacción**, en el mismo orden que Silver.

| Columna | Tipo | Rol | Definición |
| --- | --- | --- | --- |
| `step` | `int64` | clave | Hora simulada de la operación. |
| `nameOrig` | `string` | clave | Cuenta origen. |
| `nameDest` | `string` | clave | Cuenta destino (incluye comercios `M…`). |
| `type` | `string` | predictor | `PAYMENT`, `TRANSFER`, `CASH_OUT`, `DEBIT`, `CASH_IN`. |
| `amount` | `float64` | predictor | Monto de la operación. |
| `oldbalanceOrg` | `float64` | predictor | Saldo del origen antes de la operación. |
| `amount_to_origin_balance` | `float64` | predictor | `amount / (oldbalanceOrg + 1)`. |
| `exceeds_origin_balance` | `int8` | predictor | `1` si `amount > oldbalanceOrg`. |
| `origin_balance_delta` | `float64` | descriptivo | `newbalanceOrig − (oldbalanceOrg − amount)`. |
| `destination_balance_delta` | `float64` | descriptivo | `newbalanceDest − (oldbalanceDest + amount)`. |
| `isFraud` | `int8` | etiqueta | Etiqueta de fraude (0/1); nunca predictor. |
| `isFlaggedFraud` | `int8` | etiqueta | Marca de auditoría (0/1); nunca predictor. |

### Predictores y descriptivos

La lista de predictores la gobierna el
[contrato de variables de fraude](../fraude/contrato-variables.md): el mart
reutiliza `build_fraud_feature_frame`, de modo que **no duplica** esa lista. Los
residuos de balance (`*_balance_delta`) usan saldos posteriores a la operación y
se marcan como descriptivos: sirven para auditar la consistencia contable de la
simulación, no como variables disponibles al momento de predecir.

## Reglas y controles

La transformación lee el Parquet Silver en bloques y comprueba que:

1. existan las 11 columnas de Silver y ninguna contenga valores ausentes;
2. `step` sea entero no negativo y los saldos finitos y no negativos;
3. `isFraud` e `isFlaggedFraud` sean binarios y `type` sea un tipo conocido;
4. el número de filas de entrada y de salida coincida (relación 1:1);
5. la suma de `amount` se conserve;
6. los recuentos de `isFraud` y `isFlaggedFraud` se conserven;
7. los predictores del contrato de fraude estén presentes.

La escritura es atómica (`.tmp` y reemplazo) y el reporte registra la huella
SHA-256 de Silver (`source.sha256`) y del mart (`output.sha256`).

## Uso en segmentación

El mart es la base de la segmentación de cuentas de destino reincidentes: las
columnas de identidad (`nameDest`, `nameOrig`, `step`) permiten agregar
comportamiento por cuenta y los predictores y residuos aportan señales de monto
y consistencia. La construcción de la segmentación es la siguiente entrega del
módulo.

## Limitaciones

- PaySim es una simulación: `step` no es una fecha calendario y los montos no
  tienen una moneda identificada.
- Existen residuos de balance distintos de cero en gran parte de las filas
  (inconsistencias conocidas de la simulación); se conservan y se cuantifican en
  el reporte, sin corregirlos.
- El mart pesa más que Silver por incorporar columnas derivadas; se regenera
  localmente con el comando anterior.
