# API de Demostración — BankShield Analytics

Servicio web backend construido con **FastAPI** que expone endpoints analíticos para consumo de la plataforma y el dashboard interactivo.

## Estructura del Módulo

- `api/main.py`: Punto de entrada de la aplicación FastAPI, configuración de middleware CORS y registro de routers.
- `api/routers/graphs.py`: Endpoints del módulo de grafos de transacciones (`/api/graphs/*`).

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
