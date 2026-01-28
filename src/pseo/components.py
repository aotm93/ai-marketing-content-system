"""
Page Component Protocol
Implements P2-1: Standardized page component system

Defines reusable page components for pSEO:
- Summary/Hero
- Comparison Table
- FAQ
- Case Studies
- CTA
- Specifications
- Price Table
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json


class ComponentType(str, Enum):
    """Standard component types"""
    HERO = "hero"
    SUMMARY = "summary"
    TABLE = "table"
    FAQ = "faq"
    CASE_STUDY = "case_study"
    CTA = "cta"
    SPECIFICATIONS = "specifications"
    PRICE_TABLE = "price_table"
    COMPARISON = "comparison"
    PROS_CONS = "pros_cons"
    FEATURE_LIST = "feature_list"
    TESTIMONIAL = "testimonial"


@dataclass
class ComponentSchema:
    """Base schema for page components"""
    component_type: ComponentType = ComponentType.SUMMARY
    component_id: str = ""
    priority: int = 50  # 0-100, higher = more important
    required: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.component_type.value,
            "id": self.component_id,
            "priority": self.priority,
            "required": self.required
        }


@dataclass
class HeroComponent(ComponentSchema):
    """Hero section with headline and value proposition"""
    component_type: ComponentType = ComponentType.HERO
    
    headline: str = ""
    subheadline: str = ""
    value_proposition: List[str] = field(default_factory=list)
    cta_text: str = "Get Started"
    cta_url: str = "#"
    background_image: Optional[str] = None
    
    def to_html(self) -> str:
        """Generate HTML for hero component"""
        return f'''
<section class="hero-section" id="{self.component_id}">
    <div class="hero-content">
        <h1>{self.headline}</h1>
        <p class="subheadline">{self.subheadline}</p>
        <ul class="value-props">
            {"".join(f"<li>{prop}</li>" for prop in self.value_proposition)}
        </ul>
        <a href="{self.cta_url}" class="cta-button">{self.cta_text}</a>
    </div>
</section>
'''


@dataclass
class ComparisonTableComponent(ComponentSchema):
    """Comparison table for products/options"""
    component_type: ComponentType = ComponentType.COMPARISON
    
    title: str = ""
    headers: List[str] = field(default_factory=list)
    rows: List[Dict[str, Any]] = field(default_factory=list)
    highlight_column: Optional[int] = None
    
    def to_html(self) -> str:
        """Generate HTML for comparison table"""
        html = f'<section class="comparison-table" id="{self.component_id}">\n'
        if self.title:
            html += f'<h2>{self.title}</h2>\n'
        
        html += '<table class="responsive-table">\n<thead>\n<tr>\n'
        for i, header in enumerate(self.headers):
            highlight = ' class="highlight"' if i == self.highlight_column else ''
            html += f'<th{highlight}>{header}</th>\n'
        html += '</tr>\n</thead>\n<tbody>\n'
        
        for row in self.rows:
            html += '<tr>\n'
            for header in self.headers:
                value = row.get(header, '')
                html += f'<td>{value}</td>\n'
            html += '</tr>\n'
        
        html += '</tbody>\n</table>\n</section>'
        return html


@dataclass
class FAQComponent(ComponentSchema):
    """FAQ section with schema markup"""
    component_type: ComponentType = ComponentType.FAQ
    
    title: str = "Frequently Asked Questions"
    questions: List[Dict[str, str]] = field(default_factory=list)  # [{question, answer}]
    
    def to_html(self) -> str:
        """Generate HTML with schema.org markup"""
        html = f'<section class="faq-section" id="{self.component_id}">\n'
        html += f'<h2>{self.title}</h2>\n'
        
        for qa in self.questions:
            html += f'''
<div class="faq-item" itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
    <h3 itemprop="name">{qa["question"]}</h3>
    <div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
        <p itemprop="text">{qa["answer"]}</p>
    </div>
</div>
'''
        
        html += '</section>'
        return html
    
    def to_schema(self) -> Dict[str, Any]:
        """Generate structured data"""
        return {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": qa["question"],
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": qa["answer"]
                    }
                }
                for qa in self.questions
            ]
        }


@dataclass
class SpecificationsComponent(ComponentSchema):
    """Product/service specifications"""
    component_type: ComponentType = ComponentType.SPECIFICATIONS
    
    title: str = "Specifications"
    specs: Dict[str, str] = field(default_factory=dict)
    categories: Optional[Dict[str, List[str]]] = None  # Group specs by category
    
    def to_html(self) -> str:
        """Generate HTML for specifications"""
        html = f'<section class="specifications" id="{self.component_id}">\n'
        html += f'<h2>{self.title}</h2>\n'
        
        if self.categories:
            for category, keys in self.categories.items():
                html += f'<h3>{category}</h3>\n<dl class="spec-list">\n'
                for key in keys:
                    if key in self.specs:
                        html += f'<dt>{key}</dt>\n<dd>{self.specs[key]}</dd>\n'
                html += '</dl>\n'
        else:
            html += '<dl class="spec-list">\n'
            for key, value in self.specs.items():
                html += f'<dt>{key}</dt>\n<dd>{value}</dd>\n'
            html += '</dl>\n'
        
        html += '</section>'
        return html


@dataclass
class CTAComponent(ComponentSchema):
    """Call-to-action section"""
    component_type: ComponentType = ComponentType.CTA
    
    headline: str = ""
    description: str = ""
    button_text: str = "Get Started"
    button_url: str = "#"
    secondary_text: Optional[str] = None
    secondary_url: Optional[str] = None
    style: str = "primary"  # primary, secondary, inline
    
    def to_html(self) -> str:
        """Generate HTML for CTA"""
        html = f'<section class="cta-section cta-{self.style}" id="{self.component_id}">\n'
        html += f'<h2>{self.headline}</h2>\n'
        if self.description:
            html += f'<p>{self.description}</p>\n'
        
        html += f'<a href="{self.button_url}" class="cta-button primary">{self.button_text}</a>\n'
        
        if self.secondary_text and self.secondary_url:
            html += f'<a href="{self.secondary_url}" class="cta-button secondary">{self.secondary_text}</a>\n'
        
        html += '</section>'
        return html


@dataclass
class ProsConsComponent(ComponentSchema):
    """Pros and cons list"""
    component_type: ComponentType = ComponentType.PROS_CONS
    
    title: str = "Pros & Cons"
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    
    def to_html(self) -> str:
        """Generate HTML for pros/cons"""
        html = f'<section class="pros-cons" id="{self.component_id}">\n'
        html += f'<h2>{self.title}</h2>\n'
        html += '<div class="pros-cons-grid">\n'
        
        html += '<div class="pros">\n<h3>Pros</h3>\n<ul>\n'
        for pro in self.pros:
            html += f'<li class="pro">✓ {pro}</li>\n'
        html += '</ul>\n</div>\n'
        
        html += '<div class="cons">\n<h3>Cons</h3>\n<ul>\n'
        for con in self.cons:
            html += f'<li class="con">✗ {con}</li>\n'
        html += '</ul>\n</div>\n'
        
        html += '</div>\n</section>'
        return html


@dataclass
class PriceTableComponent(ComponentSchema):
    """Pricing table"""
    component_type: ComponentType = ComponentType.PRICE_TABLE
    
    title: str = "Pricing"
    plans: List[Dict[str, Any]] = field(default_factory=list)
    # Plan structure: {name, price, currency, period, features, cta_text, cta_url, highlighted}
    
    def to_html(self) -> str:
        """Generate HTML for pricing table"""
        html = f'<section class="price-table" id="{self.component_id}">\n'
        html += f'<h2>{self.title}</h2>\n'
        html += '<div class="pricing-grid">\n'
        
        for plan in self.plans:
            highlight = ' highlighted' if plan.get('highlighted') else ''
            html += f'<div class="pricing-card{highlight}">\n'
            html += f'<h3>{plan["name"]}</h3>\n'
            html += f'<div class="price">{plan.get("currency", "$")}{plan["price"]}<span class="period">/{plan.get("period", "month")}</span></div>\n'
            
            if plan.get('features'):
                html += '<ul class="features">\n'
                for feature in plan['features']:
                    html += f'<li>{feature}</li>\n'
                html += '</ul>\n'
            
            cta_text = plan.get('cta_text', 'Choose Plan')
            cta_url = plan.get('cta_url', '#')
            html += f'<a href="{cta_url}" class="plan-cta">{cta_text}</a>\n'
            html += '</div>\n'
        
        html += '</div>\n</section>'
        return html


class ComponentRegistry:
    """Registry for component types"""
    
    COMPONENTS = {
        ComponentType.HERO: HeroComponent,
        ComponentType.SUMMARY: ComponentSchema,
        ComponentType.TABLE: ComparisonTableComponent,
        ComponentType.FAQ: FAQComponent,
        ComponentType.SPECIFICATIONS: SpecificationsComponent,
        ComponentType.CTA: CTAComponent,
        ComponentType.PROS_CONS: ProsConsComponent,
        ComponentType.PRICE_TABLE: PriceTableComponent,
    }
    
    @classmethod
    def create_component(cls, component_type: ComponentType, **kwargs) -> ComponentSchema:
        """Factory method to create components"""
        component_class = cls.COMPONENTS.get(component_type, ComponentSchema)
        return component_class(component_type=component_type, **kwargs)
    
    @classmethod
    def validate_component(cls, component: ComponentSchema) -> bool:
        """Validate component structure"""
        if not component.component_id:
            return False
        if component.required and not hasattr(component, 'title'):
            return False
        return True


@dataclass
class PageTemplate:
    """Page template composed of components"""
    template_id: str
    template_name: str
    components: List[ComponentSchema] = field(default_factory=list)
    meta_template: Dict[str, str] = field(default_factory=dict)
    
    def add_component(self, component: ComponentSchema):
        """Add component to template"""
        self.components.append(component)
        # Sort by priority
        self.components.sort(key=lambda c: c.priority, reverse=True)
    
    def render(self, data: Dict[str, Any]) -> str:
        """Render template with data"""
        html_parts = []
        
        for component in self.components:
            if hasattr(component, 'to_html'):
                html_parts.append(component.to_html())
        
        return '\n'.join(html_parts)
    
    def validate(self) -> List[str]:
        """Validate template completeness"""
        errors = []
        
        # Check required components
        required = [c for c in self.components if c.required]
        if not required:
            errors.append("Template has no required components")
        
        # Check for duplicate IDs
        ids = [c.component_id for c in self.components]
        if len(ids) != len(set(ids)):
            errors.append("Duplicate component IDs found")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Export template configuration"""
        return {
            "template_id": self.template_id,
            "template_name": self.template_name,
            "components": [c.to_dict() for c in self.components],
            "meta_template": self.meta_template
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PageTemplate":
        """Import template from configuration"""
        template = cls(
            template_id=data["template_id"],
            template_name=data["template_name"],
            meta_template=data.get("meta_template", {})
        )
        
        for comp_data in data.get("components", []):
            comp_type = ComponentType(comp_data["type"])
            component = ComponentRegistry.create_component(comp_type, **comp_data)
            template.add_component(component)
        
        return template


def create_default_template(template_id: str = "default") -> PageTemplate:
    """Create a default page template (Factory Method)"""
    template = PageTemplate(
        template_id=template_id,
        template_name="Default pSEO Template"
    )
    
    # Add default components
    hero = HeroComponent(
        component_id="hero-1",
        headline="Premium {material} {capacity} Bottle",
        subheadline="Perfect for {scene} use",
        priority=100,
        required=True
    )
    template.add_component(hero)
    
    faq = FAQComponent(
        component_id="faq-1",
        title="Frequently Asked Questions",
        questions=[
            {
                "question": "What materials are available?",
                "answer": "We offer bottles in plastic, glass, aluminum, and stainless steel."
            },
            {
                "question": "What capacities do you provide?",
                "answer": "Available in 100ml, 250ml, 500ml, 750ml, and 1 liter sizes."
            }
        ],
        priority=80,
        required=True
    )
    template.add_component(faq)
    
    return template
