# Plan de desarrollo y responsabilidades

Este documento concreta las etapas y entregas de los seis integrantes. Complementa las [bases del proyecto](bases-del-proyecto.md) y el [inventario de datasets](datasets.md). Las fechas se acordarán cuando el equipo confirme su disponibilidad y los requisitos del curso.

## Revisión del avance — 9 de octubre de 2026

Estado basado en el código, reportes y referencias Git disponibles en esta copia local. No incluye trabajo sin subir ni cambios remotos posteriores al último fetch. Las responsabilidades siguientes se mantienen; esta sección registra qué entregas ya existen y cuál es el próximo paso verificable. Los reportes históricos no equivalen a una ejecución nueva validada.

| Integrante | Avance verificable | Pendientes y siguiente entrega |
| --- | --- | --- |
| Cueva | Perfil, variables, entrenamiento temporal desde Bronze o Silver, scoring, API de predicción/evaluación y página conectada a la API. Entrenamiento completo desde Silver reproducido: AP 0.961840, precisión 0.796634 y recall 0.992511. Ejemplos TP/FP/FN/TN y condiciones descriptivas disponibles. | Revisión compartida con Taco del contrato Silver y con Rhamses–Angel de API/navegación. Explicaciones de atribución del modelo y asociaciones quedan como ampliaciones posteriores; las condiciones mostradas no son explicaciones causales. |
| Sevan | CSV crediticio disponible. No se encontró código, reporte ni entrega específica de crédito en las referencias Git locales revisadas. | Primera entrega: perfil, semántica de `loan_status`, contrato de variables y estrategia de partición. Después: Silver, línea base, modelo, calibración, explicaciones, servicio y página. Revisar disponibilidad de `loan_grade` y `loan_int_rate` al decidir. |
| Rhamses | Ingesta de aristas, grafo dirigido, métricas, patrones, servicios, endpoints FastAPI y página Streamlit. Reporte sobre muestra de 50,000 transacciones. | Evaluar alertas con casos y etiquetas; revisar escala y límites de subgrafos. La página usa servicios directamente: falta conexión API → panel. Corregir caché de API: una vez cargada, ignora cambios de `limit`. |
| Taco | Bronze → Silver con tipos, controles, configuración, pruebas y reporte completo de 6,362,620 filas, sin rechazos ni duplicados exactos detectados. Silver ya regenerado en esta copia; el reporte incorpora huella del Parquet para vincularlo al entrenamiento. | Revisar con Cueva la integración implementada; definir mart y variables de segmentación, línea base, agrupamiento evaluado, servicio y página. Revisar la utilidad de las cuentas: 6,353,307 orígenes únicos para 6,362,620 transacciones limitan el historial por origen. Gold temporal de Gerardo no equivale al mart de segmentación. |
| Gerardo | Perfilado temporal, construcción Gold por `step`, controles de conservación, exploración, autocorrelación y generación de gráficos. Reporte de 743 pasos; tramo final solo fraude desde 719. | Regenerar Gold y gráficos; definir periodo y horizonte. Comparar ingenuo y estacional de 24 pasos mediante evaluación retrospectiva; añadir método principal, monitoreo, servicio y página. Preparar reproducción y Docker cuando funcione el recorrido local. |
| Angel | Perfil de 555,957 reclamos, 66,806 narrativas (12.02%), anonimización, distribución y propuesta de panel. | Corregir fechas: actualmente se comparan cadenas MM/DD/YYYY y el rango contradice los conteos anuales. Primera entrega siguiente: Silver estructurado y limpieza de texto. Después: línea base NLP, análisis principal evaluado, servicio y página; completar navegación y conexión API con Rhamses. |

### Prioridades compartidas

1. Cueva–Taco: revisar la integración Silver → variables de fraude ya implementada. Conserva predictores y cortes temporales; el entrenamiento verifica reporte completo, controles, recuentos y huellas de Bronze/Parquet.
2. Rhamses–Angel: cerrar contrato API → panel, conectar redes y definir respuestas reutilizables para nuevas páginas.
3. Sevan–Gerardo: acordar plantilla de métricas, configuración, versiones y artefactos; aplicarla a crédito y pronósticos.
4. Todos: ejecutar pruebas de sus módulos y una demostración desde un entorno limpio antes de ampliar el alcance.

### Estado de integración y reproducción

- Existen API y página de fraude conectadas entre sí, además de API de grafos y página de redes. Redes todavía consulta servicios directamente; crédito, segmentos, temporal y reclamos no tienen vistas finales.
- Silver está regenerado con 6,362,620 filas y controles aprobados. Gold temporal sigue sin regenerarse en esta copia. Los derivados están excluidos de Git.
- Modelo anterior en `artifacts/models/fraud/` y experimento Silver en `artifacts/models/fraud-silver/`, ambos locales. Otro clon debe reconstruirlos.
- Entorno común instalado con Python 3.12.14 y `pip check` aprobado. Suite completa: **111 pruebas aprobadas**, incluidas API, equivalencia Bronze/Silver e interacciones de Streamlit. Las pruebas de grafos aún usan un grafo en memoria y no validan su carga completa del CSV.
- Demostración de fraude comprobada con AppTest contra una API real en localhost y el artefacto Silver: formulario, métricas e identidad del modelo coinciden. No sustituye una revisión visual en navegador ni las revisiones del equipo.
- Procedencia y licencia de los tres CSV siguen pendientes. No hay llave compartida demostrada entre fuentes.
- La guía de ejecución, dependencias, comprobaciones y criterios de aceptación está en [pruebas y reproducción](pruebas-reproduccion.md).

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

