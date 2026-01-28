"""
Dimension Model for pSEO
Implements P2-4: Multi-dimensional attribute system

Defines dimensions for programmatic page generation:
- Material (plastic, glass, aluminum, etc.)
- Capacity (100ml, 500ml, 1L, etc.)
- Scene (home, office, outdoor, gym, etc.)
- Industry (food, cosmetics, pharmaceutical, etc.)
- Certification (FDA, EU, ISO, etc.)
- And more...

Each combination creates a unique page with differentiated content.
"""

from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import itertools
import logging

logger = logging.getLogger(__name__)


class DimensionType(str, Enum):
    """Standard dimension types for pSEO"""
    MATERIAL = "material"
    CAPACITY = "capacity"
    SIZE = "size"
    COLOR = "color"
    SCENE = "scene"
    INDUSTRY = "industry"
    CERTIFICATION = "certification"
    FEATURE = "feature"
    PRICE_RANGE = "price_range"
    BRAND = "brand"
    LOCATION = "location"
    USE_CASE = "use_case"


@dataclass
class DimensionValue:
    """A single value within a dimension"""
    value_id: str
    display_name: str
    slug: str
    priority: int = 50  # For ordering
    metadata: Dict[str, Any] = field(default_factory=dict)
    aliases: List[str] = field(default_factory=list)  # Alternative names
    
    def __hash__(self):
        return hash(self.value_id)
    
    def __eq__(self, other):
        if isinstance(other, DimensionValue):
            return self.value_id == other.value_id
        return False


@dataclass
class Dimension:
    """A dimension with multiple possible values"""
    dimension_type: DimensionType
    dimension_name: str
    values: List[DimensionValue] = field(default_factory=list)
    is_required: bool = False
    max_combinations: Optional[int] = None  # Limit combinations for this dimension
    
    def add_value(self, value: DimensionValue):
        """Add a value to this dimension"""
        if value not in self.values:
            self.values.append(value)
            self.values.sort(key=lambda v: v.priority, reverse=True)
    
    def get_value(self, value_id: str) -> Optional[DimensionValue]:
        """Get a specific value by ID"""
        return next((v for v in self.values if v.value_id == value_id), None)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.dimension_type.value,
            "name": self.dimension_name,
            "values": [
                {
                    "id": v.value_id,
                    "name": v.display_name,
                    "slug": v.slug
                }
                for v in self.values
            ],
            "is_required": self.is_required
        }


class DimensionModel:
    """
    Multi-dimensional model for pSEO page generation
    
    Example for bottle manufacturing:
    - Material: plastic, glass, aluminum, stainless_steel
    - Capacity: 100ml, 250ml, 500ml, 750ml, 1L
    - Scene: home, office, outdoor, gym, travel
    - Industry: food, beverage, cosmetics, pharmaceutical
    - Certification: FDA, EU, ISO9001, BPA_free
    
    Combinations: plastic_500ml_gym_beverage_BPA_free
    """
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.dimensions: Dict[DimensionType, Dimension] = {}
    
    def add_dimension(self, dimension: Dimension):
        """Add a dimension to the model"""
        self.dimensions[dimension.dimension_type] = dimension
        logger.info(f"Added dimension: {dimension.dimension_name} with {len(dimension.values)} values")
    
    def get_dimension(self, dimension_type: DimensionType) -> Optional[Dimension]:
        """Get a specific dimension"""
        return self.dimensions.get(dimension_type)
    
    def calculate_total_combinations(self) -> int:
        """Calculate total possible page combinations"""
        if not self.dimensions:
            return 0
        
        total = 1
        for dimension in self.dimensions.values():
            total *= len(dimension.values)
        
        return total
    
    def generate_all_combinations(
        self,
        max_combinations: Optional[int] = None
    ) -> List["PageCombination"]:
        """Generate all possible dimension combinations"""
        if not self.dimensions:
            return []
        
        # Get all dimension values as lists
        dimension_types = list(self.dimensions.keys())
        value_lists = [self.dimensions[dt].values for dt in dimension_types]
        
        # Generate cartesian product
        all_combos = list(itertools.product(*value_lists))
        
        logger.info(f"Generated {len(all_combos)} total combinations")
        
        # Convert to PageCombination objects
        combinations = []
        for combo_values in all_combos:
            combo_dict = {
                dimension_types[i]: combo_values[i]
                for i in range(len(dimension_types))
            }
            combinations.append(PageCombination(combo_dict))
        
        # Limit if needed
        if max_combinations and len(combinations) > max_combinations:
            logger.warning(f"Limiting combinations from {len(combinations)} to {max_combinations}")
            combinations = combinations[:max_combinations]
        
        return combinations
    
    def to_dict(self) -> Dict[str, Any]:
        """Export model configuration"""
        return {
            "model_name": self.model_name,
            "dimensions": {
                dt.value: dim.to_dict()
                for dt, dim in self.dimensions.items()
            },
            "total_combinations": self.calculate_total_combinations()
        }


