# BankShield Analytics: contexto completo del proyecto

**Proyecto:** Minería de Datos, Grupo 6.

**Fecha del documento:** 13 de octubre de 2026.

**Propósito:** permitir que otra persona comprenda el proyecto, su alcance, los datos, la implementación disponible, los resultados y el trabajo pendiente sin necesitar la conversación original.

Este documento describe la copia local del proyecto revisada en esa fecha. Incluye cambios locales que pueden no estar publicados en el repositorio remoto. Los resultados numéricos proceden de los reportes existentes; para preparar este documento no se volvieron a entrenar modelos ni a ejecutar la suite de pruebas.

**Actualización de pendientes — 20 de octubre de 2026:** el contraste con el PDF del curso amplía el trabajo futuro con regresión numérica, asociaciones descubiertas, comparación de grafos e integración/reproducción. El historial del desempeño es recomendado y Docker opcional. Para continuar, usar [pendientes vigentes](docs/pendientes-cierre-2026-10-20.md) y sus encargos individuales; los resultados siguientes describen las seis capacidades existentes, no acreditan esas ampliaciones.

## 1. Definición del proyecto

**BankShield Analytics es una plataforma académica de minería de datos y analítica financiera que transforma tres fuentes independientes en productos analíticos para estudiar fraude, riesgo crediticio, redes de transacciones, segmentos de comportamiento, actividad temporal y reclamos de consumidores.**

El proyecto abarca el recorrido desde los archivos originales hasta su limpieza, la construcción de variables, el análisis, la evaluación de modelos y la presentación de resultados mediante una API y un panel interactivo.

La finalidad de negocio es apoyar la priorización de revisiones y comprender patrones. La finalidad académica es demostrar un proceso reproducible, con métodos de referencia, evaluación, trazabilidad y explicaciones de los límites de cada resultado.

Los datos transaccionales son simulados. Las fuentes de crédito y reclamos pertenecen a otras poblaciones. Los resultados son estimaciones y hallazgos de una demostración académica; su utilidad en una entidad financiera real necesitaría validación con datos propios.

### Explicación breve para presentar el proyecto

> BankShield utiliza datos de operaciones, préstamos y reclamos para explorar diferentes problemas financieros. A partir de esos datos construye seis módulos: fraude, crédito, redes, segmentos, pronósticos y reclamos. Cada módulo tiene un propósito, una evaluación y una vista en el panel. Las fuentes se mantienen separadas porque no existe una llave común de clientes. El proyecto muestra cómo convertir datos en información útil y cómo reconocer las limitaciones de los resultados.

## 2. Problema y objetivos

### Problema de negocio

Las necesidades que orientan el proyecto son:

1. Identificar operaciones que merezcan revisión por posible fraude.
2. Comprender el resultado de los préstamos y explorar estimaciones de riesgo.
3. Analizar relaciones entre cuentas y patrones de circulación de dinero.
4. Describir grupos de cuentas con comportamientos similares.
5. Explorar y proyectar cantidad y monto de operaciones en el tiempo simulado.
6. Comprender la distribución de reclamos y clasificar el producto sugerido por sus relatos.

### Objetivo general

Construir una demostración reproducible de analítica financiera que conecte preparación de datos, métodos de minería de datos, evaluación y consulta de resultados desde una aplicación local.

### Objetivos específicos

- Comprender qué representa cada fuente y qué preguntas permite responder.
- Medir nulos, duplicados, valores implausibles y cobertura de información.
- Mantener los originales y registrar las transformaciones realizadas.
- Evitar utilizar etiquetas o información posterior como predictores de decisiones anteriores.
- Comparar los métodos principales con referencias sencillas.
- Separar entrenamiento, validación y prueba según las posibilidades de cada fuente.
- Mostrar resultados, ejemplos y limitaciones mediante FastAPI y Streamlit.
- Permitir que otro integrante reconstruya artefactos y compruebe los recorridos.

## 3. Alcance y evolución

La presentación de comprensión del negocio y de los datos se centra en las tres fuentes y las primeras fases metodológicas. La copia actual del repositorio ya contiene preparación, modelos, servicios y páginas para seis módulos.

El primer incremento planteado fue un recorrido completo de fraude: cargar operaciones, controlar calidad, preparar datos, entrenar un modelo y mostrar predicciones. Ese recorrido sirvió de base para desarrollar los otros módulos.

| Módulo | Pregunta central | Producto disponible en la copia local |
| --- | --- | --- |
| Fraude | ¿Qué operaciones deberían revisarse? | Score, alerta, umbral, métricas y patrones descriptivos. |
| Crédito | ¿Qué estima el modelo sobre la clase de resultado del préstamo? | Probabilidad calibrada de impago asumido y factores por oclusión. |
| Redes | ¿Cómo se conectan las cuentas y qué patrones destacan? | Indicadores, ranking, consultas de cuentas y subgrafos. |
| Segmentos | ¿Qué grupos de comportamiento aparecen entre destinos recurrentes? | Perfiles, métricas del agrupamiento y consulta de cuentas. |
| Pronósticos | ¿Cómo evolucionan cantidad y monto de operaciones? | Proyección Naive, comparación de métodos y monitoreo histórico. |
| Reclamos | ¿Qué productos y motivos aparecen, y qué producto sugiere un relato? | Tendencias, clasificador de producto, métricas y ejemplos. |

### Ampliaciones propuestas que no deben confundirse con entregas actuales

