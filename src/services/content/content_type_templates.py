"""
Content Type Templates

Per-content-type writing instruction templates for ContentCreatorAgent.
Maps ArticleContentType values to ContentTypeTemplate dataclasses with ordered
SectionTemplate lists that define the H2 skeleton and per-section writing modes.
"""

from dataclasses import dataclass, field
from typing import List
from src.models.seo_context import ArticleContentType


@dataclass
class SectionTemplate:
    """Template for a single H2 section in an article."""
    name: str          # H2 title template (may include {keyword} placeholder)
    section_type: str  # "step" | "comparison" | "list_item" | "verdict" | "faq" | "cta" | "prerequisites" | etc.
    writing_mode: str  # Instruction injected into ContentCreatorAgent writing prompt
    estimated_words: int = 350


@dataclass
class ContentTypeTemplate:
    """Full article structure template for a given ArticleContentType."""
    content_type: ArticleContentType
    opening_instruction: str   # How to open the article
    sections: List[SectionTemplate]  # Ordered H2 skeleton
    closing_instruction: str   # How to close / what CTA type


CONTENT_TYPE_TEMPLATES: dict = {
    ArticleContentType.HOW_TO: ContentTypeTemplate(
        content_type=ArticleContentType.HOW_TO,
        opening_instruction="Start with a brief outcome statement (what the reader will achieve). "
                             "Follow with a 'What You'll Need' prerequisites block.",
        sections=[
            SectionTemplate("What You'll Need", "prerequisites",
                            "Bullet list. Be concrete — tools, inputs, access levels.", 150),
            SectionTemplate("Step 1: {first_action}", "step",
                            "Numbered. One action per step. Include a 'Pro Tip' or common mistake note.", 300),
            SectionTemplate("Step 2: {second_action}", "step",
                            "Numbered. Include expected outcome after this step.", 300),
            SectionTemplate("Troubleshooting Common Issues", "troubleshooting",
                            "FAQ-style. Address the 2-3 most common failure points.", 250),
            SectionTemplate("Frequently Asked Questions", "faq",
                            "Direct Q&A. 3–4 questions.", 300),
        ],
        closing_instruction="End with a success checklist and a single CTA to the primary landing page."
    ),
    ArticleContentType.LISTICLE: ContentTypeTemplate(
        content_type=ArticleContentType.LISTICLE,
        opening_instruction="Open with the selection criteria used to build this list. State the number in H1.",
        sections=[
            SectionTemplate("How We Evaluated These Options", "methodology",
                            "2–3 bullet criteria. Data-backed where possible.", 150),
            SectionTemplate("1. {top_item}", "list_item",
                            "Lead with verdict sentence. Cover: what it is, who it's for, tradeoffs.", 300),
            SectionTemplate("2. {second_item}", "list_item",
                            "Same pattern. Include a comparison note vs item 1.", 300),
            SectionTemplate("Quick Comparison Table", "comparison_table",
                            "HTML table: item | best for | price range | key spec.", 200),
            SectionTemplate("Frequently Asked Questions", "faq",
                            "3–4 questions buyers ask when comparing these options.", 300),
        ],
        closing_instruction="Close with a 'Which should you choose?' decision guide paragraph."
    ),
    ArticleContentType.COMPARISON: ContentTypeTemplate(
        content_type=ArticleContentType.COMPARISON,
        opening_instruction="Open with the use-case framing: when would you choose A vs B? "
                             "Give a 1-sentence verdict immediately.",
        sections=[
            SectionTemplate("Quick Verdict", "verdict",
                            "2–3 sentence summary. Who wins for which use case.", 100),
            SectionTemplate("{option_a} — Strengths and Weaknesses", "analysis",
                            "Cover: specs, performance, cost implications, ideal scenario.", 350),
            SectionTemplate("{option_b} — Strengths and Weaknesses", "analysis",
                            "Same structure as option A for parallel scanning.", 350),
            SectionTemplate("Side-by-Side Comparison", "comparison_table",
                            "HTML table with 6–8 decision criteria as rows.", 200),
            SectionTemplate("Which Should You Choose?", "recommendation",
                            "Scenario-based recommendation: If X then A; if Y then B.", 250),
        ],
        closing_instruction="End with a decision tree or checklist. CTA to the more general category page."
    ),
    ArticleContentType.REVIEW: ContentTypeTemplate(
        content_type=ArticleContentType.REVIEW,
        opening_instruction="Open with the overall verdict and a star/score rating immediately.",
        sections=[
            SectionTemplate("Overview and First Impressions", "overview",
                            "What is it, who makes it, what does the reviewer's experience look like.", 200),
            SectionTemplate("Performance Testing", "evidence",
                            "Specific measurements, test conditions, benchmarks where available.", 350),
            SectionTemplate("Pros and Cons", "pros_cons",
                            "Bulleted list. Minimum 4 pros, 3 cons. Be specific.", 200),
            SectionTemplate("How It Compares", "comparison",
                            "Compare to 1–2 direct alternatives. Use a mini table.", 300),
            SectionTemplate("Verdict: Who Should Buy This?", "verdict",
                            "Scenario-based. Do not recommend universally.", 200),
        ],
        closing_instruction="Close with a clear 'Buy / Don't Buy' guidance section."
    ),
    ArticleContentType.PRICING: ContentTypeTemplate(
        content_type=ArticleContentType.PRICING,
        opening_instruction="Open with a price range summary immediately (e.g., '$X–$Y depending on...'). "
                             "Do not bury the number.",
        sections=[
            SectionTemplate("Typical Price Range for {keyword}", "price_range",
                            "Specific numbers. Segment by tier (budget / mid / premium) if applicable.", 200),
            SectionTemplate("What Drives the Cost", "cost_drivers",
                            "3–5 specific factors. Use bullet list with brief explanation each.", 300),
            SectionTemplate("Price Comparison: Top Options", "comparison_table",
                            "HTML table: option | price | what's included | best for.", 250),
            SectionTemplate("Hidden Costs to Watch For", "warnings",
                            "Concrete examples of add-ons, minimums, or fees.", 200),
            SectionTemplate("Frequently Asked Questions", "faq",
                            "Price-specific Q&A: Is it worth it? What's a fair price? etc.", 300),
        ],
        closing_instruction="Close with a 'How to Get a Quote' or 'Next Step' CTA."
    ),
    ArticleContentType.GENERAL: ContentTypeTemplate(
        content_type=ArticleContentType.GENERAL,
        opening_instruction="Open with a concise answer to the title's implicit question.",
        sections=[
            SectionTemplate("Background and Context", "background",
                            "Set the scene. Keep to 2 paragraphs max.", 250),
            SectionTemplate("Key Considerations", "main_content",
                            "3–4 substantive sections based on topic. Use subheadings.", 400),
            SectionTemplate("Frequently Asked Questions", "faq",
                            "3 Q&A pairs.", 300),
        ],
        closing_instruction="Standard summary + primary CTA."
    ),
}
