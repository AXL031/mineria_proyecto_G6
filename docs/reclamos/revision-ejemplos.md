# Revisión de ejemplos — clasificador de reclamos

Generado por `scripts/analyze_complaints_errors.py` sobre la partición de **prueba** del modelo de [resultados-modelo.md](resultados-modelo.md). Los ejemplos se eligen con semilla 42 y no se usan para ajustar el modelo. Se muestra el texto limpio (en minúsculas, con marcadores), recortado; las narrativas son públicas y anonimizadas por la CFPB.

Prueba: 9,822 reclamos, 1,480 errores (exactitud 84.93%).

## Confianza frente a acierto

| Confianza del modelo | Reclamos | Exactitud |
| --- | ---: | ---: |
| 0.0 – 0.4 | 528 | 43.75% |
| 0.4 – 0.6 | 1,234 | 60.37% |
| 0.6 – 0.8 | 1,730 | 78.03% |
| 0.8 – 1.0 | 6,330 | 95.04% |

## Casi-duplicados con el entrenamiento

31 reclamos de prueba (0.3%) tienen en entrenamiento un texto con similitud coseno TF-IDF ≥ 0.9. Exactitud en ese grupo: 87.10%; en el resto: 84.92%. La partición solo separa textos *idénticos*, así que estos casos pueden favorecer al modelo.

## Pares de productos más confundidos

| Producto real | Predicho | Errores | % del producto real |
| --- | --- | ---: | ---: |
| Debt collection | Credit reporting | 161 | 6.4% |
| Credit reporting | Debt collection | 118 | 6.0% |
| Debt collection | Credit card | 76 | 3.0% |
| Debt collection | Consumer Loan | 65 | 2.6% |

### Real: Debt collection → predicho: Credit reporting

- #1817972 (2016-03-07, confianza 0.64): `this collection company was contracted by <censurado> <censurado> to continue collecting and listing the 'debt ' on my credit report although i have underwent the process of shameful bankruptcy. the federal court has already discharged my debts but this company still listed the collection on my credit report. i saw this in my experian report and i…`
- #1820187 (2016-03-07, confianza 0.66): `i filed bankruptcy and it was discharged in <censurado> 2015. ic system inc is still showing as an open collection account on my credit report with no balance or account number on it. remarks are bankruptcy chapter <censurado>, bankruptcy discharged.`
- #1860891 (2016-04-01, confianza 0.84): `credit protection association has placed a collections item on my credit report. original creditor is listed as <censurado> <censurado>, amount of <monto>. date opened listed as <fecha>. i do not have <censurado> <censurado>. this is affecting my credit rating negatively and i would like it removed from my credit report.`

### Real: Credit reporting → predicho: Debt collection

- #1799322 (2016-02-23, confianza 0.79): `there is an account listed that is not mine reporting as a collection # <censurado> original creditor the <censurado> <censurado> for <monto> this is unknown and no such debt or account was taken. there is no way this company verified or validated anything.`
- #1833459 (2016-03-15, confianza 0.96): `<censurado> is reporting a collection on a debt that is not mine i have been fighting them thru cfpb with no solution yet they have failed to validate debt with fdcpa guidelines and this is now on my credit report`
- #1760993 (2016-01-27, confianza 0.74): `i just had a collection account from 2013 show up on my credit report from some first federal credit and collection. this would have been include in my <censurado> ch <censurado> discharge. but i want it taken off my report since they just put it on my report 3 years later if it is not deleted of my credit report i will be seeking legal action agai…`

### Real: Debt collection → predicho: Credit card

- #1758199 (2016-01-27, confianza 0.84): `i installed a new furnace in my house in <censurado> <censurado>. through the heating company they gave me a <censurado> credit card through synchrony bank. i thought 'cool. i can pay this off in installments '. silly me, i made my payments without issue for about a year and a half. i did n't pay close enough attention because sometime in there the…`
- #1797024 (2016-02-22, confianza 0.72): `on or about <fecha>, i received a letter offering to settle a debt owned by capital management services , lp from a <censurado> checking account i once had. i have n't had a checking account with <censurado> for over 3 years now, so i called the number on the letter to let capital management services know that i dispute this debt. they informed me…`
- #1768130 (2016-02-02, confianza 0.30): `i paid off my kay jewelers loam off in full and all of a sudden two years later they say i owe money`

### Real: Debt collection → predicho: Consumer Loan

