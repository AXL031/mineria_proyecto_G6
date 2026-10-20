# Panel Analítico — BankShield Analytics

## Estilo de iconos

Los emojis usan [Google Noto Emoji](https://github.com/google/fonts/tree/main/ofl/notoemoji) en su variante monocromática. Cada pantalla debe llamar a `bankshield.ui.configure_page`, que aplica la fuente local y un favicon del mismo diseño. Los assets y su licencia OFL están en `dashboard/assets/noto-emoji/`; no hay descargas de fuentes durante la demo. Evitar selectores de presentación en color (`U+FE0F`) en las etiquetas para conservar los contornos minimalistas.

Los colores se asignan por significado: amarillo/ámbar para advertencias, rojo para errores o alto riesgo, verde para resultados bajo el umbral y azul para información y acciones principales. `bankshield.ui.status_notice` combina icono, título y detalle, con variantes de contraste para tema claro/oscuro; el color no es la única señal. La pestaña de patrones utiliza un icono amarillo y los filtros explican su efecto. Una clasificación de producto es informativa, no un estado de éxito o resolución.

Aplicación web frontend interactiva construida con **Streamlit** para la exploración visual de modelos, métricas y redes.

## Estructura

- `dashboard/app.py`: Portal de inicio y guía de navegación de la plataforma.
- `dashboard/pages/01_fraude.py`: Evaluación de transacciones y métricas del modelo de fraude (`Cueva`).
- `dashboard/pages/02_credito.py`: Solicitud de crédito, probabilidad calibrada, factores y métricas del modelo; consume solo la API (`Sevan`).
- `dashboard/pages/03_redes.py`: Módulo interactivo de redes y grafos de transacciones (`Rhamses`).
- `dashboard/pages/04_pronosticos.py`: Historia, proyección Naive, incertidumbre descriptiva y monitoreo histórico; consume solo la API (`Gerardo`).

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