@dataclass
class PageCombination:
    """A specific combination of dimension values representing one page"""
    values: Dict[DimensionType, DimensionValue]
    
    def get_slug(self) -> str:
        """Generate URL slug for this combination"""
        slugs = [v.slug for v in self.values.values()]
        return "-".join(slugs)
    
    def get_title_parts(self) -> List[str]:
        """Get display names for title generation"""
        return [v.display_name for v in self.values.values()]
    
    def to_dict(self) -> Dict[str, Any]:
        """Export combination data"""
        return {
            dim_type.value: value.value_id
            for dim_type, value in self.values.items()
        }
    
    def __hash__(self):
        return hash(tuple(sorted(self.values.items())))
    
    def __repr__(self):
        parts = "_".join(v.value_id for v in self.values.values())
        return f"PageCombination({parts})"


class CombinationFilter:
    """
    Filter to control which combinations are generated
    
    Implements "whitelist" strategy to avoid:
    - Nonsensical combinations (e.g., "plastic_pharmaceutical_BPA_free" might be redundant)
    - Low-value pages
    - Cannibalization
    """
    
    def __init__(self):
        self.rules: List[Dict[str, Any]] = []
        self.blacklist: Set[Tuple] = set()
        self.whitelist: Optional[Set[Tuple]] = None
    
    def add_rule(self, rule: Dict[str, Any]):
        """
        Add a filtering rule
        
        Rule examples:
        {
            "type": "require_any",
            "dimensions": [DimensionType.CERTIFICATION, DimensionType.INDUSTRY],
            "reason": "At least one of cert or industry must be specified"
        }
        {
            "type": "exclude_combination",
            "conditions": {
                DimensionType.MATERIAL: "plastic",
                DimensionType.INDUSTRY: "pharmaceutical"
            },
            "reason": "Plastic not suitable for pharmaceutical"
        }
        """
        self.rules.append(rule)
    
    def add_to_blacklist(self, combination: PageCombination):
        """Add specific combination to blacklist"""
        combo_tuple = tuple(sorted(combination.values.items()))
        self.blacklist.add(combo_tuple)
    
    def set_whitelist(self, combinations: List[PageCombination]):
        """Set explicit whitelist of allowed combinations"""
        self.whitelist = {
            tuple(sorted(c.values.items()))
            for c in combinations
        }
    
    def filter_combinations(
        self,
        combinations: List[PageCombination]
    ) -> List[PageCombination]:
        """Apply filters to combination list"""
        filtered = []
        
        for combo in combinations:
            if self._should_include(combo):
                filtered.append(combo)
        
        logger.info(f"Filtered {len(combinations)} combinations to {len(filtered)}")
        return filtered
    
    def _should_include(self, combo: PageCombination) -> bool:
        """Check if combination should be included"""
        combo_tuple = tuple(sorted(combo.values.items()))
        
        # Check whitelist first (if set)
        if self.whitelist is not None:
            return combo_tuple in self.whitelist
        
        # Check blacklist
        if combo_tuple in self.blacklist:
            return False
        
        # Apply rules
        for rule in self.rules:
            if not self._check_rule(combo, rule):
                return False
        
        return True
    
    def _check_rule(self, combo: PageCombination, rule: Dict[str, Any]) -> bool:
        """Check if combination passes a rule"""
        rule_type = rule.get("type")
        
        if rule_type == "require_any":
            # At least one of specified dimensions must be present
            dimensions = rule.get("dimensions", [])
            return any(dim in combo.values for dim in dimensions)
        
        elif rule_type == "exclude_combination":
            # Exclude if all conditions match
            conditions = rule.get("conditions", {})
            for dim_type, value_id in conditions.items():
                if dim_type in combo.values:
                    if combo.values[dim_type].value_id == value_id:
                        continue
                    else:
                        return True  # Condition doesn't match, include
                else:
                    return True  # Dimension not in combo, include
            return False  # All conditions matched, exclude
        
        elif rule_type == "require_combination":
            # Include only if all conditions match
            conditions = rule.get("conditions", {})
            for dim_type, value_id in conditions.items():
                if dim_type not in combo.values:
                    return False
                if combo.values[dim_type].value_id != value_id:
                    return False
            return True
        
        return True


