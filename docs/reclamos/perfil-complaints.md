# Perfil de Reclamos de Clientes — Módulo NLP

Informe generado por `scripts/profile_complaints.py`. Los originales en Bronze no se modifican.

- **Archivo:** `consumer_complaints.csv`
- **SHA-256:** `df219bbcf0e8233f33eb83454ef9b3451adf471db29618acfb36d2dacc40ed3f`
- **Alcance:** `complete_file`; registros analizados: 555,957
- **Registros válidos:** 555,957; **inválidos:** 0
- **Identificadores duplicados (`complaint_id`):** 0

## 1. Cobertura de Narrativas de Texto

- **Reclamos con narrativa de texto:** 66,806 (12.02%)
- **Reclamos sin texto (solo estructurados):** 489,151 (87.98%)
- **Longitud promedio en caracteres:** 1,037.6 (Mín: 8, Máx: 5,151)
- **Longitud promedio en palabras:** 190.64 palabras por relato
- **Relatos con marcas de anonimización (`XXXX`):** 56,744 (84.94%)

> **Hallazgo clave de NLP:** Solo una fracción de los reclamos incluye narrativa libre del consumidor. El preprocesamiento debe limpiar y manejar específicamente los tokens de censura `XXXX` / fechas censuradas.

## 2. Distribución y Cobertura por Producto Financiero

| Producto | Reclamos Totales | % del Total | Con Narrativa | % Cobertura Texto |
| :--- | ---: | ---: | ---: | ---: |
| Mortgage | 186,475 | 33.54% | 14,919 | 8.00% |
| Debt collection | 101,052 | 18.18% | 17,552 | 17.37% |
| Credit reporting | 91,854 | 16.52% | 12,526 | 13.64% |
| Credit card | 66,468 | 11.96% | 7,929 | 11.93% |
| Bank account or service | 62,563 | 11.25% | 5,711 | 9.13% |
| Consumer Loan | 20,990 | 3.78% | 3,678 | 17.52% |
| Student loan | 15,839 | 2.85% | 2,128 | 13.44% |
| Payday loan | 3,877 | 0.70% | 726 | 18.73% |
| Money transfers | 3,812 | 0.69% | 666 | 17.47% |
| Prepaid card | 2,470 | 0.44% | 861 | 34.86% |
| Other financial service | 557 | 0.10% | 110 | 19.75% |

## 3. Calidad y Valores Ausentes por Columna

| Columna | Valores Ausentes | % Ausente |
| :--- | ---: | ---: |
| `date_received` | 0 | 0.00% |
| `product` | 0 | 0.00% |
| `sub_product` | 158,322 | 28.48% |
| `issue` | 0 | 0.00% |
| `sub_issue` | 343,335 | 61.76% |
| `consumer_complaint_narrative` | 489,151 | 87.98% |
| `company_public_response` | 470,833 | 84.69% |
| `company` | 0 | 0.00% |
| `state` | 4,887 | 0.88% |
| `zipcode` | 4,505 | 0.81% |
| `tags` | 477,998 | 85.98% |
| `consumer_consent_provided` | 432,499 | 77.79% |
| `submitted_via` | 0 | 0.00% |
| `date_sent_to_company` | 0 | 0.00% |
| `company_response_to_consumer` | 0 | 0.00% |
| `timely_response` | 0 | 0.00% |
| `consumer_disputed?` | 0 | 0.00% |
| `complaint_id` | 0 | 0.00% |

**Incidencias de validación:** `{}`

## 4. Cobertura Temporal y Tendencias

- **Fecha más antigua registrada:** `01/01/2012`
- **Fecha más reciente registrada:** `12/31/2015`

### Reclamos por Año

| Año | Cantidad de Reclamos |
| :--- | ---: |
| 2011 | 2,549 |
| 2012 | 72,523 |
| 2013 | 108,273 |
| 2014 | 153,138 |
| 2015 | 168,621 |
| 2016 | 50,853 |

## 5. Principales Causas y Empresas Involucradas

### Top 10 Motivos de Queja (`issue`)

| Motivo (`issue`) | Frecuencia |
| :--- | ---: |
| Loan modification,collection,foreclosure | 97,191 |
| Incorrect information on credit report | 66,718 |
| Loan servicing, payments, escrow account | 60,375 |
| Cont'd attempts collect debt not owed | 42,285 |
| Account opening, closing, or management | 26,661 |
| Communication tactics | 18,293 |
| Disclosure verification of debt | 18,292 |
| Deposits and withdrawals | 17,195 |
| Application, originator, mortgage broker | 13,306 |
| Billing disputes | 11,042 |

### Top 10 Compañías con más Quejas

| Compañía | Frecuencia |
| :--- | ---: |
| Bank of America | 55,998 |
| Wells Fargo & Company | 42,024 |
| JPMorgan Chase & Co. | 33,881 |
| Equifax | 31,828 |
| Experian | 30,905 |
| Citibank | 25,540 |
| TransUnion Intermediate Holdings, Inc. | 25,534 |
| Ocwen | 20,978 |
| Capital One | 15,628 |
| Nationstar Mortgage | 13,250 |

## 6. Conclusiones y Próximos Pasos para el Módulo NLP

1. **Estrategia dual:** Desarrollar tanto un análisis estructurado (tendencias temporales, productos, empresas) como un pipeline de NLP enfocado exclusivamente en el subconjunto de reclamos con narrativa.
2. **Limpieza de texto especializada:** Implementar una normalización que remueva ruido administrativo (`XXXX`, fechas censuradas, saltos de línea repetidos) y conserve términos financieros clave.
3. **Modelado NLP:** Línea base con TF-IDF + Clasificador supervisado (ej. predecir `product` a partir del texto de la queja) y extracción no supervisada de tópicos (NMF / LDA) para descubrir motivos ocultos de insatisfacción.
4. **Propuesta de Panel:** Una vista interactiva con KPIs globales, buscador semántico o de texto, tendencias temporales y explorador de quejas reales anonimizadas.
