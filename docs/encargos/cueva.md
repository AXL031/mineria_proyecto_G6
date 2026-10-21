# Encargo de Cueva — asociaciones y aceptación transaccional

Estado inicial: pendiente. Leer [contratos y prioridades](../pendientes-cierre-2026-10-20.md) y [TAC-01](taco.md). El clasificador, sus cortes históricos, umbral y `/api/fraud/patterns` ya existen y deben seguir funcionando.

## CUE-01 — descubrimiento automático de asociaciones (P0)

### Resultado esperado

Descubrir reglas de la forma `condiciones transaccionales → isFraud=true`, elegirlas con train/validation y evaluar el conjunto congelado en test y stress. No basta con volver a calcular las seis reglas manuales. Las asociaciones describen la simulación; no cambian la predicción ni se presentan como causas.

### Archivos

- Crear `configs/associations.json`.
- Crear `src/bankshield/features/association_transactions.py` para transformar D1 en conjuntos de ítems.
- Crear `src/bankshield/models/associations.py` con minería Apriori acotada y evaluación.
- Crear `scripts/mine_associations.py` y `src/bankshield/services/associations.py`.
- Ampliar `api/routers/fraud.py` y `dashboard/pages/01_fraude.py` sin retirar contratos existentes.
- Crear `tests/unit/test_associations.py`, `test_api_associations.py` y ampliar pruebas de página de fraude.
- Crear `docs/fraude/asociaciones-descubiertas.md` con contrato, comando, resultados y limitaciones.

### Datos, algoritmo y selección

1. Validar D1 y huellas del Parquet/esquema de discretización. Reutilizar exactamente los bins de Taco; no recalcularlos en validación o test.
2. Ítems del antecedente v1: `type=<tipo>`, `amount_bin=<bin>`, `origin_balance_bin=<bin>`, `exceeds_origin_balance=<true|false>` y `positive_amount_equals_balance=<true|false>`. Los dos últimos comparan `amount > oldbalanceOrg` y `amount > 0 and amount == oldbalanceOrg`, respectivamente, como características primitivas ya documentadas en fraude; sus combinaciones y reglas se descubren por algoritmo. Cada fila tiene un valor por atributo.
3. `isFraud` solo forma el consecuente; `isFlaggedFraud`, IDs, step, partition y saldos posteriores no son ítems predictivos. No permitir antecedentes con dos valores del mismo atributo ni consecuentes repetidos en el antecedente.
4. Implementar Apriori acotado con contadores por bloques y poda por soporte. Generar conjuntos frecuentes desde train; no enumerar reglas por inspección del test. No se requiere agregar una biblioteca externa. Máximo tres ítems de antecedente y `max_candidates=10000`; exceder el límite falla explicando cómo reducirlo, sin truncar candidatos silenciosamente.
5. Defaults: `min_support=0.0001` para soporte conjunto de antecedente y consecuente; `min_antecedent_count=50`, `min_confidence=0.5`, `min_lift=2`, `max_rules=50`. Estos parámetros quedan fijados antes de la evaluación; los fixtures de pruebas pueden reducir mínimos.
6. Filtrar candidatos en train con esos mínimos. Evaluarlos en validation y conservar los que cumplan los mismos mínimos allí. Ordenar por lift de validation descendente, soporte conjunto descendente e ID canónico ascendente; congelar como máximo 50.
7. Evaluar solo ese conjunto en test y stress. No reemplazar reglas por su resultado posterior ni reordenar la selección por test. Guardar métricas de todas las particiones, incluidas las reglas seleccionadas que dejan de cumplirse.
8. Si no se seleccionan reglas, publicar un reporte válido con lista vacía y diagnóstico; no reducir umbrales automáticamente para producir hallazgos.

### Métricas y artefacto

Guardar `artifacts/models/associations/rules.json`. Por regla: ID derivado del antecedente ordenado y consecuente, ítems legibles, conteo total, coincidencias de antecedente, coincidencias conjuntas y positivos de la partición.

