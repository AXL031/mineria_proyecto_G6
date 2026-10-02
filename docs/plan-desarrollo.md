# Plan de desarrollo y responsabilidades

Este documento concreta las etapas y entregas de los seis integrantes. Complementa las [bases del proyecto](bases-del-proyecto.md) y el [inventario de datasets](datasets.md). Las fechas se acordarán cuando el equipo confirme su disponibilidad y los requisitos del curso.

## Etapas de desarrollo

| Etapa | Qué desarrollar | Criterio de finalización |
| --- | --- | --- |
| 1. Conocer los datos | Revisar columnas, tipos, nulos, duplicados, valores extraños y significado de las etiquetas. Documentar procedencia y licencia. | Diccionario y reporte de calidad por dataset. |
| 2. Preparar los datos | Construir Bronze → Silver → Gold. Conservar originales, generar datos limpios y definir tablas analíticas por dominio. | Scripts que reconstruyan los datos sin limpieza manual. |
| 3. Desarrollar los análisis | Crear una línea base y un método principal por módulo. Separar entrenamiento, validación y prueba cuando corresponda. | Resultados evaluados y limitaciones documentadas. |
| 4. Construir la aplicación | Implementar servicios, endpoints y páginas del panel que consuman resultados reales. | Cada módulo puede demostrarse desde la aplicación. |
| 5. Integrar y entregar | Probar el recorrido completo, preparar Docker, instrucciones de ejecución y demostración. | Otro integrante puede ejecutar el proyecto desde cero siguiendo la guía. |

Las etapas tienen dependencias dentro de cada módulo, pero el equipo puede trabajar en paralelo. El primer recorrido integrado será el de fraude; crédito y reclamos pueden avanzar con sus propias muestras mientras se define el patrón común.

Los tres datasets tendrán procesamiento separado. No existe una llave compartida demostrada para construir un historial común de clientes.

## Responsabilidades individuales

### Cueva — fraude supervisado y patrones

1. Perfilar PaySim junto con Taco y revisar la distribución de `isFraud`.
2. Definir variables disponibles al momento de predecir; comprobar posibles fugas de información, especialmente datos posteriores a la operación.
3. Entrenar una línea base y un clasificador de fraude.
4. Elegir el umbral en validación y reportar PR-AUC, precisión, recall y errores.
5. Implementar el servicio de predicción y su página de fraude.
6. Después de integrar el clasificador, añadir reglas de asociación sencillas si los campos lo permiten.

**Entrega final:** modelo de fraude, reporte de métricas, servicio de predicción y página de fraude y patrones.

### Sevan — riesgo crediticio y explicabilidad

1. Perfilar `credit_risk_dataset.csv` y confirmar la semántica de `loan_status`.
2. Implementar la limpieza y las variables de crédito; revisar si `loan_grade` y `loan_int_rate` están disponibles en el momento de la decisión.
3. Entrenar una línea base y un modelo crediticio.
4. Evaluar discriminación y calibración de las probabilidades; explicar casos individuales.
5. Implementar el servicio y la página de riesgo crediticio.
6. Documentar las limitaciones para recomendar un monto de crédito: la probabilidad de impago por sí sola no determina un límite óptimo.

**Entrega final:** pipeline de crédito, modelo evaluado, explicaciones y página de riesgo.

### Rhamses — grafos de transacciones

1. Construir la red `nameOrig → nameDest` a partir de una muestra y luego ampliar el procesamiento.
2. Calcular indicadores de cuentas y conexiones.
3. Definir patrones sospechosos y revisar ejemplos; documentar el método de evaluación.
4. Implementar consultas de red y endpoints para consultar cuentas y subgrafos.
5. Crear una visualización con subgrafos manejables y rotular los resultados como simulados.

**Entrega final:** análisis de grafos, criterios de alerta, endpoints de consulta y página de redes.

### Taco — pipeline transaccional y segmentación