- Recomendación de montos o límites de crédito.
- Validación con tráfico de una entidad financiera real.
- Comunidades y evaluación temporal avanzada de redes.
- Atribuciones individuales adicionales del modelo de fraude.
- Reglas de asociación aprendidas más allá de los patrones fijos implementados.
- Extracción de tópicos y búsqueda semántica de reclamos, propuestas en documentos iniciales.
- Pronósticos de liquidez bancaria: los objetivos actuales son volumen y monto transaccionado.
- Monitoreo de producción con observaciones futuras.
- Empaquetado Docker/Compose validado y reproducción integral en otra PC.

## 4. Fuentes de datos

### Regla fundamental: no hay una llave común de clientes

Las tres bases representan entidades y poblaciones diferentes. No existe una clave compartida demostrada para unir transacciones, crédito y reclamos por persona.

`nameOrig` y `nameDest` identifican cuentas simuladas dentro de la fuente transaccional. `complaint_id` identifica una queja. El archivo de crédito no trae una clave de cliente ni fecha.

La integración se realiza mediante módulos y navegación en la misma aplicación. Cada fuente conserva su propio análisis; no se inventa una correspondencia entre sus filas.

### 4.1. Operaciones con esquema PaySim

- **Archivo:** `data/bronze/transactions/PS_20174392719_1491204439457_log.csv`.
- **Filas:** 6.362.620 operaciones simuladas.
- **Operaciones marcadas como fraude:** 8.213.
- **Prevalencia global:** 0,129082 %, aproximadamente 0,129 %.
- **Cobertura:** 743 pasos, del 1 al 743.
- **Tiempo:** cada `step` representa una hora simulada, no una fecha calendario.
- **Moneda:** no identificada en la fuente de trabajo.

| Campo | Significado y uso |
| --- | --- |
| `step` | Orden temporal de la simulación; permite separar periodos y agregar actividad. |
| `type` | Tipo de movimiento: PAYMENT, TRANSFER, CASH_OUT, DEBIT o CASH_IN. |
| `amount` | Monto de la operación. |
| `nameOrig`, `nameDest` | Identificadores de las cuentas de origen y destino. |
| `oldbalanceOrg`, `oldbalanceDest` | Saldos anteriores. |
| `newbalanceOrig`, `newbalanceDest` | Saldos posteriores; no se usan como predictores del modelo inicial de fraude. |
| `isFraud` | Etiqueta de fraude para entrenamiento y evaluación. |
| `isFlaggedFraud` | Marca de otro mecanismo; excluida del clasificador de fraude. |

**Hallazgos:**

- TRANSFER: 532.909 operaciones, 4.097 fraudes y tasa de 0,768799 %.
- CASH_OUT: 2.237.500 operaciones, 4.116 fraudes y tasa de 0,183955 %.
- Los demás tipos tienen cero fraudes registrados en esta copia.
- La capa Silver documenta 6.362.620 filas sin nulos ni rechazos.
- La ausencia de nulos no elimina las limitaciones de la simulación: existen residuos de balance que se conservan para análisis descriptivo.
- El último paso con operaciones no fraudulentas es 718. El tramo 719–743 contiene exclusivamente fraude y debe interpretarse como un cierre particular del simulador.

### 4.2. Crédito

- **Archivo:** `data/bronze/credit/credit_risk_dataset.csv`.
- **Filas originales:** 32.581.
- **Clase positiva original:** 7.108 registros, aproximadamente 21,82 %.
- **Duplicados exactos eliminados:** 165.
- **Filas rechazadas por valores implausibles:** 7.
- **Filas Silver:** 32.409.
- **Clase positiva en Silver:** aproximadamente 21,87 %.

Campos relevantes: `person_age`, `person_income`, `person_home_ownership`, `person_emp_length`, `loan_intent`, `loan_grade`, `loan_amnt`, `loan_int_rate`, `loan_status`, `loan_percent_income`, `cb_person_default_on_file` y `cb_person_cred_hist_length`.

**Interpretación pendiente:** el módulo trata `loan_status = 1` como impago asumido. El inventario menciona respaldo en una copia de OpenML, pero la definición debe confirmarse con la fuente original. El resultado debe conservar ese carácter provisional.

La limpieza rechaza cinco edades fuera de rango y dos antigüedades laborales imposibles. Conserva nulos permitidos con indicadores de ausencia y recalcula `loan_percent_income` como monto dividido entre ingreso.

El archivo no corresponde al esquema de Home Credit. Tampoco permite una evaluación temporal o por cliente porque no contiene esas claves.

### 4.3. Reclamos de consumidores

- **Archivo:** `data/bronze/complaints/consumer_complaints.csv`.
- **Filas:** 555.957 reclamos.
- **Periodo:** 1 de diciembre de 2011 a 25 de abril de 2016.
- **Con relato:** 66.806, aproximadamente 12,02 %.
- **Sin relato:** 489.151, aproximadamente 87,98 %.
- **Relatos con marcas de anonimización `XXXX`:** 56.744, aproximadamente 84,94 % de los relatos.
- **Textos utilizados para entrenar el clasificador:** 66.736; se excluyen 70 relatos con menos de cinco palabras.

| Campo | Uso |
| --- | --- |
| `date_received` | Fecha de recepción; tendencias y orden de aparición de textos. |
| `product`, `sub_product` | Producto y subproducto involucrados. |
| `issue`, `sub_issue` | Motivo y detalle del motivo. |
| `consumer_complaint_narrative` | Relato utilizado por el módulo de procesamiento de lenguaje natural. |
| `company` | Empresa relacionada con la queja. |
| `complaint_id` | Identificador de reclamo, sin vínculo con las otras fuentes. |
| Campos de consentimiento y respuesta | Contexto de publicación y tratamiento del reclamo. |

