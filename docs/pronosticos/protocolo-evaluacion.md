# Protocolo de evaluación de pronósticos

## Propósito

Este protocolo define el primer experimento reproducible del módulo de
pronósticos. El objetivo es comparar dos modelos de referencia sobre las mismas
ventanas temporales y determinar cuál pronostica mejor el volumen y el monto de
las transacciones de PaySim.

La configuración versionable del experimento se encuentra en
`configs/forecast.json`, bajo la clave `evaluation`. Este documento explica las
decisiones y las reglas que deberá respetar la implementación.

## Entrada y objetivos

- Entrada Gold: `data/gold/forecast/transactions_hourly.parquet`.
- Grano: una fila por `step`, equivalente a una hora de la simulación PaySim.
- Objetivo principal: `transaction_count`.
- Objetivo secundario: `total_amount`.
- Horizonte de cada evaluación: 24 steps consecutivos.

Cada objetivo se evaluará por separado. Las columnas `fraud_count` y
`fraud_rate` no se utilizarán como predictores de un valor del mismo step.

## Periodos del experimento

Los límites indicados son inclusivos.

| Uso | Steps | Observaciones | Regla |
| --- | ---: | ---: | --- |
| Periodo operativo | 1–718 | 718 | Único periodo permitido para seleccionar la línea base. |
| Tramo reservado para monitoreo | 719–743 | 25 | Excluido del ajuste, backtesting y selección inicial. |

El tramo 719–743 contiene únicamente operaciones fraudulentas y presenta una
reducción marcada de actividad. Se conserva para demostrar posteriormente el
monitoreo de cambios, no para medir el desempeño operativo inicial.

## Modelos de referencia

Se compararán estos modelos sobre exactamente los mismos objetivos y ventanas:

1. **Naive:** para todos los steps del horizonte, repite el último valor
   disponible al finalizar el entrenamiento.
2. **Naive estacional:** para cada step del horizonte, utiliza el valor observado
   24 steps antes. El rezago 24 se justifica por la periodicidad horaria simulada
   y por la autocorrelación observada en la exploración.

La autocorrelación de rezago 24 fue 0.8019 para `transaction_count` y 0.7174
para `total_amount`. Estos valores justifican evaluar el modelo estacional, pero
no demuestran por sí solos que será el ganador.

## Ventanas de backtesting

Se aplicará un esquema de origen expansivo: cada ventana conserva el inicio del
entrenamiento en el step 1 e incorpora más historia. El horizonte de prueba
siempre contiene 24 steps.

| Ventana | Entrenamiento | Evaluación | Tamaño de evaluación |
| --- | ---: | ---: | ---: |
| W01 | 1–622 | 623–646 | 24 |
| W02 | 1–646 | 647–670 | 24 |
| W03 | 1–670 | 671–694 | 24 |
| W04 | 1–694 | 695–718 | 24 |

Para toda ventana debe cumplirse que el último step de entrenamiento sea
estrictamente anterior al primer step de evaluación. No se permite mezclar
aleatoriamente las observaciones ni calcular una predicción pasada con datos de
un step futuro.

## Métricas

### MAE — métrica principal

El error absoluto medio conserva la unidad del objetivo y permite interpretar
el error típico sin elevarlo al cuadrado:

```text
MAE = promedio(|real - pronóstico|)
```

Será el primer criterio de comparación entre modelos.

### RMSE — métrica complementaria

La raíz del error cuadrático medio penaliza en mayor medida los errores grandes:

```text
RMSE = raíz(promedio((real - pronóstico)²))
```

### sMAPE — métrica complementaria relativa

Se utilizará la versión porcentual simétrica:

```text
sMAPE = promedio(200 × |real - pronóstico| / (|real| + |pronóstico|))
```

Cuando el valor real y el pronóstico sean ambos cero, la contribución de esa
observación se definirá como cero para evitar una división indefinida. El
resultado se reportará en porcentaje, con un rango entre 0 y 200.

Las métricas se calcularán por modelo, objetivo y ventana. También se reportará
el promedio de las cuatro ventanas para cada combinación de modelo y objetivo.

## Registro del experimento y artefactos

- Identificador: `forecast-baselines-v1`.
- Configuración: `configs/forecast.json`.
- Reporte estructurado local: `artifacts/reports/forecast_baselines.json`.
- Resultados interpretados y versionados:
  `docs/pronosticos/resultados-baselines.md`.

El reporte JSON deberá incluir, como mínimo, el identificador del experimento,
la entrada utilizada, los objetivos, modelos, ventanas, parámetros, métricas por
ventana y métricas agregadas. La fecha de ejecución y las versiones relevantes
del entorno deberán registrarse al ejecutar el experimento.

La ruta `artifacts/` contiene resultados derivados locales y permanece fuera de
Git. La configuración, el código, las pruebas y la documentación sí se
versionan.

## Criterio para elegir la línea base

Se elegirá una línea base independiente para cada objetivo. Ganará el modelo con
menor MAE promedio siempre que su comportamiento sea estable entre las cuatro
ventanas. RMSE y sMAPE ayudarán a identificar errores extremos o mejoras que
dependan de la escala.

Si las métricas discrepan o la diferencia de MAE es pequeña e inestable, se
documentará el empate práctico en lugar de afirmar una superioridad no
sustentada. La elección no dependerá de que un modelo sea más complejo.

## Alcance y limitaciones

- PaySim contiene transacciones simuladas; los resultados no representan el
  tráfico real de una institución bancaria.
- Los 718 steps operativos cubren aproximadamente un mes simulado, por lo que la
  evidencia sobre ciclos largos es limitada.
- Los montos no tienen una moneda identificada.
- Este primer experimento compara líneas base; todavía no evalúa Holt-Winters ni
  implementa monitoreo en producción.
- El tramo reservado permitirá demostrar detección de cambios históricos, pero
  no sustituye la llegada de lotes futuros para un monitoreo real.
