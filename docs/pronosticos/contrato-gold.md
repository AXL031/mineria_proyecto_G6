# Contrato de datos Gold temporal — pronósticos

## Propósito

La tabla Gold temporal transforma las transacciones individuales de Silver en
una serie regular con una fila por `step`. En PaySim, un `step` representa una
hora simulada; no corresponde a una fecha calendario.

Esta tabla prepara los objetivos que se evaluarán en el módulo de pronósticos:

- cantidad de transacciones por hora simulada;
- monto total transaccionado por hora simulada.

La construcción de Gold no entrena modelos ni genera predicciones.

## Entrada y salida

- Entrada: `data/silver/transactions/transactions.parquet`.
- Salida: `data/gold/forecast/transactions_hourly.parquet`.
- Configuración: `configs/forecast.json`.
- Comando: `python scripts/build_forecast_gold.py`.
- Reporte JSON: `artifacts/reports/forecast_gold.json`.
- Reporte Markdown: `docs/pronosticos/calidad-gold.md`.

Los archivos de `data/gold/` y `artifacts/` son derivados locales y no se
versionan. Bronze y Silver permanecen sin modificaciones.

## Grano y esquema

Grano: **una fila por `step`**, ordenada de menor a mayor.

| Columna | Tipo | Definición |
| --- | --- | --- |
| `step` | `int64` | Hora discreta de la simulación. |
| `transaction_count` | `int64` | Número de transacciones del step. |
| `total_amount` | `float64` | Suma de `amount` del step. |
| `average_amount` | `float64` | Promedio de `amount` del step. |
| `fraud_count` | `int64` | Número de transacciones con `isFraud = 1`. |
| `fraud_rate` | `float64` | `fraud_count / transaction_count`. |

Si faltara un `step` entre el mínimo y el máximo observado, se incorpora con
actividad cero para mantener una serie de frecuencia regular.

## Reglas y controles

La transformación utiliza únicamente `step`, `amount` e `isFraud` de Silver y
comprueba que:

1. `step` sea entero y no negativo;
2. `amount` sea finito y no negativo;
3. `isFraud` sea binario;
4. exista una sola fila Gold por step;
5. la secuencia de steps sea regular;
6. la cantidad de transacciones se conserve;
7. el monto y el número de fraudes se conserven después de agregar;
8. Gold no contenga valores nulos.

## Uso en pronóstico

Los primeros objetivos serán `transaction_count` y `total_amount`, evaluados
por separado. `fraud_count` y `fraud_rate` se conservan para análisis y
monitoreo, pero no deben utilizarse como información futura para predecir el
volumen del mismo step.

## Limitaciones

- PaySim es una simulación y no representa el tráfico real de un banco.
- Los montos no tienen una moneda identificada.
- La cobertura es de aproximadamente un mes, por lo que los horizontes largos
  tendrán evidencia limitada.
- El tramo final del dataset está compuesto únicamente por operaciones
  fraudulentas y debe separarse del backtesting operativo principal.