El análisis de productos y motivos cubre la base completa según la disponibilidad de sus campos. La clasificación textual cubre el subconjunto de relatos utilizables, publicados con consentimiento.

Mortgage concentra 186.475 reclamos, Debt collection 101.052 y Credit reporting 91.854. Estos recuentos describen volumen de quejas; no constituyen tasas de insatisfacción ajustadas por cantidad de clientes o contratos.

El perfil también registra 7.057 casos cuya fecha de envío a la empresa es anterior a la de recepción. Se conservan como un hallazgo de calidad.

### 4.4. Procedencia y trazabilidad

Los tres originales se conservan en Bronze y se distribuyen mediante Git LFS. La procedencia exacta, la versión y las condiciones de uso de cada copia siguen pendientes de confirmación completa.

Las huellas documentadas permiten comprobar que se utiliza la misma copia:

| Fuente | SHA-256 |
| --- | --- |
| Operaciones | `16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b` |
| Crédito | `ce3c6d2167717bf1627d1c0c81cbccd28323cd4aa7b96d542599366d5ff6aac8` |
| Reclamos | `df219bbcf0e8233f33eb83454ef9b3451adf471db29618acfb36d2dacc40ed3f` |

## 5. Metodología

La presentación organiza el proyecto con **CRISP-DM**: comprensión del negocio, comprensión de los datos, preparación, modelado, evaluación y entrega. Se trabaja en ciclos que permiten revisar hallazgos y ajustar decisiones.

KDD se utiliza como marco para explicar la obtención de conocimiento a partir de datos, y SEMMA como referencia para las actividades de exploración y modelado. CRISP-DM conecta esas actividades con las preguntas de negocio.

### Preguntas de la presentación inicial

1. ¿Dónde se concentra el fraude simulado?
2. ¿Qué muestra el resultado de los préstamos?
3. ¿Qué productos generan más reclamos?
4. ¿Cuántos reclamos permiten analizar el relato?

### Principios de evaluación aplicados

- Las etiquetas no deben aparecer entre los predictores.
- La información posterior a una operación no debe presentarse como disponible antes de ella.
- La selección de parámetros y umbrales se realiza en validación, conservando prueba para evaluación.
- Los transformadores se ajustan con entrenamiento, no con toda la base.
- Cada módulo compara su método con una referencia apropiada.
- Los supuestos de coste son académicos y no pérdidas monetarias verificadas.
- Los resultados de muestras se identifican como tales.
- Las evaluaciones de fuentes distintas no se interpretan como si pertenecieran a la misma población.

## 6. Arquitectura y tecnologías

### Flujo general

```text
CSV originales en Bronze
        |
        v
Perfilado, validación y limpieza
        |
        v
Silver: tablas tipadas y controladas en Parquet
        |
        +--> Gold: mart transaccional y agregados temporales
        |
        +--> Variables, entrenamiento y evaluación por módulo
                         |
                         v
              Modelos y reportes locales
                         |
                         v
              Servicios Python compartidos
                         |
                         v
                  API de FastAPI
                         |
                         v
                Panel de Streamlit
```

No todos los módulos recorren una tabla Gold independiente. Crédito y reclamos tienen sus propios pipelines desde Silver; grafos utiliza la fuente transaccional para construir la red.

### Capas

| Capa | Contenido y propósito |
| --- | --- |
| Bronze | Originales inmutables, separados por dominio. |
| Silver | Datos limpios, tipos, reglas de validez y reportes de calidad. |
| Gold | Tablas analíticas y agregados para consultas y modelos. |
| Artefactos | Modelos, métricas, ejemplos, reportes y metadatos generados. |
| Servicios | Lógica reutilizable para consultar datos y realizar predicciones. |
| API | Endpoints HTTP de los seis módulos. |
| Panel | Formularios, gráficos, consultas, métricas y explicaciones. |

El mart Gold transaccional conserva **una fila por operación**. El Gold temporal tiene **una fila por `step`**, con cantidad, monto total, monto promedio, cantidad de fraudes y tasa de fraude.

### Tecnologías utilizadas

| Tecnología | Función |
| --- | --- |
| Python | Pipelines, análisis, modelos, servicios y pruebas. |
| pandas y NumPy | Tratamiento de tablas y cálculo numérico. |
| PyArrow / Parquet | Almacenamiento de datos derivados. |
| scikit-learn y joblib | Transformaciones, clasificación, agrupamiento y artefactos. |
| NetworkX | Grafos dirigidos e indicadores de red. |
| statsmodels | Comparaciones de pronóstico con Holt-Winters. |
| FastAPI, Pydantic y Uvicorn | API, validación de entradas y servidor local. |
| Streamlit, requests y PyVis | Panel, consumo HTTP y visualización de redes. |
| unittest y AppTest | Pruebas de lógica, API e interacciones del panel. |
| Git, Git LFS y GitHub Actions | Código, archivos originales y workflow de pruebas. |

DuckDB y Docker Compose aparecen en la propuesta arquitectónica inicial. No se presentan aquí como una infraestructura validada de la demo actual.

## 7. Módulos y resultados documentados

### 7.1. Fraude supervisado y patrones

**Responsable principal:** Cueva.

El modelo evalúa una operación utilizando su tipo, monto y saldo anterior del origen, junto con dos variables derivadas: relación entre monto y saldo, e indicador de que el monto supera el saldo.

Se excluyen los identificadores de cuentas, las etiquetas, los saldos posteriores y la marca de otro detector.

