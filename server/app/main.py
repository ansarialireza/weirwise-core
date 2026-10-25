import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from server.app.config import get_settings
from server.app.database import get_db, engine, Base
from server.app.api import router as v1_router
from server.app.schemas import HealthResponse

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup tables if needed
    async with engine.begin() as conn:
        # If postgresql, ensure pgvector extension exists
        if conn.dialect.name == "postgresql":
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            except Exception as e:
                logger.warning(f"Could not automatically create extension 'vector': {e}")
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Weirwise Core API",
    description="Open-source lightweight, modular RAG infrastructure for developers.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health/live", tags=["Health"], response_model=HealthResponse)
async def health_live():
    return HealthResponse(status="alive", database="unverified", version="0.1.0")


@app.get("/health/ready", tags=["Health"], response_model=HealthResponse)
async def health_ready(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Readiness check database failure: {e}")
        db_status = f"unhealthy: {str(e)}"
    return HealthResponse(
        status="ready" if db_status == "healthy" else "degraded",
        database=db_status,
        version="0.1.0",
    )


app.include_router(v1_router, prefix="/api")
