# Contrato inicial de variables — Cueva

## Momento de la predicción

El primer modelo estimará riesgo **antes de ejecutar la transacción**. Sus datos de entrada deben existir en ese momento. El CSV de PaySim es una simulación; su capacidad predictiva no demuestra desempeño en una entidad bancaria.

| Campo | Uso inicial | Motivo |
| --- | --- | --- |
| `type` | Predictor categórico | Tipo de operación solicitado. |
| `amount` | Predictor numérico | Monto solicitado, finito y no negativo. |
| `oldbalanceOrg` | Predictor numérico | Saldo anterior del origen; requiere confirmar disponibilidad en el sistema objetivo. |
| `amount_to_origin_balance` | Predictor derivado | `amount / (oldbalanceOrg + 1)`; definición estable para saldo cero. |
| `exceeds_origin_balance` | Predictor derivado | Indica si el monto supera el saldo anterior del origen. |
| `step` | División temporal y perfilado | Paso de simulación; queda fuera de los predictores iniciales. |
| `isFraud` | Etiqueta | Nunca entra en el vector de variables. |
| `isFlaggedFraud` | Solo auditoría | Señal de otro detector; su disponibilidad y lógica deben verificarse antes de cualquier uso predictivo. |
| `newbalanceOrig`, `newbalanceDest` | Excluidos | Saldos posteriores a ejecutar la operación. |
| `nameOrig`, `nameDest` | Análisis de entidades | No se codifican como predictores iniciales para evitar memorizar cuentas. |
| `oldbalanceDest` | Excluido inicialmente | Disponibilidad y significado del saldo destino requieren revisión adicional. |

`build_fraud_features` aplica una lista explícita de variables y rechaza tipos desconocidos, valores ausentes, cantidades negativas y números no finitos. Los escaladores, codificadores y estadísticas agregadas futuras deben ajustarse exclusivamente con entrenamiento.

## Primera entrega implementada

- Perfilado completo en lectura secuencial, con conteos por etiqueta, tipo y paso.
- Controles de cabecera, campos ausentes, valores numéricos, tipos y etiquetas binarias.
- JSON agregado en `artifacts/reports/fraud/`; informe resumido en `docs/fraude/perfil-paysim.md`.
- Constructor inicial de variables, reutilizado por el entrenamiento documentado abajo.
- Pruebas que comprueban exclusión de información posterior, registros inválidos y manejo de referencias LFS.

No se corrige Bronze ni se implementa el pipeline Silver/Gold de Taco. El perfil no mide duplicados exactos, cuentas únicas ni cuantiles; estos controles deben completarse en la etapa de calidad compartida.

## Ejecución desde la raíz del proyecto

Requiere Python 3.11 o posterior. Esta primera entrega solo usa la biblioteca estándar.

```powershell
python scripts/profile_fraud.py --markdown docs/fraude/perfil-paysim.md
python -m unittest discover -s tests/unit -p "test_fraud*.py" -v
```

Para una comprobación rápida se puede añadir `--limit 10000`; ese informe se identifica como muestra de primeras filas y no se debe presentar como evaluación del dataset completo.

## Continuación implementada

El [entrenamiento y scoring](entrenamiento.md) usa este contrato, con particiones
temporales, una línea base y un clasificador. La versión vectorizada del constructor
se comprueba contra la versión de un registro y conserva las mismas exclusiones.

## Secuencia de modelado

1. Acordar con Taco el contrato Silver y la disponibilidad de los predictores.
2. Definir cortes por `step`, conservando operaciones del mismo paso en una sola partición y verificando clases por periodo. Revisar también cuentas repetidas entre particiones.
3. Comparar una línea base con un clasificador. Reportar prevalencia, PR-AUC, precisión, recall y matriz de confusión.
4. Elegir el umbral exclusivamente en validación con un supuesto de coste explícito, y evaluar una vez en prueba.
5. Guardar modelo y métricas antes de implementar el servicio y la página de fraude.
