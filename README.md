# BankShield Analytics

Demostración académica de minería de datos y analítica financiera del Grupo 6. Las fuentes de transacciones PaySim, crédito y reclamos se analizan por separado: no existe una llave de cliente común.

## Cierre hasta semana 13

El cierre se desarrolla en la rama `cierre-semana-13`. Incluye asociaciones descubiertas, regresión numérica y comparación de clustering, series y grafos, además de los seis módulos existentes. Los modelos se preparan offline y la API/panel solo consulta los artefactos.

- [Matriz de los 19 entregables y encargados](docs/matriz-entregables.md).
- [Estado técnico, resultados y pendientes humanos](docs/cierre-semana13.md).
- [Problema, preguntas, objetivos y CRISP-DM](docs/metodologia-y-negocio.md).
- [Diccionario de las tres fuentes](docs/diccionario-datos.md), [inventario y fuentes](docs/datasets.md).
- [Fichas de KPIs e indicadores](docs/kpis-negocio.md) y [comparación por técnica](docs/evaluacion-comparativa.md).
- [Guion para la tercera presentación](docs/guion-tercera-presentacion.md).

## Preparar, ejecutar y verificar

Python 3.12 y Git LFS. Los originales Bronze están en LFS; los datos derivados y modelos se regeneran localmente y no se añaden a Git.

```powershell
git lfs pull
powershell -ExecutionPolicy Bypass -File scripts/setup_env.ps1 -UseLock
.venv-pruebas/Scripts/python.exe scripts/prepare_demo.py --scope full
powershell -ExecutionPolicy Bypass -File scripts/start_demo.ps1
.venv-pruebas/Scripts/python.exe scripts/verify_demo.py --profile full
powershell -ExecutionPolicy Bypass -File scripts/stop_demo.ps1
```

Panel local: http://127.0.0.1:8501. API/OpenAPI: http://127.0.0.1:8000/docs. Siete páginas: Fraude, Crédito, Redes, Pronósticos, Reclamos, Segmentos y Regresión. El script de inicio comprueba los artefactos del cierre; la API puede arrancar por sí sola sin modelos y devolver 503 en las capacidades no preparadas.

`prepare_demo.py --plan` muestra dependencias sin entrenar. La preparación publica manifiesto, huellas, duración, RSS aproximado y logs por corrida; reutiliza solo salidas verificadas. `--force` reconstruye la selección. El alcance `current` conserva el recorrido base de seis módulos y D1; no acredita las ampliaciones. GER-02 (historial de desempeño) se marca como P2 omitido explícitamente.

## Módulos y resultados

| Capacidad | Encargado académico | Evidencia |
| --- | --- | --- |
| Fraude y asociaciones | Cueva | [Entrenamiento](docs/fraude/resultados-entrenamiento.md), [reglas descubiertas](docs/fraude/asociaciones-descubiertas.md). |
| Crédito | Sevan | [Contrato y límites](docs/credito/contrato-variables.md). |
| Regresión numérica | Sevan | [Contrato](docs/regresion/contrato-variables.md), [comparación real](docs/regresion/resultados-modelo.md). |
| Grafos | Rhamses | [Red contra volumen](docs/grafos/comparacion-alertas.md). |
| Datos y segmentos | Taco | [D1](docs/transacciones/contrato-analitico.md), [clustering y referencia](docs/transacciones/segmentacion.md). |
| Temporal y preparación | Gerardo | [Comparación temporal](docs/pronosticos/resultados-holt-winters.md), scripts prepare/evaluate_forecast_*. |
| NLP e integración académica | Angel | [NLP](docs/reclamos/resultados-modelo.md), [matriz](docs/matriz-entregables.md). |

Este reparto conserva los encargos del equipo; la implementación de cierre en una rama común no acredita autoría personal o aceptación humana de cada compañero. Las fuentes históricas de las copias y sus confirmaciones pendientes se explican en el inventario.

## Pruebas y evidencia reproducible

```powershell
.venv-pruebas/Scripts/python.exe -m pip check
.venv-pruebas/Scripts/python.exe -m unittest discover -s tests/unit -v
.venv-pruebas/Scripts/python.exe scripts/build_academic_evidence.py
```

El último comando genera fichas y comparación desde reportes reales, con huellas de entradas; ejecutar después de la preparación completa. La suite usa fixtures pequeños sin descargar Bronze ni entrenar los originales en CI. Los resultados del cierre están fechados en su registro; el CI de esta rama no se presume ejecutado antes de publicarla.

## Antecedentes y límites

[Plan y responsabilidades](docs/plan-desarrollo.md), [contratos de octubre](docs/pendientes-cierre-2026-10-20.md) y [contexto original](BANKSHIELD_CONTEXTO_COMPLETO.md) conservan las decisiones e historia. Para estado actual prevalecen matriz y cierre de semana 13.

PaySim es simulación, step no es fecha y no se inventa moneda. Ningún resultado constituye política bancaria, recomendación de crédito o evidencia de ahorro real. Semana 16 tiene clasificación, NLP, explicabilidad, monitoreo y producto final; algunos ya están adelantados. Docker e historial ampliado siguen como P2 del plan.
