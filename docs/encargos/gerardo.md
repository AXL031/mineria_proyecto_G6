# Encargo de Gerardo — reproducción, versiones y monitoreo

Estado inicial: pendiente. Leer [contratos y prioridades](../pendientes-cierre-2026-10-20.md). Pronósticos, comparación Holt-Winters, Naive seleccionado y monitoreo histórico ya existen. No sustituirlos ni volver a entrenarlos sin una causa documentada.

## GER-01 — preparación integral y entorno reproducible (P1)

### Archivos y propiedad

Responsable de `scripts/prepare_demo.py`, `scripts/setup_env.ps1`, dependencias `requirements/*`, extras de `pyproject.toml`, workflow `.github/workflows/tests.yml` y guía `docs/pruebas-reproduccion.md`. Coordinar con Angel los scripts start/stop si necesitan variables nuevas. Cada dueño entrega su CLI y artefactos; Gerardo los integra, no reimplementa sus modelos.

### Implementación

1. Inspeccionar los cambios locales actuales del preparador y conservar todas sus etapas: Silver transaccional, crédito, Gold temporal, segmentos, reclamos, fraude y patrones manuales.
2. Añadir DAG explícito: Silver → D1 de Taco → asociaciones de Cueva y regresión de Sevan; Bronze de redes → comparación de Rhamses. Monitoreo de desempeño, si se implementa, depende del archivo de predicciones de regresión. La comparación de demo se prepara con limit=10000 para coincidir con el panel/verificador.
3. No omitir una etapa solo porque exista un nombre de archivo. Validar schema_version, configuración, identidades y SHA de entradas de sus metadatos. Para artefactos antiguos sin contrato de metadatos comparable, documentar verificación específica y no asumir compatibilidad por existencia.
4. Generar `artifacts/reports/demo/preparation-manifest.json`: etapa, versión/huella de configuración, huellas de entrada/salida, estado (`built`, `reused`, `failed`, `skipped_optional`), inicio/fin UTC, duración, log y error si corresponde. Publicar estado final incluso ante fallo; una etapa dependiente no corre sobre salida incompleta.
5. Acordar `--force` consistente: reconstruir las etapas seleccionadas, incluido fraude si se solicita esa reconstrucción; documentar el cambio frente al comportamiento actual que conserva fraude existente. La ejecución normal reutiliza solo salidas verificadas. Una etapa no debe sobrescribir reportes Markdown versionados durante preparación de demo: usar rutas bajo artifacts/reports/demo.
6. Mantener subprocess con argumentos estructurados, cwd de proyecto, salida a logs y chequeo de código de retorno. Sin entrenamiento por HTTP. Acotar hilos numéricos como el preparador actual; no imprimir millones de filas.
7. Crear `requirements/lock-py312-windows.txt` con versiones exactas de dependencias directas/transitivas realmente instaladas y validadas en un entorno nuevo. Conservar archivos de extras/rangos para desarrollo; no publicar un freeze con rutas personales, credenciales o editable apuntando al disco del autor. Instalar el proyecto local sin resolver otro conjunto de versiones cuando se usa el lock.
8. Añadir opción explícita `-UseLock` al instalador común; sin cambiar silenciosamente su uso actual. Actualizar CI para validar Python 3.12, lock y suite con fixtures; el flujo de desarrollo por rangos puede verificarse en un trabajo separado si aporta cobertura. CI unitario no requiere LFS ni entrenamientos completos.
9. Registrar recursos observados de reproducción: SO, Python, versiones, espacio ocupado, duración de etapas y memoria aproximada/pico cuando pueda medirse. Si no se mide memoria, indicarlo; no inventar mínimos de RAM garantizados.
10. Ejecutar clon limpio con LFS, entorno nuevo y artefactos regenerados con una segunda persona. No copiar `.venv`, Silver/Gold ni modelos. Si se hace en otro directorio de la misma PC, llamarlo reproducción aislada local; la prueba en otra PC sigue pendiente hasta tener evidencia real.

### Pruebas y cierre

- Fixture de etapas prueba orden de dependencias, fallo de una etapa, reuso válido, configuración/entrada cambiada y salida incompleta. No ejecutar entrenamiento pesado en tests.
- `pip check` y suite completa en entorno del lock; logs de instalación/pruebas y versiones del intérprete.
- Preparación real seguida de verificación HTTP/páginas de Angel. Registrar fallos reales y reejecutar solo lo afectado al corregirlos.
- Entregar comandos de reproducción, manifiesto y aceptación de otra persona. Taco revisa el flujo y Sevan las versiones/modelos.

Docker/Compose es **P2 opcional**: si se conserva, crear Dockerfile/compose, montar originales/artefactos y comprobar arranque/API/panel con instrucciones desde cero; no incluir datasets/modelos enormes en capas. No marcar Docker obligatorio por aparecer entre tecnologías sugeridas.

