# Encargo de Taco — datos analíticos y cierre de segmentos

Estado inicial: pendiente. Leer primero [contratos y prioridades](../pendientes-cierre-2026-10-20.md). Trabajar sobre los cambios locales existentes sin descartarlos. Este encargo implementa datos y controles; Cueva implementa la minería de reglas y Sevan el modelo de regresión.

## Estado al 21 de octubre de 2026

**TAC-01 — implementado y ejecutado.** Archivos: `configs/analytics.json`,
`src/bankshield/transforms/analytical_transactions.py`,
`scripts/build_analytics_transactions.py`, `docs/transacciones/contrato-analitico.md`
y `tests/unit/test_analytical_transactions.py` (24 pruebas aprobadas). Corrida
completa sobre el Silver local: 6,362,620 filas, 0 excluidas, nueve controles
aprobados, monto y fraudes conservados. Huellas: Silver
`47C786D9…C2E46C`, D1 `A4C6F55E…234960EA`, esquema de bins
`54685F5B…1AD9386`. Dos ejecuciones consecutivas dieron la misma huella; la
segunda tardó ~21 s. La memoria no se instrumentó: los buffers de cuantiles
suman ~71 MB.

Particiones entregadas: `train` 1–323 (4,463,587), `validation` 324–378
(980,416), `test` 379–718 (918,321) y `stress` 719–743 (296). Cortes de
discretización: `amount` 21,649.48 / 157,428.26 y `oldbalanceOrg` 28.00 /
51,716.00.

Fixture para Cueva y Sevan:
`scripts/build_analytics_transactions.py --write-fixture artifacts/reports/analytics/fixture`.

**TAC-02 — ensayo técnico completo; quedan las revisiones humanas.** El nuevo
`scripts/verify_segments.py` ejecuta 18 comprobaciones contra los artefactos
locales (resumen, paginación, detalle, segmento y cuenta inexistentes, límite y
desplazamiento inválidos, artefacto ausente), todas aprobadas, con evidencia en
`artifacts/reports/segments-http-check.json`. Se corrigió la consulta de cuentas
para ordenar por actividad, como ya indicaba el contrato, con prueba nueva.

Suite completa al 21 de octubre: 263 pruebas, 261 aprobadas. Las 2 restantes
fallan por `statsmodels` ausente en este entorno: la dependencia ya está
declarada en el extra `forecast` y en `requirements/forecast.txt`, pero el
`.venv-pruebas` local se creó antes de esa incorporación. No es un fallo del
código de segmentos ni de D1; hay que reinstalar el extra para verificar la suite
completa.

Siguen pendientes, por ser tareas humanas: aceptación cruzada del contrato con
Cueva, revisión de particiones por Gerardo, revisión de navegación con
Rhamses–Angel y reproducción en un clon/entorno limpio coordinada con Gerardo.


## TAC-01 — tabla compartida para asociaciones y regresión (P0)

### Resultado esperado

Un script repetible construye D1 desde Silver, con trazabilidad, particiones temporales y discretización ajustada únicamente con train. No modifica el Silver, el mart de segmentos ni el modelo de fraude existente.

### Archivos

- Crear `configs/analytics.json` con entrada, reporte Silver, salidas, cortes y cuantiles `[1/3, 2/3]` expresados como números JSON.
- Crear `src/bankshield/transforms/analytical_transactions.py` con funciones separadas de validación, particionado, ajuste/aplicación de bins y construcción del archivo.
- Crear `scripts/build_analytics_transactions.py`, con `--config` y rutas relativas resueltas contra la raíz del proyecto.
- Generar `data/gold/analytics/transactions.parquet`, `artifacts/reports/analytics/dataset.json` y `discretization.json`.
- Crear `docs/transacciones/contrato-analitico.md` y `tests/unit/test_analytical_transactions.py`.

### Implementación paso a paso