#### Incremento implementado — 9 de octubre de 2026

- `api/routers/fraud.py`: `POST /api/fraud/predict` recibe únicamente `type`,
  `amount` y `oldbalanceOrg`. Valida tipos, números finitos no negativos y
  rechaza campos adicionales. Devuelve score, alerta, umbral, identidad del
  modelo y marcas de simulación/score no calibrado.
- `GET /api/fraud/model`: métricas, particiones y versiones embebidas en el
  mismo artefacto que predice. No usa un JSON de métricas independiente.
- Carga diferida y reutilizada del artefacto; responde 503 si falta o no es
  compatible. La API puede iniciar y atender otros módulos sin modelo de
  fraude. Un archivo reemplazado se recarga según su modificación/tamaño.
- `dashboard/pages/01_fraude.py`: formulario mediante HTTP, timeout y manejo
  de errores; resultado persistente al consultar métricas; condiciones de
  entrada claramente diferenciadas de atribuciones del modelo.
- `read_fraud_dataset` consume CSV o Parquet por bloques con el mismo contrato
  temporal. `train_fraud.py --input-format silver` requiere el reporte de
  calidad completo, sin rechazos, con controles aprobados, recuentos iguales
  al perfil y huellas coincidentes. Reportes Silver antiguos sin huella de
  salida deben regenerarse. No cambia automáticamente la fuente del modo CSV.
- `scripts/analyze_fraud_errors.py`: recupera los primeros ejemplos por
  resultado TP/FP/FN/TN en prueba y contrasta la matriz con las métricas del
  modelo. Los ejemplos no son representativos y no se usan para ajustar el
  umbral ni los hiperparámetros.

#### Evidencia de ejecución

- Silver completo: 6,362,620 filas, cero rechazos; controles aprobados y SHA-256
  del Parquet registrado en `artifacts/reports/transactions_silver.json`.
- Entrenamiento Silver: 4,463,587 filas de entrenamiento, 980,416 de validación
  y 918,617 de prueba; cortes 323/378 conservados, umbral 0.09878304839801404.
- Prueba: AP 0.961840, precisión 0.796634, recall 0.992511, F1 0.883850;
  TP=3976, FP=1015, FN=30, TN=913596. Se reprodujeron las métricas anteriores
  sin usarlas para escoger una configuración nueva.
- Suite: 111 pruebas aprobadas, resultado local en
  `artifacts/reports/test-suite-cueva.txt`. Hay avisos de librerías en pruebas
  de series cortas y deprecación de TestClient; no produjeron fallos.
- Demo contra API local: TRANSFER de monto 1000 y saldo 500 devuelve score
  0.000005636521, sin alerta. El formulario coincide con la API y las métricas
  corresponden al mismo modelo. Una entrada negativa devuelve 422.
- Modelo y reporte del experimento: `artifacts/models/fraud-silver/` y
  `artifacts/reports/fraud-silver-training.md`. Ejemplos de errores:
  `artifacts/reports/fraud-silver-errors.json`; verificación de demo:
  `artifacts/reports/fraud-demo-check.json`. Estos artefactos no se suben a Git.

#### Reproducir la entrega de fraude

Desde la raíz, con Bronze completo y Python 3.12 disponible:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_env.ps1
.venv-pruebas/Scripts/python.exe scripts/profile_fraud.py
.venv-pruebas/Scripts/python.exe scripts/build_silver.py --quality-markdown artifacts/reports/transactions_silver_full.md
.venv-pruebas/Scripts/python.exe scripts/train_fraud.py --input-format silver --input data/silver/transactions/transactions.parquet --output artifacts/models/fraud-silver --markdown artifacts/reports/fraud-silver-training.md
.venv-pruebas/Scripts/python.exe scripts/analyze_fraud_errors.py
```

La generación y el entrenamiento requieren memoria y procesan el archivo
completo. El experimento se guarda separado del artefacto anterior. Para
iniciar API, en una terminal:

```powershell
$env:BANKSHIELD_FRAUD_MODEL='artifacts/models/fraud-silver/model.joblib'
.venv-pruebas/Scripts/python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

En otra terminal:

```powershell
.venv-pruebas/Scripts/python.exe -m streamlit run dashboard/app.py
```

Abrir `http://localhost:8501`, seleccionar Fraude y evaluar. Ejemplo de alerta:
TRANSFER con monto 36942.13 y saldo 36942.13. No usar la etiqueta al predecir.
Swagger está en `http://127.0.0.1:8000/docs`. `BANKSHIELD_API_URL` permite
configurar otra dirección en el panel. Sin `BANKSHIELD_FRAUD_MODEL`, la API
busca el modelo anterior en `artifacts/models/fraud/model.joblib`.

#### Pendientes de Cueva

1. Revisar con Taco el contrato, las políticas de duplicados y los controles
   nuevos de procedencia; la implementación no acredita revisión de la pareja.
2. Revisar con Rhamses–Angel el contrato HTTP y navegación; comprobar la
   apariencia en navegador y el recorrido desde otro clon.
3. Documentar disponibilidad real del saldo anterior si cambia el sistema
   objetivo. La demostración actual continúa limitada a PaySim.
4. Ampliar explicaciones con atribuciones del modelo o asociaciones sencillas
   cuando exista una pregunta analítica útil. Las condiciones descriptivas y
   los ejemplos de errores ya están; no se implementaron asociaciones adicionales.

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
