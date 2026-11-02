# GER-03 — verificación técnica y aceptación pendiente

Fecha: 2 de noviembre de 2026. Rama de trabajo: `gerardo`, base `687f125`.
Estado: **validación técnica realizada; Gerardo confirmó el funcionamiento del
aviso en el panel; revisión visual exhaustiva y aceptación cruzada pendientes**.
Este registro no cierra GER-01 ni acredita reproducción desde un clon limpio.

## Alcance y evidencia

Se verificó el módulo temporal existente sin reentrenar ni sustituir sus modelos,
datos o reportes históricos. Se añadieron:

- `scripts/verify_forecast_delivery.py`: verificación de artefactos, API central
  por HTTP real, página con AppTest y recuentos de particiones sobre Silver real.
- Pruebas HTTP de objetivos, horizontes, validación de entradas, artefactos
  ausentes, monitoreo incompatible y Gold que incumple el contrato.
- Pruebas de controles y estados de error del panel.
- Aviso cuando una proyección conservada corresponde a controles anteriores.
  Antes, cambiar horizonte o historia visible podía dejar un resultado anterior
  sin advertencia; ahora se pide volver a pulsar **Generar proyección**.

Resultados técnicos:

| Comprobación | Resultado |
| --- | --- |
| Pruebas de pronóstico, API, página, transformaciones temporales y D1 | 65 aprobadas; log `artifacts/reports/ger-03/unit-tests.log`. |
| Artefactos, HTTP y página contra API real | 71 comprobaciones aprobadas; resultados y huellas en `artifacts/reports/ger-03/verification.json`. |
| Repetición final de pruebas de página | 5 aprobadas tras ampliar los casos de error; log `artifacts/reports/ger-03/dashboard-tests-final.log`. |
| Integración central | Raíz anuncia `forecast`; OpenAPI contiene ambos endpoints temporales. |
| Proyecciones API | Cantidad y monto con horizontes 1, 24, 72 y 168; pasos futuros consecutivos, Naive, límites no negativos e historia de 24 steps. |
| Entradas inválidas | HTTP 422 para objetivo desconocido, horizonte 0/169/no numérico e historia 23/719. |
| Fallos aislados en fixtures | HTTP 503 ante archivos ausentes/monitoreo incompatible; HTTP 500 ante Gold inválido, según contrato actual. Los artefactos reales se conservaron. |
| Página con HTTP real | Cantidad y monto a 1/24/72 steps; consulta del monitoreo y sus seis alertas. |
| Fallos de página con respuestas simuladas | Artefactos ausentes, desconexión, HTTP 500 y JSON inválido muestran un error sin excepción de Streamlit. |

AppTest verifica ejecución y widgets; **no acredita inspección visual del gráfico**.
Durante la ejecución automática, la apertura del navegador integrado no pudo adjuntar una pestaña y el acceso al
navegador nativo agotó la espera de autorización. No se obtuvieron capturas ni
se declara revisión visual automática aprobada. Después, Gerardo revisó el
panel y confirmó en este chat: «Está bien, parece que sí funciona». Se registra
esa confirmación para el cambio visible del aviso, sin atribuirle una revisión
de todos los horizontes, capturas ni aceptación en nombre de Sevan.

El bloqueo inicial de AppTest dentro del entorno restringido ocurrió al crear
el par de sockets de asyncio. Fuera de ese entorno aparecieron límites de
arranque de 3 segundos. Las pruebas de esta página usan ahora un límite explícito
de 30 segundos; el verificador de entrega usa 60 segundos. No se modificó la
lógica de pronóstico para superar esos problemas del entorno.

## Comparación y limitaciones para revisar con Sevan

Los dos reportes de evaluación apuntan al Gold local con SHA-256
`1470868861a9bca368c6528655cb3cc33b0beab88889f8f9c8bf65708c58a7f3`.
Hay 743 filas Gold, 6,362,620 transacciones representadas y ningún nulo.
Los modelos se compararon en las mismas cuatro ventanas de 24 steps,
con entrenamiento anterior a prueba y última prueba en 718.
El tramo 719–743 queda fuera de esa selección.

| Objetivo | MAE Naive | MAE Naive estacional | Mejor MAE Holt-Winters |
| --- | ---: | ---: | ---: |
| Cantidad | 1,366.94 | 1,455.91 | 4,518.22 |
| Monto total | 215,326,691.23 | 246,284,163.91 | 569,670,181.45 |

Se conserva Naive por menor MAE. Esto no acredita precisión absoluta alta:
los errores relativos son elevados. Se implementó y evaluó Holt-Winters,
aunque no ganó la comparación.