1. Verificar existencia, esquema y tipos del Silver, calidad aprobada y huella coincidente con su reporte. Reutilizar los controles/huellas existentes; no declarar aprobado un reporte parcial. Registrar filas de entrada, salida y excluidas.
2. Leer columnas `step`, `type`, `amount`, `oldbalanceOrg`, `isFraud`. Validar steps enteros 1–743, tipo conocido, montos/saldos finitos no negativos y etiqueta binaria. Un valor inválido detiene la construcción con motivo; no eliminarlo silenciosamente.
3. Asignar `row_id` ordinal base 1 antes de filtrar y preservarlo entre bloques. Con la misma entrada, configuración y orden, el ID debe ser estable.
4. Asignar `partition`: train 1–323, validation 324–378, test 379–718, stress 719–743. Cada fila pertenece exactamente a una. No usar `isFraud` para seleccionar, equilibrar o asignar particiones.
5. Ajustar terciles de monto y saldo solo en train, usando cuantiles exactos de las dos columnas; cargar únicamente esas columnas de train si hace falta para el cálculo. El resto de la escritura puede procesarse por bloques. No hacer muestreo oculto para calcular cuantiles.
6. Conservar solo cortes estrictamente entre el mínimo y máximo de train y colapsar los repetidos. Usar intervalos `(-inf, c1]`, `(c1, c2]`, `(c2, +inf)` y etiquetas ordenadas `b0`, `b1`, `b2`; si no quedan cortes interiores, usar solo `b0`, también al aplicar valores posteriores. Los extremos abiertos se expresan en metadatos como `null` con semántica documentada, nunca Infinity JSON. Los valores cero pertenecen al primer intervalo que los contenga.
7. Guardar bordes, convención de cierre, columnas de ajuste, rango de train, recuentos por bin, `schema_version` y una huella canónica del esquema. Aplicar exactamente esos bordes a validation/test/stress.
8. Escribir Parquet y JSON mediante archivos temporales y reemplazo al finalizar; limpiar temporales propios en fallo. El reporte debe vincular SHA-256 del Silver, del Parquet final y del esquema de bins. El dataset no se anuncia completo hasta publicar sus metadatos consistentes.
9. Reportar conservación por partición: filas, suma de `amount` con tolerancia numérica explícita y conteos por tipo/etiqueta. `source_sha256` y `dataset_sha256` tienen significados distintos y no se intercambian.

### Pruebas necesarias

- Bordes 323/324, 378/379, 718/719 y 743; rechazo fuera de rango; filas sin pérdida ni duplicación de IDs.
- Cambiar solo valores de test/stress no cambia bordes de bins ni filas de train.
- Cambiar solo etiquetas no cambia particiones, bins ni variables de entrada de regresión.
- Todos los valores iguales, cortes repetidos, cero y valores posteriores superiores al máximo de train.
- Igual resultado al procesar el fixture en bloques de distinto tamaño.
- Huella/reporte de entrada incorrectos y fila inválida provocan fallo sin publicar un resultado completo.

### Entrega y dependencias

Entregar a Cueva y Sevan un fixture pequeño D1 y los dos JSON con el mismo esquema final; pueden desarrollar sin esperar a la corrida completa. Ejecutar el script sobre Silver completo y registrar tiempo, memoria aproximada y tamaños de salida. Si el entorno no permite la ejecución completa, informar el bloqueo y no declarar entrega de datos reales.

Comando objetivo, después de implementarlo:

```powershell
.venv-pruebas/Scripts/python.exe scripts/build_analytics_transactions.py --config configs/analytics.json
.venv-pruebas/Scripts/python.exe -m unittest discover -s tests/unit -p "test_analytical_transactions.py" -v
```

**Aceptación:** D1 y metadatos coherentes, controles de conservación aprobados, pruebas sin fuga y consumo correcto por Cueva/Sevan. Gerardo revisa particiones; Cueva registra aceptación humana del contrato cuando la confirme.

## TAC-02 — segmentos y trazabilidad pendientes (P1)

- [x] Ensayar resumen, paginación, detalle de cuenta, segmento inexistente y parámetros inválidos con los artefactos locales ya preparados. Hecho el 21 de octubre: `scripts/verify_segments.py`, 18 comprobaciones aprobadas con 146,629 cuentas (`artifacts/reports/segments-http-check.json`).
- [x] Conservar la prueba de independencia de `isFraud`: fraude queda solo para describir grupos después del ajuste. Verificado en `tests/unit/test_segments.py` y en D1 (`test_changing_labels_does_not_change_partitions_or_bins`).
- [ ] Revisar con Cueva Silver/Gold y la corrección de segmentación; registrar nombres, fecha, decisión y evidencia de la aceptación real. Requiere a las personas.
- [x] Explicar perfiles, k seleccionado, silueta, estabilidad y límites; no presentar grupos como categorías de riesgo validadas. Documentado en el [reporte de segmentación](../transacciones/segmentacion.md) y en el [contrato analítico](../transacciones/contrato-analitico.md); k=2, silueta 0.2305, ARI 0.7280.
- [ ] Apoyar a Cueva con procedencia/versión de PaySim y comprobar que las huellas del equipo coinciden. La huella local del CSV coincide con su reporte; falta la confirmación de fuente/licencia de Cueva.
- [ ] Reproducir su etapa en el clon limpio coordinado por Gerardo, sin copiar Parquet/modelos de esta PC.

No volver a asignar como trabajo nuevo la API/página de segmentos o su reconstrucción local ya documentada. No publicar el dataset analítico generado en Git.
