# Perfil de red de transacciones — módulo de grafos

Informe generado por `scripts/profile_graph.py`.  Los datos provienen
de una simulación (PaySim); los resultados son simulados.

- Alcance: `muestra`.
- Aristas leídas: 50,000.
- Cuentas origen únicas: 50,000.
- Cuentas destino únicas: 28,499.
- Cuentas totales únicas: 78,499.
- Monto total: 7,813,225,537.54.
- Aristas fraudulentas: 100 (0.2000%).

## Transacciones por tipo

| Tipo | Transacciones | Monto total | Monto medio | Fraudes |
| --- | ---: | ---: | ---: | ---: |
| CASH_IN | 8,992 | 1,512,628,147.00 | 168,219.32 | 0 |
| CASH_OUT | 13,756 | 2,521,983,704.00 | 183,337.00 | 51 |
| DEBIT | 640 | 2,388,349.00 | 3,731.80 | 0 |
| PAYMENT | 21,912 | 213,150,878.00 | 9,727.59 | 0 |
| TRANSFER | 4,700 | 3,563,074,458.00 | 758,100.95 | 49 |

## Resumen del grafo

- Nodos: 78,499.
- Aristas únicas (pares): 50,000.
- Densidad: 0.000008.
- Componentes débilmente conexos: 28,499.
- Mayor componente: 75 nodos (0.10%).
- Grado de salida medio: 0.64; máximo: 1.
- Grado de entrada medio: 0.64; máximo: 74.
- Pares con al menos una transacción fraudulenta: 100.

### Nodos por tipo de cuenta

- cliente: 56,587.
- comercio: 21,912.

## Cuentas con mayor PageRank

| Cuenta | Tipo | PageRank | Tx enviadas | Tx recibidas |
| --- | --- | ---: | ---: | ---: |
| `C985934102` | cliente | 0.000528 | 0 | 74 |
| `C1286084959` | cliente | 0.000479 | 0 | 67 |
| `C1590550415` | cliente | 0.000458 | 0 | 64 |
| `C2083562754` | cliente | 0.000444 | 0 | 62 |
| `C977993101` | cliente | 0.000437 | 0 | 61 |
| `C248609774` | cliente | 0.000437 | 0 | 61 |
| `C1360767589` | cliente | 0.000430 | 0 | 60 |
| `C665576141` | cliente | 0.000409 | 0 | 57 |
| `C451111351` | cliente | 0.000381 | 0 | 53 |
| `C1782113663` | cliente | 0.000381 | 0 | 53 |

## Cuentas con múltiples indicadores de sospecha

| Cuenta | Tipo | Patrones | Nº patrones | Fraudes | PageRank |
| --- | --- | --- | ---: | ---: | ---: |
| `C1223591088` | cliente | high_fanin, net_flow_anomaly | 2 | 0 | 0.000029 |
| `C755355682` | cliente | high_fanin, net_flow_anomaly | 2 | 0 | 0.000029 |
| `C1916720513` | cliente | high_fanin, net_flow_anomaly | 2 | 0 | 0.000289 |
| `C803116137` | cliente | high_fanin, net_flow_anomaly | 2 | 1 | 0.000289 |
| `C1721246982` | cliente | high_fanin, net_flow_anomaly | 2 | 0 | 0.000289 |
| `C1674899618` | cliente | high_fanin, net_flow_anomaly | 2 | 0 | 0.000296 |
| `C909295153` | cliente | high_fanin, net_flow_anomaly | 2 | 0 | 0.000303 |
| `C1504109395` | cliente | high_fanin, net_flow_anomaly | 2 | 0 | 0.000303 |
| `C33524623` | cliente | high_fanin, net_flow_anomaly | 2 | 0 | 0.000310 |
| `C564160838` | cliente | high_fanin, net_flow_anomaly | 2 | 0 | 0.000310 |

## Limitaciones

- Los datos provienen de PaySim, una simulación.  Los patrones detectados reflejan la estructura del simulador, no operaciones bancarias reales.
- `step` no corresponde a fechas calendario; no se puede hacer análisis temporal con fechas.
- Los umbrales de detección son percentiles exploratorios; requieren calibración con datos reales.
- La búsqueda de ciclos está limitada en longitud y cantidad por razones de cómputo.
- El grafo agrega todas las transacciones del mismo par en una sola arista; se pierde el detalle temporal.
- Este perfil no mide: comunidades, componentes fuertemente conexos de gran escala, ni evolución temporal de la red.