- Referencia: `DummyClassifier` con prevalencia de entrenamiento.
- Modelo: `HistGradientBoostingClassifier`.
- Entrenamiento: steps 1–323, 4.463.587 filas.
- Validación: steps 324–378, 980.416 filas.
- Prueba: steps 379–743, 918.617 filas.
- Umbral seleccionado en validación: aproximadamente 0,09878305.
- Costes supuestos: falso positivo = 1; falso negativo = 20.
- No se aplicó submuestreo, sobremuestreo ni balanceo de clases en el experimento documentado.

| Métrica de prueba del clasificador con umbral seleccionado | Resultado |
| --- | ---: |
| Average Precision (AP) | 0,961840 |
| Precisión | 0,796634 |
| Recall | 0,992511 |
| F1 | 0,883850 |
| Verdaderos positivos | 3.976 |
| Falsos positivos | 1.015 |
| Falsos negativos | 30 |
| Verdaderos negativos | 913.596 |

AP es Average Precision; el reporte distingue esta medida del área trapezoidal de la curva precisión-recall.

También existen seis patrones fijos con soporte, confianza, lift y cobertura. Son asociaciones retrospectivas de la simulación, no explicaciones individuales de las predicciones del clasificador.

**Límites:** el score no está calibrado como probabilidad de fraude real. Las cifras describen PaySim y no prueban generalización a una entidad financiera ni a cuentas completamente nuevas. Una elevada exactitud por sí sola sería insuficiente debido a la baja prevalencia.

### 7.2. Riesgo crediticio y explicabilidad

**Responsable principal:** Sevan.

El módulo estima la probabilidad de la clase positiva de `loan_status`, interpretada provisionalmente como impago. Utiliza información de solicitud e historial y excluye `loan_grade` y `loan_int_rate` del modelo principal porque reflejan una evaluación del prestamista.

- Referencias: prevalencia constante y regresión logística.
- Modelo principal: `HistGradientBoostingClassifier`.
- Partición: aleatoria estratificada 70/15/15 con semilla fija.
- Filas: 22.685 de entrenamiento, 4.862 de validación y 4.862 de prueba.
- Calibración: sigmoide ajustada en validación.
- Umbral: aproximadamente 0,1553.
- Costes supuestos: falso positivo = 1; falso negativo = 5.
- Explicación: hasta cinco factores por oclusión, sustituyendo variables por referencias de entrenamiento.

| Métrica de prueba del modelo principal calibrado | Resultado |
| --- | ---: |
| ROC-AUC | 0,8886 |
| AP | 0,7968 |
| Brier | 0,0871 |
| ECE | 0,0118 |
| Precisión al umbral seleccionado | 0,522 |
| Recall al umbral seleccionado | 0,792 |

**Límites:** la etiqueta requiere confirmación original; no hay evaluación temporal o por cliente; las explicaciones describen al modelo y no causalidad. El modelo utiliza edad, cuyo uso necesitaría revisión antes de una aplicación real. La salida no recomienda un monto ni un límite de crédito.

### 7.3. Grafos de transacciones

**Responsable principal:** Rhamses.

Construye una red dirigida: cada cuenta es un nodo y cada relación origen–destino es una arista. Varias operaciones entre el mismo par se agregan, conservando conteos, montos y atributos.

Incluye grados de entrada y salida, centralidades, PageRank, número de orígenes y destinos, montos enviados y recibidos, flujo neto y componentes débilmente conexos.

Patrones exploratorios: muchos destinos, muchos orígenes, ciclos cortos, conexiones de alto monto y flujos netos extremos.

El panel permite consultar cuentas, ranking y subgrafos. La demo arranca con una muestra de 10.000 operaciones; la evaluación documentada de alertas utiliza 50.000. Los subgrafos se limitan a 500 nodos.

**Límites:** los patrones no prueban fraude. Los resultados de muestra no representan la red completa. Los umbrales son exploratorios, la agregación pierde detalle individual y faltan una referencia comparable cerrada y una evaluación predictiva temporal. Comunidades no es una capacidad implementada en este alcance.

### 7.4. Transacciones y segmentación

**Responsable principal:** Taco.

Además de Silver y el mart Gold transaccional, el módulo agrupa cuentas de destino con diez o más operaciones recibidas.

- Universo: 146.629 cuentas de destino recurrentes.
- Referencia: grupos por cuantiles de actividad.
- Modelo: MiniBatchKMeans sobre variables estandarizadas de comportamiento.
- Número de grupos: `k = 2`, seleccionado por silueta.
- Silueta: 0,2305, calculada sobre una muestra.
- Estabilidad: ARI medio 0,7280 en remuestras.
- Segmento 0: 48.334 cuentas.
- Segmento 1: 98.295 cuentas.

El segmento 0 presenta, en promedio, mayor actividad recibida, mayor monto medio y mayor proporción de transferencias que el segmento 1.

**Corrección relevante:** `fraud_rate_received` queda fuera de la matriz de agrupamiento. Las etiquetas solo se usan después para describir grupos. Existe una prueba que verifica que cambiar únicamente `isFraud` no altera la matriz ni las asignaciones.

**Límites:** los grupos son perfiles de comportamiento simulado, no categorías de riesgo validadas. Se excluyen los destinos con menos de diez operaciones, incluyendo la mayoría de cuentas que reciben una sola vez.

### 7.5. Pronósticos y monitoreo histórico

**Responsable principal:** Gerardo.

El módulo agrega operaciones por `step` y analiza dos objetivos: cantidad de transacciones y monto total.

