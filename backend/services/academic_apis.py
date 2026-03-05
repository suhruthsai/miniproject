"""Academic API clients for Semantic Scholar, ArXiv, and CrossRef."""
import httpx
import logging
import xml.etree.ElementTree as ET
from typing import Optional
import asyncio
import re

logger = logging.getLogger(__name__)


class AcademicAPIs:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.semantic_scholar_base = "https://api.semanticscholar.org/graph/v1"
        self.arxiv_base = "http://export.arxiv.org/api/query"
        self.crossref_base = "https://api.crossref.org/works"

    # ── Semantic Scholar ──────────────────────────────────────────────

    async def search_semantic_scholar(
        self,
        query: str,
        limit: int = 50,
        year_start: int = None,
        year_end: int = None,
        min_citations: int = 0,
    ) -> list:
        """Search Semantic Scholar for papers."""
        try:
            params = {
                "query": query,
                "limit": min(limit, 100),
                "fields": "title,abstract,year,citationCount,authors,externalIds,url,venue,publicationDate",
            }
            if year_start and year_end:
                params["year"] = f"{year_start}-{year_end}"

            resp = await self.client.get(
                f"{self.semantic_scholar_base}/paper/search", params=params
            )
            if resp.status_code == 200:
                data = resp.json()
                papers = []
                for item in data.get("data", []):
                    if item.get("citationCount", 0) >= min_citations:
                        authors = [
                            a.get("name", "") for a in item.get("authors", [])
                        ]
                        papers.append(
                            {
                                "paper_id": item.get("paperId", ""),
                                "title": item.get("title", ""),
                                "abstract": item.get("abstract", ""),
                                "year": item.get("year", 0),
                                "citation_count": item.get("citationCount", 0),
                                "authors": authors,
                                "doi": (item.get("externalIds") or {}).get("DOI", ""),
                                "url": item.get("url", ""),
                                "venue": item.get("venue", ""),
                                "source": "semantic_scholar",
                                "publication_date": item.get("publicationDate", ""),
                            }
                        )
                return papers
            else:
                logger.warning(f"Semantic Scholar returned {resp.status_code}")
        except Exception as e:
            logger.error(f"Semantic Scholar search error: {e}")
        return []

    async def get_paper_details(self, paper_id: str) -> Optional[dict]:
        """Get detailed info about a specific paper from Semantic Scholar."""
        try:
            fields = "title,abstract,year,citationCount,authors,references,citations,externalIds,venue,publicationDate"
            resp = await self.client.get(
                f"{self.semantic_scholar_base}/paper/{paper_id}",
                params={"fields": fields},
            )
            if resp.status_code == 200:
                item = resp.json()
                return {
                    "paper_id": item.get("paperId", ""),
                    "title": item.get("title", ""),
                    "abstract": item.get("abstract", ""),
                    "year": item.get("year", 0),
                    "citation_count": item.get("citationCount", 0),
                    "authors": [
                        a.get("name", "") for a in item.get("authors", [])
                    ],
                    "references": [
                        {
                            "paper_id": r.get("paperId", ""),
                            "title": r.get("title", ""),
                        }
                        for r in item.get("references", [])[:50]
                        if r.get("paperId")
                    ],
                    "citations": [
                        {
                            "paper_id": c.get("paperId", ""),
                            "title": c.get("title", ""),
                        }
                        for c in item.get("citations", [])[:50]
                        if c.get("paperId")
                    ],
                    "doi": (item.get("externalIds") or {}).get("DOI", ""),
                    "venue": item.get("venue", ""),
                    "source": "semantic_scholar",
                }
        except Exception as e:
            logger.error(f"Semantic Scholar detail error: {e}")
        return None

    async def verify_paper(self, paper_id: str) -> dict:
        """Verify a paper exists and get its metadata for fact-checking."""
        details = await self.get_paper_details(paper_id)
        if details:
            return {
                "verified": True,
                "title": details["title"],
                "authors": details["authors"],
                "year": details["year"],
                "citation_count": details["citation_count"],
                "doi": details["doi"],
            }
        return {"verified": False}

    # ── ArXiv ─────────────────────────────────────────────────────────

    async def search_arxiv(
        self,
        query: str,
        limit: int = 50,
        categories: list = None,
    ) -> list:
        """Search ArXiv for papers."""
        try:
            search_query = f"all:{query}"
            if categories:
                cat_query = " OR ".join(f"cat:{c}" for c in categories)
                search_query = f"({search_query}) AND ({cat_query})"

            params = {
                "search_query": search_query,
                "start": 0,
                "max_results": min(limit, 100),
                "sortBy": "relevance",
                "sortOrder": "descending",
            }

            resp = await self.client.get(self.arxiv_base, params=params)
            if resp.status_code == 200:
                return self._parse_arxiv_xml(resp.text)
        except Exception as e:
            logger.error(f"ArXiv search error: {e}")
        return []

    def _parse_arxiv_xml(self, xml_text: str) -> list:
        """Parse ArXiv API XML response."""
        papers = []
        try:
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            root = ET.fromstring(xml_text)

            for entry in root.findall("atom:entry", ns):
                title = entry.find("atom:title", ns)
                summary = entry.find("atom:summary", ns)
                published = entry.find("atom:published", ns)
                link = entry.find("atom:id", ns)

                authors = []
                for author in entry.findall("atom:author", ns):
                    name = author.find("atom:name", ns)
                    if name is not None:
                        authors.append(name.text.strip())

                year = 0
                if published is not None and published.text:
                    year = int(published.text[:4])

                arxiv_id = ""
                if link is not None and link.text:
                    arxiv_id = link.text.split("/abs/")[-1]

                papers.append(
                    {
                        "paper_id": f"arxiv_{arxiv_id}",
                        "title": title.text.strip().replace("\n", " ") if title is not None else "",
                        "abstract": summary.text.strip().replace("\n", " ") if summary is not None else "",
                        "year": year,
                        "authors": authors,
                        "citation_count": 0,
                        "doi": "",
                        "url": link.text if link is not None else "",
                        "venue": "ArXiv",
                        "source": "arxiv",
                    }
                )
        except Exception as e:
            logger.error(f"ArXiv XML parse error: {e}")
        return papers

    # ── CrossRef ──────────────────────────────────────────────────────

    async def search_crossref(
        self,
        query: str,
        limit: int = 30,
        year_start: int = None,
        year_end: int = None,
    ) -> list:
        """Search CrossRef for papers."""
        try:
            params = {
                "query": query,
                "rows": min(limit, 100),
                "sort": "relevance",
                "order": "desc",
                "select": "DOI,title,abstract,author,published-print,is-referenced-by-count,container-title",
            }

            if year_start:
                params["filter"] = f"from-pub-date:{year_start}"
                if year_end:
                    params["filter"] += f",until-pub-date:{year_end}"

            resp = await self.client.get(self.crossref_base, params=params)
            if resp.status_code == 200:
                data = resp.json()
                papers = []
                for item in data.get("message", {}).get("items", []):
                    title_list = item.get("title", [])
                    title = title_list[0] if title_list else ""

                    authors = []
                    for a in item.get("author", []):
                        name = f"{a.get('given', '')} {a.get('family', '')}".strip()
                        if name:
                            authors.append(name)

                    year = 0
                    pub_date = item.get("published-print", {})
                    if pub_date and pub_date.get("date-parts"):
                        year = pub_date["date-parts"][0][0]

                    venue_list = item.get("container-title", [])
                    venue = venue_list[0] if venue_list else ""

                    # Clean abstract HTML tags
                    abstract = item.get("abstract", "")
                    if abstract:
                        abstract = re.sub(r"<[^>]+>", "", abstract)

                    papers.append(
                        {
                            "paper_id": f"crossref_{item.get('DOI', '')}",
                            "title": title,
                            "abstract": abstract,
                            "year": year,
                            "authors": authors,
                            "citation_count": item.get("is-referenced-by-count", 0),
                            "doi": item.get("DOI", ""),
                            "url": f"https://doi.org/{item.get('DOI', '')}",
                            "venue": venue,
                            "source": "crossref",
                        }
                    )
                return papers
        except Exception as e:
            logger.error(f"CrossRef search error: {e}")
        return []

    # ── Unified Search ────────────────────────────────────────────────

    async def search_all(
        self,
        query: str,
        sources: list = None,
        limit_per_source: int = 40,
        year_start: int = None,
        year_end: int = None,
        min_citations: int = 0,
        arxiv_categories: list = None,
    ) -> list:
        """Search all configured academic APIs and deduplicate results."""
        if sources is None:
            sources = ["semantic_scholar", "arxiv", "crossref"]

        tasks = []
        if "semantic_scholar" in sources:
            tasks.append(
                self.search_semantic_scholar(
                    query, limit_per_source, year_start, year_end, min_citations
                )
            )
        if "arxiv" in sources:
            tasks.append(
                self.search_arxiv(query, limit_per_source, arxiv_categories)
            )
        if "crossref" in sources:
            tasks.append(
                self.search_crossref(query, limit_per_source, year_start, year_end)
            )

        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten and deduplicate
        papers = []
        seen_titles = set()
        for result in all_results:
            if isinstance(result, Exception):
                logger.error(f"Search source error: {result}")
                continue
            for paper in result:
                title_key = paper.get("title", "").lower().strip()
                if title_key and title_key not in seen_titles:
                    seen_titles.add(title_key)
                    papers.append(paper)

        # Sort by citation count (seminal papers first)
        papers.sort(key=lambda p: p.get("citation_count", 0), reverse=True)
        return papers

    async def close(self):
        await self.client.aclose()


academic_apis = AcademicAPIs()
