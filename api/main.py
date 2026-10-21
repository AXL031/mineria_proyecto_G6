"""Aplicación central FastAPI de BankShield Analytics."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.routers.graphs import router as graphs_router
from api.routers.fraud import router as fraud_router
from api.routers.credit import router as credit_router
from api.routers.forecast import router as forecast_router
from api.routers.segments import router as segments_router
from api.routers.complaints import router as complaints_router

app = FastAPI(
    title="BankShield Analytics API",
    description=(
        "API analítica para detección de fraude, riesgo crediticio, "
        "análisis de grafos transaccionales, segmentación de cuentas, "
        "pronósticos y reclamos financieros."
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
app.include_router(fraud_router, prefix="/api")
app.include_router(credit_router, prefix="/api")
app.include_router(forecast_router, prefix="/api")
app.include_router(segments_router, prefix="/api")
app.include_router(complaints_router, prefix="/api")


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # No devolver valores de entrada: NaN/Infinity tampoco se serializan en JSON.
    return JSONResponse(status_code=422, content={
        "detail": [{key: error[key] for key in ("type", "loc", "msg")}
                   for error in exc.errors()]
    })


@app.get("/", tags=["Health"])
def health_check():
    """Endpoint de estado del servicio."""
    return {
        "status": "online",
        "service": "BankShield Analytics API",
        "version": "0.1.0",
        "modules": ["graphs", "fraud", "credit", "forecast", "segments", "complaints"],
        "fraud_model_status": "consultar /api/fraud/model",
        "credit_model_status": "consultar /api/credit/model",
        "forecast_status": "consultar /api/forecast/projection",
        "segments_status": "consultar /api/segments/summary",
        "complaints_status": "consultar /api/complaints/model",
    }
