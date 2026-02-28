from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.endpoints import chat
from app.models.database import init_db
from app.utils.logger import setup_logging
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa la DB y logging al arrancar."""
    setup_logging()
    init_db()
    print("✅ Base de datos inicializada.")
    yield
    print("🛑 Servidor apagándose.")

app = FastAPI(
    title="Asistente de Gestión de Incidentes TI",
    description="Backend para clasificar y crear tickets en Jira usando OpenAI",
    version="1.0.0",
    lifespan=lifespan
)

# Configuración básica de CORS para permitir que el frontend web (popup) consuma la API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En producción se debe restringir al dominio del frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "message": "Backend Asistente TI Activo"}
