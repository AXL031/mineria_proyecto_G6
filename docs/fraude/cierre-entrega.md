# Entrega de fraude y patrones — Cueva

Revisión del 12 de octubre de 2026, realizada por Codex a solicitud de Cueva. Este documento registra la entrega técnica y su reproducción; no atribuye a Taco, Rhamses o Angel una revisión humana que todavía no se haya registrado.

## Alcance implementado

| Entrega | Evidencia |
| --- | --- |
| Perfil, etiqueta y calidad de PaySim | `scripts/profile_fraud.py`, [perfil](perfil-paysim.md), contrato Silver y huellas de Bronze/Parquet. |
| Variables anteriores a la operación | `type`, `amount`, `oldbalanceOrg` y dos derivados; etiquetas, cuentas y saldos posteriores fuera del clasificador. |
| Referencia y modelo supervisado | DummyClassifier y HistGradientBoostingClassifier; cortes cronológicos por steps enteros y umbral por coste elegido en validación. |
| Métricas y errores | AP, precisión, recall, F1, matriz de confusión y ejemplos TP/FP/FN/TN. |
| Predicción y evaluación por API | `POST /api/fraud/predict`, `GET /api/fraud/model`; identidad SHA-256 del mismo modelo que predice. |
| Asociaciones sencillas | Seis reglas fijas sobre tipo, monto y saldo anterior; soporte, confianza, lift y cobertura por partición. [Reporte completo](patrones-descriptivos.md). |
| Consulta de patrones por API | `GET /api/fraud/patterns`; rechaza un reporte de otro modelo/fuente o con recuentos/métricas inconsistentes. Reporte opcional: su ausencia no impide predecir. |
| Página de fraude | Formulario, alerta, score/umbral, métricas, condiciones de entrada y patrones, consumidos exclusivamente por HTTP. |
| Reproducción automatizada | `scripts/reproduce_fraud.ps1` reconstruye perfil, Silver, modelo, errores y patrones y verifica la página contra una API temporal real. |

## Contrato Silver revisado desde fraude

Se verificó técnicamente el contrato documentado por Taco: mismas columnas canónicas, predictores conservados, particiones temporales, controles requeridos, recuentos y huellas. El Silver local tiene 6,362,620 filas y su huella coincide con el reporte. Las pruebas ejercitan equivalencia Bronze/Silver y rechazan muestra, rechazos, procedencia distinta, huella distinta y Parquet modificado.

La política de duplicados sigue siendo conservarlos en Silver porque no hay identificador de transacción. El entrenamiento exige cero duplicados exactos detectados; si aparecen, debe detenerse y revisarse la política Cueva–Taco antes de continuar. Las etiquetas se conservan exclusivamente para evaluación y asociaciones retrospectivas, nunca como predictores ni antecedentes de las reglas.

Esta revisión técnica completa el trabajo de comprobación del lado de fraude solicitado por Cueva. La revisión cruzada humana del PR se mantiene como criterio de integración del equipo.

## Resultados y demostración

El artefacto Silver existente registra AP 0.961840, precisión 0.796634, recall 0.992511 y F1 0.883850; TP=3976, FP=1015, FN=30, TN=913596. No se utilizó esta revisión para cambiar hiperparámetros ni el umbral del clasificador.

La verificación HTTP del modelo local pasó 14 comprobaciones: disponibilidad de evaluación, identidad de patrones, inicialización de página, predicción con/sin alerta, igualdad página/API, persistencia al consultar métricas, visualización de patrones, entrada inválida, modelo ausente, limpieza del resultado fallido, health y API desconectada. Log/JSON locales: `artifacts/reports/fraud-delivery-check.log` y `fraud-delivery-check.json`.

La navegación desde el portal y la página se comprobaron en navegador: TRANSFER 1000 con saldo 500 sin alerta; TRANSFER 36942.13 con saldo 36942.13 con alerta. La tabla de prueba muestra seis asociaciones con porcentajes y límites. Captura local: `artifacts/reports/fraude-patrones-browser.png`.

Las reglas están predefinidas y no seleccionadas por sus resultados en prueba. Son asociaciones descriptivas, no una búsqueda exhaustiva de reglas ni explicaciones de la decisión del clasificador. El patrón de igualdad positiva monto/saldo alcanza 3,892 coincidencias fraudulentas en prueba y cobertura 97.1543%; describe una regularidad de PaySim y no garantiza ese comportamiento fuera del simulador.

## Reproducir desde un clon

Con Python 3.12, Git LFS y espacio/memoria para procesar el CSV completo:

```powershell
git lfs pull
powershell -ExecutionPolicy Bypass -File scripts/reproduce_fraud.ps1
```

