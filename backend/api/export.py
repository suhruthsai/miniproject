"""Export API routes for LaTeX, Markdown, Word formats."""
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from agents.coordinator import coordinator

router = APIRouter(prefix="/api", tags=["export"])


@router.get("/export/{research_id}")
async def export_document(research_id: str, format: str = "markdown"):
    """Export the generated literature review in various formats."""
    result = coordinator.get_result(research_id)
    if not result:
        return {"error": "Research not found or still in progress"}

    document = result.get("document", {})
    references = document.get("references", [])
    sections = document.get("sections", [])

    if format == "markdown":
        return PlainTextResponse(
            content=_to_markdown(document, sections, references),
            media_type="text/markdown",
        )
    elif format == "latex":
        return PlainTextResponse(
            content=_to_latex(document, sections, references),
            media_type="text/plain",
        )
    elif format == "word":
        # Return structured JSON that frontend can convert to .docx
        return {
            "format": "word",
            "title": document.get("title", ""),
            "sections": sections,
            "references": references,
        }
    else:
        return {"error": f"Unsupported format: {format}. Use markdown, latex, or word."}


def _to_markdown(document: dict, sections: list, references: list) -> str:
    """Convert to Markdown format."""
    lines = [f"# {document.get('title', 'Literature Review')}\n"]

    for section in sections:
        lines.append(f"\n## {section.get('heading', '')}\n")
        lines.append(section.get("content", ""))
        lines.append("")

    lines.append("\n## References\n")
    for ref in references:
        lines.append(f"{ref.get('key', '')} {ref.get('formatted', '')}")

    return "\n".join(lines)


def _to_latex(document: dict, sections: list, references: list) -> str:
    """Convert to LaTeX format."""
    title = document.get("title", "Literature Review")
    
    lines = [
        r"\documentclass[12pt]{article}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage{natbib}",
        r"\usepackage{hyperref}",
        r"\usepackage[margin=1in]{geometry}",
        "",
        f"\\title{{{_escape_latex(title)}}}",
        r"\author{Research Assistant}",
        r"\date{\today}",
        "",
        r"\begin{document}",
        r"\maketitle",
        r"\begin{abstract}",
        "This literature review was generated using the Autonomous Multi-Agent Research Assistant.",
        r"\end{abstract}",
        "",
    ]

    for section in sections:
        heading = section.get("heading", "").lstrip("0123456789. ")
        content = _escape_latex(section.get("content", ""))
        lines.append(f"\\section{{{heading}}}")
        lines.append(content)
        lines.append("")

    lines.append(r"\begin{thebibliography}{99}")
    for ref in references:
        key = ref.get("key", "").strip("[]")
        formatted = _escape_latex(ref.get("formatted", ""))
        lines.append(f"\\bibitem{{{key}}} {formatted}")
    lines.append(r"\end{thebibliography}")
    lines.append(r"\end{document}")

    return "\n".join(lines)


def _escape_latex(text: str) -> str:
    """Escape special LaTeX characters."""
    chars = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "~": r"\textasciitilde{}"}
    for char, replacement in chars.items():
        text = text.replace(char, replacement)
    return text
