"""Agent 1: Paper Hunter - Finds 100+ research papers on any topic."""
import asyncio
from agents.base_agent import BaseAgent
from services.academic_apis import academic_apis
from services.ollama_service import ollama_service
from config import settings


class PaperHunterAgent(BaseAgent):
    """
    Paper Hunter Agent - Retrieval specialist.
    
    Features:
    - Multi-source search (Semantic Scholar, ArXiv, CrossRef)
    - Smart query expansion (adds related terms)
    - Diversity sampling (seminal + recent papers)
    - Year/citation filtering
    - Domain-aware source routing
    """

    def __init__(self):
        super().__init__(
            name="Paper Hunter",
            description="Finds relevant research papers from multiple academic databases",
            icon="📚",
        )

    async def execute(self, context: dict) -> dict:
        topic = context.get("topic", "")
        domain = context.get("domain", "custom")
        year_start = context.get("year_start", settings.DEFAULT_YEAR_START)
        year_end = context.get("year_end", settings.DEFAULT_YEAR_END)
        min_citations = context.get("min_citations", 0)
        max_papers = context.get("max_papers", settings.MAX_PAPERS)

        # Step 1: Expand the query with related terms
        self.update_progress(5, "Expanding search query with related terms...")
        expanded_queries = await self._expand_query(topic, domain)

        # Step 2: Determine API sources based on domain
        domain_config = settings.DOMAIN_SOURCES.get(domain, settings.DOMAIN_SOURCES["custom"])
        sources = domain_config.get("apis", ["semantic_scholar", "arxiv", "crossref"])
        arxiv_categories = domain_config.get("arxiv_categories", [])

        # Step 3: Search all sources with expanded queries
        self.update_progress(15, f"Searching {len(sources)} academic databases...")
        all_papers = []

        for i, query in enumerate(expanded_queries):
            self.update_progress(
                15 + int((i / len(expanded_queries)) * 50),
                f"Searching: '{query}' ({i+1}/{len(expanded_queries)})",
            )
            papers = await academic_apis.search_all(
                query=query,
                sources=sources,
                limit_per_source=max(20, max_papers // (len(expanded_queries) * len(sources))),
                year_start=year_start,
                year_end=year_end,
                min_citations=min_citations,
                arxiv_categories=arxiv_categories,
            )
            all_papers.extend(papers)
            # Small delay to respect rate limits
            await asyncio.sleep(0.5)

        # Step 4: Deduplicate
        self.update_progress(70, "Deduplicating results...")
        unique_papers = self._deduplicate(all_papers)

        # Step 5: Apply diversity sampling (40% seminal + 60% recent)
        self.update_progress(80, "Applying diversity sampling...")
        diverse_papers = self._diversity_sample(unique_papers, max_papers)

        # Step 6: Rank and finalize
        self.update_progress(90, f"Found {len(diverse_papers)} unique papers, ranking...")
        diverse_papers.sort(key=lambda p: p.get("citation_count", 0), reverse=True)

        self.update_progress(100, f"✅ Found {len(diverse_papers)} papers from {len(sources)} sources")

        return {
            "papers": diverse_papers[:max_papers],
            "total_found": len(all_papers),
            "unique_count": len(unique_papers),
            "final_count": len(diverse_papers[:max_papers]),
            "queries_used": expanded_queries,
            "sources_searched": sources,
        }

    async def _expand_query(self, topic: str, domain: str) -> list:
        """Expand the search query with related terms using LLM."""
        queries = [topic]

        prompt = f"""You are a research query expansion expert. 
Given this research topic: "{topic}" (domain: {domain})

Generate 3 alternative search queries that would find related papers.
Include synonyms, related technical terms, and broader/narrower terms.

Return ONLY the queries, one per line, no numbering or explanation.
Example output:
photovoltaic efficiency optimization
perovskite solar cell performance
bifacial solar module energy yield"""

        response = await ollama_service.generate(prompt)
        
        # Parse expanded queries
        for line in response.strip().split("\n"):
            line = line.strip().strip("-").strip("•").strip()
            if line and len(line) > 5 and len(line) < 200:
                queries.append(line)

        return queries[:4]  # Original + up to 3 expansions

    def _deduplicate(self, papers: list) -> list:
        """Remove duplicate papers based on title similarity."""
        seen = set()
        unique = []
        for paper in papers:
            key = paper.get("title", "").lower().strip()[:100]
            if key and key not in seen:
                seen.add(key)
                unique.append(paper)
        return unique

    def _diversity_sample(self, papers: list, max_count: int) -> list:
        """Apply diversity sampling: 40% seminal (high citations) + 60% recent."""
        if len(papers) <= max_count:
            return papers

        # Sort by citations for seminal papers
        by_citations = sorted(papers, key=lambda p: p.get("citation_count", 0), reverse=True)
        seminal_count = int(max_count * 0.4)
        seminal = by_citations[:seminal_count]
        seminal_ids = {p.get("paper_id") for p in seminal}

        # Sort by year for recent papers
        remaining = [p for p in papers if p.get("paper_id") not in seminal_ids]
        by_year = sorted(remaining, key=lambda p: p.get("year", 0), reverse=True)
        recent_count = max_count - seminal_count
        recent = by_year[:recent_count]

        return seminal + recent
