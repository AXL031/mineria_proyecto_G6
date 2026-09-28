# BankShield Analytics

Proyecto académico de minería de datos y analítica financiera. La visión incluye detección de fraude, riesgo crediticio, análisis de reclamos, pronósticos y explicabilidad sobre una arquitectura Bronze → Silver → Gold.

## Punto de partida

La [base del proyecto](docs/bases-del-proyecto.md) define el alcance inicial, los límites de las fuentes públicas, la arquitectura propuesta, los criterios de evaluación, el reparto entre los seis integrantes y el orden de trabajo. Es una propuesta de ejecución para discutir con el equipo antes de implementar los módulos.

**Primer incremento propuesto:** cargar transacciones, aplicar controles de calidad, construir un mart analítico, entrenar un detector de fraude de referencia y mostrar sus resultados en un panel local. El mismo recorrido servirá como patrón para los módulos posteriores.

## Estado

- [x] Contexto y bases documentados.
- [ ] Fuente transaccional elegida y licencia revisada.
- [ ] Contrato de datos y muestra exploratoria validados.
- [ ] Pipeline Bronze → Silver → Gold reproducible.
- [ ] Modelo de referencia y evaluación.
- [ ] API y panel de demostración.

Todavía no hay datasets, modelos ni servicios implementados en este repositorio.
