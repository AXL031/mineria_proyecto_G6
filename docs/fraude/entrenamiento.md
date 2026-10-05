# Entrenamiento y scoring de fraude — Cueva

## Alcance de esta entrega

Se implementa un lector temporal del CSV de Bronze, una línea base, un clasificador,
selección del umbral en validación, evaluación final en prueba y scoring local del
artefacto guardado. El procesamiento Silver/Gold y la infraestructura API/panel
siguen en el reparto del equipo; el lector puede sustituirse sin cambiar el contrato
de variables ni la evaluación.

## Separación fijada para el primer experimento

| Partición | Pasos de simulación | Filas | Fraudes |
| --- | --- | ---: | ---: |
| Entrenamiento | 1–323 | 4463587 | 3643 |
| Validación | 324–378 | 980416 | 564 |
| Prueba | 379–743 | 918617 | 4006 |

Los límites son los pasos que alcanzan aproximadamente el 70 % y 85 % de filas
acumuladas. `derive_split_steps` solo utiliza pasos y recuentos, no etiquetas.
Cada paso pertenece a una única partición. La prevalencia cambia entre periodos;
esto debe conservarse y explicarse, sin eliminar pasos por contener solo fraude.
Esta evaluación temporal puede incluir cuentas observadas anteriormente y no
equivale a evaluar únicamente cuentas nuevas.

## Modelo y criterio de decisión

- Línea base: `DummyClassifier(strategy="prior")`, ajustada con entrenamiento.
- Clasificador: `HistGradientBoostingClassifier`, 80 iteraciones y hasta 15 hojas.
- Variables: las definidas en el [contrato](contrato-variables.md); tipo transaccional
  se codifica en el pipeline ajustado con entrenamiento.
- No se balancean ni se descartan clases. La parada temprana aleatoria está desactivada.
- El umbral minimiza `FP × 1 + FN × 20` exclusivamente en validación. Se considera
  también la opción de no emitir alertas; en empates se elige el umbral mayor.
- Los costes son supuestos académicos, no pérdidas monetarias medidas. Antes de
  adoptar una política de negocio deben acordarse con el equipo.
- El JSON conserva Average Precision (AP), área trapezoidal de precisión-recall,
  precisión, recall, F1, matriz de confusión y coste supuesto. AP y el área
  trapezoidal se reportan como métricas diferentes.
- El score es una salida del clasificador sin calibración externa; no se presenta
  como una probabilidad validada de fraude en un banco real.

Después de elegir el umbral, el modelo queda congelado y se evalúa en prueba.
Una ejecución reproduce el protocolo; las métricas de prueba de esta versión no
deben usarse para escoger hiperparámetros o ajustar su umbral.

## Entorno y comandos

El entorno local `.venv` está preparado con Python 3.12. Las dependencias generales
están en el extra `fraud` de `pyproject.toml`, y las versiones de esta ejecución
están fijadas en `requirements/fraud.txt`. Con un intérprete Python 3.12 disponible,
se puede crear el entorno desde la raíz y ejecutar:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements/fraud.txt
.venv/Scripts/python.exe -m pip install -e . --no-deps
.venv/Scripts/python.exe scripts/profile_fraud.py --markdown docs/fraude/perfil-paysim.md
.venv/Scripts/python.exe -m unittest discover -s tests/unit -p "test_fraud*.py" -v
.venv/Scripts/python.exe scripts/train_fraud.py
.venv/Scripts/python.exe scripts/predict_fraud.py --type TRANSFER --amount 1000 --origin-balance 500
```

El entrenamiento verifica la huella del CSV contra el perfil completo y conserva
los recuentos. Si cambia la fuente o aparecen registros inválidos, se detiene.
Lee en bloques, pero materializa las variables de las tres particiones para
entrenar y evaluar; necesita más memoria que el perfilado secuencial.

La configuración está en `configs/fraud.json`. Las rutas de entrada, perfil,
configuración, salida e informe pueden cambiarse mediante argumentos de
`scripts/train_fraud.py --help`.

## Salidas e integración

- `artifacts/models/fraud/model.joblib`: pipeline, umbral, contrato y metadatos.
- `artifacts/models/fraud/metrics.json`: métricas, versiones, configuración y huellas de código.
- [Resultados de entrenamiento](resultados-entrenamiento.md): resumen Markdown de la ejecución.
- `FraudScorer` en `src/bankshield/services/fraud.py`: recibe registros con `type`,
  `amount` y `oldbalanceOrg`; devuelve `score`, `alert`, `threshold` y
  `score_is_calibrated=false`. No recibe ni requiere la etiqueta.

Los artefactos se reconstruyen localmente y están excluidos de Git. El servicio
se conectará posteriormente al contrato de API de Rhamses y al panel.

## Auditoría y trabajo posterior

La lectura registra intersecciones de una muestra determinista aproximada del 1 %
de cuentas por rol. Esto detecta coincidencias, pero no sustituye una auditoría
completa de entidades ni comprueba duplicados exactos. Se mantienen pendientes
el contrato definitivo Silver, la disponibilidad real del saldo anterior,
las explicaciones de casos y la conexión del endpoint y página de fraude.
Las reglas de asociación se incorporarán después de integrar el clasificador.

## Resultado de la primera ejecución

Se entrenó con las 4463587 filas del periodo de entrenamiento y se evaluó en las
918617 filas del periodo de prueba. El umbral seleccionado en validación fue
`0.09878304839801404`. En prueba: AP `0.961840`, precisión `0.796634`, recall
`0.992511`, 3976 verdaderos positivos, 1015 falsos positivos y 30 falsos negativos.
Estos valores describen este experimento simulado y sus costes supuestos.

Las 13 pruebas del módulo verifican el contrato sin información posterior,
particiones por pasos completos, selección del umbral frente a un cálculo
exhaustivo, manejo de empates, métricas, fuente modificada y recarga del artefacto.

## Referencias

- [HistGradientBoostingClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingClassifier.html)
- [Average Precision](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html)
