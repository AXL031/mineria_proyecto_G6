# Resultados de regresión numérica del monto transaccional

Modelo seleccionado: **median_by_type**, por MAE de validation.
Modelo SHA-256: `fe2845d17beda154ddcc412d9856d7a2c26b1e4fd846bdb3bc84b9ac3309fddb`.
D1 SHA-256: `a4c6f55ec8dbb5351b8f2b6f5b8be59e8c4c4696fbc4815f22b6cdc1234960ea`.
Corrida UTC: 2026-11-09T15:41:22.111591+00:00; duración: 36.05 s.
Train: 200,000 de 4,463,587 filas; semilla 42.

| Partición | Candidato | n | MAE | RMSE | R² | Sesgo medio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| validation | median_by_type | 980416 | 146150.5493 | 624706.8215 | 0.119311 | -87434.1540 |
| validation | ridge_alpha_1 | 980416 | 149224.2003 | 632102.2561 | 0.098336 | -109059.4511 |
| validation | ridge_alpha_10 | 980416 | 149239.3820 | 632162.1481 | 0.098165 | -109112.8185 |
| validation | hist_gradient_boosting | 980416 | 149239.2209 | 632188.2046 | 0.098091 | -109309.3879 |
| test | median_by_type | 918321 | 109127.8246 | 354977.9572 | 0.199430 | -43564.1587 |
| test | ridge_alpha_1 | 918321 | 110486.3472 | 361670.6516 | 0.168958 | -64846.4344 |
| test | ridge_alpha_10 | 918321 | 110491.7571 | 361716.0403 | 0.168749 | -64900.9600 |
| test | hist_gradient_boosting | 918321 | 110097.1254 | 356578.3097 | 0.192195 | -64708.0756 |
| stress | median_by_type | 296 | 1463877.9056 | 3045245.9315 | -0.214586 | -1279901.7211 |
| stress | ridge_alpha_1 | 296 | 1473977.2813 | 3076895.2223 | -0.239963 | -1326179.6566 |
| stress | ridge_alpha_10 | 296 | 1473948.8971 | 3076955.4055 | -0.240012 | -1326429.6094 |
| stress | hist_gradient_boosting | 296 | 1371337.0084 | 2896339.2645 | -0.098708 | -1222933.4777 |

Stress se informa separado de test. Ningún candidato se reajustó después de validation.

## Errores del modelo seleccionado por tipo y tramo de monto

Cortes de monto ajustados solo con train: [21649.48, 157428.2600000001]

| Partición | Agrupación | Grupo | n | MAE | RMSE |
| --- | --- | --- | ---: | ---: | ---: |
| validation | by_type | CASH_IN | 217839 | 100104.5940 | 131880.0179 |
| validation | by_type | CASH_OUT | 344551 | 102614.1530 | 151923.6981 |
| validation | by_type | DEBIT | 7080 | 3495.3726 | 7336.8189 |
| validation | by_type | PAYMENT | 327506 | 9756.4533 | 14437.8552 |
| validation | by_type | TRANSFER | 83440 | 993597.7836 | 2108075.5219 |
| validation | by_amount_bin | 0 | 298730 | 24854.3274 | 60064.0632 |
| validation | by_amount_bin | 1 | 343562 | 60563.5280 | 89762.8354 |
| validation | by_amount_bin | 2 | 338124 | 340278.3505 | 1058399.6955 |
| test | by_type | CASH_IN | 204069 | 97375.3130 | 128051.0344 |
| test | by_type | CASH_OUT | 310154 | 104270.5400 | 257772.5739 |
| test | by_type | DEBIT | 6588 | 3900.1691 | 17595.2400 |
| test | by_type | PAYMENT | 317437 | 9269.8625 | 14464.0421 |
| test | by_type | TRANSFER | 80073 | 562422.7089 | 1070105.9826 |
| test | by_amount_bin | 0 | 300647 | 24573.1103 | 61690.2164 |
| test | by_amount_bin | 1 | 321067 | 65641.4947 | 98992.1574 |
| test | by_amount_bin | 2 | 296607 | 241906.7093 | 612919.8891 |
| stress | by_type | CASH_OUT | 148 | 1407122.1852 | 3015782.3044 |
| stress | by_type | TRANSFER | 148 | 1520633.6261 | 3074427.2084 |
| stress | by_amount_bin | 0 | 9 | 248230.1244 | 288278.6514 |
| stress | by_amount_bin | 1 | 86 | 219324.3005 | 271820.2245 |
| stress | by_amount_bin | 2 | 201 | 2050805.4682 | 3690690.5787 |

## Procedencia

```json
{
  "sampling": {
    "algorithm": "uniform_reservoir_iid_priorities",
    "seed": 42,
    "rows_available": 4463587,
    "rows_used": 200000,
    "row_ids_sha256": "885f1385168dd01de8b5de7b730af14cf713715c77511da0c4c81cc4ee3e735a"
  },
  "selection": {
    "partition": "validation",
    "metric": "mae",
    "tie_tolerance": 1e-09,
    "tie_order": [
      "median_by_type",
      "ridge_alpha_1",
      "ridge_alpha_10",
      "hist_gradient_boosting"
    ],
    "refit_validation": false
  },
  "export": {
    "rows_by_partition": {
      "validation": 980416,
      "test": 918321,
      "stress": 296
    },
    "examples_count": 200,
    "examples_method": "uniform_test_reservoir_seed_42",
    "predictions_sha256": "521baa7a19f4608eec07243f62c477ac0362c8b5d8c85dd9519a706eb91a42bd",
    "examples_sha256": "c96f709b17b0ba233964332aa20c62d507b731bb26409a9bb83d773f4b16a4d2"
  },
  "versions": {
    "python": "3.12.14",
    "numpy": "2.5.3",
    "pandas": "3.0.6",
    "scikit_learn": "1.9.1",
    "joblib": "1.6.0"
  },
  "git": {
    "commit": "de6bbe27620d42b96cc1014e6b581480adba0c43",
    "tree_dirty": true
  },
  "code_sha256": {
    "src/bankshield/models/regression.py": "686cf84ad55bdd44c33f2cbc659f3c8a5a8f5986e547fa4109df814d74c8625d",
    "src/bankshield/analytics_contract.py": "10bde7f82edd20fe165eaaf40def390abb8aa375230adefd182d6f333aad56b7",
    "src/bankshield/features/regression.py": "54e73a21c2dcc6831d0fa8bf921c98614b21330ec898ca22ffd0063fa4b83446"
  }
}
```

## Limitaciones

- Estimación académica sobre PaySim; no constituye una alerta de fraude ni un límite de crédito.
- Los montos no tienen moneda verificada; step es una hora simulada.
- El modelo se selecciona por MAE de validation, sin reajustar con validation o test.
- Stress 719-743 se informa aparte; no selecciona modelos ni umbrales.
- Los saldos de PaySim pueden reflejar limitaciones del simulador; no extrapolar a una entidad real.
