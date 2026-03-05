"""ChromaDB vector database service for semantic search."""
import logging
import hashlib
from config import settings

logger = logging.getLogger(__name__)


class ChromaService:
    def __init__(self):
        self.client = None
        self.collection = None
        self.available = False
        self._embedding_fn = None

    async def initialize(self) -> bool:
        """Initialize ChromaDB with sentence-transformers embeddings."""
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self.client = chromadb.Client(
                ChromaSettings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory=settings.CHROMA_PERSIST_DIR,
                    anonymized_telemetry=False,
                )
            )
            self.available = True
            logger.info("ChromaDB initialized successfully")
            return True
        except Exception as e:
            logger.warning(f"ChromaDB init failed, using basic fallback: {e}")
            try:
                import chromadb

                self.client = chromadb.Client()
                self.available = True
                logger.info("ChromaDB initialized with ephemeral client")
                return True
            except Exception as e2:
                logger.error(f"ChromaDB completely unavailable: {e2}")
                self.available = False
                return False

    def get_or_create_collection(self, name: str = "research_papers"):
        """Get or create a ChromaDB collection."""
        if not self.available or not self.client:
            return None
        try:
            self.collection = self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
            return self.collection
        except Exception as e:
            logger.error(f"ChromaDB collection error: {e}")
            return None

    async def add_documents(self, papers: list, collection_name: str = "research_papers"):
        """Add paper abstracts to vector store."""
        collection = self.get_or_create_collection(collection_name)
        if not collection:
            return False

        try:
            documents = []
            ids = []
            metadatas = []

            for paper in papers:
                text = paper.get("abstract", "") or paper.get("title", "")
                if not text:
                    continue

                doc_id = hashlib.md5(text.encode()).hexdigest()
                documents.append(text)
                ids.append(doc_id)
                metadatas.append(
                    {
                        "title": paper.get("title", "")[:500],
                        "year": str(paper.get("year", "")),
                        "authors": ", ".join(paper.get("authors", [])[:5]),
                        "paper_id": paper.get("paper_id", ""),
                        "citation_count": str(paper.get("citation_count", 0)),
                    }
                )

            if documents:
                # Add in batches of 50
                batch_size = 50
                for i in range(0, len(documents), batch_size):
                    batch_end = min(i + batch_size, len(documents))
                    collection.add(
                        documents=documents[i:batch_end],
                        ids=ids[i:batch_end],
                        metadatas=metadatas[i:batch_end],
                    )
                logger.info(f"Added {len(documents)} documents to ChromaDB")
            return True
        except Exception as e:
            logger.error(f"ChromaDB add_documents error: {e}")
            return False

    async def semantic_search(
        self, query: str, n_results: int = 10, collection_name: str = "research_papers"
    ) -> list:
        """Search for semantically similar papers."""
        collection = self.get_or_create_collection(collection_name)
        if not collection:
            return []

        try:
            results = collection.query(
                query_texts=[query],
                n_results=min(n_results, collection.count() or 1),
            )
            papers = []
            if results and results.get("documents"):
                for i, doc in enumerate(results["documents"][0]):
                    meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                    distance = (
                        results["distances"][0][i] if results.get("distances") else 1.0
                    )
                    papers.append(
                        {
                            "text": doc,
                            "title": meta.get("title", ""),
                            "year": meta.get("year", ""),
                            "authors": meta.get("authors", ""),
                            "similarity": round(1 - distance, 3),
                        }
                    )
            return papers
        except Exception as e:
            logger.error(f"ChromaDB search error: {e}")
            return []

    async def close(self):
        """Cleanup ChromaDB resources."""
        pass


chroma_service = ChromaService()
