# Resultados del análisis NLP de reclamos — Angel

Generado por `scripts/train_complaints.py`. Tarea: predecir el **producto** del reclamo (`product`, 11 clases) a partir de `narrative_clean`.

Entrada Silver SHA-256: `ba939fe172c4d938bee3d5266048506eb7c1bc7f79ea2252ff679eeb0dd0ff07`.

## Datos y partición

De 555,957 reclamos del Silver se usan 66,736: se excluyen 489,151 sin narrativa y 70 con menos de 5 palabras.

Partición cronológica 70/15/15 por fecha de primera aparición del texto: entrenamiento hasta 2015-11-26, validación hasta 2016-01-25 y prueba después. Un texto idéntico en varios reclamos se asigna completo a una sola partición, así el mismo texto no está en entrenamiento y prueba; por eso la última fecha de entrenamiento puede superar el corte, ya que incluye repeticiones tardías de textos vistos antes. El vectorizador se ajusta solo con entrenamiento.

| Partición | Filas | Primera fecha | Última fecha |
| --- | ---: | --- | --- |
| train | 46,740 | 2015-03-19 | 2016-01-21 |
| validation | 10,174 | 2015-11-27 | 2016-03-16 |
| test | 9,822 | 2016-01-26 | 2016-04-20 |

## Método

- **Referencia trivial:** producto más frecuente en entrenamiento.
- **Línea base:** Naive Bayes multinomial sobre conteos de palabras (alpha 0.1).
- **Método principal:** TF-IDF de 1 a 2 palabras con regresión logística y pesos balanceados por clase. C = 5, elegido por macro-F1 en validación entre 1, 5, 20.
- Las stopwords en inglés y los marcadores `<fecha>`, `<monto>` y `<censurado>` no entran al vocabulario.
- La prueba se evalúa una sola vez, con los modelos ya congelados.

## Resultados en prueba

| Modelo | Exactitud | Macro-F1 | F1 ponderado | Top-3 |
| --- | ---: | ---: | ---: | ---: |
| `prior` | 0.2542 | 0.0369 | 0.1031 | 0.6771 |
| `naive_bayes` | 0.8201 | 0.6677 | 0.8209 | 0.9610 |
| `logistic_tfidf` | 0.8493 | 0.7278 | 0.8494 | 0.9738 |

El método principal **supera** a ambas referencias en macro-F1. La macro-F1 pesa igual a cada producto; la exactitud, en cambio, premia acertar los productos grandes.

### Elección de C (validación)

| C | Macro-F1 validación | Convergió |
| ---: | ---: | --- |
| 1 | 0.7307 | sí |
| 5 | 0.7426 | sí |
| 20 | 0.7244 | sí |

### Métricas por producto (método principal, prueba)

| Producto | Precisión | Recall | F1 | Soporte |
| --- | ---: | ---: | ---: | ---: |
| Debt collection | 0.869 | 0.817 | 0.842 | 2,497 |
| Mortgage | 0.933 | 0.934 | 0.934 | 2,173 |
| Credit reporting | 0.856 | 0.860 | 0.858 | 1,980 |
| Credit card | 0.817 | 0.854 | 0.835 | 1,273 |
| Bank account or service | 0.812 | 0.841 | 0.826 | 872 |
| Consumer Loan | 0.694 | 0.699 | 0.696 | 564 |
| Student loan | 0.778 | 0.861 | 0.817 | 244 |
| Payday loan | 0.464 | 0.527 | 0.494 | 74 |
| Money transfers | 0.701 | 0.761 | 0.730 | 71 |
| Prepaid card | 0.729 | 0.850 | 0.785 | 60 |
| Other financial service | 0.286 | 0.143 | 0.190 | 14 |

## Términos con mayor peso por producto

| Producto | Términos |
| --- | --- |
| Bank account or service | `bank`, `scottrade`, `branch`, `overdraft`, `account`, `deposit`, `chase`, `atm`, `debit`, `suntrust` |
| Consumer Loan | `vehicle`, `loan`, `car`, `santander`, `ally`, `finance`, `financial`, `auto`, `auto loan`, `credit` |
| Credit card | `card`, `capital`, `credit card`, `discover`, `credit`, `citi`, `chase`, `macy`, `citibank`, `target` |
| Credit reporting | `equifax`, `experian`, `transunion`, `report`, `credit`, `trans union`, `trans`, `inquiries`, `lived`, `score` |
| Debt collection | `debt`, `collection`, `recovery`, `owe`, `calling`, `collections`, `collect`, `owed`, `calls`, `medical` |
| Money transfers | `transfer`, `money`, `moneygram`, `paypal`, `wire`, `western union`, `transaction`, `western`, `money gram`, `gram` |
| Mortgage | `mortgage`, `ocwen`, `modification`, `escrow`, `foreclosure`, `home`, `nationstar`, `loan`, `greentree`, `property` |
| Other financial service | `check`, `money order`, `lexington`, `lexington law`, `global client`, `client solutions`, `certegy`, `cash check`, `global`, `cash` |
| Payday loan | `loan`, `payday`, `cash`, `lender`, `borrowed`, `pay day`, `payday loans`, `bank account`, `payday loan`, `fees` |
| Prepaid card | `card`, `rushcard`, `prepaid`, `netspend`, `funds`, `money`, `direct`, `rush card`, `cards`, `rush` |
| Student loan | `navient`, `loans`, `loan`, `student`, `school`, `private`, `aes`, `university`, `student loan`, `education` |

Muchos términos son **nombres de empresas** (`equifax`, `ocwen`, `moneygram`...). Están en la propia narrativa, así que no es fuga de datos, pero parte del acierto consiste en reconocer empresas y el modelo podría rendir peor con una empresa que no aparece en entrenamiento.

## Límites

- `only_complaints_with_narrative_and_consent`
- `thirteen_months_of_text`
- `label_chosen_by_consumer`
- `contradictory_labels_for_identical_texts`
- `rare_classes_have_few_examples`
- `company_names_dominate_top_terms`
- `may_generalize_worse_to_unseen_companies`
- `no_hyperparameter_search_beyond_C`
- `redaction_markers_ignored_by_vectorizer`

El modelo describe **qué producto sugiere el texto**, no la calidad de la atención ni el resultado del reclamo. Solo cubre reclamos con narrativa publicada con consentimiento; no representa a todos. Los ejemplos revisados están en [revision-ejemplos.md](revision-ejemplos.md).
