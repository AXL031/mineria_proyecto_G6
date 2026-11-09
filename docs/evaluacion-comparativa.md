# Evaluación comparativa por técnica — semana 13

Generación UTC: 2026-11-09T15:42:22.363632+00:00.

Cada comparación se realiza dentro de una tarea. No se comparan MAE, silueta o F1 entre problemas distintos.

| Técnica / partición | Candidato | Población | Métricas | Decisión |
| --- | --- | --- | --- | --- |
| clustering | kmeans | 146629 cuentas, k=2 | silhouette=0.230484; mean_stability_ari=0.728025 | k fijado por silueta KMeans; comparación exploratoria |
| clustering | activity_quantiles | 146629 cuentas, k=2 | silhouette=0.120737; mean_stability_ari=0.993067 | k fijado por silueta KMeans; comparación exploratoria |
| series/transaction_count | naive | mismas cuatro ventanas de 24 steps | mae=1,366.937500; rmse=1,815.357029; smape=128.864123; window_count=4 | Naive conservado por menor MAE |
| series/transaction_count | seasonal_naive | mismas cuatro ventanas de 24 steps | mae=1,455.906250; rmse=2,293.532496; smape=121.432262; window_count=4 | Naive conservado por menor MAE |
| series/transaction_count | holt_winters_level_seasonal | mismas cuatro ventanas de 24 steps | mae=4,674.277627; rmse=6,903.839340; smape=172.076981; window_count=4 | Naive conservado por menor MAE |
| series/transaction_count | holt_winters_additive | mismas cuatro ventanas de 24 steps | mae=4,518.221181; rmse=6,686.276806; smape=172.332471; window_count=4 | Naive conservado por menor MAE |
| series/transaction_count | holt_winters_damped | mismas cuatro ventanas de 24 steps | mae=4,679.151342; rmse=6,866.608750; smape=172.484235; window_count=4 | Naive conservado por menor MAE |
| series/total_amount | naive | mismas cuatro ventanas de 24 steps | mae=215,326,691.225833; rmse=289,394,248.895359; smape=140.148290; window_count=4 | Naive conservado por menor MAE |
| series/total_amount | seasonal_naive | mismas cuatro ventanas de 24 steps | mae=246,284,163.913437; rmse=398,886,099.361508; smape=127.737254; window_count=4 | Naive conservado por menor MAE |
| series/total_amount | holt_winters_level_seasonal | mismas cuatro ventanas de 24 steps | mae=851,973,198.404809; rmse=1,219,633,259.354572; smape=171.243600; window_count=4 | Naive conservado por menor MAE |
| series/total_amount | holt_winters_additive | mismas cuatro ventanas de 24 steps | mae=569,670,181.447849; rmse=834,059,022.380795; smape=173.283344; window_count=4 | Naive conservado por menor MAE |
| series/total_amount | holt_winters_damped | mismas cuatro ventanas de 24 steps | mae=857,356,050.983245; rmse=1,221,793,550.644526; smape=169.615817; window_count=4 | Naive conservado por menor MAE |
| grafos/k=10 | network_indicators | prefijo 10000 filas, universo compartido | account_precision=0.000000; fraud_coverage=0.000000 | Comparación retrospectiva a igual k; sin selección por etiquetas |
| grafos/k=10 | volume_reference | prefijo 10000 filas, universo compartido | account_precision=0.100000; fraud_coverage=0.014706 | Comparación retrospectiva a igual k; sin selección por etiquetas |
| grafos/k=50 | network_indicators | prefijo 10000 filas, universo compartido | account_precision=0.080000; fraud_coverage=0.058824 | Comparación retrospectiva a igual k; sin selección por etiquetas |
| grafos/k=50 | volume_reference | prefijo 10000 filas, universo compartido | account_precision=0.180000; fraud_coverage=0.102941 | Comparación retrospectiva a igual k; sin selección por etiquetas |
| grafos/k=100 | network_indicators | prefijo 10000 filas, universo compartido | account_precision=0.070000; fraud_coverage=0.102941 | Comparación retrospectiva a igual k; sin selección por etiquetas |
| grafos/k=100 | volume_reference | prefijo 10000 filas, universo compartido | account_precision=0.130000; fraud_coverage=0.132353 | Comparación retrospectiva a igual k; sin selección por etiquetas |
| regresion/validation | median_by_type | [324, 378] | n=980416; mae=146,150.549331; rmse=624,706.821533; r2=0.119311; mean_bias=-87,434.154003 | median_by_type elegido solo por MAE validation |
| regresion/validation | ridge_alpha_1 | [324, 378] | n=980416; mae=149,224.200261; rmse=632,102.256124; r2=0.098336; mean_bias=-109,059.451136 | median_by_type elegido solo por MAE validation |
| regresion/validation | ridge_alpha_10 | [324, 378] | n=980416; mae=149,239.382016; rmse=632,162.148067; r2=0.098165; mean_bias=-109,112.818494 | median_by_type elegido solo por MAE validation |
| regresion/validation | hist_gradient_boosting | [324, 378] | n=980416; mae=149,239.220915; rmse=632,188.204590; r2=0.098091; mean_bias=-109,309.387922 | median_by_type elegido solo por MAE validation |
| regresion/test | median_by_type | [379, 718] | n=918321; mae=109,127.824624; rmse=354,977.957211; r2=0.199430; mean_bias=-43,564.158654 | median_by_type elegido solo por MAE validation |
| regresion/test | ridge_alpha_1 | [379, 718] | n=918321; mae=110,486.347246; rmse=361,670.651562; r2=0.168958; mean_bias=-64,846.434441 | median_by_type elegido solo por MAE validation |
| regresion/test | ridge_alpha_10 | [379, 718] | n=918321; mae=110,491.757118; rmse=361,716.040274; r2=0.168749; mean_bias=-64,900.960016 | median_by_type elegido solo por MAE validation |
| regresion/test | hist_gradient_boosting | [379, 718] | n=918321; mae=110,097.125425; rmse=356,578.309688; r2=0.192195; mean_bias=-64,708.075566 | median_by_type elegido solo por MAE validation |
| regresion/stress | median_by_type | [719, 743] | n=296; mae=1,463,877.905642; rmse=3,045,245.931524; r2=-0.214586; mean_bias=-1,279,901.721081 | median_by_type elegido solo por MAE validation |
| regresion/stress | ridge_alpha_1 | [719, 743] | n=296; mae=1,473,977.281309; rmse=3,076,895.222281; r2=-0.239963; mean_bias=-1,326,179.656601 | median_by_type elegido solo por MAE validation |
| regresion/stress | ridge_alpha_10 | [719, 743] | n=296; mae=1,473,948.897110; rmse=3,076,955.405452; r2=-0.240012; mean_bias=-1,326,429.609389 | median_by_type elegido solo por MAE validation |
| regresion/stress | hist_gradient_boosting | [719, 743] | n=296; mae=1,371,337.008359; rmse=2,896,339.264482; r2=-0.098708; mean_bias=-1,222,933.477712 | median_by_type elegido solo por MAE validation |

## Asociaciones de semana 10

Reglas seleccionadas: 18; análisis `1131a324085626e45e523fcb9d410b73eaa506ced1a6a464680c5013d1ed0465`.
La búsqueda se hace en train, se filtra en validation y se congelan las reglas para test/stress. No se suman coberturas solapadas.

## Límites para la defensa

- Clustering: k se eligió con KMeans; no es una evaluación externa de categorías bancarias.
- Series: los errores relativos son elevados; ganar a los candidatos no significa precisión suficiente para operación real.
- Grafos: prefijo no aleatorio y evaluación retrospectiva; no es detección predictiva temporal.
- Regresión: stress se mantiene aparte; la referencia ganadora permanece seleccionada.
- Fuentes/aceptaciones de personas pendientes se registran en cierre-semana13.md.
