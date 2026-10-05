# Panel Analítico — BankShield Analytics

Aplicación web frontend interactiva construida con **Streamlit** para la exploración visual de modelos, métricas y redes.

## Estructura

- `dashboard/app.py`: Portal de inicio y guía de navegación de la plataforma.
- `dashboard/pages/03_redes.py`: Módulo interactivo de redes y grafos de transacciones (`Rhamses`).

## Capacidades de la Vista de Redes

1. **KPIs Topológicos Globales:** Volumen operado, densidad del grafo, pares con fraude y componentes.
2. **Explorador Interactivo con Pyvis:** Visualización gráfica con física de fuerzas (ForceAtlas2), diferenciando clientes (`C`, azul) y comercios (`M`, verde) del nodo investigado (rojo). Permite zoom, arrastre y hover para inspeccionar montos.
3. **Monitoreo de Anomalías:** Filtros configurables para detección de abanicos de dispersión (*high fan-out*), embudos de captación (*high fan-in*) y circularidad.
4. **Ranking de Centralidad:** Tablas dinámicas según PageRank, transacciones recibidas/enviadas o flujo neto.

## Instrucciones de Ejecución

Desde la raíz del proyecto:

```powershell
python -m pip install -r requirements/dashboard.txt
streamlit run dashboard/app.py
```

La interfaz se abrirá automáticamente en tu navegador en:
`http://localhost:8501`
