# Guion de tercera presentación — semana 13

Propuesta para el equipo; adaptar tiempos al espacio asignado por el docente. Los responsables del plan conservan la explicación de su módulo, aunque el cierre se haya implementado en una rama común. Las cifras se toman de los reportes enlazados; no completar con números inventados.

| Bloque | Encargado | Qué mostrar | Mensaje defendible |
| --- | --- | --- | --- |
| 1. Problema, objetivo y método | Angel coordina; equipo valida. | [Negocio/CRISP-DM](metodologia-y-negocio.md), arquitectura Bronze → Silver → Gold → modelo → API → panel. | Demostración académica financiera, tres fuentes independientes. |
| 2. Datos, diccionario, EDA y calidad | Taco y Cueva; Sevan/Angel explican sus fuentes. | [Diccionario](diccionario-datos.md), tamaños, nulos/duplicados, gráfico por step y cobertura de texto. | Originales inmutables, supuestos explícitos y transformaciones reproducibles. |
| 3. KPIs y preparación | Angel consolida; Taco explica D1. | Dos fichas de [KPIs](kpis-negocio.md), nueve controles D1 y cortes train/validation/test/stress. | Indicadores con fórmula y población; sin supuestos de ahorro económico real. |
| 4. Asociaciones de semana 10 | Cueva; Sevan revisa metodología. | Fraude → Consultar asociaciones descubiertas; alternar validation/test y leer antecedente, soporte conjunto, confianza y lift. | Reglas descubiertas por algoritmo, seleccionadas antes de ver test; no cambian el clasificador. |
| 5. Clustering | Taco. | Segmentos → perfiles, k, silueta, ARI y comparación contra cuantiles. | KMeans tiene mejor separación en el espacio evaluado; la referencia puede tener mayor estabilidad. Son cuentas recurrentes, no categorías de riesgo validadas. |
| 6. Series temporales | Gerardo. | Pronósticos → cantidad/monto y [comparación](evaluacion-comparativa.md). | Naive supera a Holt-Winters por MAE; conservar la referencia es una decisión válida. Tiempo simulado y errores relativos elevados. |
| 7. Grafos | Rhamses. | Redes → comparación Red vs Volumen para 10,000 filas, k=10/50/100; subgrafo acotado. | Igual universo/presupuesto; red no tiene que ganar. Evaluación retrospectiva del prefijo, sin extrapolar a toda la red. |
| 8. Regresión numérica | Sevan. | Regresión → type TRANSFER, saldo 500 → Estimar monto; Consultar evaluación y ejemplos. | La mediana por tipo gana en validation; prueba y stress separados. No es clasificación logística ni límite de crédito. |
| 9. Verificación y conclusiones | Angel y Gerardo; todos responden. | [Matriz](matriz-entregables.md), log de tests, manifiesto y verificador de [cierre](cierre-semana13.md). | Código, experimentos y demo tienen evidencia; fuentes históricas/aceptaciones pendientes siguen visibles. |

## Preparación del ensayo

1. Instalar el entorno y recuperar Bronze con LFS según README; ejecutar preparación offline completa antes de exponer.
2. Ejecutar suite y verificador integral; consultar el reporte si falla. Ninguna consulta del panel debe entrenar modelos.
3. Abrir la demo con los scripts de inicio. Probar los siete módulos y las secciones nuevas; mantener la muestra de grafos en 10,000 para el reporte correspondiente.
4. Tener disponibles los Markdown de resultados y sus capturas para explicar las cifras si se interrumpe la demo, identificándolas como evidencia previamente generada.
5. Cada integrante lee límites, métricas y un error de su módulo; registrar su revisión cuando realmente ocurra.

## Respuestas que deben poder explicar

- ¿Por qué no unir crédito, reclamos y transacciones por cliente? No existe llave común demostrada.
- ¿Por qué separar stress? El tramo 719–743 tiene un régimen distinto y no participa en selección de modelos/reglas.
- ¿Por qué elegir un método simple? La selección usa la métrica fijada y una referencia ganadora se conserva.
- ¿Qué diferencia hay entre asociaciones manuales y descubiertas? Las primeras fijan condiciones; las nuevas buscan combinaciones frecuentes y filtran por criterios predefinidos.
- ¿Qué diferencia hay entre clasificación y regresión? La primera predice una clase/score; aquí se estima un monto numérico.
- ¿Qué demuestran los tests? Contratos y comportamientos definidos; no garantizan utilidad bancaria real, aceptación del docente o aprobación de personas.
