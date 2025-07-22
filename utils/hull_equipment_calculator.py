# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: hull_equipment_calculatorユーティリティ
# -*- coding: utf-8 -*-
"""Utility for calculating hull-specific equipment effects."""

"""Calculate hull performance impact based on added equipment."""

from typing import Dict, List


class HullEquipmentEffectCalculator:
    """Calculate effect of equipment weight on hull speed and range."""

    def __init__(self, weight_factor: float = 0.2, range_factor: float = 0.1):
        """Initialize calculator coefficients."""
        self.weight_factor = weight_factor
        self.range_factor = range_factor

    def calculate_effect(self, hull: Dict[str, float], equipments: List[Dict[str, float]]) -> Dict[str, float]:
        """Return new speed and range after applying equipment weight effects."""
        total_weight = sum(e.get("weight", 0.0) for e in equipments)
        hull_weight = hull.get("weight", 1.0)
        max_speed = hull.get("speed", 0.0)
        cruise_speed = hull.get("cruise_speed", 0.0)
        naval_range = hull.get("range", 0.0)
        armor = max(hull.get("armor_max", 0.0), hull.get("armor_min", 0.0))
        length = hull.get("length", 1.0)
        beam = hull.get("beam", 1.0)

        weight_ratio = total_weight / hull_weight if hull_weight else 0
        armor_factor = armor / 1000.0
        size_factor = (length * beam) / 10000.0

        speed_penalty = max_speed * (
            weight_ratio * self.weight_factor + armor_factor + size_factor * 0.1
        )
        cruise_penalty = cruise_speed * (
            weight_ratio * self.weight_factor * 0.5
            + armor_factor * 0.5
            + size_factor * 0.05
        )
        range_penalty = naval_range * (
            weight_ratio * self.range_factor + armor_factor * 0.5 + size_factor * 0.1
        )

        return {
            "new_speed": max(0.0, max_speed - speed_penalty),
            "new_cruise_speed": max(0.0, cruise_speed - cruise_penalty),
            "new_range": max(0.0, naval_range - range_penalty),
        }


def create_hull_specific_equipment(hull_id: str, effect: Dict[str, float], equipment_model) -> str:
    """Save hull specific equipment data and return its ID."""

    # Equipment entry is stored using equipment_model. The returned ID can be
    # associated with a hull to indicate performance changes caused by added
    # weight or armor.
    equipment_id = f"HULL_{hull_id}"
    equipment_data = {
        "equipment_type": "hull_specific",
        "common": {
            "ID": equipment_id,
            "名前": f"{hull_id}専用装備",
        },
        "specific_elements": effect,
    }
    equipment_model.save_equipment(equipment_data)
    return equipment_id
