# Encargo de Taco — datos analíticos y cierre de segmentos

Estado inicial: pendiente. Leer primero [contratos y prioridades](../pendientes-cierre-2026-10-20.md). Trabajar sobre los cambios locales existentes sin descartarlos. Este encargo implementa datos y controles; Cueva implementa la minería de reglas y Sevan el modelo de regresión.

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

- [ ] Ensayar resumen, paginación, detalle de cuenta, segmento inexistente y parámetros inválidos con los artefactos locales ya preparados.
- [ ] Conservar la prueba de independencia de `isFraud`: fraude queda solo para describir grupos después del ajuste.
- [ ] Revisar con Cueva Silver/Gold y la corrección de segmentación; registrar nombres, fecha, decisión y evidencia de la aceptación real.
- [ ] Explicar perfiles, k seleccionado, silueta, estabilidad y límites; no presentar grupos como categorías de riesgo validadas.
- [ ] Apoyar a Cueva con procedencia/versión de PaySim y comprobar que las huellas del equipo coinciden.
- [ ] Reproducir su etapa en el clon limpio coordinado por Gerardo, sin copiar Parquet/modelos de esta PC.

No volver a asignar como trabajo nuevo la API/página de segmentos o su reconstrucción local ya documentada. No publicar el dataset analítico generado en Git.
