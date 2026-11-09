# Asociaciones descubiertas automáticamente

Análisis `1131a324085626e45e523fcb9d410b73eaa506ced1a6a464680c5013d1ed0465`; método Apriori acotado; selección en validation.
Corrida UTC: 2026-11-09T15:40:50.115215+00:00; duración: 68.04 s.
D1 SHA-256: `a4c6f55ec8dbb5351b8f2b6f5b8be59e8c4c4696fbc4815f22b6cdc1234960ea`.
Candidatos: 60; reglas seleccionadas: 18.

Reglas congeladas por validation.

Soporte = coincidencias conjuntas de antecedente y fraude / filas. Se distingue del soporte del antecedente.

| Partición | Filas | Fraudes | Coincidencias de la unión | Fraudes cubiertos | Cobertura |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 4463587 | 3643 | 3567 | 3567 | 97.9138% |
| validation | 980416 | 564 | 559 | 559 | 99.1135% |
| test | 918321 | 3710 | 3611 | 3611 | 97.3315% |
| stress | 296 | 296 | 281 | 281 | 94.9324% |

| Regla seleccionada | Confianza validation | Lift validation | Confianza test | Lift test |
| --- | ---: | ---: | ---: | ---: |
| exceeds_origin_balance=false y positive_amount_equals_balance=true → fraude | 1.000000 | 1738.326241 | 1.000000 | 247.525876 |
| positive_amount_equals_balance=true → fraude | 1.000000 | 1738.326241 | 1.000000 | 247.525876 |
| exceeds_origin_balance=false y origin_balance_bin=b2 y positive_amount_equals_balance=true → fraude | 1.000000 | 1738.326241 | 1.000000 | 247.525876 |
| origin_balance_bin=b2 y positive_amount_equals_balance=true → fraude | 1.000000 | 1738.326241 | 1.000000 | 247.525876 |
| amount_bin=b2 y exceeds_origin_balance=false y positive_amount_equals_balance=true → fraude | 1.000000 | 1738.326241 | 1.000000 | 247.525876 |
| amount_bin=b2 y origin_balance_bin=b2 y positive_amount_equals_balance=true → fraude | 1.000000 | 1738.326241 | 1.000000 | 247.525876 |
| amount_bin=b2 y positive_amount_equals_balance=true → fraude | 1.000000 | 1738.326241 | 1.000000 | 247.525876 |
| exceeds_origin_balance=false y positive_amount_equals_balance=true y type=CASH_OUT → fraude | 1.000000 | 1738.326241 | 1.000000 | 247.525876 |
| positive_amount_equals_balance=true y type=CASH_OUT → fraude | 1.000000 | 1738.326241 | 1.000000 | 247.525876 |
| exceeds_origin_balance=false y positive_amount_equals_balance=true y type=TRANSFER → fraude | 1.000000 | 1738.326241 | 1.000000 | 247.525876 |
| positive_amount_equals_balance=true y type=TRANSFER → fraude | 1.000000 | 1738.326241 | 1.000000 | 247.525876 |
| origin_balance_bin=b2 y positive_amount_equals_balance=true y type=CASH_OUT → fraude | 1.000000 | 1738.326241 | 1.000000 | 247.525876 |
| origin_balance_bin=b2 y positive_amount_equals_balance=true y type=TRANSFER → fraude | 1.000000 | 1738.326241 | 1.000000 | 247.525876 |
| amount_bin=b2 y positive_amount_equals_balance=true y type=CASH_OUT → fraude | 1.000000 | 1738.326241 | 1.000000 | 247.525876 |
| amount_bin=b2 y positive_amount_equals_balance=true y type=TRANSFER → fraude | 1.000000 | 1738.326241 | 1.000000 | 247.525876 |
| amount_bin=b1 y exceeds_origin_balance=false y positive_amount_equals_balance=true → fraude | 1.000000 | 1738.326241 | 1.000000 | 247.525876 |
| amount_bin=b1 y positive_amount_equals_balance=true → fraude | 1.000000 | 1738.326241 | 1.000000 | 247.525876 |
| amount_bin=b1 y origin_balance_bin=b2 y positive_amount_equals_balance=true → fraude | 1.000000 | 1738.326241 | 1.000000 | 247.525876 |

## Configuración y procedencia

```json
{
  "config": {
    "min_support": 0.0001,
    "min_antecedent_count": 50,
    "min_confidence": 0.5,
    "min_lift": 2.0,
    "max_rules": 50,
    "max_antecedent_items": 3,
    "max_candidates": 10000
  },
  "dataset": {
    "source_sha256": "47c786d91fd92d81842bbd83bba86b5d39fc94f43f9928315884c6e118c2e46c",
    "dataset_sha256": "a4c6f55ec8dbb5351b8f2b6f5b8be59e8c4c4696fbc4815f22b6cdc1234960ea",
    "discretization_sha256": "54685f5bdba5360600b74e4539ab13fb76faae2bad4d062a2cdb60eab1ad9386",
    "partitions": {
      "train": [
        1,
        323
      ],
      "validation": [
        324,
        378
      ],
      "test": [
        379,
        718
      ],
      "stress": [
        719,
        743
      ]
    },
    "rows": {
      "train": 4463587,
      "validation": 980416,
      "test": 918321,
      "stress": 296
    }
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
    "src/bankshield/models/associations.py": "8c67047b692068f867505183d574c4d211b8734060be209593247f218ffd1593",
    "src/bankshield/analytics_contract.py": "10bde7f82edd20fe165eaaf40def390abb8aa375230adefd182d6f333aad56b7",
    "src/bankshield/features/association_transactions.py": "e4d04d89cd92ba3f6942ffdb78364df74d9569d3eb7cdc99e9f96e8a4db5abff"
  }
}
```

## Limitaciones

- Datos simulados PaySim; las asociaciones no prueban causalidad ni cambian el clasificador.
- Selección en validation; test y stress no seleccionan ni reordenan reglas.
- Las reglas se solapan: no se suman sus coberturas.
- Los patrones de saldo pueden reflejar mecanismos del simulador; no extrapolar a fraude real.
