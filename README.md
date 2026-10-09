# BankShield Analytics

Proyecto académico de minería de datos y analítica financiera. La visión incluye detección de fraude, riesgo crediticio, análisis de reclamos, pronósticos y explicabilidad sobre una arquitectura Bronze → Silver → Gold.

## Punto de partida

La [base del proyecto](docs/bases-del-proyecto.md) define el alcance inicial, los límites de las fuentes públicas, la arquitectura propuesta, los criterios de evaluación, el reparto entre los seis integrantes y el orden de trabajo. Es una propuesta de ejecución para discutir con el equipo antes de implementar los módulos.

El [plan de desarrollo](docs/plan-desarrollo.md) detalla las cinco etapas, las tareas de cada integrante, las responsabilidades compartidas y las primeras entregas.

La revisión del **9 de octubre de 2026** en ese plan registra el avance verificable y la siguiente entrega de cada integrante. La [guía de pruebas y reproducción](docs/pruebas-reproduccion.md) reúne dependencias, bloqueos, comandos y criterios para probar los componentes existentes y cerrar el MVP integrado.

La primera entrega de Cueva incluye [perfilado y contrato de variables de fraude](docs/fraude/contrato-variables.md), con comandos reproducibles y controles de información disponible antes de la operación.

El [entrenamiento de fraude](docs/fraude/entrenamiento.md) añade separación temporal, línea base, clasificador, selección de umbral y scoring local, con instrucciones para reproducir los resultados.

La entrega de Angel incluye el [perfilado y cobertura de narrativas de reclamos](docs/reclamos/perfil-complaints.md) y la [propuesta de navegación y panel](docs/reclamos/propuesta-panel.md), con análisis de textos censurados (`XXXX`) y distribución por producto.

Los tres CSV aportados están organizados en `data/bronze/` y se versionan mediante **Git LFS**. El [inventario de datos](docs/datasets.md) registra sus columnas, tamaños y huellas SHA-256. Los datos derivados y artefactos generados siguen excluidos de Git. Cada integrante necesita Git LFS instalado para recibir el contenido completo de los CSV al clonar o hacer pull.

**Primer incremento propuesto:** cargar transacciones, aplicar controles de calidad, construir un mart analítico, entrenar un detector de fraude de referencia y mostrar sus resultados en un panel local. El mismo recorrido servirá como patrón para los módulos posteriores.

## Estado

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
- [ ] Conexión API → panel y página/endpoint de fraude integrados.

Fraude tiene un modelo entrenado y un servicio de scoring local. Grafos tiene perfilado, métricas, patrones, servicios, endpoints y página de redes (ver [contrato](docs/grafos/contrato-variables.md) y [perfil](docs/grafos/perfil-red.md)); la página llama directamente a servicios y falta conectarla a la API. Reclamos tiene perfilado de 555,957 quejas y propuesta del panel; su rango temporal requiere corrección. Transacciones tiene Silver y controles; pronósticos tiene Gold por `step` y exploración, pero aún no un pronóstico evaluado. Crédito, segmentación y modelado NLP siguen pendientes. Los Parquet y modelos se regeneran localmente y quedan fuera de Git.

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
