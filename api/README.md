# API de Demostración — BankShield Analytics

Servicio web backend construido con **FastAPI** que expone endpoints analíticos para consumo de la plataforma y el dashboard interactivo.

## Estructura del Módulo

- `api/main.py`: Punto de entrada de la aplicación FastAPI, configuración de middleware CORS y registro de routers.
- `api/routers/graphs.py`: Endpoints del módulo de grafos de transacciones (`/api/graphs/*`).
- `api/routers/fraud.py`: Predicción y métricas de fraude (`/api/fraud/*`).
- `api/routers/credit.py`: Riesgo crediticio (`/api/credit/*`).
- `api/routers/segments.py`: Segmentación de cuentas de destino (`/api/segments/*`).
- `api/routers/forecast.py`: Proyección y monitoreo temporal (`/api/forecast/*`).

## Endpoints Disponibles (Grafos)

| Método | Endpoint | Parámetros | Descripción |
|---|---|---|---|
| `GET` | `/` | Ninguno | Health check y estado de los módulos. |
| `GET` | `/api/graphs/summary` | `limit` (opcional, default 100k) | Métricas globales de la red transaccional. |
| `GET` | `/api/graphs/account/{account_id}` | `account_id` | Consulta detallada de una cuenta y flujos de fondos. |
| `GET` | `/api/graphs/subgraph/{account_id}` | `depth` (1 o 2) | Nodos y aristas del subgrafo ego para visualizaciones. |
| `GET` | `/api/graphs/top` | `metric`, `top_n` | Ranking de cuentas por centralidad/flujo. |
| `GET` | `/api/graphs/patterns/suspicious` | `fanout_pct`, `fanin_pct` | Detección de cuentas con alertas atípicas combinadas. |

## Instrucciones de Ejecución

Desde la raíz del proyecto:

```powershell
python -m pip install -r requirements/api.txt
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

La documentación Swagger interactiva queda accesible en:
`http://127.0.0.1:8000/docs`

## Pruebas Unitarias

```powershell
python -m unittest tests/unit/test_api_graphs.py -v
```

## Endpoints de Fraude

| Método | Endpoint | Descripción |
| --- | --- | --- |
| `POST` | `/api/fraud/predict` | Score no calibrado, alerta, umbral e identidad del modelo; solo acepta `type`, `amount` y `oldbalanceOrg`. |
| `GET` | `/api/fraud/model` | Métricas y metadatos embebidos en el modelo que predice. |
| `GET` | `/api/fraud/patterns` | Asociaciones descriptivas por partición, vinculadas a la identidad del modelo y su Silver. |

`BANKSHIELD_FRAUD_MODEL` indica el modelo; por defecto se usa `artifacts/models/fraud/model.joblib`. Los patrones se leen de `patterns.json` junto al modelo o de `BANKSHIELD_FRAUD_PATTERNS`. Un reporte ausente, de otro modelo o inconsistente devuelve 503 y no deshabilita la predicción. Ver [entrega y reproducción](../docs/fraude/cierre-entrega.md).

## Endpoints de Crédito

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/credit/predict` | Probabilidad calibrada de impago asumido, clasificación frente al umbral y hasta cinco factores por oclusión. Solo acepta variables de la solicitud; rechaza `loan_grade`, `loan_int_rate` y campos extra. No recomienda montos. |
| `GET` | `/api/credit/model` | Métricas, particiones, versiones y límites embebidos en el artefacto. |

El modelo se indica con `BANKSHIELD_CREDIT_MODEL` (por defecto `artifacts/models/credit/model.joblib`). Si falta o es incompatible, responde 503 sin afectar a los demás módulos. Ver el [contrato de variables](../docs/credito/contrato-variables.md).

## Endpoints de Segmentos

| Método | Endpoint | Parámetros | Descripción |
|---|---|---|---|
| `GET` | `/api/segments/summary` | Ninguno | Perfil de los segmentos de cuentas de destino reincidentes (tamaño, actividad y tasa de fraude por segmento). |
| `GET` | `/api/segments/{segmento}/accounts` | `limit` (1-1000, default 50), `offset` (default 0) | Cuentas del segmento indicado, ordenadas por actividad. |
| `GET` | `/api/segments/{segmento}/account/{cuenta}` | Ninguno | Detalle de una cuenta de destino dentro de su segmento. |

Los datos se leen de `data/gold/segments/account_segments.parquet` y `artifacts/reports/segments.json`, generados por `scripts/segment_transactions.py` (rutas ajustables con `BANKSHIELD_SEGMENTS_PARQUET` y `BANKSHIELD_SEGMENTS_REPORT`). Si falta un artefacto responde 503 con el comando para generarlo; un segmento o cuenta inexistente responde 404 y un identificador inválido 422. Ver la [segmentación](../docs/transacciones/segmentacion.md).
## Endpoints de pronósticos

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/forecast/projection` | Historia y proyección Naive para cantidad o monto; admite `target`, `horizon` e `history_steps`. Incluye un intervalo empírico no calibrado. |
| `GET` | `/api/forecast/monitoring` | Comparación histórica de volumen, montos, tipos y fraude entre los steps 694–718 y 719–743. |

La serie se lee desde `data/gold/forecast/transactions_hourly.parquet` o desde
`BANKSHIELD_FORECAST_GOLD`. El monitoreo se lee desde
`artifacts/reports/forecast_monitoring.json` o desde
`BANKSHIELD_FORECAST_MONITORING`. Si falta un derivado, solo este módulo responde
503; la API puede seguir atendiendo los demás dominios.

## Demo de reclamos

El módulo `/api/complaints` expone `POST /predict` con `{"narrative": "texto en inglés"}`, y `GET /model`, `/summary` y `/examples`. El clasificador aplica la misma limpieza que Silver y devuelve producto y tres puntuaciones no calibradas. Rechaza entradas sin texto suficiente o términos reconocidos (422); artefactos ausentes/incompatibles responden 503 sin impedir otros módulos.

`BANKSHIELD_COMPLAINTS_MODEL`, `BANKSHIELD_COMPLAINTS_SILVER` y `BANKSHIELD_COMPLAINTS_EXAMPLES` permiten rutas alternativas. La guía [demo local](../docs/demo-local.md) contiene preparación y verificación de los seis módulos. Las consultas de grafos admiten `limit` para mantener una muestra consistente.
