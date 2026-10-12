# Resultados del modelo de riesgo crediticio — Sevan

Generado por `scripts/train_credit.py`. Clase positiva = impago **asumido** (ver [perfil](perfil-credito.md)).

Entrada Silver SHA-256: `e0980b5eb868a0d639509ed0fb200920a7560419be056e687e9d6c58dcc68087`.

## Partición

Aleatoria estratificada 70/15/15 con semilla fija, sobre filas sin duplicados exactos (no hay fecha ni cliente). No se aplicó balanceo de clases.

| Partición | Filas | Positivos | Prevalencia |
| --- | ---: | ---: | ---: |
| train | 22,685 | 4,962 | 21.87% |
| validation | 4,862 | 1,063 | 21.86% |
| test | 4,862 | 1,063 | 21.86% |

## Método

- **Línea base trivial:** prevalencia de entrenamiento (`prior`).
- **Línea base lineal:** regresión logística con imputación, escalado y logaritmo de ingreso/monto.
- **Modelo principal:** `HistGradientBoostingClassifier` solo con variables de la solicitud (sin `loan_grade` ni `loan_int_rate`). Se fijó antes de ver validación o prueba.
- **Comparación:** el mismo modelo con grado y tasa, para cuantificar cuánto aporta el riesgo ya evaluado por el prestamista; no se recomienda para decidir.
- **Calibración:** sigmoide (Platt) ajustada en validación sobre el score del modelo principal.
- **Umbral:** 0.1553 sobre la probabilidad calibrada; minimiza FP×1 + FN×5 en validación. Los costes son supuestos académicos.

## Resultados en prueba

Los modelos sin sufijo `calibrated` usan umbral 0.5 y sirven solo para comparar discriminación y calibración; el modelo calibrado usa el umbral elegido en validación.

| Modelo | ROC-AUC | AP | Brier | ECE | Precisión | Recall | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `prior:application` | 0.5000 | 0.2186 | 0.1708 | 0.0001 | 0.000 | 0.000 | 0 | 1063 |
| `logistic:application` | 0.8071 | 0.6258 | 0.1235 | 0.0229 | 0.737 | 0.419 | 159 | 618 |
| `hist_gradient_boosting:application` | 0.8886 | 0.7968 | 0.0874 | 0.0138 | 0.939 | 0.510 | 35 | 521 |
| `hist_gradient_boosting:with_pricing` | 0.9388 | 0.8932 | 0.0557 | 0.0154 | 0.982 | 0.711 | 14 | 307 |
| `hist_gradient_boosting:application:calibrated` | 0.8886 | 0.7968 | 0.0871 | 0.0118 | 0.522 | 0.792 | 770 | 221 |

## Calibración en prueba (modelo principal)

| Decil | Filas | Predicha sin calibrar | Predicha calibrada | Observada |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 487 | 0.014 | 0.006 | 0.008 |
| 2 | 486 | 0.036 | 0.021 | 0.021 |
| 3 | 486 | 0.056 | 0.037 | 0.053 |
| 4 | 486 | 0.074 | 0.054 | 0.047 |
| 5 | 486 | 0.096 | 0.076 | 0.086 |
| 6 | 486 | 0.121 | 0.104 | 0.138 |
| 7 | 486 | 0.158 | 0.147 | 0.154 |
| 8 | 486 | 0.228 | 0.239 | 0.243 |
| 9 | 486 | 0.408 | 0.482 | 0.440 |
| 10 | 487 | 0.964 | 0.987 | 0.994 |

La sigmoide es monótona, así que ambos conjuntos de deciles contienen las mismas filas y comparten la tasa observada.

## Límites

- `label_semantics_unconfirmed`
- `no_temporal_or_customer_split`
- `random_split_may_overestimate_generalization`
- `academic_error_costs`
- `age_is_a_predictor_review_before_any_real_use`
- `calibrator_and_threshold_share_validation_set`
- `probability_of_default_does_not_define_optimal_credit_limit`

La probabilidad de impago **no** determina un monto o límite óptimo: faltan pérdida dada el impago, margen, plazo, costo de fondeo y respuesta de la demanda. El servicio no recomienda montos.
