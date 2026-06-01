from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.endpoints import index, users, recommendations
from app.services import embedder
from config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Carga al iniciar la aplicación ---
    # Carga el modelo de embedding en memoria para que esté listo para usarse.
    # Esto evita cargarlo en cada petición, lo cual sería muy lento.
    print("INFO:     Iniciando ciclo de vida de la aplicación...")
    embedder.load_model()
    yield
    # --- Limpieza al apagar la aplicación (si es necesario) ---
    print("INFO:     Finalizando ciclo de vida de la aplicación.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

# --- Inclusión de Routers ---
# Cada router agrupa los endpoints de una sección de la API.
app.include_router(index.router, prefix="/api/v1", tags=["Indexing"])
app.include_router(users.router, prefix="/api/v1", tags=["User Profile"])
app.include_router(recommendations.router, prefix="/api/v1", tags=["Recommendations"])