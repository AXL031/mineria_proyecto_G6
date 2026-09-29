# Bases del proyecto — BankShield Analytics

## Propósito y alcance

BankShield Analytics será una demostración académica reproducible de cómo datos financieros pasan de una fuente pública a productos analíticos y modelos explicables. La propuesta original contempla fraude, riesgo crediticio, límites de financiación, segmentación, redes de transacciones, liquidez y reclamos. Estos dominios siguen en la visión, pero se desarrollarán por incrementos verificables.

La aplicación presentará **estimaciones para análisis y apoyo a decisiones**. Las decisiones bancarias reales requerirían datos propios, validación externa y controles adicionales que este proyecto no aporta.

### Primer incremento vertical (MVP)

1. Ingestar un conjunto transaccional público con identificador, orden temporal, monto y etiqueta de fraude.
2. Conservar el archivo original en Bronze y crear una versión tipada, documentada y validada en Silver.
3. Construir en Gold un mart de transacciones y agregados que sean posibles con las columnas observadas.
4. Comparar un modelo de referencia sencillo con un modelo supervisado de fraude; registrar métricas y explicaciones.
5. Exponer resultados agregados, predicciones de demostración y límites del modelo en una API y un panel local.

**Terminado significa:** otra persona del equipo puede reconstruir los datos derivados y las métricas desde el archivo original mediante comandos documentados, y recorrer un ejemplo en la interfaz sin editar notebooks. La meta numérica de desempeño se establecerá tras conocer prevalencia, periodo y coste de errores del dataset elegido.

### Incrementos posteriores

| Orden | Capacidad | Condición para iniciarla |
| --- | --- | --- |
| 2 | Riesgo crediticio y explicabilidad | Fuente y definición exacta de `default` verificadas; evaluación independiente del fraude. |
| 3 | Segmentación, reglas y grafos | Identidades de cuentas y relaciones reales dentro de una misma fuente, o datos sintéticos claramente rotulados. |
| 4 | Reclamos con NLP | Cobertura y permiso de uso del texto comprobados; análisis independiente de clientes transaccionales. |
| 5 | Pronóstico y monitoreo | Serie con fechas y horizonte suficientes; línea base temporal y nuevas observaciones para medir deriva. |

La recomendación de límite de crédito queda como investigación posterior: una probabilidad de impago por sí sola no determina un monto óptimo sin política de riesgo, pérdidas esperadas y datos de exposición.

## Decisión sobre datos

Los tres archivos aportados representan entidades distintas. **No existe una llave de cliente compartida demostrada** entre las transacciones, el crédito y los reclamos. No se unirán por posición de fila, nombres de campo parecidos ni identificadores inventados. El warehouse tendrá marts separados por fuente; cualquier vista integrada será un ejemplo sintético o una agregación explícitamente marcada. El [inventario local](datasets.md) documenta los archivos disponibles.

| Dominio | Fuente candidata | Uso posible | Límite que condiciona el diseño |
| --- | --- | --- | --- |
| Fraude y grafos | `PS_20174392719_1491204439457_log.csv` (esquema PaySim) | Clasificación de transacciones y relaciones origen → destino. | Datos de simulación; `step` no es una fecha calendario. |
| Riesgo crediticio | `credit_risk_dataset.csv` | Modelo independiente con etiqueta candidata `loan_status`. | No es Home Credit; no trae identificador de cliente ni fecha en su cabecera. La semántica de la etiqueta debe confirmarse. |
| Reclamos | `consumer_complaints.csv` | Frecuencia de asuntos y análisis de narrativas disponibles. | `complaint_id` no une reclamos con las otras fuentes; debe medirse la cobertura del texto. |

**Selección para el primer incremento:** trabajar con el CSV transaccional aportado, cuyo esquema corresponde a PaySim. Falta confirmar la procedencia y licencia de esta copia. El contrato canónico se definirá tras perfilar sus valores; los nombres de la propuesta original (`user_id`, `receiver_id`, `timestamp`, etc.) son requisitos conceptuales, no columnas del archivo.

## Arquitectura mínima propuesta

```text
Archivo público (versión y procedencia registradas)
  → Bronze: copia original inmutable
  → Silver: tipos, nulos, duplicados, rangos y diccionario de campos
  → Gold: mart transaccional + agregados y variables disponibles al predecir
  → entrenamiento/evaluación → artefacto versionado
  → API FastAPI → panel Streamlit
```

