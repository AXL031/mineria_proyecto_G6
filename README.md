# BankShield Analytics

Proyecto académico de minería de datos y analítica financiera. La visión incluye detección de fraude, riesgo crediticio, análisis de reclamos, pronósticos y explicabilidad sobre una arquitectura Bronze → Silver → Gold.

## Punto de partida

La [base del proyecto](docs/bases-del-proyecto.md) define el alcance inicial, los límites de las fuentes públicas, la arquitectura propuesta, los criterios de evaluación, el reparto entre los seis integrantes y el orden de trabajo. Es una propuesta de ejecución para discutir con el equipo antes de implementar los módulos.

El [plan de desarrollo](docs/plan-desarrollo.md) detalla las cinco etapas, las tareas de cada integrante, las responsabilidades compartidas y las primeras entregas.

La primera entrega de Cueva incluye [perfilado y contrato de variables de fraude](docs/fraude/contrato-variables.md), con comandos reproducibles y controles de información disponible antes de la operación.

El [entrenamiento de fraude](docs/fraude/entrenamiento.md) añade separación temporal, línea base, clasificador, selección de umbral y scoring local, con instrucciones para reproducir los resultados.

Los tres CSV aportados están organizados en `data/bronze/` y se versionan mediante **Git LFS**. El [inventario de datos](docs/datasets.md) registra sus columnas, tamaños y huellas SHA-256. Los datos derivados y artefactos generados siguen excluidos de Git. Cada integrante necesita Git LFS instalado para recibir el contenido completo de los CSV al clonar o hacer pull.

**Primer incremento propuesto:** cargar transacciones, aplicar controles de calidad, construir un mart analítico, entrenar un detector de fraude de referencia y mostrar sus resultados en un panel local. El mismo recorrido servirá como patrón para los módulos posteriores.

## Estado

- [x] Contexto y bases documentados.
- [x] Fuente transaccional de trabajo elegida: archivo con esquema PaySim.
- [ ] Procedencia y licencia de los tres archivos confirmadas.
- [ ] Contrato de datos y muestra exploratoria validados.
- [ ] Pipeline Bronze → Silver → Gold reproducible.
- [x] Línea base y clasificador de fraude evaluados temporalmente.
- [x] Ingesta, grafo dirigido, métricas de red y detección de patrones de transacciones implementados.
- [ ] API y panel de demostración.

Fraude tiene un modelo entrenado y un servicio de scoring local. El módulo de grafos cuenta con perfilado de red, extracción de subgrafos, indicadores de sospecha y servicios de consulta (ver [contrato de variables de grafos](docs/grafos/contrato-variables.md) y [perfil de red](docs/grafos/perfil-red.md)). La API y el panel integrados siguen pendientes.

## Estructura

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
`pyproject.toml` declara el paquete Python base; las dependencias de datos, API y panel se agregarán cuando se implemente cada componente.
