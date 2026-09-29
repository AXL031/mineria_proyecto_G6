# BankShield Analytics

Proyecto académico de minería de datos y analítica financiera. La visión incluye detección de fraude, riesgo crediticio, análisis de reclamos, pronósticos y explicabilidad sobre una arquitectura Bronze → Silver → Gold.

## Punto de partida

La [base del proyecto](docs/bases-del-proyecto.md) define el alcance inicial, los límites de las fuentes públicas, la arquitectura propuesta, los criterios de evaluación, el reparto entre los seis integrantes y el orden de trabajo. Es una propuesta de ejecución para discutir con el equipo antes de implementar los módulos.

Los tres CSV aportados están organizados localmente en `data/bronze/`. El [inventario de datos](docs/datasets.md) registra sus columnas, tamaños y huellas SHA-256. Los CSV y las salidas generadas están excluidos de Git; cada integrante debe obtener su propia copia de los datos.

**Primer incremento propuesto:** cargar transacciones, aplicar controles de calidad, construir un mart analítico, entrenar un detector de fraude de referencia y mostrar sus resultados en un panel local. El mismo recorrido servirá como patrón para los módulos posteriores.

## Estado

- [x] Contexto y bases documentados.
- [x] Fuente transaccional de trabajo elegida: archivo con esquema PaySim.
- [ ] Procedencia y licencia de los tres archivos confirmadas.
- [ ] Contrato de datos y muestra exploratoria validados.
- [ ] Pipeline Bronze → Silver → Gold reproducible.
- [ ] Modelo de referencia y evaluación.
- [ ] API y panel de demostración.

Los datasets están disponibles solo en este equipo; todavía no hay modelos ni servicios implementados.

## Estructura

| Ruta | Propósito |
| --- | --- |
| `data/bronze/` | CSV originales, separados por dominio y excluidos de Git. |
| `data/silver/`, `data/gold/` | Datos limpios y marts generados. |
| `src/bankshield/` | Ingesta, transformaciones, variables, modelos y servicios compartidos. |
| `api/`, `dashboard/` | API y panel de demostración. |
| `tests/` | Pruebas unitarias y de integración. |
| `configs/`, `scripts/`, `notebooks/` | Configuración, comandos y exploración. |
| `artifacts/` | Modelos y reportes generados, fuera de Git. |

Cada carpeta incluye una breve guía o un marcador para que la estructura aparezca al clonar el repositorio.
`pyproject.toml` declara el paquete Python base; las dependencias de datos, API y panel se agregarán cuando se implemente cada componente.