- `antecedent_support = n(A)/N`.
- `support = n(A y fraude)/N` — soporte conjunto; distinguirlo del soporte del antecedente mostrado por el reporte manual histórico.
- `confidence = n(A y fraude)/n(A)`.
- `lift = confidence / (n(fraude)/N)`.
- `fraud_coverage = n(A y fraude)/n(fraude)`.

Denominador cero: `null` y motivo. Las reglas pueden solaparse: no sumar coberturas. Añadir cobertura de la unión con conteo real si se muestra una cobertura global. Calcular `analysis_id` sobre contenido canónico de configuración, fuente, esquema y selección, excluyendo fecha y rutas absolutas; el servicio valida versión e identidad. No ligar estas reglas artificialmente al SHA del clasificador de fraude.

### HTTP y panel

`GET /api/fraud/associations?partition=test&limit=20&offset=0`, con partition en train/validation/test/stress, limit 1–100 y offset no negativo. Respuesta mínima:

```json
{
  "schema_version": 1,
  "analysis_id": "<sha256>",
  "method": "apriori_bounded",
  "partition": "test",
  "simulation_data": true,
  "selection_partition": "validation",
  "total_rules": 0,
  "limit": 20,
  "offset": 0,
  "rules": [],
  "limitations": []
}
```

Servicio de solo lectura y carga diferida; variable `BANKSHIELD_ASSOCIATIONS_REPORT`. Ausencia/incompatibilidad: 503; parámetros inválidos: 422; conjunto válido sin reglas: 200. La página conserva patrones manuales y agrega una sección diferenciada de reglas descubiertas, filtros, métricas, periodo, análisis y limitaciones. No usar el score o la alerta actual como consecuente: se evalúa contra la etiqueta observada.

### Pruebas y aceptación

- Fixture con reglas conocidas y comprobación manual de conteos, soporte conjunto, confianza, lift y cobertura.
- Cambiar test/stress no altera bins, candidatos ni reglas seleccionadas; cambiar etiquetas cambia evaluación pero nunca los ítems del antecedente.
- Manejar cero positivos, cero coincidencias, lista vacía, solapamiento, empate y límite de candidatos.
- Conteos equivalentes para distintos tamaños de bloque; selección/IDs deterministas.
- HTTP 200/422/503 y paginación consistente; AppTest consulta HTTP y distingue reglas manuales/descubiertas.
- Ejecutar minería completa con D1 real y entregar reporte sin afirmar mejoras no observadas.

Comandos objetivo:

```powershell
.venv-pruebas/Scripts/python.exe scripts/mine_associations.py --config configs/associations.json
.venv-pruebas/Scripts/python.exe -m unittest discover -s tests/unit -p "test*associations*.py" -v
```

**Aceptación:** reglas generadas por algoritmo, selección sin test, evaluación independiente, endpoint/página reales y trazabilidad. Sevan revisa método/evaluación; Taco confirma el contrato de datos. Dar a Angel casos HTTP y etiquetas estables de botones para su verificador; dar a Gerardo salidas y CLI para preparación.

## CUE-02 — cierre previo que continúa pendiente (P1)

- [ ] Revisar y registrar aceptación real con Taco de Silver/Gold y segmentación independiente de etiquetas.
- [ ] Revisar con Rhamses–Angel el contrato HTTP/navegación de fraude y la integración ampliada.
- [ ] Aportar fuente primaria, versión/fecha de obtención y condiciones de uso de la copia PaySim; actualizar `docs/datasets.md` sin inventar datos históricos de descarga.
- [ ] Participar en la demo y en la reproducción integrada de fraude; la reproducción aislada previa no acredita todo el proyecto.
- [ ] Revisar comparación de grafos de Rhamses, especialmente igualdad de universo/presupuesto y ausencia de etiqueta en el ranking.

Las atribuciones individuales adicionales del clasificador siguen siendo opcionales; la explicabilidad crediticia ya cubre una capacidad existente. No cambiar el modelo o umbral de fraude como efecto secundario de descubrir asociaciones.