- Serie Gold completa: 743 observaciones.
- Evaluación operativa: steps 1–718.
- Backtesting: cuatro ventanas expansivas con horizonte de 24 steps.
- Referencias: Naive y Naive estacional con rezago 24.
- Comparación: tres configuraciones Holt-Winters aditivas.
- Métrica principal: MAE; también se registran RMSE y sMAPE.
- Método servido: Naive, que proyecta el último valor observado.

| Objetivo | MAE promedio de Naive |
| --- | ---: |
| Cantidad de transacciones | 1.366,94 operaciones |
| Monto total | 215.326.691,23 unidades monetarias no identificadas |

Ninguna configuración Holt-Winters mejora el MAE promedio de Naive. La referencia estacional sigue siendo competitiva en algunas ventanas y obtiene menor sMAPE, por lo que la selección no implica superioridad universal ni precisión absoluta alta.

El monitoreo compara steps 694–718 con 719–743. Registra seis indicadores fuera de umbrales descriptivos: volumen, monto total, monto promedio, distribución de montos, mezcla de tipos y tasa de fraude.

**Límites:** se analiza una simulación corta. El monitoreo detecta un cambio histórico evidente, no anticipa deriva futura. Los intervalos de la página son descriptivos y no tienen cobertura calibrada. La proyección parte de la última observación disponible, por lo que no debe confundirse con la evaluación restringida al tramo operativo. No se pronostica liquidez bancaria.

### 7.6. Reclamos y procesamiento de lenguaje natural

**Responsable principal:** Angel.

El módulo combina análisis estructurado de reclamos y clasificación del producto a partir del relato en inglés.

- Objetivo del clasificador: `product`, con 11 clases.
- Limpieza: tratamiento de censuras, fechas, montos y ruido del texto.
- Textos utilizables: 66.736.
- Referencia trivial: producto más frecuente.
- Referencia adicional: Naive Bayes multinomial.
- Modelo principal: TF-IDF de una y dos palabras más regresión logística con pesos balanceados.
- Parámetro `C = 5`, seleccionado por macro-F1 en validación.
- Partición por orden de primera aparición del texto, manteniendo textos idénticos en una sola partición para evitar compartirlos entre entrenamiento y prueba.

Debido a que los textos repetidos permanecen juntos, las fechas de filas pueden solaparse entre particiones: la separación se basa en la primera aparición del texto y no en un corte estricto de todas las filas por fecha.

| Método | Exactitud en prueba | Macro-F1 |
| --- | ---: | ---: |
| Producto más frecuente | 0,2542 | 0,0369 |
| Naive Bayes | 0,8201 | 0,6677 |
| TF-IDF + regresión logística | 0,8493 | 0,7278 |

La aplicación permite clasificar relatos, consultar tendencias, métricas y ejemplos de aciertos y errores.

**Límites:** aproximadamente 88 % de las quejas no tiene texto. El modelo sugiere un producto; no determina la resolución ni la calidad de atención. Sus scores no están calibrados. No se ha demostrado rendimiento en español. Los nombres de empresas tienen peso en la clasificación y pueden limitar la generalización a empresas nuevas. Las clases pequeñas tienen menos evidencia y la revisión humana cruzada de ejemplos sigue pendiente.

## 8. Aplicación y API

La aplicación tiene una portada y seis páginas. Las páginas consultan los resultados mediante HTTP a la API local.

- Panel: `http://127.0.0.1:8501`.
- Documentación interactiva de la API: `http://127.0.0.1:8000/docs`.
- API raíz: `http://127.0.0.1:8000/`.

| Método | Endpoint | Función |
| --- | --- | --- |
| GET | `/` | Estado de la API y lista de módulos. |
| POST | `/api/fraud/predict` | Score y alerta de una operación. |
| GET | `/api/fraud/model` | Métricas y metadatos del artefacto de fraude. |
| GET | `/api/fraud/patterns` | Asociaciones descriptivas compatibles con ese modelo. |
| POST | `/api/credit/predict` | Probabilidad calibrada y factores por oclusión. |
| GET | `/api/credit/model` | Evaluación y límites del modelo crediticio. |
| GET | `/api/graphs/summary` | Resumen de la muestra transaccional usada como red. |
| GET | `/api/graphs/account/{account_id}` | Indicadores y conexiones de una cuenta. |
| GET | `/api/graphs/subgraph/{account_id}` | Subgrafo alrededor de una cuenta. |
| GET | `/api/graphs/top` | Ranking de cuentas. |
| GET | `/api/graphs/patterns/suspicious` | Patrones exploratorios de red. |
| GET | `/api/segments/summary` | Métricas y perfiles de los segmentos. |
| GET | `/api/segments/{segment_id}/accounts` | Cuentas del grupo con paginación. |
| GET | `/api/segments/{segment_id}/account/{account_id}` | Detalle de una cuenta del grupo. |
| GET | `/api/forecast/projection` | Historia y proyección de cantidad o monto. |
| GET | `/api/forecast/monitoring` | Comparación histórica de ventanas. |
| POST | `/api/complaints/predict` | Producto sugerido por un relato. |
| GET | `/api/complaints/model` | Métricas y límites del clasificador textual. |
| GET | `/api/complaints/summary` | Distribuciones y tendencias de los reclamos. |
| GET | `/api/complaints/examples` | Ejemplos de la evaluación. |

Los contratos contemplan entradas inválidas y artefactos ausentes. En varios módulos, un artefacto ausente o incompatible genera 503; las entradas inválidas generan 422 y los recursos inexistentes pueden generar 404. Una respuesta correcta de la raíz no demuestra por sí sola que todos los artefactos estén disponibles.