El comando instala el entorno común y ejecuta la suite antes del procesamiento. Si el lanzador `py` no existe, pasar `-PythonExecutable 'C:\ruta\python.exe'`. Si el entorno ya está instalado y validado, se puede usar `-SkipInstall`; esa opción no acredita una instalación limpia. No se mide aquí el mínimo de RAM ni se promete una duración fija.

Las salidas se guardan en `artifacts/reports/fraud-reproduction/`: `profile.json`, `transactions.parquet`, `silver-quality.json`, `model/model.joblib`, `model/metrics.json`, `model/patterns.json`, `errors.json`, reportes Markdown y `delivery-check.json`. Son derivados fuera de Git. No se sustituyen los modelos previos ni los reportes de otros módulos.

Para iniciar tu demostración, en una terminal:

```powershell
$env:BANKSHIELD_FRAUD_MODEL = (Resolve-Path artifacts/reports/fraud-reproduction/model/model.joblib).Path
.venv-pruebas/Scripts/python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

En otra:

```powershell
.venv-pruebas/Scripts/python.exe -m streamlit run dashboard/app.py
```

Abrir `http://localhost:8501` y seleccionar Fraude. Para otra dirección de API, configurar `BANKSHIELD_API_URL` en la terminal del panel. Los patrones se buscan junto al modelo; `BANKSHIELD_FRAUD_PATTERNS` permite indicar otra ruta compatible. Si se cambia el modelo, regenerar su reporte de patrones. Sin configuración explícita de modelo, la API sigue usando `artifacts/models/fraud/model.joblib`, que puede no tener un reporte de patrones.

Para comprobar un artefacto ya generado sin repetir el entrenamiento:

```powershell
.venv-pruebas/Scripts/python.exe scripts/verify_fraud_delivery.py --model artifacts/reports/fraud-reproduction/model/model.joblib
```

La API HTTP temporal se inicia en un puerto libre de localhost y se cierra al terminar. La comprobación de página usa AppTest con solicitudes HTTP reales; la inspección visual de navegador fue una comprobación adicional.

## Reproducción aislada de esta revisión

Se preparó una copia de las fuentes y del Bronze en `artifacts/reports/fraud-clean-reproduction/`, sin reutilizar Silver ni modelos, y un entorno virtual nuevo. No es un clon remoto adicional ni prueba la descarga de LFS en otro equipo; comprueba reconstrucción con el mismo CSV completo en fuentes y dependencias aisladas.

En ese entorno, `pip check` pasó y **160 pruebas pasaron en 17.150 segundos**. Versiones principales: Python 3.12.14, NumPy 2.5.4, pandas 3.0.6, scikit-learn 1.9.1, PyArrow 25.0.1. La suite final en el entorno original también pasó: **160 pruebas en 16.617 segundos**. Los avisos de TestClient y NumPy en series pequeñas no produjeron fallos.

La reconstrucción completa terminó con código 0: perfil de 6,362,620 filas y 8,213 fraudes, Silver sin rechazos, entrenamiento desde ese Silver nuevo, análisis de errores, asociaciones y **14 comprobaciones HTTP/página aprobadas** sobre el modelo nuevo. Conservó los cortes 323/378 y reprodujo el umbral 0.09878304839801404, AP 0.9618400220552937, precisión 0.7966339410939691, recall 0.9925112331502746 y la matriz TP=3976, FP=1015, FN=30, TN=913596. Estas cifras coinciden con el experimento Silver previo sin usar la prueba para cambiar la configuración.

Evidencia local dentro de la copia aislada: `tests-clean.txt`, `reproduction.txt`, `environment-lock.txt` y `artifacts/reports/fraud-reproduction/{silver-quality.json,model/metrics.json,errors.json,model/patterns.json,delivery-check.json}`. La instalación usa una referencia editable a la propia copia aislada, no al código del directorio original. La copia completa está excluida de Git.

## Qué permite avanzar y qué sigue pendiente del equipo

- Fraude tiene contrato, implementación, asociaciones, endpoints, página y comandos propios. Puede evolucionar sin esperar los modelos o vistas de crédito, segmentos, pronósticos o reclamos.
- `oldbalanceOrg` debe existir antes de la operación. Si el sistema objetivo no lo tiene, se requiere otro contrato y un modelo nuevo; no usar saldo posterior ni rellenar un saldo ficticio. La demostración actual queda limitada a PaySim.
- Procedencia/licencia del CSV y requisitos finales del curso siguen siendo decisiones compartidas. No se presume su confirmación.
- La revisión humana cruzada del PR y del contrato API/navegación con Rhamses–Angel debe registrarse antes de declarar aceptación de todo el equipo. Las verificaciones automáticas y visuales ya aportan evidencia para esa revisión.
- Atribuciones individuales, reglas aprendidas adicionales y validación fuera de PaySim son ampliaciones posteriores; no bloquean la entrega académica básica implementada aquí. Para reglas nuevas, no ajustar sobre la prueba histórica ya consultada.