Para una demostración local, la propuesta técnica inicial es **Python + Parquet + DuckDB** para transformación y consulta, **scikit-learn** para líneas base, **FastAPI** y **Streamlit** para consumo, y **Docker Compose** cuando el recorrido funcione localmente. Los notebooks pueden servir para explorar; la transformación final debe ejecutarse como código repetible.

El esquema en estrella se diseñará a partir de las claves observadas. La primera tabla de hechos tendrá grano **una fila por transacción**; dimensiones de tiempo, canal, cuenta o comercio solo existirán cuando la fuente las sustente. Los datos de entrenamiento conservarán versión de fuente, corte temporal, código y parámetros. No se usará la etiqueta ni información posterior al evento como variable predictora.

### Organización prevista

```text
docs/                  decisiones, inventario y metodología
data/bronze/           originales por dominio, los tres CSV iniciales en Git LFS
data/silver/           datos limpios generados, fuera de Git
data/gold/             marts generados, fuera de Git
src/bankshield/        ingesta, transformaciones, variables, modelos y servicios
api/                   endpoints de demostración
dashboard/             panel analítico
tests/                 pruebas de contratos y lógica crítica
artifacts/             modelos y reportes generados, fuera de Git
configs/               configuración versionable sin secretos
scripts/               comandos reproducibles
notebooks/             exploración, fuera del recorrido final
```

La estructura de carpetas ya está creada. El repositorio versionará scripts, configuración sin secretos y documentación; los tres CSV iniciales se almacenarán con Git LFS, mientras que los datos derivados y artefactos entrenados permanecerán fuera de Git.

## Reparto del equipo (6 integrantes)

La unidad de trabajo de cada integrante es un **módulo vertical**: perfilar su fuente, construir sus datos Silver/Gold, implementar el análisis, evaluarlo y entregar una vista o endpoint con una explicación de sus límites. Nadie queda asignado únicamente a documentación, interfaz o infraestructura. Los módulos de fases posteriores pueden comenzar con muestras pequeñas mientras se termina el primer recorrido de fraude.

| Integrante | Módulo principal y entregable verificable | Aporte al primer recorrido y a la integración |
| --- | --- | --- |
| **Cueva** | **Fraude supervisado y patrones:** variables disponibles al momento de la transacción, línea base y clasificador, umbral, PR-AUC y errores; reglas de asociación simples si los campos las permiten; vista de predicción y patrones. | Perfilar la fuente transaccional y definir el contrato de entrada junto con Taco. Integra el modelo de fraude, sin asumir la integración de todos los módulos. |
| **Sevan** | **Riesgo crediticio:** pipeline independiente del CSV de crédito aportado, interpretación documentada de `loan_status`, modelo, calibración y explicaciones de casos; vista de riesgo. Documenta por qué una probabilidad no basta para fijar un límite de crédito. | Definir junto con Gerardo la plantilla común de evaluación, registro de experimentos y comprobación de fuga de información; aplicarla al fraude inicial. |
| **Rhamses** | **Grafos de transacciones:** construir aristas cuenta → cuenta a partir de `nameOrig` y `nameDest`, calcular indicadores de red y evaluar casos sospechosos; visualización de subgrafos. Los resultados se rotularán como simulados. | Definir junto con Angel el contrato de respuesta de la API y conectar la primera consulta del mart transaccional. |
| **Taco** | **Segmentación:** variables de comportamiento calculadas solo cuando las identidades sean fiables, agrupación comparada con una línea base y perfiles interpretables; vista de segmentos. | Implementar el recorrido Bronze → Silver → Gold de transacciones con controles de calidad, junto con Cueva en el contrato. Establecer el patrón reutilizable para otras fuentes. |
| **Gerardo** | **Pronósticos y monitoreo:** serie agregada, línea base temporal, evaluación retrospectiva y panel de pronóstico; comparación de distribuciones entre lotes cuando existan datos posteriores. Los horizontes dependerán de la cobertura real. | Preparar junto con Sevan la plantilla de métricas y artefactos; documentar el comando reproducible y el empaquetado local cuando el flujo funcione. |
| **Angel** | **Reclamos y NLP:** pipeline independiente de CFPB, cobertura del texto, categorías o tópicos interpretables y evaluación con revisión de ejemplos; vista de reclamos. | Crear junto con Rhamses el esqueleto del panel y el contrato API → interfaz; cada integrante agregará su propia página, evitando que Angel implemente todas las vistas. |

### Regla de equilibrio y revisión