- #1842386 (2016-03-21, confianza 0.42): `started getting calls again for another person. i told them on <censurado> <censurado> that i do not know who he is do not call my number again. they said they would add my number to the do not call list. again today i received a call from ally bank looking for him. i had this same issue with them a few years back and they are starting up again.`
- #1872478 (2016-04-10, confianza 0.70): `<censurado> <censurado> i, <censurado> <censurado>, was co-signer on an auto loan with <censurado> <censurado> in <censurado> <censurado> tn, terms spanning 48 mo., 24 % apr & mo. payments of <monto> through credit acceptance , corp. ( ca herein ). first major delinquency was <fecha> due to loss of employment & the balance due according to <censura…`
- #1759959 (2016-01-27, confianza 0.58): `i called to make payment arrangements on bills that i owe. i spoke with <censurado> who states he was a supervisor. i explained to him my financial situation and offered what i could do. he got very ugly and asked why i didnt go get a loan to pay off my medical bills or get a credit card. he asked personal questions that did not relate to the medic…`

## Errores con mayor confianza

- #1797047 real **Debt collection**, predicho **Consumer Loan** (confianza 1.00): `ally financial lease car returned <fecha>. third party inspection @ <censurado> of <censurado> dealership noted returned vehicle passing total condition compliance with noting no damage. ally representative informed me that my balance was <monto>. that day, i purchased a new lease through ally 's sister company, <censurado> <censurado>, at same dea…`
- #1767492 real **Consumer Loan**, predicho **Debt collection** (confianza 1.00): `a collection agency first national collection bureau in <censurado> nevada is trying to collect a sum of <monto>. received a mailing from them last summer stating i owed a debt which they were hired to collect.`
- #1765995 real **Debt collection**, predicho **Mortgage** (confianza 1.00): `we are filing a dispute regarding the failure for <censurado> <censurado> <censurado> ( <censurado> ) to complete a modification review under home affordable modification program ( hamp ). our loan was originated in <censurado> with <censurado> mortgage company, which in deed makes our family eligible for the review of hamp programs and all of the…`
- #1887146 real **Credit reporting**, predicho **Mortgage** (confianza 1.00): `fha loan-short sale, fha requires that i am late on my mortgage payment to be considered for a short sale. due to <censurado> issues, job change and increase in expenses ( due to <censurado> issues ) our family experienced a hardship and was forced into a short sale and in order to be considered for a short sale fha requires us to be late on mortga…`
- #1758987 real **Debt collection**, predicho **Student loan** (confianza 1.00): `yesterday ( <censurado> <censurado>, <censurado> ), <censurado> <censurado> <censurado> ( complainant ) had visited <censurado> college 's <censurado> <censurado> <censurado> <censurado> <censurado> to verified her student loan debts held in default status and discovered, illinois student assistance commission ( isac ) had transferred her student l…`
- #1885906 real **Credit reporting**, predicho **Mortgage** (confianza 1.00): `fha loan-short sale, fha requires that i am late on my mortgage payment to be considered for a short sale. due to medical issues, job change and increase in expenses ( due to <censurado> issues ) our family experienced a hardship and was forced into a short sale and in order to be considered for a short sale fha requires us to be late on mortgage p…`
- #1823498 real **Consumer Loan**, predicho **Mortgage** (confianza 1.00): `can my reverse mortgage lender refuse to continue/renew my current property tax loan? hi, my lender, wells fargo, is telling me that they can not continue/renew my current loan that they had advanced for property taxes that were due. they have informed me that, unless i repay the full balance, they will begin foreclosure proceedings on my home now.…`
- #1771349 real **Debt collection**, predicho **Consumer Loan** (confianza 1.00): `the seller of the auto usa santander consumer agency sold th is car to me without disclosing the condition of t he car. the <censurado> <censurado> <censurado> <censurado> had a very bad deficiencies with the breaks that made the car low, stop right in the tracffice on the freeway .also the car would n't breaks, it could be very danger because the…`

## Aciertos de referencia

- #1811518 **Debt collection** (confianza 0.71): `professional account management, <censurado>, wi, allegedly acting on behalf of the <censurado> va, is trying to collect an " unpaid parking ticket '' in the amount of <monto>. the supposed date of the violation was <fecha>. i have called <censurado> and p.a.m and explained that on the date cited, i was at the virginia <censurado> <censurado>, work…`
- #1807125 **Mortgage** (confianza 1.00): `i am attempting to obtain mortgage assistance and avoid a foreclosure sale. i have submitted a completed mortgage assistance package to my servicer - wells fargo. wells fargo has my file in review and has issued no written decision. they have, however, scheduled a foreclosure sale for <censurado> <censurado>, 2016. not only has wells fargo not issu…`
- #1795200 **Credit reporting** (confianza 0.92): `my legal name is <censurado> <censurado> <censurado> my physical address is <censurado> <censurado> <censurado> <censurado>, ca <censurado> i am self employed at <censurado> <censurado> and <censurado> <censurado> <censurado> <censurado> <censurado>, ca <censurado> i need the other names, addresses and employers removed from my credit report as the…`
- #1822437 **Credit card** (confianza 0.69): `i was not allowed to dispute a <censurado> dollar charged on my account. the charge was from <censurado>. the charge is not authorized. the charge is for a pen scribble on a white chair. my wife and i noticed the pen mark when we checked in. the room was free and my card was swiped foa a " <censurado> hold for incidentals '' .i never signed anythin…`

