"""Agent 2: Synthesis Agent - Reads papers and extracts insights."""
from agents.base_agent import BaseAgent
from services.ollama_service import ollama_service
from services.chroma_service import chroma_service
from services.neo4j_service import neo4j_service


class SynthesisAgent(BaseAgent):
    """
    Synthesis Agent - Deep analysis specialist.
    
    Features:
    - Reads and understands paper abstracts via LLM
    - Concept extraction and relationship mapping
    - Contradiction detection across papers
    - Trend analysis (publication volume over years)
    - Research gap identification
    - Stores embeddings in ChromaDB, relationships in Neo4j
    """

    def __init__(self):
        super().__init__(
            name="Synthesis Agent",
            description="Analyzes papers and extracts key insights, trends, and gaps",
            icon="🧠",
        )

    async def execute(self, context: dict) -> dict:
        papers = context.get("papers", [])
        topic = context.get("topic", "")

        if not papers:
            return {"error": "No papers to analyze", "themes": [], "gaps": []}

        # Step 1: Store papers in vector database
        self.update_progress(5, "Indexing papers in vector database...")
        await chroma_service.add_documents(papers)

        # Step 2: Store papers in knowledge graph
        self.update_progress(15, "Building knowledge graph...")
        for paper in papers[:50]:  # Limit for performance
            await neo4j_service.add_paper(paper)

        # Step 3: Analyze trends
        self.update_progress(25, "Analyzing publication trends...")
        trends = self._analyze_trends(papers)

        # Step 4: Extract key themes and concepts
        self.update_progress(35, "Extracting key themes from papers...")
        themes = await self._extract_themes(papers, topic)

        # Step 5: Detect contradictions
        self.update_progress(55, "Detecting contradictions across papers...")
        contradictions = await self._detect_contradictions(papers, topic)

        # Step 6: Identify research gaps
        self.update_progress(75, "Identifying research gaps...")
        gaps = await self._identify_gaps(papers, topic, themes)

        # Step 7: Generate topic clusters for knowledge graph
        self.update_progress(85, "Creating topic clusters...")
        if themes:
            for theme in themes[:10]:
                theme_name = theme.get("name", "")
                related_paper_ids = [
                    p.get("paper_id", "") for p in papers
                    if theme_name.lower() in (p.get("title", "") + " " + p.get("abstract", "")).lower()
                ][:10]
                await neo4j_service.add_topic(theme_name, related_paper_ids)

        # Step 8: Create paper summaries
        self.update_progress(90, "Summarizing key papers...")
        summaries = await self._summarize_top_papers(papers[:10], topic)

        self.update_progress(100, f"✅ Analyzed {len(papers)} papers, found {len(themes)} themes")

        return {
            "total_analyzed": len(papers),
            "themes": themes,
            "contradictions": contradictions,
            "trends": trends,
            "gaps": gaps,
            "summaries": summaries,
            "top_authors": self._get_top_authors(papers),
        }

    def _analyze_trends(self, papers: list) -> dict:
        """Analyze publication trends by year."""
        year_counts = {}
        for paper in papers:
            year = paper.get("year", 0)
            if year > 0:
                year_counts[year] = year_counts.get(year, 0) + 1

        sorted_years = sorted(year_counts.items())
        
        # Determine trend direction
        trend = "stable"
        if len(sorted_years) >= 2:
            recent_avg = sum(c for _, c in sorted_years[-2:]) / 2
            older_avg = sum(c for _, c in sorted_years[:2]) / max(1, min(2, len(sorted_years)))
            if recent_avg > older_avg * 1.5:
                trend = "rapidly_growing"
            elif recent_avg > older_avg:
                trend = "growing"
            elif recent_avg < older_avg * 0.5:
                trend = "declining"

        return {
            "yearly_counts": dict(sorted_years),
            "trend": trend,
            "total_papers": len(papers),
            "avg_citations": round(
                sum(p.get("citation_count", 0) for p in papers) / max(1, len(papers)), 1
            ),
        }

    async def _extract_themes(self, papers: list, topic: str) -> list:
        """Extract key research themes using LLM."""
        # Build a condensed view of papers for LLM
        paper_text = "\n".join(
            f"- {p.get('title', '')} ({p.get('year', '')}): {(p.get('abstract', '') or '')[:200]}"
            for p in papers[:30]
        )

        prompt = f"""Analyze these research papers on "{topic}" and identify 5-7 key themes or research directions.

Papers:
{paper_text}

For each theme, provide:
1. Theme name (short, 3-5 words)
2. Description (1-2 sentences)
3. Number of papers that likely relate to this theme

Format your response as a numbered list:
1. THEME NAME: description (approximately N papers)"""

        response = await ollama_service.generate(prompt)
        
        themes = []
        for line in response.strip().split("\n"):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                # Parse the theme
                parts = line.lstrip("0123456789.-) ").split(":", 1)
                name = parts[0].strip()
                desc = parts[1].strip() if len(parts) > 1 else ""
                if name:
                    themes.append({
                        "name": name,
                        "description": desc,
                        "paper_count": sum(
                            1 for p in papers
                            if name.lower().split()[0] in (p.get("title", "") + " " + p.get("abstract", "")).lower()
                        ),
                    })

        if not themes:
            # Fallback themes
            themes = [
                {"name": "Current Methods", "description": f"Existing approaches in {topic}", "paper_count": len(papers) // 3},
                {"name": "Performance Analysis", "description": "Evaluation and comparison of methods", "paper_count": len(papers) // 4},
                {"name": "Novel Approaches", "description": "Emerging techniques and innovations", "paper_count": len(papers) // 5},
                {"name": "Applications", "description": "Real-world implementations and use cases", "paper_count": len(papers) // 4},
            ]

        return themes

    async def _detect_contradictions(self, papers: list, topic: str) -> list:
        """Detect contradicting findings across papers."""
        paper_text = "\n".join(
            f"Paper: \"{p.get('title', '')}\" by {', '.join(p.get('authors', [])[:2])} ({p.get('year', '')})\n"
            f"Abstract: {(p.get('abstract', '') or '')[:300]}\n"
            for p in papers[:20]
        )

        prompt = f"""Analyze these papers on "{topic}" and identify any contradictions or conflicting findings.

{paper_text}

List 2-3 contradictions found. For each:
1. What claim/finding is contradicted
2. Which papers disagree
3. Possible reason for the contradiction

If no clear contradictions exist, describe areas where studies show varying results."""

        response = await ollama_service.generate(prompt)
        
        contradictions = []
        current = ""
        for line in response.strip().split("\n"):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                if current:
                    contradictions.append({"description": current})
                current = line.lstrip("0123456789.-) ")
            elif line:
                current += " " + line

        if current:
            contradictions.append({"description": current})

        return contradictions[:5]

    async def _identify_gaps(self, papers: list, topic: str, themes: list) -> list:
        """Identify research gaps based on analyzed literature."""
        theme_text = "\n".join(
            f"- {t.get('name', '')}: {t.get('description', '')}" for t in themes
        )

        prompt = f"""Based on the analysis of {len(papers)} papers on "{topic}", these themes emerged:

{theme_text}

Identify 3-5 specific RESEARCH GAPS - areas that have NOT been adequately studied.
For each gap:
1. Describe what's missing
2. Why it matters
3. Suggest a potential research direction

Format as numbered list."""

        response = await ollama_service.generate(prompt)
        
        gaps = []
        current = ""
        for line in response.strip().split("\n"):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                if current:
                    gaps.append({"description": current})
                current = line.lstrip("0123456789.-) ")
            elif line:
                current += " " + line

        if current:
            gaps.append({"description": current})

        return gaps[:5]

    async def _summarize_top_papers(self, papers: list, topic: str) -> list:
        """Generate concise summaries of the most important papers."""
        summaries = []
        for paper in papers[:5]:
            abstract = paper.get("abstract", "")
            if not abstract:
                summaries.append({
                    "paper_id": paper.get("paper_id", ""),
                    "title": paper.get("title", ""),
                    "summary": "Abstract not available for summarization.",
                })
                continue

            prompt = f"""Summarize this research paper in 2-3 sentences, focusing on key findings and contributions.

Title: {paper.get('title', '')}
Abstract: {abstract}

Provide a concise, academic summary."""

            summary = await ollama_service.generate(prompt)
            summaries.append({
                "paper_id": paper.get("paper_id", ""),
                "title": paper.get("title", ""),
                "summary": summary.strip(),
            })

        return summaries

    def _get_top_authors(self, papers: list) -> list:
        """Get most prolific authors from the paper set."""
        author_counts = {}
        for paper in papers:
            for author in paper.get("authors", []):
                if author:
                    author_counts[author] = author_counts.get(author, 0) + 1

        sorted_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)
        return [
            {"name": name, "paper_count": count}
            for name, count in sorted_authors[:10]
        ]