- Cada módulo entrega **una fuente documentada, una transformación reproducible, un método analítico comparado con una línea base, una evaluación, una vista y una breve sección de limitaciones**. Esto iguala el tipo de trabajo, aunque las técnicas cambien.
- Las tareas comunes se realizan en tres parejas: **Cueva–Taco** (datos), **Sevan–Gerardo** (evaluación y reproducción) y **Rhamses–Angel** (API e interfaz). En cada pareja ambos revisan el código y la documentación del otro. La responsabilidad de cerrar una integración rota pertenece a la pareja que mantiene ese contrato, no a una sola persona.
- Al finalizar cada hito, el equipo revisará esfuerzo real, bloqueos y alcance. Si un módulo exige claramente más trabajo, se recorta primero su alcance avanzado (por ejemplo, modelos adicionales o visualizaciones complejas) o se redistribuye una tarea común. No se medirá el reparto por número de archivos o líneas de código.
- Las tareas de infraestructura compartida se limitan al mínimo que necesita el primer recorrido. Si consumen más de un hito, las otras parejas toman parte de ese trabajo antes de ampliar sus propios módulos.
- Todo PR de módulo requiere una revisión de alguien de otra pareja. Las decisiones sobre fuente, esquema y alcance se registran en `docs/`; las seis personas participan en la demostración final.

### Primer hito con trabajo para todos

| Integrante | Entrega inicial |
| --- | --- |
| Cueva | Perfil de columnas, etiqueta y riesgos de fuga de la fuente transaccional elegida. |
| Sevan | Protocolo de separación de datos y métricas de fraude que se ejecutará sobre la primera línea base. |
| Rhamses | Prueba de viabilidad de aristas de cuentas con el CSV aportado y esquema de respuesta de una consulta de red. |
| Taco | Ingesta Bronze/Silver, validaciones y primer mart de transacciones. |
| Gerardo | Agregados temporales disponibles, comando de reproducción y registro de resultados de la línea base. |
| Angel | Esqueleto del panel, contrato con la API y primera vista de calidad/métricas reales. |

La primera demostración se considera integrada cuando estas seis entregas funcionan juntas. Los módulos posteriores se desarrollan en paralelo sobre el patrón acordado, con revisiones cruzadas.

## Calidad y evaluación

- Cada fuente tendrá procedencia, versión o fecha de descarga, licencia, esquema observado, unidad de análisis y significado de la etiqueta.
- La ingesta comprobará identificadores únicos cuando correspondan, tipos, nulos, valores fuera de rango y recuentos antes/después de la limpieza. Rechazos y transformaciones quedarán registrados.
- La separación entrenamiento/prueba respetará el orden temporal si la fuente lo permite. El preprocesamiento se ajustará solo con entrenamiento. Se revisarán duplicados y entidades repetidas entre particiones.
- En fraude se reportarán prevalencia, matriz de confusión, precisión, recall y PR-AUC; el umbral se elegirá en validación con un supuesto de coste documentado. Se comparará con una línea base trivial.
- En crédito se reportarán discriminación y calibración, además de resultados por segmentos cuando la muestra lo permita. Una explicación local no sustituye una validación de equidad o causalidad.
- Los pronósticos usarán evaluación retrospectiva y una línea base estacional o ingenua. No se prometerán horizontes de 7, 30, 60 y 90 días si la serie no los sustenta.
- El monitoreo de deriva solo se activará cuando existan lotes posteriores comparables. La deriva estadística no implica por sí misma caída de desempeño; el reentrenamiento no será automático sin evaluación.

## Secuencia inmediata

1. Confirmar procedencia y condiciones de uso de los tres CSV aportados.
2. Perfilar los archivos locales y completar un diccionario de datos con ejemplos y unidades.
3. Fijar el contrato del primer mart y las pruebas de calidad sobre la fuente elegida.
4. Implementar el recorrido Bronze → Silver → Gold y documentar un comando de reproducción.
5. Entrenar la línea base, registrar evaluación y después construir API y panel sobre resultados reales.

## Decisiones abiertas

- Procedencia exacta, versión y licencia de los tres CSV.
- Tiempo, tamaño máximo de datos y recursos de cómputo disponibles para el equipo.
- Requisitos de entrega del curso: módulos obligatorios, fecha, formato de demostración y criterios de evaluación.
- Disponibilidad y experiencia de cada integrante para ajustar el reparto sin perder equilibrio.

## Archivo de referencia

La propuesta original mencionó IEEE-CIS y Home Credit como posibles fuentes. El desarrollo actual parte de los tres archivos inventariados en [datasets.md](datasets.md), cuyos esquemas son distintos. Cualquier cambio de fuente deberá actualizar contratos, métricas y esta documentación.