## Textos idénticos con productos distintos

19 textos aparecen en reclamos con más de un producto: ningún modelo puede acertar todos. Los de mayor repetición:

- 5 reclamos — Consumer Loan (3), Credit card (2): `pulled credit report without permission`
- 3 reclamos — Debt collection (2), Consumer Loan (1): `i have sent numerous debt validation notices and never received a response back from the creditor. as per the fair debt collection practice act ( fdcpa ), a credit is supposed to response and no attempt to collect until they have responded. however,…`
- 3 reclamos — Debt collection (2), Credit card (1): `this acct is fraudulent and when initially submitting information was not totally complete this was a case of identity theft and needs to be removed from your records and my file asap`
- 2 reclamos — Debt collection (1), Credit reporting (1): `an amount on my credit report which is not in my name nor have i had a history with this company`
- 2 reclamos — Debt collection (1), Mortgage (1): `after the past several years of <censurado>, starting at the height of the subprime mortgage crisis, my wife and i have been through hell with our property in <censurado>. everything from a neighborhood turning into a criminal wasteland because of ev…`
- 2 reclamos — Debt collection (1), Credit reporting (1): `<censurado> <censurado> <censurado> has been trying to collect a debt for over <monto> for cell phone service that i am not responsible for. i have contacted them on many occasions to explain that this is a fraudulent account and have requested that…`

<!-- OBSERVACIONES -->

## Observaciones de la revisión

**Estado:** primera lectura redactada a partir de los fragmentos recortados de arriba (350 caracteres), no de los reclamos completos. Falta que Angel lea una muestra y confirme o corrija lo siguiente.

1. **La confianza sirve para priorizar.** El 64% de la prueba (6,330 de 9,822) tiene confianza ≥ 0.8 y acierta el 95.0%; por debajo de 0.4 acierta el 43.8%. Un uso razonable es aceptar las predicciones seguras y mandar el resto a revisión humana. Las probabilidades no están calibradas: sirven para ordenar, no como porcentaje literal de acierto.
2. **La confusión principal es de frontera entre productos, no de vocabulario.** *Debt collection* ↔ *Credit reporting* concentra los dos pares más grandes (161 y 118 errores). Los ejemplos muestran reclamos sobre una cuenta en cobranza que aparece en el reporte de crédito (#1817972, #1820187, #1860891 y, al revés, #1799322, #1833459, #1760993): el texto habla de las dos cosas y la etiqueta depende de lo que el consumidor eligió.
3. **Los errores de mayor confianza parecen, en su mayoría, ambigüedad o error de etiqueta.** Entre los 8 más seguros, el fragmento sugiere que la predicción es defendible en casi todos: #1765995 describe una modificación HAMP (hipoteca) etiquetada como cobranza; #1823498 trata de una hipoteca inversa etiquetada como préstamo al consumo; #1758987 habla de deuda estudiantil etiquetada como cobranza; #1767492 describe una agencia de cobranza etiquetada como préstamo al consumo. No es una conclusión firme: conviene leer los textos completos.
4. **Hay reclamos duplicados con distinta censura.** #1887146 y #1885906 son el mismo reclamo presentado dos veces (en el fragmento visible solo difiere una palabra, censurada en uno y visible en el otro) y ambos llevan la etiqueta *Credit reporting* aunque el texto es de una venta corta de hipoteca FHA. La partición solo separa textos idénticos; se midió el efecto y es pequeño (0.3% de la prueba con casi-duplicado en entrenamiento, ver arriba), pero no es nulo.
5. **Los textos muy cortos o con errores generan baja confianza,** como debe ser: #1768130 ("loam" por "loan", una sola frase) tiene confianza 0.30.
6. **Hay un techo de acierto por etiquetas contradictorias.** 19 textos idénticos aparecen con productos distintos; el más repetido es "pulled credit report without permission" (5 reclamos: 3 *Consumer Loan*, 2 *Credit card*). Ningún modelo puede acertarlos todos.
7. **Los nombres de empresas pesan mucho** (ver términos en [resultados-modelo.md](resultados-modelo.md)): en #1771349 (*Santander*), #1797047 y #1842386 (*Ally*) la empresa nombrada es de financiamiento de autos y la predicción fue *Consumer Loan* aunque la etiqueta era *Debt collection*. Es información legítima del texto, pero implica menor robustez ante empresas nuevas.

**Conclusión provisional:** la mayor parte del error restante parece venir de la ambigüedad de la etiqueta y no de fallas evidentes del modelo. Eso refuerza evaluar con macro-F1 y no tratar `product` como verdad absoluta.