## 9. Estructura del repositorio

```text
README.md                       Entrada general y enlaces al estado
BANKSHIELD_CONTEXTO_COMPLETO.md  Documento de contexto para compartir
docs/                           Contratos, calidad, resultados y guías
data/
  bronze/                       Originales con Git LFS
  silver/                       Tablas limpias generadas
  gold/                         Mart y agregados generados
src/bankshield/
  ingestion/                    Lectura y perfilado
  transforms/                   Limpieza y construcción de capas
  features/                     Variables y limpieza de texto
  models/                       Clasificación, agrupamiento y pronóstico
  evaluation/                   Evaluación temporal
  services/                     Servicios analíticos reutilizables
api/                            Aplicación FastAPI y routers
dashboard/                      Portada, páginas y recursos visuales
configs/                        Parámetros por módulo
scripts/                        Preparación, entrenamiento y demo
requirements/                   Dependencias
tests/unit/                     Suite de pruebas
artifacts/                      Modelos y reportes locales
notebooks/                      Exploración
output/                         Entregables generados
```

Silver, Gold, entornos virtuales y modelos se regeneran localmente y permanecen fuera de Git. Por eso, obtener el código no basta para disponer de toda la demo.

## 10. Cómo preparar y ejecutar la demo

Los comandos siguientes se ejecutan en PowerShell desde la raíz del proyecto. Requieren el repositorio completo, Python 3.12, Git LFS y los CSV originales completos.

El paquete declara Python 3.11 o posterior, pero el instalador común exige 3.12 para el entorno del equipo. No copiar entornos virtuales entre PCs.

### 10.1. Obtener originales y preparar dependencias

```powershell
git lfs version
git lfs pull
powershell -ExecutionPolicy Bypass -File scripts/setup_env.ps1
```

El instalador crea `.venv-pruebas`, instala el conjunto común, comprueba dependencias y ejecuta pruebas. Si no existe el lanzador `py`, admite `-PythonExecutable` con la ruta de Python 3.12.

### 10.2. Generar los artefactos faltantes

```powershell
.venv-pruebas/Scripts/python.exe scripts/prepare_demo.py
```

El preparador reutiliza archivos existentes y genera los faltantes de Silver, Gold, crédito, segmentos, monitoreo, reclamos y fraude. Sus reportes de demo se guardan en `artifacts/reports/demo/` para no sustituir los Markdown versionados.

La opción `--force` reconstruye las etapas que la admiten; la lógica de fraude conserva el modelo existente cuando ya está presente. La preparación puede requerir tiempo, memoria y espacio debido al tamaño transaccional. No hay un mínimo de RAM ni una duración garantizados documentados.

### 10.3. Iniciar y comprobar

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_demo.ps1
.venv-pruebas/Scripts/python.exe scripts/verify_demo.py
```

El arranque configura fraude-Silver, usa una muestra inicial de 10.000 operaciones para redes y levanta API/panel en localhost. La verificación necesita la API iniciada y comprueba recorridos con artefactos reales.

### 10.4. Detener

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop_demo.ps1
```

