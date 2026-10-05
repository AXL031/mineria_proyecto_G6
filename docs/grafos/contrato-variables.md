# Contrato de variables — Rhamses (grafos de transacciones)

## Fuente de datos

El módulo de grafos utiliza el CSV transaccional con esquema PaySim
almacenado en `data/bronze/transactions/`.  Los datos son de simulación;
todos los resultados deben rotularse como simulados.

## Variables utilizadas

| Campo | Uso en grafos | Motivo |
| --- | --- | --- |
| `nameOrig` | Nodo origen (cuenta que envía) | Identifica la cuenta originadora de la transacción. |
| `nameDest` | Nodo destino (cuenta que recibe) | Identifica la cuenta receptora. |
| `amount` | Peso de la arista | Monto de la transacción; se agrega por par de cuentas. |
| `type` | Atributo de arista | Tipo de operación (PAYMENT, TRANSFER, CASH_OUT, DEBIT, CASH_IN). |
| `step` | Atributo temporal | Paso de simulación; no es fecha calendario.  Útil para analizar evolución. |
| `isFraud` | Atributo de arista | Etiqueta de fraude para evaluar patrones detectados. |

## Variables excluidas

| Campo | Motivo de exclusión |
| --- | --- |
| `oldbalanceOrg` | Saldo previo del origen; no aporta a la estructura de red. |
| `newbalanceOrig` | Saldo posterior; información post-operación. |
| `oldbalanceDest` | Saldo previo del destino; requiere revisión de disponibilidad. |
| `newbalanceDest` | Saldo posterior; información post-operación. |
| `isFlaggedFraud` | Señal de otro detector; no se usa como variable de red. |

## Convención de cuentas en PaySim

- Prefijo `C`: cuenta de cliente.
- Prefijo `M`: cuenta de comercio (merchant).

Los comercios solo aparecen como destino en transacciones de tipo PAYMENT.
Esta convención se usa para clasificar nodos pero no ha sido verificada
en todos los registros.

## Construcción del grafo

### Tipo de grafo

Se construye un **grafo dirigido** (`nx.DiGraph`) donde:

- Cada **nodo** es una cuenta única (`nameOrig` o `nameDest`).
- Cada **arista** representa el flujo agregado entre un par de cuentas.

Las transacciones del mismo par `(origen, destino)` se agregan en una sola
arista con atributos acumulados (conteo, monto total, monto medio, tipos,
conteo de fraude).

### Justificación

Un grafo dirigido (no multigrafo) permite calcular métricas de centralidad
de forma eficiente mientras conserva la dirección del flujo de dinero.
La información temporal se preserva en los atributos de arista (`steps`)
para análisis posteriores.

## Indicadores de red

### Por nodo (cuenta)

| Indicador | Descripción |
| --- | --- |
| `weighted_in_degree` | Grado de entrada ponderado por transacciones. |
| `weighted_out_degree` | Grado de salida ponderado. |
| `in_degree_centrality` | Centralidad de grado de entrada normalizada. |
| `out_degree_centrality` | Centralidad de grado de salida normalizada. |
| `pagerank` | Importancia relativa en la red (PageRank con pesos). |
| `unique_destinations` | Número de destinos distintos. |
| `unique_sources` | Número de orígenes distintos. |
| `total_amount_sent` | Monto total enviado. |
| `total_amount_received` | Monto total recibido. |
| `net_flow` | Flujo neto (recibido − enviado). |

### A nivel de grafo

| Indicador | Descripción |
| --- | --- |
| Densidad | Proporción de aristas existentes sobre el total posible. |
| Componentes débilmente conexos | Grupos de cuentas conectadas sin considerar dirección. |
| Mayor componente | Tamaño y porcentaje del componente más grande. |
| Distribución de grados | Media y máximo de grados de entrada y salida. |

## Patrones sospechosos

Los patrones definidos son **exploratorios**.  No constituyen evidencia
de fraude; requieren calibración con datos reales y revisión de expertos.

| Patrón | Descripción | Umbral inicial |
| --- | --- | --- |
| `high_fanout` | Cuenta que envía a muchos destinos distintos (abanico). | Percentil 95 de grado de salida. |
| `high_fanin` | Cuenta que recibe de muchos orígenes (embudo). | Percentil 95 de grado de entrada. |
| `circular` | Ciclos cortos (≤ 4 nodos) que podrían indicar circularidad. | Longitud máxima configurable. |
| `high_value_edge` | Pares con monto total excepcionalmente alto. | Percentil 99 de monto total. |
| `net_flow_anomaly` | Flujo neto extremo (acumulador o distribuidor). | Percentil 95 en ambos extremos. |

## Esquema de respuesta de consulta de cuenta

```json
{
  "account": "C1231006815",
  "account_type": "cliente",
  "transactions_sent": 3,
  "transactions_received": 1,
  "unique_destinations": 3,
  "unique_sources": 1,
  "total_amount_sent": 8000.0,
  "total_amount_received": 1500.0,
  "net_flow": -6500.0,
  "outgoing_connections": [
    {
      "destination": "C400",
      "transaction_count": 1,
      "total_amount": 5000.0,
      "mean_amount": 5000.0,
      "fraud_count": 1,
      "types": ["TRANSFER"]
    }
  ],
  "incoming_connections": [
    {
      "origin": "C500",
      "transaction_count": 1,
      "total_amount": 1500.0,
      "mean_amount": 1500.0,
      "fraud_count": 0,
      "types": ["TRANSFER"]
    }
  ],
  "simulation_data": true
}
```

## Esquema de respuesta de consulta de subgrafo

```json
{
  "center_account": "C1231006815",
  "depth": 1,
  "node_count": 5,
  "edge_count": 4,
  "nodes": [
    {"id": "C1231006815", "account_type": "cliente", "is_center": true, "transactions_sent": 3, "transactions_received": 1}
  ],
  "edges": [
    {"source": "C1231006815", "target": "C400", "weight": 1, "total_amount": 5000.0, "fraud_count": 1, "types": ["TRANSFER"]}
  ],
  "simulation_data": true
}
```

## Ejecución

Requiere Python 3.11 o posterior y `networkx`, `pandas`, `numpy`.

```powershell
pip install -r requirements/graph.txt
python scripts/profile_graph.py --markdown docs/grafos/perfil-red.md
python scripts/profile_graph.py --limit 100000
python -m unittest discover -s tests/unit -p "test_graph*.py" -v
```

## Limitaciones

- Los datos son de simulación; las métricas de red reflejan la estructura
  del simulador, no de un sistema bancario real.
- `step` no es una fecha calendario; no se puede hacer análisis temporal
  con fechas.
- El grafo agrega transacciones del mismo par en una sola arista; se pierde
  el detalle de transacciones individuales entre el mismo par.
- Los umbrales de detección son percentiles exploratorios y no han sido
  calibrados contra una línea base de patrones conocidos.
- No se mide: evolución temporal de la red, comunidades, ni componentes
  fuertemente conexos de gran escala.
- `nameOrig` y `nameDest` son identificadores sintéticos; no representan
  clientes reales.
