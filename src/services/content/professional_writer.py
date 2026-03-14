"""
Professional Content Writer
Generates in-depth content based on search intent analysis
"""

from typing import Optional
from src.services.content.intent_analyzer import SearchIntentAnalyzer, IntentSignal, UserIntent
from src.models.content_intelligence import OutlineSection


class ProfessionalContentWriter:
    """Generate professional, in-depth content based on user intent"""

    CONTENT_REQUIREMENTS = {
        UserIntent.PROBLEM_SOLVING: {
            "root_cause_analysis": True,
            "actionable_solutions": True,
            "avoid_generic": True,
            "require_data": True
        },
        UserIntent.SPECIFICATION: {
            "technical_parameters": True,
            "avoid_basic_explanation": True,
            "require_standards": True,
            "avoid_generic": True
        },
        UserIntent.COMPARISON: {
            "specific_metrics": True,
            "avoid_generic": True
        }
    }

    def __init__(self):
        self.intent_analyzer = SearchIntentAnalyzer()

    def build_section_prompt(
        self,
        section: OutlineSection,
        intent_signal: IntentSignal,
        research_data: Optional[dict] = None
    ) -> str:
        """Build professional prompt avoiding generic templates"""

        intent = intent_signal.intent
        reqs = self.get_content_requirements(intent)

        if intent == UserIntent.PROBLEM_SOLVING:
            return f"""Write technical analysis for: {section.title}

Requirements:
- Explain root causes with specific technical details
- Provide data-backed evidence
- Give actionable solutions
- Avoid generic advice like "be careful" or "follow best practices"
- Start with a concise 40-60 word summary for Featured Snippet optimization

Key points to cover: {', '.join(section.key_points)}"""

        elif intent == UserIntent.SPECIFICATION:
            return f"""Write technical specification analysis for: {section.title}

Requirements:
- Provide specific technical parameters and data
- Compare different specifications in table format
- Reference industry standards
- Skip basic introductory explanations
- Use structured format (lists/tables) for Featured Snippet eligibility

Key points to cover: {', '.join(section.key_points)}"""

        return f"""Write professional content for: {section.title}

Requirements:
- Start with a clear, concise answer (40-60 words)
- Use structured formatting (lists, tables) where appropriate
- Provide specific, actionable information

Key points: {', '.join(section.key_points)}"""

    def get_content_requirements(self, intent: UserIntent) -> dict:
        """Get specific requirements for each intent type"""
        return self.CONTENT_REQUIREMENTS.get(intent, {})
