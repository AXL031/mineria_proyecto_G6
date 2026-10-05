# Fuente y diccionario de datos — PaySim

## Resumen

La fuente transaccional queda identificada como la muestra pública de **PaySim** distribuida en Kaggle.

## Referencias

- Publicación de referencia: [Synthetic Financial Datasets For Fraud Detection](https://www.kaggle.com/datasets/ealaxi/paysim1).
- Proyecto de los autores: [EdgarLopezPhD/PaySim](https://github.com/EdgarLopezPhD/PaySim).
- Artículo: E. A. Lopez-Rojas, A. Elmir y S. Axelsson, [PaySim: A Financial Mobile Money Simulator for Fraud Detection](https://www.msc-les.org/proceedings/emss/2016/EMSS2016_249.pdf), EMSS 2016.
- Licencia indicada por la publicación de Kaggle: CC BY-SA 4.0.

## Identificación de la copia local

| Propiedad | Valor |
| --- | --- |
| Archivo | `data/bronze/transactions/PS_20174392719_1491204439457_log.csv` |
| Formato | CSV delimitado por comas |
| Tamaño | 493,534,783 bytes |
| Filas de datos | 6,362,620 |
| Columnas | 11 |
| Versión de referencia en Kaggle | 2 |
| SHA-256 | `16910F90577B0D981BF8FF289714510BB89BC71BFF7D3F220F024E287E4EEA6B` |

## Qué representa

PaySim es un simulador de transacciones de dinero móvil. Genera datos sintéticos usando propiedades estadísticas obtenidas de registros transaccionales agregados. Las filas publicadas no corresponden a operaciones de clientes reales.

La simulación incluye cinco tipos de transacción:

| Tipo | Significado |
| --- | --- |
| `CASH_IN` | Ingreso de efectivo mediante un agente o comercio, que aumenta el saldo de la cuenta. |
| `CASH_OUT` | Retiro de efectivo mediante un agente o comercio, que reduce el saldo de la cuenta. |
| `DEBIT` | Envío de dinero desde el servicio móvil hacia una cuenta bancaria. |
| `PAYMENT` | Pago de bienes o servicios a un comercio. |
| `TRANSFER` | Envío de dinero a otro usuario del servicio. |

## Cobertura temporal

`step` es el reloj discreto de la simulación. **Un `step` equivale a una hora simulada** y varias transacciones pueden compartir el mismo valor. La copia local contiene 743 valores consecutivos, desde 1 hasta 743, equivalentes aproximadamente a un mes simulado.

`step` no es un identificador de transacción ni una fecha real. El archivo no proporciona año, mes calendario, zona horaria o fecha de inicio. Por ello, el módulo puede pronosticar la próxima hora simulada, pero no debe presentar el resultado como una fecha real.

## Diccionario de las 11 columnas

| Columna | Tipo esperado | Unidad o dominio | Descripción | Uso inicial en pronóstico |
| --- | --- | --- | --- | --- |
| `step` | Entero | 1 a 743 en la copia local | Hora de la simulación. Un step equivale a una hora simulada. | Esencial: orden y grano temporal. |
| `type` | Categoría | `CASH_IN`, `CASH_OUT`, `DEBIT`, `PAYMENT`, `TRANSFER` | Tipo de transacción de dinero móvil. | Esencial para conteos y montos por tipo. |
| `amount` | Decimal | Unidad monetaria local no especificada | Monto de la transacción. | Esencial para monto total, promedio y distribución. |
| `nameOrig` | Texto | Identificador con prefijo `C` | Cuenta o cliente que inicia la transacción. | No necesario para el primer pronóstico agregado; útil para segmentación y grafos. |
| `oldbalanceOrg` | Decimal | Unidad monetaria local no especificada | Saldo del origen antes de la transacción. | No necesario para la primera serie agregada. |
| `newbalanceOrig` | Decimal | Unidad monetaria local no especificada | Saldo del origen después de la transacción. | No necesario para la primera serie agregada. |
| `nameDest` | Texto | Identificador con prefijo `C` o `M` | Cuenta o comercio que recibe la transacción. `C` identifica cuentas de clientes y `M` comercios. | No necesario para el primer pronóstico; útil para grafos y segmentación. |
| `oldbalanceDest` | Decimal | Unidad monetaria local no especificada | Saldo del destino antes de la transacción. | No necesario para la primera serie agregada. |
| `newbalanceDest` | Decimal | Unidad monetaria local no especificada | Saldo del destino después de la transacción. | No necesario para la primera serie agregada. |
| `isFraud` | Entero binario | 0 o 1 | Etiqueta generada por la simulación: 1 indica una transacción fraudulenta. | Útil para agregar cantidad y proporción de fraude por step; no es el objetivo principal del pronóstico. |
| `isFlaggedFraud` | Entero binario | 0 o 1 | Resultado de una regla preexistente que intenta señalar transferencias de gran monto. No equivale a la etiqueta real `isFraud`. | No usar como variable objetivo del pronóstico. Puede documentarse como señal auxiliar. |

## Comprobaciones observadas en la copia local

| Comprobación | Resultado |
| --- | ---: |
| Filas | 6,362,620 |
| Valores nulos | 0 en las 11 columnas |
| Steps distintos | 743 |
| Step mínimo / máximo | 1 / 743 |
| Monto mínimo / máximo | 0 / 92,445,516.64 |
| Transacciones `CASH_OUT` | 2,237,500 |
| Transacciones `PAYMENT` | 2,151,495 |
| Transacciones `CASH_IN` | 1,399,284 |
| Transacciones `TRANSFER` | 532,909 |
| Transacciones `DEBIT` | 41,432 |
| Transacciones con `isFraud = 1` | 8,213 |
| Transacciones con `isFlaggedFraud = 1` | 16 |

Estas comprobaciones describen la copia actual. El perfilado reproducible y las reglas de validación se desarrollarán por separado.

## Columnas mínimas para el módulo de Gerardo

La primera tabla temporal puede construirse con:

```text
step, type, amount, isFraud
```

La tabla Gold de pronóstico deberá tener una fila por `step` y, como mínimo:

```text
step
transaction_count
total_amount
average_amount
fraud_count
fraud_rate
```

También puede incorporar cantidades y montos separados por `type`.

## Limitaciones para el módulo

- Los datos son sintéticos y no demuestran desempeño en una institución real.
- El monto está expresado en una unidad monetaria no identificada; no debe mostrarse como soles o dólares.
- La cobertura es aproximadamente un mes, suficiente para experimentos horarios pero limitada para pronósticos diarios o semanales largos.
- La fuente permite pronosticar volumen transaccional simulado, no liquidez bancaria.
- La ausencia de fechas reales impide asociar los steps con feriados, días de semana o eventos de calendario observados.