# Pre-built dimension models for common use cases

def create_bottle_dimension_model() -> DimensionModel:
    """Example: Bottle manufacturing pSEO model"""
    model = DimensionModel("bottle_pseo")
    
    # Material dimension
    material_dim = Dimension(
        dimension_type=DimensionType.MATERIAL,
        dimension_name="Material",
        is_required=True
    )
    material_dim.add_value(DimensionValue("plastic", "Plastic", "plastic", priority=90))
    material_dim.add_value(DimensionValue("glass", "Glass", "glass", priority=85))
    material_dim.add_value(DimensionValue("aluminum", "Aluminum", "aluminum", priority=80))
    material_dim.add_value(DimensionValue("stainless", "Stainless Steel", "stainless-steel", priority=75))
    model.add_dimension(material_dim)
    
    # Capacity dimension
    capacity_dim = Dimension(
        dimension_type=DimensionType.CAPACITY,
        dimension_name="Capacity",
        is_required=True
    )
    capacity_dim.add_value(DimensionValue("100ml", "100ml", "100ml", priority=50))
    capacity_dim.add_value(DimensionValue("250ml", "250ml", "250ml", priority=60))
    capacity_dim.add_value(DimensionValue("500ml", "500ml", "500ml", priority=90))
    capacity_dim.add_value(DimensionValue("750ml", "750ml", "750ml", priority=70))
    capacity_dim.add_value(DimensionValue("1l", "1 Liter", "1-liter", priority=80))
    model.add_dimension(capacity_dim)
    
    # Scene dimension
    scene_dim = Dimension(
        dimension_type=DimensionType.SCENE,
        dimension_name="Use Scene"
    )
    scene_dim.add_value(DimensionValue("gym", "Gym", "gym", priority=90))
    scene_dim.add_value(DimensionValue("office", "Office", "office", priority=85))
    scene_dim.add_value(DimensionValue("outdoor", "Outdoor", "outdoor", priority=80))
    scene_dim.add_value(DimensionValue("travel", "Travel", "travel", priority=75))
    model.add_dimension(scene_dim)
    
    # Industry dimension
    industry_dim = Dimension(
        dimension_type=DimensionType.INDUSTRY,
        dimension_name="Industry"
    )
    industry_dim.add_value(DimensionValue("beverage", "Beverage", "beverage", priority=90))
    industry_dim.add_value(DimensionValue("cosmetics", "Cosmetics", "cosmetics", priority=85))
    industry_dim.add_value(DimensionValue("pharmaceutical", "Pharmaceutical", "pharmaceutical", priority=80))
    model.add_dimension(industry_dim)
    
    return model


def create_saas_pricing_model() -> DimensionModel:
    """Example: SaaS pricing page pSEO model"""
    model = DimensionModel("saas_pricing_pseo")
    
    # Plan type
    plan_dim = Dimension(
        dimension_type=DimensionType.FEATURE,
        dimension_name="Plan Type",
        is_required=True
    )
    plan_dim.add_value(DimensionValue("starter", "Starter", "starter"))
    plan_dim.add_value(DimensionValue("professional", "Professional", "professional"))
    plan_dim.add_value(DimensionValue("enterprise", "Enterprise", "enterprise"))
    model.add_dimension(plan_dim)
    
    # Industry
    industry_dim = Dimension(
        dimension_type=DimensionType.INDUSTRY,
        dimension_name="Industry"
    )
    industry_dim.add_value(DimensionValue("ecommerce", "E-commerce", "ecommerce"))
    industry_dim.add_value(DimensionValue("saas", "SaaS", "saas"))
    industry_dim.add_value(DimensionValue("agency", "Agency", "agency"))
    model.add_dimension(industry_dim)
    
    # Company size
    size_dim = Dimension(
        dimension_type=DimensionType.SIZE,
        dimension_name="Company Size"
    )
    size_dim.add_value(DimensionValue("small", "Small Business (1-20)", "small-business"))
    size_dim.add_value(DimensionValue("medium", "Mid-Market (21-200)", "mid-market"))
    size_dim.add_value(DimensionValue("large", "Enterprise (201+)", "enterprise-level"))
    model.add_dimension(size_dim)
    
    return model