En la PC preparada también existen accesos locales **Abrir BankShield** y **Cerrar BankShield**. Si cambia la ubicación de la carpeta, pueden recrearse con:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/create_demo_shortcuts.ps1
```

### 10.5. Ejecutar la suite por separado

```powershell
.venv-pruebas/Scripts/python.exe -m unittest discover -s tests/unit -v
```

`requirements/common.txt` reúne los extras del proyecto mediante rangos compatibles. No es un bloqueo exacto de versiones; para comparar métricas históricas hay que revisar las versiones registradas en los artefactos.

## 11. Ejemplos para mostrar el proyecto

Estos casos corresponden a la demo documentada; sus salidas dependen del artefacto cargado.

### Fraude

| Tipo | Monto | Saldo anterior del origen | Resultado documentado de fraude-Silver |
| --- | ---: | ---: | --- |
| TRANSFER | 1.000,00 | 500,00 | Sin alerta. |
| TRANSFER | 36.942,13 | 36.942,13 | Alerta. |

### Crédito

Perfil: edad 30, ingreso anual 55.000, vivienda RENT, antigüedad laboral 4 años, historial de 5 años, finalidad PERSONAL, monto 10.000 e impago previo N.

La demo documenta una probabilidad aproximada de 6,09 %, frente a un umbral de 15,53 %. Es una salida del modelo con semántica de impago asumida, no una aprobación automática.

### Redes y segmentos

- Redes: muestra de 10.000 operaciones y consulta de `C985934102`.
- Segmentos: segmento 0 y cuenta `C1286084959`.
- Explicar que son cuentas simuladas y que cada consulta depende del universo utilizado.

### Pronósticos

Solicitar horizonte de 24 steps para cantidad y luego para monto. Consultar el monitoreo histórico y explicar por qué Naive permanece seleccionado tras compararlo con Holt-Winters.

### Reclamos

Texto de demostración:

> My credit report contains an account that does not belong to me. I disputed the incorrect information with the credit bureau but it has not been removed.

Producto sugerido documentado: **Credit reporting**. La puntuación no es una certeza de resolución del reclamo.

## 12. Equipo y responsabilidades

| Integrante | Módulo principal | Responsabilidades compartidas |
| --- | --- | --- |
| Cueva | Fraude supervisado y patrones. | Contrato transaccional con Taco; revisión de integración de fraude. |
| Sevan | Crédito, calibración y explicaciones. | Evaluación, versiones y reproducción con Gerardo. |
| Rhamses | Grafos y patrones de red. | Contratos HTTP y navegación con Angel. |
| Taco | Silver/Gold transaccional y segmentación. | Contratos de datos con Cueva y trazabilidad. |
| Gerardo | Pronósticos y monitoreo. | Evaluación, entorno y empaquetado con Sevan. |
| Angel | Reclamos y procesamiento de texto. | Contratos HTTP y navegación con Rhamses. |

El reparto es por módulos completos: datos, análisis, evaluación y exposición de resultados. La preparación posterior de la demo incluye trabajo de integración local y no debe atribuirse automáticamente a los responsables originales como si ellos hubieran realizado o aceptado todos esos cambios.

## 13. Estado actual y evidencia

### Implementado en esta copia

- Tres originales organizados en Bronze.
- Perfilado y contratos de datos por dominio.
- Silver transaccional, crediticio y de reclamos.
- Mart transaccional y Gold temporal.
- Modelos y análisis de los seis módulos.
- Servicios, endpoints y seis páginas.
- Scripts de preparación, arranque, parada y verificación.
- Demo local con artefactos preparados.
- Workflow de pruebas en GitHub Actions.

### Evidencia existente

La actualización posterior de `docs/revision-avance-2026-10-13.md` registra **238 pruebas aprobadas** y **48 comprobaciones del recorrido** con HTTP real y las seis páginas. Existen los archivos locales `artifacts/reports/demo/test-suite.log` y `artifacts/reports/demo/delivery-check.json`.

La entrega de fraude también documenta una reconstrucción aislada sin reutilizar Silver ni modelos y reproducción de sus métricas. Esa experiencia no equivale a una descarga y ejecución del proyecto completo desde otra PC.

Este documento recopila esas evidencias existentes: no declara una nueva ejecución de pruebas o entrenamiento.

### Cómo resolver diferencias entre documentos

Algunas secciones históricas del README, del plan y de las revisiones siguen mencionando ausencia de páginas o artefactos ya preparados después.

Para el estado de esta copia, utilizar la **actualización posterior de la revisión del 13 de octubre**, `docs/demo-local.md` y el código actual. Las cifras anteriores de 160, 213 y 230 pruebas corresponden a cortes previos; los resultados antiguos de segmentación `k = 5` y ARI 0,3883 fueron reemplazados por la entrega corregida.

La preparación local no demuestra que todos los cambios se encuentren publicados en GitHub. Al compartir el proyecto, comprobar qué archivos forman parte de la entrega.

## 14. Pendientes para cerrar la entrega integral

El detalle vigente por persona, archivos, contratos, pruebas y dependencias está en [la guía del 20 de octubre](docs/pendientes-cierre-2026-10-20.md). Además de los pendientes de validación siguientes, se asignaron estas implementaciones futuras:

| Implementación | Responsable | Alcance |
| --- | --- | --- |
| Datos analíticos D1 | Taco | Particiones, bins ajustados solo con train y trazabilidad para los dos análisis nuevos. |
| Asociaciones descubiertas | Cueva | Minería automática, selección en validación, evaluación, API y ampliación de Fraude. |
| Regresión numérica | Sevan | Monto transaccional desde tipo/saldo, referencias, evaluación, artefacto, API y página. |
| Comparación de grafos | Rhamses | Red frente a volumen con igual universo y cantidad de alertas, reporte y consulta. |
| Preparación/reproducción | Gerardo | DAG, reuso validado, versiones exactas y entorno limpio; historial ampliado como P2 recomendado. |
| Integración/evidencia | Angel | Registro de routers, navegación, verificación ampliada y matriz de entregables. |

| Pendiente | Qué falta concretamente |
| --- | --- |
| Fuentes y condiciones de uso | Confirmar origen, versión, fecha de obtención y licencia de los tres archivos. |
| Semántica de crédito | Confirmar `loan_status` con la fuente original y registrar el respaldo. |
| Aceptación humana | Registrar revisiones cruzadas de contratos, integración y corrección de segmentación. |
| Revisión de reclamos | Validar mediante lectura humana los ejemplos y las limitaciones del clasificador. |
| Comparación de grafos | Cerrar una referencia comparable y documentar precisión, cobertura y límites. |
| Reproducción en otra PC | Ejecutar clon con LFS, entorno nuevo, preparación y seis recorridos. |
| Versiones | Validar un conjunto exacto de dependencias si se requiere reproducir cifras históricas. |
| Empaquetado | Completar y verificar Docker/Compose si se conserva como entregable. |
| Publicación e integración | Comprobar cambios compartidos, revisión del equipo y resultado remoto del workflow. |

No volver a implementar los seis módulos existentes. El cierre combina las ampliaciones anteriores con confirmación de fuentes, revisión, evaluación y reproducción. El monitoreo histórico actual se conserva; un historial de desempeño por lotes se informa como mejora recomendada separada.

### Criterio de cierre

La entrega integral ampliada estará cerrada cuando otra persona pueda obtener los originales completos, crear el entorno, reconstruir artefactos y recorrer las seis capacidades existentes más regresión, asociaciones descubiertas y comparación de grafos con sus limitaciones visibles. También exige evidencia de las comprobaciones, revisión de fuentes y aceptación real de contratos según el checklist del 20 de octubre. El historial ampliado y Docker se informan aparte como P2.

## 15. Guía para quien recibe este documento

### Si solo necesita comprender o explicar el proyecto

Leer las secciones 1–5, revisar la tabla de módulos y utilizar la sección 7 para explicar métodos, resultados y límites. Las secciones 13–14 distinguen lo entregado de lo pendiente.

### Si necesita ejecutar la aplicación

Debe recibir el repositorio completo y tener acceso a los originales de Git LFS. Seguir la sección 10 y comprobar los ejemplos de la sección 11. El archivo Markdown transmite contexto, pero por sí solo no contiene datos, modelos ni aplicación.

### Si necesita continuar el desarrollo

1. Leer `docs/pendientes-cierre-2026-10-20.md` y el encargo individual allí enlazado; consultar la revisión del 13 de octubre solo como evidencia histórica.
2. Leer el contrato y los resultados del módulo correspondiente.
3. Comprobar qué artefactos existen y qué cambios están solo en la copia local.
4. Elegir una tarea de los pendientes vigentes, evitando repetir entregas implementadas.
5. Mantener la separación de fuentes y los controles de fuga de información.
6. Ejecutar las comprobaciones relevantes y registrar el resultado y los cambios de alcance.

## 16. Documentación para profundizar

Las rutas siguientes son relativas a la raíz del repositorio; el contenido principal de este archivo puede leerse de forma independiente.

| Documento | Contenido |
| --- | --- |
| `README.md` | Entrada general, estado y organización. |
| `docs/bases-del-proyecto.md` | Definición inicial, alcance y arquitectura propuesta. |
| `docs/plan-desarrollo.md` | Etapas, reparto y coordinación. |
| `docs/pendientes-cierre-2026-10-20.md` | Backlog vigente, prioridades, contratos y enlaces a seis encargos ejecutables por agentes. |
| `docs/datasets.md` | Inventario, campos y huellas de originales. |
| `docs/revision-avance-2026-10-13.md` | Actualización de integración y pendientes. |
| `docs/demo-local.md` | Preparación, ejemplos y límites de la demo. |
| `docs/pruebas-reproduccion.md` | Entorno, pruebas y antecedentes de reproducción. |
| `docs/fraude/cierre-entrega.md` | Entrega y reconstrucción de fraude. |
| `docs/fraude/resultados-entrenamiento.md` | Particiones y métricas de fraude. |
| `docs/credito/contrato-variables.md` | Campos permitidos, semántica y explicación. |
| `docs/credito/resultados-modelo.md` | Modelos, calibración y resultados crediticios. |
| `docs/grafos/contrato-variables.md` | Construcción de red e indicadores. |
| `docs/grafos/perfil-red.md` | Resultados y limitaciones de la muestra de red. |
| `docs/transacciones/contrato-gold.md` | Mart por transacción. |
| `docs/transacciones/segmentacion.md` | Agrupamiento y perfiles corregidos. |
| `docs/pronosticos/contrato-gold.md` | Agregados por hora simulada. |
| `docs/pronosticos/resultados-baselines.md` | Comparación de referencias temporales. |
| `docs/pronosticos/resultados-holt-winters.md` | Comparación de Holt-Winters y decisión. |
| `docs/pronosticos/resultados-monitoreo.md` | Cambio histórico en el tramo final. |
| `docs/reclamos/perfil-complaints.md` | Cobertura, fechas y distribución de reclamos. |
| `docs/reclamos/resultados-modelo.md` | Clasificación textual y evaluación. |
| `docs/reclamos/revision-ejemplos.md` | Casos para revisión humana. |
| `api/README.md` | Contratos HTTP y configuración. |

La presentación suministrada, titulada **BankShield Analytics · Comprensión del negocio y de los datos**, aporta el contexto de las primeras etapas y los indicadores iniciales. Este documento amplía ese contexto con la implementación y los reportes de la copia local.

## 17. Glosario breve

| Término | Significado dentro del proyecto |
| --- | --- |
| Pipeline | Secuencia de pasos para transformar datos o realizar una predicción. |
| Mart | Tabla organizada para un propósito analítico concreto. |
| Artefacto | Archivo generado, como modelo, métricas o reporte. |
| Etiqueta | Resultado conocido que se utiliza para entrenar o evaluar clasificación. |
| Fuga de información | Uso de datos que no estarían disponibles al predecir o que revelan indebidamente el resultado. |
| Score | Puntuación del modelo; no siempre es una probabilidad calibrada. |
| Umbral | Valor a partir del cual una puntuación genera una alerta o clasificación. |
| Precisión | Proporción de alertas positivas que corresponde a casos positivos. |
| Recall | Proporción de casos positivos que se detecta. |
| F1 | Medida que combina precisión y recall. |
| Macro-F1 | Promedio de F1 que da el mismo peso a cada clase. |
| AP | Average Precision, resumen de precisión-recall a distintos umbrales. |
| ROC-AUC | Medida de capacidad para ordenar positivos por encima de negativos. |
| Calibración | Correspondencia entre probabilidades estimadas y frecuencias observadas. |
| Brier / ECE | Medidas utilizadas para evaluar probabilidades y calibración. |
| Silueta | Medida de separación y cohesión de los grupos. |
| ARI | Medida de concordancia entre agrupamientos, usada para estudiar estabilidad. |
| Backtesting | Evaluación de pronósticos usando periodos históricos posteriores al ajuste. |
| MAE / RMSE | Medidas de error de pronóstico en las unidades del objetivo. |
| sMAPE | Medida porcentual de error relativo. |
| Oclusión | Explicación basada en cambiar una variable y observar la respuesta del modelo. |
| NLP | Procesamiento de lenguaje natural; aquí, limpieza y clasificación de relatos. |
| TF-IDF | Representación del texto mediante pesos de términos. |
| Git LFS | Sistema para distribuir archivos grandes junto al repositorio. |
