# Matriz de entregables y responsables — hasta tercera presentación

Referencia: `ENTREGABLES DE PROYECTO (2).pdf`, página 1, proporcionado por el usuario; revisión del 9 de noviembre de 2026. El PDF enumera nueve entregables para semana 7, cinco para semana 10 y cinco para semana 13; no aporta ponderaciones para calcular una nota. «Desarrollado» acredita implementación/evidencia técnica identificable, no una aprobación del docente o una firma humana.

Rama de cierre: `cierre-semana-13`. Responsables académicos según el plan original; la implementación de cierre se realiza en esta rama, sin atribuirla como trabajo personal nuevo de cada compañero.

| ID / semana | Requisito | Estado técnico de cierre | Encargado principal | Revisor / apoyo | Evidencia / ejecución | Límite o pendiente humano |
| --- | --- | --- | --- | --- | --- | --- |
| S7-01 / 7 | Problema | Desarrollado | Equipo; Angel consolida ANG-03. | Los seis validan su dominio. | [Negocio](metodologia-y-negocio.md), bases y contexto. | Alcance académico; no impacto bancario validado. |
| S7-02 / 7 | Objetivos | Desarrollado | Equipo; Angel consolida. | Dueños de módulos. | Objetivo general y ocho objetivos verificables en [metodología](metodologia-y-negocio.md). | No prometer liquidez bancaria ni límites crediticios. |
| S7-03 / 7 | Preguntas de negocio | Desarrollado | Cada responsable; Angel consolida. | Equipo. | Tabla pregunta → indicador → responsable en [negocio](metodologia-y-negocio.md). | Fuentes independientes. |
| S7-04 / 7 | KPIs | Desarrollado: fichas y cálculo reproducible | Angel consolida; cada dueño aporta su indicador. | Sevan–Gerardo: métricas. | [Fichas generadas](kpis-negocio.md); `scripts/build_academic_evidence.py`, JSON académico con huellas. | Metas de negocio sin validación; métricas técnicas no son ahorro observado. |
| S7-05 / 7 | Dataset | Datos y trazabilidad desarrollados; procedencia histórica parcial | Cueva–Taco PaySim; Sevan crédito; Angel reclamos. | Gerardo: reproducción. | [Inventario y consulta de fuentes](datasets.md), Bronze/LFS y SHA-256. | Fecha/origen exacto de las copias y condiciones pendientes según inventario. |
| S7-06 / 7 | Diccionario de datos | Desarrollado con incertidumbres explícitas | Cueva–Taco, Sevan y Angel. | Gerardo: tiempo; Rhamses: identidades. | [Diccionario de 41 campos originales](diccionario-datos.md) y contratos derivados. | Unidades crediticias y vínculo de la copia con catálogo pendiente de confirmación. |
| S7-07 / 7 | EDA | Desarrollado | Cueva–Taco transacciones; Sevan crédito; Angel reclamos; Gerardo temporal; Rhamses red. | Parejas del plan. | Perfiles por fuente, `profile_*.py`, `analyze_forecast_series.py`; [exploración](pronosticos/exploracion-serie.md). | Gráficos/tablas describen las poblaciones observadas. |
| S7-08 / 7 | Calidad de datos | Desarrollado | Taco patrón; Sevan/Angel sus fuentes. | Cueva y Gerardo: controles/consumo. | Contratos/reportes Silver y Gold; `build_*.py` y pruebas. | Las anomalías reales se registran, no se borran para mejorar métricas. |
| S7-09 / 7 | Metodología | Desarrollado | Equipo; Angel consolida. | Parejas datos/evaluación/interfaz. | [CRISP-DM aplicado](metodologia-y-negocio.md), decisiones y evidencia por fase. | KDD/SEMMA son referencias; CRISP-DM conduce el proceso. |
| S10-01 / 10 | Dataset procesado | Desarrollado y ejecutado | Taco D1/transacciones; Sevan crédito; Angel reclamos; Gerardo temporal. | Consumidores y revisores D1. | Silver/Gold y D1: 6,362,620 filas, nueve controles; [contrato](transacciones/contrato-analitico.md). | Derivados fuera de Git, se reconstruyen. |
| S10-02 / 10 | Feature engineering | Desarrollado | Cada dueño; Taco D1. | Sevan–Gerardo: ausencia de fuga. | Variables/bins, contrato de [regresión](regresion/contrato-variables.md), pruebas de invariancia. | Transformadores aprendidos solo en train. |
| S10-03 / 10 | Modelos de asociación | Desarrollado y ejecutado en el cierre | Cueva, CUE-01. | Sevan método; Taco datos; Angel integración; Gerardo preparación. | `mine_associations.py`, API `/api/fraud/associations`, sección Fraude; [reporte real](fraude/asociaciones-descubiertas.md). | Revisión humana pendiente; reglas simuladas, solapadas y no causales. |
| S10-04 / 10 | Primer prototipo | Desarrollado | Rhamses–Angel, cada dueño su vista. | Gerardo: preparación. | FastAPI y Streamlit, siete páginas; `start_demo.ps1`. | Aplicación local; una capacidad puede devolver 503 sin artefacto. |
| S10-05 / 10 | Resultados preliminares | Desarrollado | Cada dueño; Angel consolida. | Sevan–Gerardo: interpretación. | Reportes y [síntesis comparativa](evaluacion-comparativa.md). | Se incluyen resultados desfavorables. |
| S13-01 / 13 | Clustering | Desarrollado y comparado | Taco, TAC-02. | Cueva; Rhamses–Angel navegación. | `segment_transactions.py`; [reporte](transacciones/segmentacion.md), API/página Segmentos. | Cuentas con >=10 recepciones; k elegido con KMeans; revisión humana pendiente. |
| S13-02 / 13 | Series temporales | Desarrollado y comparado | Gerardo, GER-03. | Sevan evaluación; Taco reproducción. | Backtesting Naive/estacional/Holt-Winters; scripts evaluate_forecast_*; API/panel. | Horas simuladas; Naive conserva menor MAE, sin promesa de precisión operativa. |
| S13-03 / 13 | Grafos | Desarrollado y comparado | Rhamses, RHA-01. | Cueva evaluación; Angel interfaz. | `evaluate_graph_alerts.py`; [comparación](grafos/comparacion-alertas.md), `/api/graphs/evaluation`. | Prefijo no aleatorio, retrospectivo; revisión humana pendiente. |
| S13-04 / 13 | Regresión | Desarrollado y ejecutado en el cierre | Sevan, SEV-01. | Rhamses contrato/evaluación; Gerardo reproducción; Angel integración. | `train_regression.py`; [métricas reales](regresion/resultados-modelo.md), `/api/regression/*`, página 07. | Mediana por tipo gana en validation; stress separado; no es una alerta ni recomendación de crédito. |
| S13-05 / 13 | Evaluación comparativa | Desarrollado: métricas equivalentes por tarea | Cada dueño; Angel consolida ANG-03. | Sevan–Gerardo: coherencia; revisores de cada módulo. | [Síntesis generada](evaluacion-comparativa.md), JSON académico y huellas de reportes. | No comparar métricas de tareas/poblaciones distintas; aceptación humana pendiente. |

## Verificación integral

`prepare_demo.py --scope full` prepara dependencias y artefactos; `verify_demo.py --profile full` exige asociaciones, regresión y comparación de grafos, además de los seis módulos originales. El verificador usa HTTP y AppTest con controles identificados por etiqueta/key. Publica un reporte incluso ante fallo y marca el historial P2 como `skipped_optional` si no se exige.

Los comandos, resultados finales y pendientes se consolidan en [cierre-semana13.md](cierre-semana13.md). Una suite verde solo cubre sus pruebas: las corridas reales y el recorrido integrado son evidencia adicional necesaria.

## Fuera de este cierre académico

Semana 16 incluye web/dashboard, clasificación, NLP, explicabilidad, monitoreo, documentación final y sustentación. Varios módulos ya están adelantados. GER-02 (historial de desempeño) y Docker siguen como mejoras P2 del plan; no se declaran implementados. Una segunda persona/PC y aceptaciones humanas no se simulan mediante una ejecución automática.
