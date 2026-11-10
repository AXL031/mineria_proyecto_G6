# Resultados de la regresión del monto (SEV-01)

Corrida real sobre D1 completo (6,362,620 filas; 4,463,587 en train) el 10 de noviembre de 2026.

```powershell
.venv/Scripts/python.exe scripts/train_regression.py --config configs/regression.json
```

Recursos: 8.4 s de reloj y 23.5 s de CPU en total (ajuste de los cuatro candidatos, evaluación por bloques
de 500,000 filas y exportación de 1,899,033 predicciones). Muestra de train: 200,000 filas (huella de `row_id`
`8f33df83…ba2e34`). Cortes de tramo de monto (terciles de la muestra de train): 21,855.33 y 157,377.18.
Unidades de monto simuladas, sin moneda real.

## Comparación (escala original)

| Modelo | MAE validation | MAE test | RMSE test | R² test | Sesgo test |
| --- | ---: | ---: | ---: | ---: | ---: |
| **Referencia (mediana por tipo)** | **146,063.85** | **109,132.80** | 354,622.45 | 0.2010 | −43,267.9 |
| Ridge alpha=1 | 149,215.24 | 110,515.42 | 361,486.73 | 0.1698 | −64,862.2 |
| Ridge alpha=10 | 149,230.37 | 110,520.68 | 361,532.13 | 0.1696 | −64,916.8 |
| Boosting (HGB) | 149,182.09 | 109,531.02 | 349,728.56 | 0.2229 | −64,179.6 |

Selección por menor MAE en validation: gana la **referencia**. Ningún candidato complejo la supera en MAE;
el boosting logra menor RMSE y mayor R² en test, pero la regla se fijó antes de evaluar y no se cambió.
Stress (296 filas, solo fraude) se reporta aparte: MAE de la referencia 1,464,176.4 y R² −0.2138; no es comparable
con test.

## Errores del modelo seleccionado en test

| Tipo | n | MAE | Sesgo medio |
| --- | ---: | ---: | ---: |
| PAYMENT | 317,437 | 9,266.7 | −4,851.8 |
| TRANSFER | 80,073 | 562,474.5 | −305,577.1 |
| CASH_OUT | 310,154 | 104,269.4 | −26,446.1 |
| DEBIT | 6,588 | 3,920.1 | −2,016.3 |
| CASH_IN | 204,069 | 97,383.4 | −26,998.7 |

| Tramo de monto | n | MAE | Sesgo medio |
| --- | ---: | ---: | ---: |
| ≤ 21,855.33 | 301,987 | 24,695.3 | +20,880.6 |
| 21,855.33–157,377.18 | 319,631 | 65,766.0 | +54,508.0 |
| > 157,377.18 | 296,703 | 241,792.1 | −213,890.6 |

Lectura: el tipo concentra casi todo el poder explicativo y el saldo previo aporta poco. El modelo subestima los
montos altos (sesgo negativo) y sobreestima los bajos; los errores son mayores en `TRANSFER`. Es un hallazgo
descriptivo de predictores muy limitados, no un defecto de implementación.

## Límites

Datos simulados; sin moneda ni intervalos de confianza; no es un modelo de fraude ni de límites de crédito.
Rhamses revisa contrato y evaluación; Gerardo reproduce desde un clon limpio (pendiente de ambos).
