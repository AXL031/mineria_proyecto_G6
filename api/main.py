"""Aplicación central FastAPI de BankShield Analytics."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers.graphs import router as graphs_router

app = FastAPI(
    title="BankShield Analytics API",
    description=(
        "API analítica para detección de fraude, riesgo crediticio, "
        "análisis de grafos transaccionales y reclamos financieros."
    ),
    version="0.1.0",
)

# Permitir CORS para integración fluida con Streamlit o frontend externo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers de módulos
app.include_router(graphs_router, prefix="/api")


@app.get("/", tags=["Health"])
def health_check():
    """Endpoint de estado del servicio."""
    return {
        "status": "online",
        "service": "BankShield Analytics API",
        "version": "0.1.0",
        "modules": ["graphs", "fraud (scoring local)", "credit (en progreso)", "complaints (en progreso)"],
    }
