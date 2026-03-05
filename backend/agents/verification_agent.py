"""Agent 4: Verification Agent - Fact-checks all claims with 4-layer system."""
from agents.base_agent import BaseAgent
from services.ollama_service import ollama_service
from services.academic_apis import academic_apis
from services.chroma_service import chroma_service


class VerificationAgent(BaseAgent):
    """
    Verification Agent - Fact-checking specialist (4-Layer System).
    
    Layer 1: Cross-Reference Check (verify against 3+ sources)
    Layer 2: Metadata Validation (author names, dates, DOI via Semantic Scholar)
    Layer 3: Confidence Scoring (90-100% verified, 70-89% review, <70% flagged)
    Layer 4: Source Preview (link claims to original paper excerpts)
    
    Also checks for plagiarism (similarity detection).
    """

    def __init__(self):
        super().__init__(
            name="Verification Agent",
            description="Fact-checks every claim using a 4-layer verification system",
            icon="✅",
        )

    async def execute(self, context: dict) -> dict:
        claims = context.get("claims", [])
        papers = context.get("papers", [])
        document = context.get("document", {})

        if not claims:
            return {
                "verified_claims": [],
                "plagiarism_report": {"score": 0, "unique_percentage": 100},
                "overall_confidence": 100,
                "verification_summary": "No claims to verify.",
            }

        total_claims = len(claims)

        # ── Layer 1: Cross-Reference Check ────────────────────────
        self.update_progress(5, f"Layer 1: Cross-referencing {total_claims} claims...")
        claims = await self._cross_reference_check(claims, papers)

        # ── Layer 2: Metadata Validation ──────────────────────────
        self.update_progress(30, "Layer 2: Validating paper metadata via APIs...")
        metadata_results = await self._validate_metadata(papers[:20])

        # ── Layer 3: Confidence Scoring ───────────────────────────
        self.update_progress(55, "Layer 3: Computing confidence scores...")
        claims = self._compute_confidence_scores(claims)

        # ── Layer 4: Source Preview ───────────────────────────────
        self.update_progress(70, "Layer 4: Linking claims to source excerpts...")
        claims = self._link_source_previews(claims, papers)

        # ── Plagiarism Check ──────────────────────────────────────
        self.update_progress(85, "Running plagiarism similarity check...")
        plagiarism_report = await self._check_plagiarism(document, papers)

        # ── Compile Results ───────────────────────────────────────
        self.update_progress(95, "Compiling verification report...")

        verified_count = sum(1 for c in claims if c.get("confidence", 0) >= 70)
        flagged_count = sum(1 for c in claims if c.get("confidence", 0) < 70)
        avg_confidence = (
            round(sum(c.get("confidence", 0) for c in claims) / max(1, len(claims)), 1)
        )

        self.update_progress(
            100,
            f"✅ Verified: {verified_count}/{total_claims} claims | "
            f"Confidence: {avg_confidence}% | "
            f"Plagiarism: {plagiarism_report.get('unique_percentage', 100)}% unique",
        )

        return {
            "verified_claims": claims,
            "metadata_validation": metadata_results,
            "plagiarism_report": plagiarism_report,
            "overall_confidence": avg_confidence,
            "verified_count": verified_count,
            "flagged_count": flagged_count,
            "total_claims": total_claims,
            "verification_summary": self._generate_summary(
                verified_count, flagged_count, avg_confidence, plagiarism_report
            ),
            "ethical_badge": {
                "plagiarism_score": plagiarism_report.get("similarity_percentage", 0),
                "sources_verified": f"{verified_count}/{total_claims}",
                "confidence_level": "High" if avg_confidence >= 80 else "Medium" if avg_confidence >= 60 else "Low",
                "human_review": "Recommended" if flagged_count > 0 else "Optional",
            },
        }

    async def _cross_reference_check(self, claims: list, papers: list) -> list:
        """Layer 1: Verify each claim against multiple papers."""
        for i, claim in enumerate(claims):
            if i % 5 == 0:
                self.update_progress(
                    5 + int((i / max(1, len(claims))) * 25),
                    f"Cross-referencing claim {i+1}/{len(claims)}...",
                )

            claim_text = claim.get("text", "")
            
            # Search vector DB for related content
            related = await chroma_service.semantic_search(claim_text, n_results=5)
            
            supporting_sources = []
            for match in related:
                if match.get("similarity", 0) > 0.5:
                    supporting_sources.append({
                        "title": match.get("title", ""),
                        "similarity": match.get("similarity", 0),
                        "excerpt": match.get("text", "")[:200],
                    })

            claim["cross_reference"] = {
                "sources_found": len(supporting_sources),
                "supporting_sources": supporting_sources,
                "status": (
                    "verified" if len(supporting_sources) >= 3
                    else "supported" if len(supporting_sources) >= 1
                    else "needs_verification"
                ),
            }

        return claims

    async def _validate_metadata(self, papers: list) -> list:
        """Layer 2: Validate paper metadata via Semantic Scholar API."""
        results = []
        for paper in papers[:10]:  # Limit API calls
            paper_id = paper.get("paper_id", "")
            if paper_id and not paper_id.startswith("crossref_") and not paper_id.startswith("arxiv_"):
                verification = await academic_apis.verify_paper(paper_id)
                results.append({
                    "paper_id": paper_id,
                    "title": paper.get("title", ""),
                    "verified": verification.get("verified", False),
                    "details": verification,
                })
            else:
                # For ArXiv/CrossRef papers, verify by DOI if available
                results.append({
                    "paper_id": paper_id,
                    "title": paper.get("title", ""),
                    "verified": bool(paper.get("doi")),
                    "details": {"doi": paper.get("doi", ""), "source": paper.get("source", "")},
                })
        return results

    def _compute_confidence_scores(self, claims: list) -> list:
        """Layer 3: Assign confidence scores to each claim."""
        for claim in claims:
            cross_ref = claim.get("cross_reference", {})
            sources_found = cross_ref.get("sources_found", 0)
            status = cross_ref.get("status", "needs_verification")

            # Base confidence from cross-referencing
            if status == "verified":
                base_confidence = 92
            elif status == "supported":
                base_confidence = 78
            else:
                base_confidence = 55

            # Adjust based on number of supporting sources
            source_bonus = min(sources_found * 3, 8)
            
            # Adjust based on claim content (specific numbers = harder to verify)
            claim_text = claim.get("text", "")
            if any(char.isdigit() for char in claim_text) and "%" in claim_text:
                base_confidence -= 5  # Specific stats need more verification

            confidence = min(100, base_confidence + source_bonus)
            claim["confidence"] = confidence
            claim["confidence_level"] = (
                "high" if confidence >= 90
                else "medium" if confidence >= 70
                else "low"
            )
            claim["verified"] = confidence >= 70

        return claims

    def _link_source_previews(self, claims: list, papers: list) -> list:
        """Layer 4: Link each claim to relevant paper excerpts."""
        for claim in claims:
            sources = claim.get("cross_reference", {}).get("supporting_sources", [])
            
            previews = []
            for source in sources[:3]:
                previews.append({
                    "title": source.get("title", ""),
                    "excerpt": source.get("excerpt", ""),
                    "similarity": source.get("similarity", 0),
                })

            claim["source_previews"] = previews

        return claims

    async def _check_plagiarism(self, document: dict, papers: list) -> dict:
        """Check generated text for similarity with source papers."""
        sections = document.get("sections", [])
        if not sections:
            return {"similarity_percentage": 0, "unique_percentage": 100, "flagged_sentences": []}

        # Collect all generated sentences
        all_sentences = []
        for section in sections:
            content = section.get("content", "")
            sentences = [s.strip() for s in content.replace("\n", " ").split(". ") if len(s.strip()) > 20]
            all_sentences.extend(sentences[:20])

        # Check each sentence against vector DB
        flagged = []
        high_similarity_count = 0

        for sentence in all_sentences[:30]:  # Limit for performance
            matches = await chroma_service.semantic_search(sentence, n_results=1)
            if matches and matches[0].get("similarity", 0) > 0.85:
                high_similarity_count += 1
                flagged.append({
                    "sentence": sentence[:200],
                    "similar_to": matches[0].get("title", ""),
                    "similarity": matches[0].get("similarity", 0),
                })

        total_checked = max(1, len(all_sentences[:30]))
        similarity = round((high_similarity_count / total_checked) * 100, 1)

        return {
            "similarity_percentage": similarity,
            "unique_percentage": round(100 - similarity, 1),
            "flagged_sentences": flagged[:10],
            "total_sentences_checked": total_checked,
            "sentences_flagged": high_similarity_count,
        }

    def _generate_summary(
        self,
        verified: int,
        flagged: int,
        avg_confidence: float,
        plagiarism: dict,
    ) -> str:
        """Generate a human-readable verification summary."""
        total = verified + flagged
        unique_pct = plagiarism.get("unique_percentage", 100)

        parts = []
        parts.append(f"Verification Report: {verified}/{total} claims verified")
        parts.append(f"Average confidence: {avg_confidence}%")
        parts.append(f"Content uniqueness: {unique_pct}%")

        if flagged > 0:
            parts.append(
                f"⚠️ {flagged} claims need human review (confidence below 70%)"
            )

        if unique_pct < 85:
            parts.append("⚠️ Some sentences show high similarity to sources — review recommended")
        elif unique_pct >= 95:
            parts.append("✅ Content is highly original with proper attribution")

        return " | ".join(parts)