## GER-02 — historial del desempeño de regresión (P2 recomendado)

Esta ampliación da evidencia adicional de seguimiento de modelos; el monitoreo histórico de distribuciones ya funciona y debe permanecer disponible. El MVP de esta tarea cubre solo regresión; no anunciar monitoreo de rendimiento para todos los módulos sin implementarlo.

### Archivos y entrada

- Crear `configs/model_monitoring.json`, `src/bankshield/evaluation/model_monitoring.py`, `scripts/monitor_model_performance.py`, `src/bankshield/services/monitoring.py` y `api/routers/monitoring.py`.
- Ampliar `dashboard/pages/04_pronosticos.py` con una sección separada de desempeño de regresión, manteniendo proyección y monitoreo histórico.
- Crear pruebas `test_model_monitoring.py`, `test_api_monitoring.py` y ampliar pruebas de página temporal.
- Crear `docs/monitoreo/desempeno-modelos.md` y `docs/monitoreo/mantenimiento.md`.
- Entrada: `predictions.parquet`, `model.joblib`/metrics de SEV-01 y manifiesto D1. Validar SHA/model_id, fuente, filas, particiones y ausencia de row_id duplicados. No recalcular predicciones con otro modelo para completar filas faltantes silenciosamente.

### Cálculo y alertas

1. Referencia de desempeño: validation 324–378 del mismo artefacto. Como allí se seleccionó el modelo, documentar que la referencia puede ser optimista; no presentarla como una evaluación externa.
2. Agrupar test 379–718 en ventanas consecutivas de 25 steps, comenzando en 379; conservar la última ventana más corta indicando `complete_window=false`. Tratar 719–743 como un único lote stress separado y claramente rotulado.
3. Por lote calcular filas, rango real/configurado, MAE, RMSE y sesgo. Default `min_rows=100`; por debajo, estado `insufficient_data`, sin alerta de deterioro. Una ventana incompleta con filas suficientes conserva métricas, pero se señala su menor duración.
4. Alerta configurada: `MAE_batch > MAE_reference * 1.20` y `MAE_batch - MAE_reference > 1e-9`, con datos suficientes. Guardar valores y razones. Si MAE_reference es cero, usar solo el criterio absoluto; cambio relativo null. Los umbrales son académicos, fijados antes de consultar los lotes; no calibrarlos con stress.
5. Estados de lote: `stable`, `performance_degraded`, `insufficient_data`. Identificar explícitamente los lotes con etiquetas/valores reales; sin objetivos reales no calcular desempeño ni inferir que está estable.
6. Escribir ejecuciones inmutables bajo `artifacts/reports/monitoring/runs/<run_id>.json`, con UTC, modelo, fuente, configuración, referencia, ventanas y limitaciones. `run_id` generado internamente, sin rutas externas; publicar archivo al completar su escritura. Una nueva corrida no borra el historial anterior.
7. No reentrenar ni reemplazar modelos automáticamente al disparar una alerta.

### HTTP y mantenimiento

GET `/api/monitoring/runs?model_id=<sha256>&limit=20`, limit 1–100, orden UTC descendente; respuesta `total`, `runs` con run_id, created_at_utc, model_id, status y recuento de alertas. Sin historial válido: 200 y lista vacía; almacén ilegible/configuración incompatible: 503.

GET `/api/monitoring/runs/{run_id}`: 200 ejecución completa, 404 ID inexistente, 422 ID con formato inválido; impedir traversal y usar IDs generados por el sistema. Variable `BANKSHIELD_MONITORING_DIR`. Consultas solo leen, no generan corridas. Angel registra el router central cuando esté listo.

El panel muestra historial, modelo/periodos, MAE/RMSE por lote, alertas, insuficiencia de datos y stress; diferenciar desempeño de regresión frente a cambios de distribución PaySim. La guía de mantenimiento establece: revisar calidad/fuente/versión ante una alerta; evaluar candidatos en datos autorizados con protocolo nuevo; comparar antes de reemplazar; conservar versión previa para volver atrás. No automatizar esa decisión humana.

Pruebas: métricas manuales, límites de lote, resto corto, referencia cero, datos insuficientes, identidades mezcladas, duplicados, historial conservado, HTTP/paginación/path traversal y AppTest. Sevan revisa interpretación de métricas. Marcar esta tarea como recomendada al informar avance global.

## GER-03 — aceptación temporal pendiente (P1)

- [ ] Registrar revisión visual de cantidad/monto, horizontes y errores de API/página; los artefactos locales ya existen.
- [ ] Revisar con Sevan comparación, versiones y limitaciones de Naive/Holt-Winters, intervalos descriptivos y monitoreo histórico.
- [ ] Registrar aceptación humana real de integración, sin usar el commit en main como sustituto de revisión.
- [ ] Participar en revisión de particiones D1 de Taco e integración central de Angel.
