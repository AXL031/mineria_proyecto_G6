# Comparación de Holt-Winters y líneas base

## Resumen

Se evaluaron tres configuraciones Holt-Winters aditivas contra Naive y Naive
estacional. Todos los modelos usaron los mismos objetivos, las mismas cuatro
ventanas expansivas y el horizonte de 24 steps definido previamente. No se usó
ningún dato de los steps 719–743 para ajustar ni seleccionar modelos.

**Resultado:** ninguna configuración Holt-Winters superó a Naive. Se mantiene
Naive como modelo seleccionado para `transaction_count` y `total_amount`. El
modelo ajustado se conserva como comparación metodológica, no como modelo para
servir en la aplicación.

- Experimento: `forecast-holt-winters-v1`.
- Ejecución: 12 de octubre de 2026 (`2026-10-12T21:26:06Z`).
- Entrada: `data/gold/forecast/transactions_hourly.parquet`.
- SHA-256: `1470868861a9bca368c6528655cb3cc33b0beab88889f8f9c8bf65708c58a7f3`.
- Entorno: Python 3.12.14, NumPy 2.5.3, pandas 3.0.6 y statsmodels 0.15.0.
- Reporte local: `artifacts/reports/forecast_holt_winters.json`.

## Configuraciones

Las tres configuraciones usan estacionalidad aditiva de 24 steps e
inicialización estimada. Las predicciones se limitan inferiormente a cero porque
los objetivos son cantidades y montos no negativos.

| Identificador | Nivel | Tendencia | Tendencia amortiguada | Estacionalidad |
| --- | --- | --- | --- | --- |
| `holt_winters_level_seasonal` | Ajustado | Ninguna | No | Aditiva, 24 |
| `holt_winters_additive` | Ajustado | Aditiva | No | Aditiva, 24 |
| `holt_winters_damped` | Ajustado | Aditiva | Sí | Aditiva, 24 |

El ajuste se realiza de nuevo dentro de cada ventana usando solamente su
historial. La implementación rechaza un ajuste que no converge y no reutiliza
parámetros aprendidos con ventanas posteriores.

## MAE por ventana

### Cantidad de transacciones

| Modelo | W01 | W02 | W03 | W04 | Promedio |
| --- | ---: | ---: | ---: | ---: | ---: |
| Naive | **353.08** | **598.42** | 2,426.00 | 2,090.25 | **1,366.94** |
| Naive estacional | 988.62 | 568.08 | **2,192.25** | **2,074.67** | 1,455.91 |
| HW nivel + estacionalidad | 4,572.60 | 4,585.38 | 3,852.25 | 5,686.88 | 4,674.28 |
| HW aditivo | 4,188.31 | 4,282.60 | 3,749.26 | 5,852.72 | 4,518.22 |
| HW aditivo amortiguado | 4,618.32 | 4,377.19 | 3,925.36 | 5,795.74 | 4,679.15 |

### Monto total

| Modelo | W01 | W02 | W03 | W04 | Promedio |
| --- | ---: | ---: | ---: | ---: | ---: |
| Naive | **72,148,651.77** | 162,262,822.07 | **383,708,474.98** | **243,186,816.08** | **215,326,691.23** |
| Naive estacional | 148,943,158.19 | **102,060,814.28** | 389,590,434.68 | 344,542,248.50 | 246,284,163.91 |
| HW nivel + estacionalidad | 832,492,069.38 | 858,785,214.52 | 686,851,598.50 | 1,029,763,911.22 | 851,973,198.40 |
| HW aditivo | 554,013,466.69 | 585,692,491.53 | 441,386,433.83 | 697,588,333.74 | 569,670,181.45 |
| HW aditivo amortiguado | 832,514,169.68 | 919,000,572.87 | 684,003,555.04 | 993,905,906.34 | 857,356,050.98 |

## Métricas agregadas

| Objetivo | Modelo | MAE | RMSE | sMAPE |
| --- | --- | ---: | ---: | ---: |
| Cantidad | Naive | **1,366.94** | **1,815.36** | 128.86 % |
| Cantidad | Naive estacional | 1,455.91 | 2,293.53 | **121.43 %** |
| Cantidad | HW nivel + estacionalidad | 4,674.28 | 6,903.84 | 172.08 % |
| Cantidad | HW aditivo | 4,518.22 | 6,686.28 | 172.33 % |
| Cantidad | HW aditivo amortiguado | 4,679.15 | 6,866.61 | 172.48 % |
| Monto | Naive | **215,326,691.23** | **289,394,248.90** | 140.15 % |
| Monto | Naive estacional | 246,284,163.91 | 398,886,099.36 | **127.74 %** |
| Monto | HW nivel + estacionalidad | 851,973,198.40 | 1,219,633,259.35 | 171.24 % |
| Monto | HW aditivo | 569,670,181.45 | 834,059,022.38 | 173.28 % |
| Monto | HW aditivo amortiguado | 857,356,050.98 | 1,221,793,550.64 | 169.62 % |

## Interpretación y decisión

La serie cambia de nivel y presenta picos muy grandes cerca de las ventanas de
evaluación. Las configuraciones Holt-Winters extrapolaron un nivel y un patrón
estacional demasiado altos para los periodos siguientes. El recorte a cero
evitó resultados imposibles, pero no corrigió el desajuste estructural.

Holt-Winters aditivo fue la mejor de sus tres variantes por MAE, pero aun así su
error fue 3.31 veces el de Naive para cantidad y 2.65 veces para monto. Además,
perdió contra Naive en las cuatro ventanas y en los dos objetivos. No existe una
mejora aislada que justifique adoptarlo.

Se mantiene **Naive** porque gana la métrica principal y el RMSE agregado para
ambos objetivos. Naive estacional continúa siendo una referencia secundaria
útil: consigue menor sMAPE y gana algunas ventanas, pero no el MAE agregado.

Esta decisión no implica que Naive sea preciso en términos absolutos. Los errores
relativos siguen siendo altos. Significa únicamente que, entre los métodos
evaluados con el protocolo acordado, es la opción menos mala y más estable.

## Limitaciones y siguiente paso

- Solo hay cuatro ventanas de 24 steps y 718 observaciones operativas.
- PaySim es una simulación y sus picos/cambios de nivel no representan
  necesariamente una operación bancaria real.
- La estacionalidad de 24 steps tiene autocorrelación, pero no es estable en
  magnitud; Holt-Winters aditivo no logra adaptarse a esos cambios.
- El recorte a cero es una restricción de dominio y debe conservarse si se
  prueban otros modelos numéricos.
- No se estimaron intervalos de predicción.

El siguiente incremento no debe seguir ajustando Holt-Winters sobre las mismas
cuatro ventanas. Corresponde analizar los errores y luego implementar el
monitoreo histórico sobre los steps 719–743. La API y la página pueden usar Naive
como modelo seleccionado y presentar claramente sus limitaciones.

## Reproducción

```powershell
python -m pip install -e ".[forecast]"
python scripts/evaluate_forecast_models.py
```

El primer comando instala statsmodels. El segundo reconstruye el reporte JSON
local desde la configuración versionada y el Gold temporal.
