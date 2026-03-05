"""Neo4j knowledge graph service with in-memory fallback."""
import logging
from config import settings

logger = logging.getLogger(__name__)


class Neo4jService:
    def __init__(self):
        self.driver = None
        self.available = False
        # In-memory fallback graph
        self._memory_nodes = []
        self._memory_edges = []

    async def connect(self) -> bool:
        """Connect to Neo4j. Falls back to in-memory graph."""
        try:
            from neo4j import GraphDatabase

            self.driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            )
            self.driver.verify_connectivity()
            self.available = True
            logger.info("Neo4j connected successfully")
            return True
        except Exception as e:
            logger.warning(f"Neo4j not available, using in-memory fallback: {e}")
            self.available = False
            return False

    async def add_paper(self, paper: dict):
        """Add a paper node to the knowledge graph."""
        node = {
            "id": paper.get("paper_id", paper.get("title", "")),
            "type": "paper",
            "label": paper.get("title", "Unknown"),
            "year": paper.get("year", 0),
            "citations": paper.get("citation_count", 0),
            "authors": paper.get("authors", []),
            "abstract": paper.get("abstract", ""),
        }

        if self.available and self.driver:
            try:
                with self.driver.session() as session:
                    session.run(
                        """
                        MERGE (p:Paper {id: $id})
                        SET p.title = $label,
                            p.year = $year,
                            p.citations = $citations,
                            p.abstract = $abstract
                        """,
                        id=node["id"],
                        label=node["label"],
                        year=node["year"],
                        citations=node["citations"],
                        abstract=node["abstract"],
                    )
                    # Add author nodes and relationships
                    for author in node["authors"]:
                        session.run(
                            """
                            MERGE (a:Author {name: $name})
                            WITH a
                            MATCH (p:Paper {id: $paper_id})
                            MERGE (a)-[:AUTHORED]->(p)
                            """,
                            name=author,
                            paper_id=node["id"],
                        )
            except Exception as e:
                logger.error(f"Neo4j add_paper error: {e}")
                self._add_to_memory(node)
        else:
            self._add_to_memory(node)

    async def add_citation(self, from_paper_id: str, to_paper_id: str):
        """Add a citation relationship."""
        edge = {
            "source": from_paper_id,
            "target": to_paper_id,
            "type": "CITES",
        }

        if self.available and self.driver:
            try:
                with self.driver.session() as session:
                    session.run(
                        """
                        MATCH (a:Paper {id: $from_id})
                        MATCH (b:Paper {id: $to_id})
                        MERGE (a)-[:CITES]->(b)
                        """,
                        from_id=from_paper_id,
                        to_id=to_paper_id,
                    )
            except Exception as e:
                logger.error(f"Neo4j add_citation error: {e}")
                self._memory_edges.append(edge)
        else:
            self._memory_edges.append(edge)

    async def add_topic(self, topic: str, paper_ids: list):
        """Add a topic node linked to papers."""
        node = {"id": f"topic_{topic}", "type": "topic", "label": topic}
        self._add_to_memory(node)

        for pid in paper_ids:
            edge = {"source": pid, "target": node["id"], "type": "HAS_TOPIC"}
            self._memory_edges.append(edge)

    async def get_graph_data(self) -> dict:
        """Get graph data for D3.js visualization."""
        if self.available and self.driver:
            try:
                with self.driver.session() as session:
                    # Get papers
                    papers = session.run(
                        "MATCH (p:Paper) RETURN p LIMIT 200"
                    ).data()
                    # Get authors
                    authors = session.run(
                        "MATCH (a:Author) RETURN a LIMIT 100"
                    ).data()
                    # Get relationships
                    rels = session.run(
                        """
                        MATCH (a)-[r]->(b)
                        RETURN a.id as source, b.id as target, type(r) as type
                        LIMIT 500
                        """
                    ).data()

                    nodes = []
                    for p in papers:
                        props = dict(p["p"])
                        nodes.append(
                            {
                                "id": props.get("id", ""),
                                "label": props.get("title", ""),
                                "type": "paper",
                                "year": props.get("year", 0),
                                "citations": props.get("citations", 0),
                            }
                        )
                    for a in authors:
                        props = dict(a["a"])
                        nodes.append(
                            {
                                "id": props.get("name", ""),
                                "label": props.get("name", ""),
                                "type": "author",
                            }
                        )

                    return {"nodes": nodes, "edges": rels}
            except Exception as e:
                logger.error(f"Neo4j get_graph error: {e}")

        # Fallback: return in-memory graph
        return {"nodes": self._memory_nodes, "edges": self._memory_edges}

    def _add_to_memory(self, node: dict):
        """Add node to in-memory graph, avoiding duplicates."""
        if not any(n["id"] == node["id"] for n in self._memory_nodes):
            self._memory_nodes.append(node)

    async def clear(self):
        """Clear the graph data."""
        self._memory_nodes = []
        self._memory_edges = []
        if self.available and self.driver:
            try:
                with self.driver.session() as session:
                    session.run("MATCH (n) DETACH DELETE n")
            except Exception:
                pass

    async def close(self):
        if self.driver:
            self.driver.close()


neo4j_service = Neo4jService()
