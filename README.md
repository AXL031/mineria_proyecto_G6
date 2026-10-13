# BankShield Analytics

Proyecto académico de minería de datos y analítica financiera. La visión incluye detección de fraude, riesgo crediticio, análisis de reclamos, pronósticos y explicabilidad sobre una arquitectura Bronze → Silver → Gold.

## Guía vigente para continuar el desarrollo

**Antes de elegir o implementar una tarea, cada integrante debe consultar el [avance y pendientes — 13 de octubre de 2026](docs/revision-avance-2026-10-13.md).** Allí están los cambios de los seis responsables, sus próximas entregas, las tareas compartidas y los criterios de aceptación. El estado incorpora segmentos de Taco hasta `2c28fec` y conserva pronósticos de Gerardo, con **230 pruebas aprobadas** en la integración.

El [plan de desarrollo](docs/plan-desarrollo.md) mantiene el alcance y el reparto de responsabilidades. Para decidir qué hacer ahora, guiarse por la verificación vigente: sus pendientes actualizados reemplazan los estados históricos que contradigan el código. Al completar una entrega, registrar su evidencia y actualizar ambos documentos para mantener esta guía al día.

**Transacciones y segmentación — Taco:** los cinco commits hasta `2c28fec` corrigen el uso de la etiqueta en agrupamiento y añaden servicio, endpoints `/api/segments/...` y página `06_segmentos.py`. El [reporte regenerado](docs/transacciones/segmentacion.md) documenta k=2, silueta 0.2305 y estabilidad ARI 0.7280. La prueba de independencia de etiquetas verifica matriz y grupos. Falta reconstruir artefactos aquí, demostrar el recorrido y registrar aceptación cruzada.

**Reclamos — Angel:** el [perfil](docs/reclamos/perfil-complaints.md) ya tiene el rango de fechas corregido y el [contrato Silver](docs/reclamos/contrato-silver.md) describe la tabla limpia (`scripts/build_silver_complaints.py`). El [clasificador de producto por narrativa](docs/reclamos/resultados-modelo.md) supera a sus referencias en la prueba temporal y sus [ejemplos](docs/reclamos/revision-ejemplos.md) están extraídos; siguen pendientes la lectura humana de esa revisión, el servicio, la API y la página.

**Fraude y patrones — Cueva:** consultar el [cierre de entrega](docs/fraude/cierre-entrega.md) para las comprobaciones más recientes, asociaciones descriptivas, endpoints y el comando `scripts/reproduce_fraud.ps1` que reconstruye y verifica el módulo.

**Pronósticos — Gerardo:** las [líneas base](docs/pronosticos/resultados-baselines.md)
y [tres configuraciones Holt-Winters](docs/pronosticos/resultados-holt-winters.md)
se evaluaron sobre las mismas cuatro ventanas. Naive se mantiene seleccionado;
el [monitoreo histórico](docs/pronosticos/resultados-monitoreo.md) detecta el
cambio del tramo 719–743. El servicio y la página temporal exponen la proyección
Naive, incertidumbre descriptiva y los indicadores de cambio mediante la API.

## Punto de partida

La [base del proyecto](docs/bases-del-proyecto.md) define el alcance inicial, los límites de las fuentes públicas, la arquitectura propuesta, los criterios de evaluación, el reparto entre los seis integrantes y el orden de trabajo. Es una propuesta de ejecución para discutir con el equipo antes de implementar los módulos.

El [plan de desarrollo](docs/plan-desarrollo.md) detalla las cinco etapas, las tareas de cada integrante, las responsabilidades compartidas y las primeras entregas.

La revisión vigente del **13 de octubre de 2026** está enlazada al inicio de ese plan. La [guía de pruebas y reproducción](docs/pruebas-reproduccion.md) reúne dependencias, comandos y criterios de ejecución; sus bloqueos históricos deben contrastarse con la revisión vigente. Hay cinco módulos con API/página: fraude, crédito, grafos, pronósticos y segmentos; falta la vista de reclamos. Antes de la demo local deben reconstruirse el modelo de crédito, Gold temporal, reporte de monitoreo y artefactos de segmentos. El avance global orientativo es 85%; no sustituye los criterios de aceptación.

La primera entrega de Cueva incluye [perfilado y contrato de variables de fraude](docs/fraude/contrato-variables.md), con comandos reproducibles y controles de información disponible antes de la operación.

El [entrenamiento de fraude](docs/fraude/entrenamiento.md) añade separación temporal, línea base, clasificador, selección de umbral y scoring local, con instrucciones para reproducir los resultados.

La entrega de Angel incluye el [perfilado y cobertura de narrativas de reclamos](docs/reclamos/perfil-complaints.md) y la [propuesta de navegación y panel](docs/reclamos/propuesta-panel.md), con análisis de textos censurados (`XXXX`) y distribución por producto.

