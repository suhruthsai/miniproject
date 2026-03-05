"""FastAPI entry point for the Research Assistant backend."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from services.ollama_service import ollama_service
from services.neo4j_service import neo4j_service
from services.chroma_service import chroma_service
from services.academic_apis import academic_apis
from api.research import router as research_router
from api.knowledge_graph import router as graph_router
from api.export import router as export_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🚀 Starting Research Assistant Backend...")

    # Check Ollama
    ollama_ok = await ollama_service.check_health()
    if ollama_ok:
        logger.info(f"✅ Ollama connected (model: {settings.OLLAMA_MODEL})")
    else:
        logger.warning("⚠️ Ollama not available — using demo fallback responses")

    # Connect Neo4j
    neo4j_ok = await neo4j_service.connect()
    if neo4j_ok:
        logger.info("✅ Neo4j connected")
    else:
        logger.warning("⚠️ Neo4j not available — using in-memory graph")

    # Initialize ChromaDB
    chroma_ok = await chroma_service.initialize()
    if chroma_ok:
        logger.info("✅ ChromaDB initialized")
    else:
        logger.warning("⚠️ ChromaDB not available")

    logger.info("🟢 Backend ready!")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await ollama_service.close()
    await neo4j_service.close()
    await chroma_service.close()
    await academic_apis.close()


app = FastAPI(
    title="Research Assistant API",
    description="Autonomous Multi-Agent Research & Thesis Assistant",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(research_router)
app.include_router(graph_router)
app.include_router(export_router)


@app.get("/")
async def root():
    """Root endpoint with system info."""
    from agents.coordinator import coordinator

    return {
        "name": "Research Assistant API",
        "version": "1.0.0",
        "agents": coordinator.get_all_status(),
        "status": "ready",
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    ollama_ok = await ollama_service.check_health()
    return {
        "status": "healthy",
        "ollama": ollama_ok,
        "neo4j": neo4j_service.available,
        "chromadb": chroma_service.available,
    }


@app.get("/api/domains")
async def get_domains():
    """Get available research domains."""
    domains = []
    for key, config in settings.DOMAIN_SOURCES.items():
        domains.append({
            "id": key,
            "name": config["name"],
            "icon": config["icon"],
            "apis": config["apis"],
        })
    return {"domains": domains}
