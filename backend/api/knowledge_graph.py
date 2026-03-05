"""Knowledge Graph API routes."""
from fastapi import APIRouter
from services.neo4j_service import neo4j_service

router = APIRouter(prefix="/api", tags=["knowledge_graph"])


@router.get("/graph/{research_id}")
async def get_knowledge_graph(research_id: str):
    """Get knowledge graph data for D3.js visualization."""
    graph_data = await neo4j_service.get_graph_data()
    return {
        "research_id": research_id,
        "nodes": graph_data.get("nodes", []),
        "edges": graph_data.get("edges", []),
        "stats": {
            "total_nodes": len(graph_data.get("nodes", [])),
            "total_edges": len(graph_data.get("edges", [])),
            "paper_count": sum(
                1 for n in graph_data.get("nodes", []) if n.get("type") == "paper"
            ),
            "author_count": sum(
                1 for n in graph_data.get("nodes", []) if n.get("type") == "author"
            ),
            "topic_count": sum(
                1 for n in graph_data.get("nodes", []) if n.get("type") == "topic"
            ),
        },
    }


@router.get("/graph/{research_id}/stats")
async def get_graph_stats(research_id: str):
    """Get knowledge graph statistics."""
    graph_data = await neo4j_service.get_graph_data()
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    return {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "node_types": {
            "papers": sum(1 for n in nodes if n.get("type") == "paper"),
            "authors": sum(1 for n in nodes if n.get("type") == "author"),
            "topics": sum(1 for n in nodes if n.get("type") == "topic"),
        },
        "edge_types": {
            "citations": sum(1 for e in edges if e.get("type") == "CITES"),
            "authored": sum(1 for e in edges if e.get("type") == "AUTHORED"),
            "has_topic": sum(1 for e in edges if e.get("type") == "HAS_TOPIC"),
        },
    }
