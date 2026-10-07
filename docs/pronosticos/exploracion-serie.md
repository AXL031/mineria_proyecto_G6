# Exploración de la serie temporal

Análisis generado por `scripts/analyze_forecast_series.py` sobre la tabla Gold.

## Cobertura utilizada

- Serie completa: steps 1–743 (743 observaciones).
- Periodo operativo para explorar patrones: 718 steps.
- Inicio del tramo final solo fraude: step 719.
- Longitud del tramo final: 25 steps.

## Estadísticas del periodo operativo

| Serie | Promedio | Mediana | Desv. estándar | Mínimo | Máximo |
| --- | ---: | ---: | ---: | ---: | ---: |
| Cantidad de transacciones | 8,861.18 | 765.00 | 13,522.90 | 2 | 51,352 |
| Monto total | 1,593,208,888.47 | 94,376,336.32 | 2,696,588,780.42 | 84,837.70 | 24,963,550,343.94 |

## Autocorrelación del periodo operativo

| Rezago | Cantidad | Monto total | Interpretación inicial |
| ---: | ---: | ---: | --- |
| 1 | 0.9228 | 0.8982 | Relación con la hora anterior |
| 24 | 0.8019 | 0.7174 | Posible repetición diaria |
| 168 | 0.4989 | 0.3578 | Posible repetición semanal |

## Gráficos generados

- Cantidad por step: `artifacts\plots\forecast\transaction-count-by-step.png`.
- Monto por step: `artifacts\plots\forecast\total-amount-by-step.png`.
- Ciclo de 24 horas: `artifacts\plots\forecast\simulated-hour-cycle.png`.

## Lectura inicial

- La media móvil de 24 steps permite separar el nivel general de las variaciones horarias.
- La autocorrelación en el rezago 24 indicará si una línea base estacional diaria tiene sentido.
- El tramo final solo fraude se conserva en Gold, pero no se mezcla automáticamente con el periodo operativo para decidir el modelo.
- En el tramo final, la cantidad promedio baja a 11.84 transacciones por step, por lo que debe tratarse como un cambio de comportamiento del simulador.

## Decisiones pendientes

1. Confirmar el periodo de evaluación principal y el horizonte inicial.
2. Comparar Naive con Naive estacional de 24 steps.
3. Mantener el tramo final como caso separado para monitoreo.