Los tres CSV aportados están organizados en `data/bronze/` y se versionan mediante **Git LFS**. El [inventario de datos](docs/datasets.md) registra sus columnas, tamaños y huellas SHA-256. Los datos derivados y artefactos generados siguen excluidos de Git. Cada integrante necesita Git LFS instalado para recibir el contenido completo de los CSV al clonar o hacer pull.

**Primer incremento propuesto:** cargar transacciones, aplicar controles de calidad, construir un mart analítico, entrenar un detector de fraude de referencia y mostrar sus resultados en un panel local. El mismo recorrido servirá como patrón para los módulos posteriores.

## Estado histórico

Esta lista conserva el estado anterior a la verificación del 12 de octubre y contiene pendientes ya implementados. Para el estado actual y las próximas tareas, consultar la [revisión vigente](docs/revision-avance-2026-10-13.md).

- [x] Contexto y bases documentados.
- [x] Fuente transaccional de trabajo elegida: archivo con esquema PaySim.
- [ ] Procedencia y licencia de los tres archivos confirmadas.
- [x] Contratos y reportes de transacciones, fraude, grafos y Gold temporal implementados; revisión cruzada pendiente.
- [x] Scripts Bronze → Silver transaccional → Gold temporal implementados y reportes completos documentados.
- [ ] Recorrido completo reproducido y probado desde un entorno limpio.
- [x] Línea base y clasificador de fraude evaluados temporalmente.
- [x] Ingesta, grafo dirigido, métricas de red y detección de patrones de transacciones implementados.
- [x] Perfilado de reclamos y análisis de cobertura de narrativas de texto (NLP) completado.
- [x] Ingesta transaccional con controles de calidad y capa Silver en Parquet (ver [contrato Silver](docs/transacciones/contrato-silver.md)).
- [x] API de grafos y página de redes implementadas como componentes separados.
- [x] Riesgo crediticio: Silver, modelo calibrado, explicación por oclusión, endpoints y página (ver [contrato](docs/credito/contrato-variables.md) y [resultados](docs/credito/resultados-modelo.md)).
- [ ] Conexión API → panel y página/endpoint de fraude integrados.

Fraude tiene un modelo entrenado y un servicio de scoring local. Grafos tiene perfilado, métricas, patrones, servicios, endpoints y página de redes (ver [contrato](docs/grafos/contrato-variables.md) y [perfil](docs/grafos/perfil-red.md)); la página llama directamente a servicios y falta conectarla a la API. Reclamos tiene perfilado de 555,957 quejas y propuesta del panel; su rango temporal requiere corrección. Transacciones tiene Silver y controles; pronósticos tiene Gold por `step` y exploración, pero aún no un pronóstico evaluado. Crédito tiene perfil, Silver, modelo calibrado, API y página; falta confirmar con la fuente original el significado de `loan_status`. Segmentación y modelado NLP siguen pendientes. Los Parquet y modelos se regeneran localmente y quedan fuera de Git.

## Preparación común del equipo

Instalar Python 3.12 y Git LFS. Desde la raíz, después de clonar o actualizar:

```powershell
git lfs pull
powershell -ExecutionPolicy Bypass -File scripts/setup_env.ps1
```

El script crea `.venv-pruebas`, instala `requirements/common.txt`, comprueba
dependencias y ejecuta las pruebas. No modifica la política de ejecución
permanente. No subir entornos virtuales, modelos ni datos derivados.
Si no existe el lanzador `py`, pasar `-PythonExecutable` con la ruta de Python 3.12.
La [guía de pruebas](docs/pruebas-reproduccion.md) explica generación de datos,
API/panel y flujo de colaboración. GitHub Actions ejecutará las pruebas en
Windows y Python 3.12 por cada push y pull request; la validación de CI está pendiente.

## Carpetas

| Ruta | Propósito |
| --- | --- |
| `data/bronze/` | CSV originales separados por dominio y versionados con Git LFS. |
| `data/silver/`, `data/gold/` | Datos limpios y marts generados. |
| `src/bankshield/` | Ingesta, transformaciones, variables, modelos y servicios compartidos. |
| `api/`, `dashboard/` | API y panel de demostración. |
| `tests/` | Pruebas unitarias y de integración. |
| `configs/`, `scripts/`, `notebooks/` | Configuración, comandos y exploración. |
| `artifacts/` | Modelos y reportes generados, fuera de Git. |

Cada carpeta incluye una breve guía o un marcador para que la estructura aparezca al clonar el repositorio.
`pyproject.toml` declara el paquete Python y extras para datos, modelos, API y panel. La guía de pruebas documenta cómo instalarlos juntos y las diferencias entre los archivos de versiones fijadas por módulo.
