"""Configuration for the Research Assistant backend."""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Ollama
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")

    # Neo4j
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "password")

    # ChromaDB
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")

    # API Settings
    CORS_ORIGINS: list = ["http://localhost:3000", "http://127.0.0.1:3000"]
    MAX_PAPERS: int = int(os.getenv("MAX_PAPERS", "100"))
    DEFAULT_YEAR_START: int = 2020
    DEFAULT_YEAR_END: int = 2026

    # Domains and their API sources
    DOMAIN_SOURCES: dict = {
        "computer_science": {
            "name": "Computer Science",
            "icon": "💻",
            "apis": ["semantic_scholar", "arxiv", "crossref"],
            "arxiv_categories": ["cs.AI", "cs.LG", "cs.CL", "cs.CV", "cs.SE"],
        },
        "electrical_engineering": {
            "name": "Electrical Engineering",
            "icon": "⚡",
            "apis": ["semantic_scholar", "arxiv", "crossref"],
            "arxiv_categories": ["eess.SP", "eess.SY", "cs.NI"],
        },
        "biotechnology": {
            "name": "Biotechnology",
            "icon": "🧬",
            "apis": ["semantic_scholar", "crossref"],
            "arxiv_categories": ["q-bio"],
        },
        "mechanical_engineering": {
            "name": "Mechanical Engineering",
            "icon": "⚙️",
            "apis": ["semantic_scholar", "crossref"],
            "arxiv_categories": [],
        },
        "physics": {
            "name": "Physics",
            "icon": "⚛️",
            "apis": ["semantic_scholar", "arxiv", "crossref"],
            "arxiv_categories": ["physics", "cond-mat"],
        },
        "custom": {
            "name": "Custom",
            "icon": "🔬",
            "apis": ["semantic_scholar", "arxiv", "crossref"],
            "arxiv_categories": [],
        },
    }


settings = Settings()
