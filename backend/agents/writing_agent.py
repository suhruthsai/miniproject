"""Agent 3: Writing Agent - Generates publication-grade literature reviews."""
from agents.base_agent import BaseAgent
from services.ollama_service import ollama_service


class WritingAgent(BaseAgent):
    """
    Writing Agent - Academic writing specialist.
    
    Features:
    - IMRAD-structured output
    - Critical analysis (not just summary)
    - Paraphrasing engine (synthesizes from multiple sources)
    - Automatic citation management (APA, IEEE, Harvard)
    - Research gap section + novel proposal generation
    - Confidence scores on every claim
    """

    CITATION_FORMATS = {
        "apa": "{authors} ({year}). {title}. {venue}.",
        "ieee": "{authors}, \"{title},\" {venue}, {year}.",
        "harvard": "{authors} ({year}) '{title}', {venue}.",
    }

    def __init__(self):
        super().__init__(
            name="Writing Agent",
            description="Generates publication-grade literature reviews with proper citations",
            icon="✍️",
        )

    async def execute(self, context: dict) -> dict:
        papers = context.get("papers", [])
        topic = context.get("topic", "")
        analysis = context.get("analysis", {})
        citation_format = context.get("citation_format", "apa")
        themes = analysis.get("themes", [])
        gaps = analysis.get("gaps", [])
        contradictions = analysis.get("contradictions", [])
        trends = analysis.get("trends", {})

        # Step 1: Generate citations
        self.update_progress(5, "Generating citation bibliography...")
        citations = self._generate_citations(papers, citation_format)

        # Step 2: Write Introduction
        self.update_progress(10, "Writing Introduction section...")
        introduction = await self._write_introduction(topic, papers, trends)

        # Step 3: Write Background
        self.update_progress(25, "Writing Background section...")
        background = await self._write_background(topic, papers, themes)

        # Step 4: Write Current Research (main literature review)
        self.update_progress(40, "Writing Literature Review body...")
        current_research = await self._write_current_research(
            topic, papers, themes, contradictions
        )

        # Step 5: Write Research Gaps
        self.update_progress(60, "Writing Research Gaps section...")
        gap_section = await self._write_gaps_section(topic, gaps)

        # Step 6: Write Future Directions + Novel Proposal
        self.update_progress(70, "Generating novel research proposals...")
        future_directions = await self._write_future_directions(topic, gaps, trends)

        # Step 7: Write Conclusion
        self.update_progress(80, "Writing Conclusion...")
        conclusion = await self._write_conclusion(topic, themes, gaps)

        # Step 8: Compile full document with confidence scores
        self.update_progress(90, "Compiling final document with confidence scores...")
        
        document = {
            "title": f"Literature Review: {topic}",
            "sections": [
                {
                    "heading": "1. Introduction",
                    "content": introduction,
                    "confidence": 95,
                },
                {
                    "heading": "2. Background",
                    "content": background,
                    "confidence": 90,
                },
                {
                    "heading": "3. Current State of Research",
                    "content": current_research,
                    "confidence": 85,
                },
                {
                    "heading": "4. Research Gaps",
                    "content": gap_section,
                    "confidence": 80,
                },
                {
                    "heading": "5. Future Directions",
                    "content": future_directions,
                    "confidence": 75,
                },
                {
                    "heading": "6. Conclusion",
                    "content": conclusion,
                    "confidence": 90,
                },
            ],
            "references": citations,
            "metadata": {
                "total_papers_cited": len(papers),
                "citation_format": citation_format,
                "themes_covered": len(themes),
                "gaps_identified": len(gaps),
            },
        }

        # Generate claims with confidence for verification
        claims = self._extract_claims(document)

        self.update_progress(100, f"✅ Generated complete literature review with {len(citations)} citations")

        return {
            "document": document,
            "claims": claims,
            "citation_count": len(citations),
        }

    def _generate_citations(self, papers: list, fmt: str = "apa") -> list:
        """Generate formatted bibliography entries."""
        citations = []
        for i, paper in enumerate(papers):
            authors = paper.get("authors", [])
            if not authors:
                author_str = "Unknown"
            elif len(authors) <= 2:
                author_str = " & ".join(authors)
            else:
                author_str = f"{authors[0]} et al."

            citation = {
                "index": i + 1,
                "key": f"[{i+1}]",
                "authors": author_str,
                "year": paper.get("year", "n.d."),
                "title": paper.get("title", "Untitled"),
                "venue": paper.get("venue", ""),
                "doi": paper.get("doi", ""),
                "paper_id": paper.get("paper_id", ""),
                "citation_count": paper.get("citation_count", 0),
            }

            # Format the citation string
            if fmt == "apa":
                citation["formatted"] = (
                    f"{author_str} ({citation['year']}). {citation['title']}. "
                    f"{citation['venue']}."
                )
            elif fmt == "ieee":
                citation["formatted"] = (
                    f"[{i+1}] {author_str}, \"{citation['title']},\" "
                    f"{citation['venue']}, {citation['year']}."
                )
            else:  # harvard
                citation["formatted"] = (
                    f"{author_str} ({citation['year']}) '{citation['title']}', "
                    f"{citation['venue']}."
                )

            citations.append(citation)

        return citations

    async def _write_introduction(self, topic: str, papers: list, trends: dict) -> str:
        """Write the introduction section."""
        trend_desc = trends.get("trend", "growing")
        total = len(papers)

        prompt = f"""Write an academic introduction (3-4 paragraphs) for a literature review on "{topic}".

Statistics:
- {total} papers analyzed
- Publication trend: {trend_desc}
- Average citations per paper: {trends.get('avg_citations', 0)}

Requirements:
- Use formal academic tone suitable for SCI publication
- Begin with broad context, then narrow to specific topic
- State the purpose and scope of the review
- Mention the methodology (systematic review of {total} papers)
- DO NOT copy phrases - write original academic prose
- Include placeholder citations like (Author et al., Year) that reference real papers
- End with an overview of the review structure

Important: Write unique, paraphrased content. Never copy text from any source."""

        return await ollama_service.generate(prompt)

    async def _write_background(self, topic: str, papers: list, themes: list) -> str:
        """Write background/theoretical framework section."""
        theme_list = "\n".join(f"- {t['name']}: {t.get('description', '')}" for t in themes[:5])
        
        top_papers = "\n".join(
            f"- \"{p['title']}\" by {', '.join(p.get('authors', [])[:2])} ({p.get('year', '')})"
            for p in papers[:10]
        )

        prompt = f"""Write a Background section (2-3 paragraphs) for a literature review on "{topic}".

Key themes identified:
{theme_list}

Important foundational papers:
{top_papers}

Requirements:
- Explain key concepts and theoretical foundations
- Reference foundational works with proper in-text citations
- Build from established knowledge to current research frontiers
- Use formal academic writing, completely paraphrased
- Synthesize information from multiple sources, don't just describe one paper at a time"""

        return await ollama_service.generate(prompt)

    async def _write_current_research(
        self, topic: str, papers: list, themes: list, contradictions: list
    ) -> str:
        """Write the main literature review body organized by themes."""
        sections = []

        for i, theme in enumerate(themes[:5]):
            theme_name = theme.get("name", "")
            theme_desc = theme.get("description", "")
            
            # Find papers most relevant to this theme
            relevant = [
                p for p in papers
                if theme_name.lower().split()[0] in (p.get("title", "") + " " + p.get("abstract", "")).lower()
            ][:8]

            if not relevant:
                relevant = papers[i * 5 : (i + 1) * 5]

            paper_info = "\n".join(
                f"- \"{p['title']}\" ({p.get('year', '')}, {p.get('citation_count', 0)} citations): "
                f"{(p.get('abstract', '') or '')[:250]}"
                for p in relevant
            )

            contradiction_text = ""
            if contradictions:
                contradiction_text = f"\n\nContradictions to address:\n" + "\n".join(
                    f"- {c.get('description', '')}" for c in contradictions[:2]
                )

            prompt = f"""Write a subsection (2-3 paragraphs) for the literature review on "{topic}".

Subtopic: {theme_name} - {theme_desc}

Relevant papers:
{paper_info}
{contradiction_text}

Requirements:
- CRITICALLY ANALYZE, don't just summarize
- Discuss methodology strengths and weaknesses
- Compare and contrast findings across papers
- Use SYNTHESIS: combine ideas from multiple papers in each paragraph
- Include in-text citations like (Author et al., Year)
- Note any limitations or conflicting results
- Write completely original, paraphrased academic prose"""

            section_text = await ollama_service.generate(prompt)
            sections.append(f"### 3.{i+1} {theme_name}\n\n{section_text}")

        return "\n\n".join(sections)

    async def _write_gaps_section(self, topic: str, gaps: list) -> str:
        """Write the research gaps section."""
        gap_text = "\n".join(f"- {g.get('description', '')}" for g in gaps)

        prompt = f"""Write a Research Gaps section (2-3 paragraphs) for a literature review on "{topic}".

Identified gaps:
{gap_text}

Requirements:
- Clearly articulate what has NOT been studied
- Explain why each gap matters
- Connect gaps to future research opportunities
- Use formal academic tone
- This section should demonstrate deep understanding of the field"""

        return await ollama_service.generate(prompt)

    async def _write_future_directions(self, topic: str, gaps: list, trends: dict) -> str:
        """Write future directions with novel research proposals."""
        gap_text = "\n".join(f"- {g.get('description', '')}" for g in gaps)

        prompt = f"""Write a Future Directions section for a literature review on "{topic}".

Research gaps identified:
{gap_text}

Field trend: {trends.get('trend', 'growing')}

Requirements:
1. Suggest 2-3 specific, novel research proposals based on the gaps
2. For each proposal, include:
   - Proposed study title
   - Brief methodology suggestion
   - Expected contribution to the field
3. Discuss emerging technologies or methods that could advance the field
4. Use formal academic tone suitable for SCI publication
5. Be specific and actionable, not vague"""

        return await ollama_service.generate(prompt)

    async def _write_conclusion(self, topic: str, themes: list, gaps: list) -> str:
        """Write the conclusion section."""
        theme_names = ", ".join(t.get("name", "") for t in themes[:5])

        prompt = f"""Write a Conclusion (2-3 paragraphs) for a literature review on "{topic}".

Key themes covered: {theme_names}
Number of gaps identified: {len(gaps)}

Requirements:
- Summarize the main findings of the review
- Highlight the most significant contributions in the field
- Emphasize the most critical research gaps
- End with a forward-looking statement about the field's future
- Use formal academic tone"""

        return await ollama_service.generate(prompt)

    def _extract_claims(self, document: dict) -> list:
        """Extract verifiable claims from the generated document."""
        claims = []
        claim_id = 0
        
        for section in document.get("sections", []):
            content = section.get("content", "")
            sentences = content.replace("\n", " ").split(". ")
            
            for sentence in sentences:
                sentence = sentence.strip()
                # Claims are sentences that contain specific facts/numbers/comparisons
                if any(indicator in sentence.lower() for indicator in [
                    "found that", "showed that", "demonstrated", "reported",
                    "significantly", "improved", "increased", "decreased",
                    "achieved", "outperformed", "compared to", "%",
                    "higher", "lower", "better", "worse",
                ]):
                    claim_id += 1
                    claims.append({
                        "id": claim_id,
                        "text": sentence,
                        "section": section.get("heading", ""),
                        "confidence": section.get("confidence", 0),
                        "verified": False,
                        "sources": [],
                    })

        return claims[:50]  # Limit to 50 claims for verification
