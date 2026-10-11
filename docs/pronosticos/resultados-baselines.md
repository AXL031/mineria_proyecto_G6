# Resultados de las líneas base de pronóstico

## Resumen del experimento

Se compararon los modelos Naive y Naive estacional con rezago 24 sobre los
steps operativos 1–718 de la serie Gold temporal. Ambos modelos utilizaron las
mismas cuatro ventanas de backtesting y un horizonte de 24 steps.

- Identificador: `forecast-baselines-v1`.
- Ejecución: 10 de octubre de 2026 (`2026-10-10T05:27:37Z`).
- Entrada: `data/gold/forecast/transactions_hourly.parquet`.
- SHA-256 de la entrada:
  `1470868861a9bca368c6528655cb3cc33b0beab88889f8f9c8bf65708c58a7f3`.
- Entorno: Python 3.12.14, NumPy 2.5.3 y pandas 3.0.6.
- Reporte local: `artifacts/reports/forecast_baselines.json`.

Los steps 719–743 permanecieron fuera del ajuste y de la evaluación. El
reporte confirma que la última ventana termina en el step 718.

## Resultados por ventana

MAE y RMSE conservan la unidad de cada objetivo. sMAPE se expresa como
porcentaje y puede tomar valores entre 0 y 200.

| Ventana | Evaluación | Objetivo | Modelo | MAE | RMSE | sMAPE |
| --- | --- | --- | --- | ---: | ---: | ---: |
| W01 | 623–646 | Cantidad | Naive | 353.08 | 909.33 | 110.21 % |
| W01 | 623–646 | Cantidad | Naive estacional | 988.62 | 1,456.42 | 133.37 % |
| W01 | 623–646 | Monto | Naive | 72,148,651.77 | 153,230,425.64 | 149.87 % |
| W01 | 623–646 | Monto | Naive estacional | 148,943,158.19 | 223,352,277.46 | 141.59 % |
| W02 | 647–670 | Cantidad | Naive | 598.42 | 1,296.77 | 112.33 % |
| W02 | 647–670 | Cantidad | Naive estacional | 568.08 | 1,006.86 | 105.86 % |
| W02 | 647–670 | Monto | Naive | 162,262,822.07 | 243,923,403.05 | 143.27 % |
| W02 | 647–670 | Monto | Naive estacional | 102,060,814.28 | 211,018,425.21 | 115.17 % |
| W03 | 671–694 | Cantidad | Naive | 2,426.00 | 2,794.24 | 145.12 % |
| W03 | 671–694 | Cantidad | Naive estacional | 2,192.25 | 3,457.36 | 119.00 % |
| W03 | 671–694 | Monto | Naive | 383,708,474.98 | 495,807,728.64 | 132.88 % |
| W03 | 671–694 | Monto | Naive estacional | 389,590,434.68 | 605,591,722.28 | 129.84 % |
| W04 | 695–718 | Cantidad | Naive | 2,090.25 | 2,261.09 | 147.80 % |
| W04 | 695–718 | Cantidad | Naive estacional | 2,074.67 | 3,253.49 | 127.50 % |
| W04 | 695–718 | Monto | Naive | 243,186,816.08 | 264,615,438.24 | 134.57 % |
| W04 | 695–718 | Monto | Naive estacional | 344,542,248.50 | 555,581,972.50 | 124.34 % |

## Resultados agregados

Los valores siguientes son el promedio de las cuatro ventanas, todas con el
mismo tamaño.

| Objetivo | Modelo | MAE promedio | RMSE promedio | sMAPE promedio |
| --- | --- | ---: | ---: | ---: |
| Cantidad | Naive | **1,366.94** | **1,815.36** | 128.86 % |
| Cantidad | Naive estacional | 1,455.91 | 2,293.53 | **121.43 %** |
| Monto | Naive | **215,326,691.23** | **289,394,248.90** | 140.15 % |
| Monto | Naive estacional | 246,284,163.91 | 398,886,099.36 | **127.74 %** |

## Elección de la línea base

### Cantidad de transacciones

Se selecciona **Naive como referencia formal** porque obtiene el menor MAE
promedio, la métrica principal definida antes de ejecutar el experimento, y un
RMSE promedio menor. Su MAE es aproximadamente 6.1 % menor que el de Naive
estacional.

La decisión no demuestra una superioridad estable. Naive estacional obtiene un
MAE menor en W02, W03 y W04, aunque por márgenes pequeños, y también consigue un
sMAPE promedio menor. La ventaja agregada de Naive depende en gran medida de
W01. Por ello, para cantidad ambos modelos deben considerarse competitivos y la
selección de Naive debe interpretarse como una referencia conservadora, no como
un ganador concluyente.

### Monto total

Se selecciona **Naive**. Obtiene menor MAE en tres de las cuatro ventanas, un
MAE promedio aproximadamente 12.6 % menor y un RMSE promedio aproximadamente
27.4 % menor que Naive estacional. La evidencia es más consistente que para la
cantidad.

Naive estacional presenta menor sMAPE promedio. Esta diferencia indica que su
error relativo es más favorable en algunos periodos, pero no compensa sus
errores absolutos grandes bajo la métrica principal ni su RMSE más alto.

## Utilidad del patrón de 24 steps

La autocorrelación observada en el rezago 24 justificó probar la línea base
estacional, pero no produjo una mejora consistente. Fue útil en W02 para ambos
objetivos y fue competitivo para la cantidad en las ventanas posteriores. Sin
embargo, perdió en el MAE agregado y produjo errores grandes que elevaron el
RMSE, especialmente para el monto.

La autocorrelación mide asociación histórica; no garantiza por sí sola que el
nivel del ciclo anterior sea un buen pronóstico cuando cambia la escala o la
volatilidad de la serie.

## Decisión sobre Holt-Winters

Se justifica continuar con Holt-Winters y compararlo contra Naive usando las
mismas cuatro ventanas. Los errores relativos son altos para ambas líneas base
y el desempeño empeora en las últimas ventanas, lo que deja espacio para un
modelo que represente nivel, tendencia y estacionalidad de manera ajustada.

Holt-Winters solo deberá adoptarse si reduce los errores fuera de muestra de
forma suficientemente estable. No se elegirá únicamente por ser un modelo más
complejo. Para cantidad también deberá compararse cuidadosamente con Naive
estacional debido a su competitividad en tres ventanas.

## Limitaciones

- PaySim es una simulación y no representa el tráfico de un banco real.
- La serie operativa contiene solo 718 steps, aproximadamente un mes simulado.
- Los montos no tienen una moneda identificada.
- El promedio de cuatro ventanas resume poca evidencia y puede estar dominado
  por una ventana con un error grande.
- Los valores altos de sMAPE reflejan cambios de escala y periodos con actividad
  baja; deben leerse junto con MAE y RMSE.
- El tramo 719–743 fue reservado para monitoreo y estos resultados no describen
  el comportamiento de ese tramo anómalo.
- Este experimento compara reglas de referencia; todavía no estima intervalos
  de predicción ni evalúa un modelo ajustado.

## Reproducción

Desde un entorno con las dependencias del extra `forecast` instaladas:

```powershell
python scripts/evaluate_forecast_baselines.py
```

El comando lee las ventanas y parámetros desde `configs/forecast.json` y
regenera `artifacts/reports/forecast_baselines.json`.
