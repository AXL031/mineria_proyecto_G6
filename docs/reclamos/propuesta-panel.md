# Propuesta de Navegación del Panel y Página de Reclamos — Angel & Rhamses

Este documento define la arquitectura de navegación del panel analítico (**Streamlit**) y la especificación detallada de la página y endpoints del módulo de **Reclamos y Minería de Texto (CFPB)**, completando la primera entrega del plan de trabajo.

---

## 1. Arquitectura de Navegación del Panel (Rhamses & Angel)

El panel principal (`dashboard/app.py`) actúa como portal institucional. La navegación multifuente se organiza mediante páginas numeradas en `dashboard/pages/` para garantizar un orden canónico:

```text
dashboard/
├── app.py                     # Portal de bienvenida, aviso de compliance y resumen de módulos
└── pages/
    ├── 01_fraude.py           # Detección supervisada y scoring en vivo (Cueva)
    ├── 02_riesgo.py           # Riesgo crediticio y explicabilidad (Sevan)
    ├── 03_redes.py            # Topología de red y subgrafos interactivos (Rhamses) [Implementado]
    ├── 04_reclamos.py         # Análisis de quejas, NLP y tópicos (Angel)
    └── 05_pronosticos.py      # Series de tiempo y monitoreo de deriva (Gerardo)
```

### Principios de Diseño Común:
- **Estilo visual bancario unificado:** Paleta de colores formal (azules pizarra `#1E3A8A`, fondos `#F8FAFC`, bordes sutiles `#E2E8F0`).
- **Aviso de compliance/datos reales:** Identificación clara de la fuente (CFPB en Reclamos, PaySim en Transacciones).
- **Consumo desacoplado:** Cada página del panel puede consultar servicios locales en `src/bankshield/services/` o endpoints de la API (`FastAPI`).

---

## 2. Estructura de la Página de Reclamos (`04_reclamos.py`)

La vista de reclamos se estructurará en 4 pestañas interactivas:

### Pestaña 1: 📊 Panorama Ejecutivo y Tendencias
- **Tarjetas de KPIs:**
  - Total de reclamos registrados (555,957).
  - Reclamos con narrativa de texto (66,806 — 12.02%).
  - Tasa de disputa del consumidor (`consumer_disputed?`).
  - Empresa con mayor volumen de reclamos (Bank of America).
- **Gráficos interactivos:**
  - Serie temporal de reclamos por año y mes (2011–2016).
  - Distribución por Producto Financiero (Hipoteca, Cobranza, Reporte Crediticio, etc.).
  - Top 10 Compañías con mayor concentración de quejas.

### Pestaña 2: 🔍 Explorador y Filtro de Quejas
- **Filtros interactivos:**
  - Selector de producto financiero (`product`).
  - Selector de empresa (`company`).
  - Checkbox para filtrar exclusivamente quejas que contengan narrativa libre.
  - Filtro por disputa del cliente (`consumer_disputed?`).
- **Visor de casos individuales:**
  - Tabla paginada de resultados.
  - Vista expandible del texto completo de la narrativa, con badge indicativo de anonimización (`XXXX`) y fecha de recepción.

### Pestaña 3: 🧠 Minería de Texto y Descubrimiento de Tópicos
- **Análisis léxico:**
  - Palabras y n-gramas más frecuentes por producto financiero (después de remover stopwords y tokens de censura).
  - Comparativa de vocabulario entre quejas disputadas vs no disputadas.
- **Tópicos no supervisados (LDA / NMF):**
  - Identificación de los 5 a 10 tópicos latentes en las narrativas (ej. problemas con cobranzas indebidas, errores de buró de crédito, cobros de comisiones no autorizadas).
  - Distribución de quejas asignadas a cada tópico.

### Pestaña 4: ⚡ Clasificador NLP en Tiempo Real
- **Simulador interactivo:**
  - Campo de texto libre para que el analista redacte o pegue una queja en lenguaje natural.
  - Modelo de clasificación (TF-IDF + clasificador) que predice en milisegundos:
    - Producto financiero más probable.
    - Probabilidad / nivel de confianza del modelo.
    - Términos clave de la queja que más influyeron en la clasificación (explicabilidad de vocabulario).

---

## 3. Contrato de Endpoints API propuesto (`api/routers/complaints.py`)

Para mantener la consistencia con `api/routers/graphs.py`, el router de reclamos expondrá los siguientes endpoints:

### `GET /api/complaints/summary`
Devuelve las métricas consolidadas del dataset (totales, cobertura de texto, rangos de fechas).

### `GET /api/complaints/products`
Devuelve el listado de productos financieros con sus conteos y porcentaje de narrativas.

### `GET /api/complaints/trends`
Devuelve la evolución temporal agregada de reclamos por año/mes.

### `GET /api/complaints/search`
Permite buscar quejas con parámetros de consulta:
- `product`: string opcional
- `company`: string opcional
- `has_narrative`: boolean opcional
- `limit`: int (default: 50)

### `POST /api/complaints/classify`
Endpoint de inferencia en tiempo real:
- **Request:**
  ```json
  {
    "narrative": "I noticed an unknown monthly fee charged to my account without notice."
  }
  ```
- **Response:**
  ```json
  {
    "predicted_product": "Bank account or service",
    "confidence": 0.84,
    "top_keywords": ["fee", "account", "monthly"]
  }
  ```

---

## 4. Próxima Etapa de Ejecución
Con el perfilado completo y la arquitectura definida:
1. Construir el módulo de limpieza de texto en `src/bankshield/features/text_cleaning.py`.
2. Implementar el pipeline de clasificación y tópicos en `src/bankshield/models/complaints.py`.
3. Desarrollar la página `dashboard/pages/04_reclamos.py` y el router `api/routers/complaints.py`.
