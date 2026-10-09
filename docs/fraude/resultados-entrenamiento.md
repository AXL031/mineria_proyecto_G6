# Entrenamiento inicial de fraude — Cueva

Resultados de una ejecución completa, reproducible desde `scripts/train_fraud.py`.

Fuente SHA-256: `16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b`.

## Separación temporal

Los cortes coinciden con el volumen acumulado objetivo 70/15/15, sin fraccionar pasos ni elegirlos por etiquetas. No se aplicó submuestreo, sobremuestreo ni balanceo de clases.

| Partición | Pasos | Filas | Fraudes | Prevalencia |
| --- | --- | ---: | ---: | ---: |
| train | 1–323 | 4,463,587 | 3,643 | 0.081616% |
| validation | 324–378 | 980,416 | 564 | 0.057527% |
| test | 379–743 | 918,617 | 4,006 | 0.436090% |

## Método y umbral

Línea base: puntuación constante igual a la prevalencia de entrenamiento (`DummyClassifier`). Clasificador: `HistGradientBoostingClassifier`, con codificación de tipo ajustada en entrenamiento. Se desactivó la parada temprana aleatoria; los hiperparámetros están fijados en `configs/fraud.json`.

Umbral elegido en validación: **0.09878305**. Coste supuesto: FP=1.0, FN=20.0. Se minimiza FP×C_FP + FN×C_FN, incluyendo la opción de no emitir alertas. Estos costes son supuestos académicos, no pérdidas monetarias verificadas.

## Resultados

AP es Average Precision, la métrica principal de resumen de precisión-recall. El JSON también conserva el área trapezoidal de esa curva como una métrica distinta.

| Partición | Método | Umbral | AP | Precisión | Recall | F1 | FP | FN | TP | TN |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| validation | baseline_prior | 0.50000000 | 0.000575 | 0.000000 | 0.000000 | 0.000000 | 0 | 564 | 0 | 979852 |
| validation | classifier_default | 0.50000000 | 0.836929 | 0.814453 | 0.739362 | 0.775093 | 95 | 147 | 417 | 979757 |
| validation | classifier_selected | 0.09878305 | 0.836929 | 0.378016 | 1.000000 | 0.548638 | 928 | 0 | 564 | 978924 |
| test | baseline_prior | 0.50000000 | 0.004361 | 0.000000 | 0.000000 | 0.000000 | 0 | 4006 | 0 | 914611 |
| test | classifier_default | 0.50000000 | 0.961840 | 0.960772 | 0.758113 | 0.847495 | 124 | 969 | 3037 | 914487 |
| test | classifier_selected | 0.09878305 | 0.961840 | 0.796634 | 0.992511 | 0.883850 | 1015 | 30 | 3976 | 913596 |

## Auditoría y límites

Se audita una muestra determinista aproximada del 1 % de cuentas por rol, sin usar identificadores como predictores. Los conteos de intersección son de la muestra, no totales.

| Rol | Train–validación | Train–prueba | Validación–prueba |
| --- | ---: | ---: | ---: |
| nameOrig | 18 | 27 | 10 |
| nameDest | 2651 | 2357 | 2232 |

Los resultados describen la simulación PaySim. No validan una política bancaria real ni desempeño para cuentas completamente nuevas. Los scores no están calibrados como probabilidades de riesgo reales. La ejecución Silver posterior ya documenta un contrato y cero duplicados exactos detectados para la misma fuente; falta revisar esa evidencia con Taco e incorporarla a la auditoría de fraude. Las métricas de prueba se obtuvieron después de congelar modelo y umbral; no deben usarse para ajustar esta versión.

## Artefactos

`artifacts/models/fraud/model.joblib` contiene el pipeline, el umbral, las variables y los metadatos. `artifacts/models/fraud/metrics.json` conserva configuración, versiones, huellas de código y métricas. Ambos están excluidos de Git.

## Referencias del método

- [HistGradientBoostingClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingClassifier.html)
- [Average Precision](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html)
