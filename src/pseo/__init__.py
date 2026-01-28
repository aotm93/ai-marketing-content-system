"""
pSEO pseo __init__
"""

from .components import (
    ComponentType,
    ComponentSchema,
    HeroComponent,
    ComparisonTableComponent,
    FAQComponent,
    SpecificationsComponent,
    CTAComponent,
    ProsConsComponent,
    PriceTableComponent,
    PageTemplate,
    ComponentRegistry
)

from .dimension_model import (
    DimensionType,
    Dimension,
    DimensionValue,
    DimensionModel,
    CombinationFilter,
    PageCombination
)

from .page_factory import (
    pSEOFactory,
    FactoryConfig,
    GenerationResult
)

__all__ = [
    "ComponentType",
    "ComponentSchema",
    "HeroComponent",
    "ComparisonTableComponent",
    "FAQComponent",
    "SpecificationsComponent",
    "CTAComponent",
    "ProsConsComponent",
    "PriceTableComponent",
    "PageTemplate",
    "ComponentRegistry",
    "DimensionType",
    "Dimension",
    "DimensionValue",
    "DimensionModel",
    "CombinationFilter",
    "PageCombination",
    "pSEOFactory",
    "FactoryConfig",
    "GenerationResult",
]
