# Comprensión del negocio y metodología — semanas 7 a 13

## Problema y alcance

BankShield estudia cómo convertir datos de transacciones, préstamos y reclamos en resultados analíticos reproducibles para apoyar una revisión financiera. Son tres poblaciones independientes. PaySim es una simulación; el proyecto no valida decisiones bancarias reales ni demuestra ahorros económicos.

Objetivo general: desarrollar y evaluar una demostración de minería de datos que conecte preparación, modelos, comparación y consulta de resultados.

Objetivos verificables: (1) caracterizar/calificar fuentes; (2) construir Silver/Gold trazables; (3) descubrir asociaciones; (4) segmentar cuentas; (5) pronosticar actividad; (6) describir redes; (7) estimar montos por regresión; (8) comparar cada método con referencias y exponer límites. Clasificación y NLP ya existentes aportan avances de semana 16.

## Preguntas de negocio e indicadores

| Pregunta | Indicador / evidencia | Encargado |
| --- | --- | --- |
| ¿Dónde se concentra el fraude simulado? | Prevalencia por tipo/periodo; cobertura de reglas y errores del clasificador. | Cueva; Taco valida datos. |
| ¿Qué grupos de actividad aparecen entre cuentas destino recurrentes? | Tamaños/perfiles de segmentos, silueta y estabilidad frente a cuantiles. | Taco; Cueva revisa. |
| ¿Cómo cambia la cantidad/monto de operaciones y qué referencia predice mejor? | MAE/RMSE por ventana temporal y cambio histórico de distribución. | Gerardo; Sevan revisa. |
| ¿Qué ranking de cuentas cubre más fraude a igual presupuesto? | Cobertura red/volumen, mismo universo y k. | Rhamses; Cueva revisa. |
| ¿Qué monto se puede estimar con tipo y saldo anterior? | MAE/RMSE/R² y sesgo por partición/tipo. | Sevan; Rhamses y Gerardo revisan. |
| ¿Qué muestran los préstamos y reclamos de las otras fuentes? | Proporción positiva asumida y cobertura del texto; evaluación separada. | Sevan y Angel. |

Fórmulas, unidades, poblaciones y resultados observados se generan en [KPIs](kpis-negocio.md). Las métricas técnicas evalúan métodos; no son beneficios de negocio observados. No se inventa una meta numérica posterior a observar test.

## CRISP-DM aplicado

| Fase | Actividad y decisión | Evidencia / responsable |
| --- | --- | --- |
| Comprensión de negocio | Preguntas anteriores, alcance académico y límites de decisión. | Este documento; equipo, consolidación Angel. |
| Comprensión de datos | Perfil, nulos, duplicados, cobertura, fuentes y significado. | [Inventario](datasets.md), [diccionario](diccionario-datos.md), perfiles; cada dueño. |
| Preparación | Originales inmutables, Silver tipado, Gold/D1, bins aprendidos en train. | Scripts build_* y reportes; Taco y dueños de fuente. |
| Modelado | Asociación, clustering, series, grafos y regresión; referencias fijadas. | src/bankshield, configs y reportes por módulo. |
| Evaluación | Selección en validación, test posterior, stress aparte; métricas adecuadas a cada tarea. | [Comparación](evaluacion-comparativa.md); cada dueño, apoyo Sevan–Gerardo. |
| Entrega | Artefactos offline, FastAPI, siete páginas, pruebas y verificador integral. | scripts/prepare_demo.py y verify_demo.py; Angel–Gerardo y dueños. |

KDD describe la transformación de datos a conocimiento y SEMMA orienta exploración/modelado; CRISP-DM es el marco conductor. Se conservan decisiones desfavorables: una referencia que gana permanece seleccionada.

## Datos, EDA y calidad para presentar

- PaySim: 6,362,620 operaciones, fuerte desbalance de fraude y tramo stress final; EDA por tipo, monto y step. [Perfil](fraude/perfil-paysim.md), [calidad Silver](transacciones/calidad-silver.md), [exploración temporal](pronosticos/exploracion-serie.md).
- Crédito: 32,581 registros, sin fecha ni cliente, duplicados y valores implausibles; [perfil](credito/perfil-credito.md) y [calidad](credito/calidad-silver.md).
- Reclamos: 555,957 casos; texto minoritario y anonimizado; [perfil](reclamos/perfil-complaints.md) y [calidad](reclamos/calidad-silver.md).

Las figuras se regeneran con los scripts de perfil/serie y las vistas del panel. No se exige un notebook para sustituir código reproducible. Las fuentes exactas de las copias, las revisiones humanas y la ejecución en otra PC se registran honestamente en [cierre](cierre-semana13.md).