Versiones locales observadas: Python 3.12.14, NumPy 2.5.3, pandas 3.0.6,
PyArrow 25.0.1, statsmodels 0.15.0, FastAPI 0.143.0 y Streamlit 1.65.0.
Python/NumPy/pandas coinciden con los reportes locales de evaluación;
statsmodels también coincide con el reporte Holt-Winters. Esto no sustituye
el lock ni la instalación limpia de GER-01.

Para la demo:

- El panel permite 1–72 steps y la API 1–168; su diferencia de rango es explícita.
- La API proyecta desde el último dato del Gold completo, **step 743**, que ya
  pertenece al cierre anómalo. Naive repite **8 transacciones** o
  **17,519,825.50 de monto** a partir del step 744. No confundir ese punto de
  partida de la demo con la selección del modelo en steps 1–718.
- Los límites usan percentiles 10/90 de cambios históricos por horizonte;
  no son intervalos probabilísticos calibrados ni garantizan cobertura del 80%.
- Monitoreo compara 694–718 con 719–743: seis indicadores en alerta,
  296 transacciones observadas y tasa de fraude del 100% en el cierre.
  Es un cambio histórico de una simulación; no demuestra vigilancia en producción.
- `step` representa una hora simulada, sin fecha calendario real.

## Revisión de particiones D1

Se leyeron las columnas `step` e `isFraud` del Silver real por bloques y se
contrastaron independientemente los cortes de Taco:

| Partición | Steps | Filas | Fraudes |
| --- | --- | ---: | ---: |
| train | 1–323 | 4,463,587 | 3,643 |
| validation | 324–378 | 980,416 | 564 |
| test | 379–718 | 918,321 | 3,710 |
| stress | 719–743 | 296 | 296 |

Los recuentos coinciden con el contrato D1 y `test + stress = 918,617`,
el universo de prueba histórico de fraude. Pasaron las pruebas de bordes
323/324, 378/379 y 718/719, independencia de etiquetas y ajuste de bins solo en train.

**Actualización durante GER-01 (2 de noviembre):** D1 y sus metadatos ya fueron
reconstruidos desde Silver completo. Pasaron sus nueve controles y coincidieron
las tres huellas documentadas por Taco: Silver `47C786D9…C2E46C`,
D1 `A4C6F55E…234960EA` y discretización `54685F5B…1AD9386`.
Esta evidencia técnica se suma al contraste inicial sobre Silver. La aceptación
humana cruzada de Gerardo–Taco sigue pendiente; reconstruir no equivale a firmarla.

## Repetir la verificación

Con el entorno del proyecto preparado y la API iniciada desde la raíz:

```powershell
# Terminal 1: API central; no inicia entrenamientos.
.venv-pruebas/Scripts/python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
# Terminal 2: panel con navegación central.
.venv-pruebas/Scripts/python.exe -m streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
# Terminal 3: artefactos, HTTP real, AppTest y cortes Silver.
.venv-pruebas/Scripts/python.exe scripts/verify_forecast_delivery.py
```

Para repetir las pruebas pertinentes:

```powershell
.venv-pruebas/Scripts/python.exe -m unittest discover -s tests/unit -p "test_forecast*.py" -v
.venv-pruebas/Scripts/python.exe -m unittest discover -s tests/unit -p "test_api_forecast.py" -v
.venv-pruebas/Scripts/python.exe -m unittest discover -s tests/unit -p "test_temporal*.py" -v
.venv-pruebas/Scripts/python.exe -m unittest discover -s tests/unit -p "test_analytical_transactions.py" -v
```

## Aceptación que falta registrar

No marcar una revisión como realizada sin confirmación de quien la hace.

- [x] Verificación técnica de cantidad, monto, horizontes y errores, con evidencia local.
- [x] Contraste técnico de los cortes D1 sobre Silver real y pruebas del contrato.
- [x] Gerardo confirmó en el chat el funcionamiento del aviso en el panel
  el 2 de noviembre de 2026.
- [ ] Gerardo: abrir `http://127.0.0.1:8501`, entrar en **Pronósticos** y revisar
  gráfico, etiquetas, cantidad/monto, horizontes 1/24/72 y legibilidad de avisos.
  Cambiar un control sin regenerar: debe aparecer el aviso de controles anteriores;
  regenerar y comprobar que desaparece. Registrar fecha, observación y capturas.
- [ ] Sevan: confirmar revisión de comparación, versiones, intervalos descriptivos,
  exclusión de stress en evaluación y limitaciones del monitoreo histórico.
- [ ] Gerardo/equipo: confirmar aceptación humana de integración central.
- [x] Reconstrucción técnica de D1 completo, nueve controles y comparación de
  las tres huellas con la entrega documentada por Taco (durante GER-01).
- [ ] Gerardo–Taco: confirmar revisión humana de D1 y sus metadatos reconstruidos.

GER-03 permanece **parcial** hasta esas revisiones. El avance técnico permite
continuar GER-01 mientras se coordina la aceptación humana.
