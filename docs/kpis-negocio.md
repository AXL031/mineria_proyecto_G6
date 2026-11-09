# KPIs, indicadores descriptivos y métricas de evaluación

Generado desde los artefactos reales: 2026-11-09T15:42:22.363632+00:00.

No se midieron beneficios económicos reales. Cada indicador tiene población propia; las fuentes no se unen por cliente.
Las metas de negocio no están validadas. Las métricas técnicas no se presentan como ahorro o impacto causal.

## K01 — ¿Qué proporción de operaciones tiene etiqueta fraude?

- Encargado: Cueva–Taco.
- Clase: descriptivo.
- Fórmula: `100 * fraudes / operaciones`.
- Unidad: %.
- Población/periodo: PaySim completo, steps 1–743.
- Valor observado: **0.129082**.
- Evidencia: `artifacts/models/fraud-silver/metrics.json`.
- Meta: Sin meta de negocio validada; resultado académico descriptivo.

## K02 — ¿Qué fracción del fraude de prueba recupera el clasificador?

- Encargado: Cueva.
- Clase: métrica técnica.
- Fórmula: `100 * TP / (TP + FN)`.
- Unidad: %.
- Población/periodo: Prueba histórica de fraude 379–743, distinta de test D1.
- Valor observado: **99.251123**.
- Evidencia: `artifacts/models/fraud-silver/metrics.json`.
- Meta: Sin meta de negocio validada; resultado académico descriptivo.

## K03 — ¿Qué proporción de préstamos tiene clase positiva asumida?

- Encargado: Sevan.
- Clase: descriptivo; semántica de copia pendiente.
- Fórmula: `100 * loan_status=1 / registros`.
- Unidad: %.
- Población/periodo: Crédito Bronze completo; sin fecha disponible.
- Valor observado: **21.816396**.
- Evidencia: `data\bronze\credit\credit_risk_dataset.csv`.
- Meta: Sin meta de negocio validada; resultado académico descriptivo.

## K04 — ¿Qué proporción de reclamos tiene narrativa publicada?

- Encargado: Angel.
- Clase: cobertura de datos.
- Fórmula: `100 * narrativas no vacías / reclamos`.
- Unidad: %.
- Población/periodo: Copia CFPB completa, 2011–2016.
- Valor observado: **12.016397**.
- Evidencia: `data\bronze\complaints\consumer_complaints.csv`.
- Meta: Sin meta de negocio validada; resultado académico descriptivo.

## K05 — ¿Qué concentración tiene el producto con más reclamos (Mortgage)?

- Encargado: Angel.
- Clase: descriptivo.
- Fórmula: `100 * reclamos del producto / reclamos`.
- Unidad: %.
- Población/periodo: Copia CFPB completa; sin ajuste por cuota de mercado.
- Valor observado: **33.541263**.
- Evidencia: `data\bronze\complaints\consumer_complaints.csv`.
- Meta: Sin meta de negocio validada; resultado académico descriptivo.

## K06 — ¿Qué proporción de destinos entra al agrupamiento?

- Encargado: Taco.
- Clase: cobertura de análisis.
- Fórmula: `100 * destinos con >=10 recepciones / destinos únicos`.
- Unidad: %.
- Población/periodo: PaySim completo; universo de destinos del Silver.
- Valor observado: **5.386095**.
- Evidencia: `artifacts/reports/segments.json`.
- Meta: Sin meta de negocio validada; resultado académico descriptivo.

## K07 — ¿Cuál es el error de cantidad transaccional de la referencia temporal?

- Encargado: Gerardo.
- Clase: métrica técnica.
- Fórmula: `promedio de MAE de cuatro ventanas de 24 steps`.
- Unidad: transacciones por hora simulada.
- Población/periodo: Ventanas 623–718; sin stress.
- Valor observado: **1,366.937500**.
- Evidencia: `artifacts/reports/forecast_holt_winters.json`.
- Meta: Sin meta de negocio validada; resultado académico descriptivo.

## K08 — ¿Cuál es el error de estimación del monto?

- Encargado: Sevan.
- Clase: métrica técnica.
- Fórmula: `sum(abs(prediction-actual)) / n`.
- Unidad: unidad monetaria no verificada.
- Población/periodo: Test D1 379–718 completo.
- Valor observado: **109,127.824624**.
- Evidencia: `artifacts/models/regression/metrics.json`.
- Meta: Sin meta de negocio validada; resultado académico descriptivo.

## K09 — ¿Qué fracción del fraude cubre la unión de asociaciones congeladas?

- Encargado: Cueva.
- Clase: métrica técnica retrospectiva.
- Fórmula: `100 * fraudes cubiertos por al menos una regla / fraudes`.
- Unidad: %.
- Población/periodo: Test D1 379–718 completo; reglas elegidas en validation.
- Valor observado: **97.331536**.
- Evidencia: `artifacts/models/associations/rules.json`.
- Meta: Sin meta de negocio validada; resultado académico descriptivo.