1. Implementar la ingesta transaccional y sus controles de calidad.
2. Generar Silver y definir el mart de transacciones en Gold junto con Cueva.
3. Construir variables de comportamiento por cuenta cuando sus identidades sean fiables.
4. Crear segmentos, evaluar su calidad y explicar las características de cada grupo.
5. Implementar el servicio de consulta y la página de segmentos.

**Entrega final:** pipeline transaccional reproducible, tablas Gold, segmentación evaluada y página de segmentos.

### Gerardo — pronósticos, monitoreo y reproducción

1. Agregar montos y cantidades de transacciones por `step` y analizar la cobertura temporal.
2. Comparar una línea base temporal con un método principal de pronóstico.
3. Evaluar retrospectivamente, respetando el orden de los periodos.
4. Añadir comparación de distribuciones entre periodos o lotes comparables, con límites documentados.
5. Implementar el servicio y la página temporal.
6. Preparar el comando de ejecución reproducible y Docker cuando el recorrido local funcione.

**Entrega final:** serie agregada, pronóstico evaluado, reporte de deriva, página temporal e instrucciones de ejecución.

Con los datos actuales se pronosticará volumen transaccional simulado. Para medir liquidez bancaria faltan datos de exposición y disponibilidad de fondos. Los horizontes se fijarán tras conocer la cobertura real; no se asumirán fechas calendario a partir de `step`.

### Angel — reclamos, NLP y navegación del panel

1. Perfilar `consumer_complaints.csv` y medir cuántos reclamos tienen narrativa.
2. Implementar la limpieza estructurada y del texto.
3. Crear una línea base y un análisis principal de categorías o tópicos.
4. Evaluar los resultados mediante métricas pertinentes y revisión documentada de ejemplos.
5. Implementar el servicio y la página de reclamos, con tendencias y ejemplos permitidos.
6. Construir con Rhamses el esqueleto de navegación del panel y su conexión con la API.

**Entrega final:** pipeline de reclamos, análisis NLP evaluado, página de reclamos y navegación inicial del panel.

## Trabajo compartido y equilibrio

| Pareja | Responsabilidad común |
| --- | --- |
| Cueva y Taco | Contrato transaccional, calidad, estructura Silver/Gold y variables compartidas. |
| Sevan y Gerardo | Formato de métricas, registro de experimentos, artefactos y reproducción. |
| Rhamses y Angel | Contratos de la API, navegación del panel y conexión entre ambos. |

Cada integrante implementa su propia vista, documenta su módulo y prueba su lógica. Sevan mantiene el procesamiento de crédito y Angel el de reclamos; Taco establece el patrón compartido y mantiene el procesamiento transaccional.

El alcance inicial será una línea base y un método principal por módulo. Las asociaciones avanzadas, modelos adicionales y reentrenamiento automático se incorporarán después de integrar las primeras entregas. Si una tarea común supera un hito o un módulo exige claramente más esfuerzo, el equipo redistribuirá esa tarea antes de ampliar otros módulos.

## Primeras entregas

| Integrante | Primera entrega verificable |
| --- | --- |
| Cueva | Reporte de PaySim, distribución de `isFraud` y lista inicial de variables. |
| Sevan | Reporte del dataset crediticio y propuesta de separación y evaluación. |
| Rhamses | Red pequeña construida con una muestra y ejemplos de consultas. |
| Taco | Primer script que produzca Silver desde el CSV transaccional. |
| Gerardo | Tabla de monto y cantidad por `step`, con análisis de cobertura. |
| Angel | Reporte de cobertura de narrativas y propuesta de páginas del panel. |

## Criterio común de entrega

Cada módulo debe incluir entradas y salidas documentadas, ejecución reproducible, evaluación contra una línea base, su vista en el panel y limitaciones. Los notebooks pueden apoyar la exploración; la lógica que produce resultados finales debe ejecutarse desde código en `src/bankshield/` y comandos en `scripts/`.
