import math
from typing import Dict, Any, List

MATERIALS = {
    "structural_steel": {
        "name": "Structural Steel (A36)",
        "elastic_modulus_gpa": 200.0,
        "description": "General structural steel, E = 200 GPa"
    },
    "stainless_steel": {
        "name": "Stainless Steel 304",
        "elastic_modulus_gpa": 193.0,
        "description": "Austenitic stainless steel, E = 193 GPa"
    },
    "aluminum_6061": {
        "name": "Aluminum 6061-T6",
        "elastic_modulus_gpa": 69.0,
        "description": "Aircraft/structural aluminum alloy, E = 69 GPa"
    },
    "titanium_gr5": {
        "name": "Titanium (Ti-6Al-4V)",
        "elastic_modulus_gpa": 114.0,
        "description": "High-strength aerospace titanium, E = 114 GPa"
    },
    "structural_timber": {
        "name": "Structural Timber",
        "elastic_modulus_gpa": 12.0,
        "description": "Standard soft/hardwood construction timber, E = 12 GPa"
    },
    "concrete_c30": {
        "name": "Structural Concrete (C30)",
        "elastic_modulus_gpa": 30.0,
        "description": "Normal weight reinforced concrete, E = 30 GPa"
    }
}

PRESETS: List[Dict[str, Any]] = [
    {
        "id": "ss_center_point",
        "name": "Simply Supported — Center Point Load",
        "category": "Determinate",
        "description": "Pin at x=0m, Roller at x=6m, with 20 kN downward point load at midspan (x=3m).",
        "beam": {"length": 6.0, "elastic_modulus": 200.0, "moment_of_inertia": 83.3},
        "supports": [
            {"type": "pin", "position": 0.0},
            {"type": "roller", "position": 6.0}
        ],
        "loads": [
            {"type": "point", "magnitude": 20.0, "position": 3.0}
        ]
    },
    {
        "id": "ss_full_udl",
        "name": "Simply Supported — Full UDL",
        "category": "Determinate",
        "description": "Pin at x=0m, Roller at x=8m, with 12 kN/m uniformly distributed load across the entire span.",
        "beam": {"length": 8.0, "elastic_modulus": 200.0, "moment_of_inertia": 120.0},
        "supports": [
            {"type": "pin", "position": 0.0},
            {"type": "roller", "position": 8.0}
        ],
        "loads": [
            {"type": "udl", "start_pos": 0.0, "end_pos": 8.0, "start_magnitude": 12.0, "end_magnitude": 12.0}
        ]
    },
    {
        "id": "cantilever_end_point",
        "name": "Cantilever — End Point Load",
        "category": "Determinate",
        "description": "Fixed support at x=0m, with 15 kN downward point load at the free tip (x=4m).",
        "beam": {"length": 4.0, "elastic_modulus": 200.0, "moment_of_inertia": 65.0},
        "supports": [
            {"type": "fixed", "position": 0.0}
        ],
        "loads": [
            {"type": "point", "magnitude": 15.0, "position": 4.0}
        ]
    },
    {
        "id": "cantilever_full_udl",
        "name": "Cantilever — Full UDL",
        "category": "Determinate",
        "description": "Fixed support at x=0m, with 10 kN/m UDL over the entire 5m span.",
        "beam": {"length": 5.0, "elastic_modulus": 200.0, "moment_of_inertia": 90.0},
        "supports": [
            {"type": "fixed", "position": 0.0}
        ],
        "loads": [
            {"type": "udl", "start_pos": 0.0, "end_pos": 5.0, "start_magnitude": 10.0, "end_magnitude": 10.0}
        ]
    },
    {
        "id": "overhanging_combined",
        "name": "Overhanging Beam — Combined Loads",
        "category": "Determinate",
        "description": "Beam length 10m, Pin at x=2m, Roller at x=8m, overhangs on both sides with point load & UDL.",
        "beam": {"length": 10.0, "elastic_modulus": 200.0, "moment_of_inertia": 150.0},
        "supports": [
            {"type": "pin", "position": 2.0},
            {"type": "roller", "position": 8.0}
        ],
        "loads": [
            {"type": "point", "magnitude": 10.0, "position": 0.0},
            {"type": "udl", "start_pos": 2.0, "end_pos": 8.0, "start_magnitude": 8.0, "end_magnitude": 8.0},
            {"type": "point", "magnitude": 15.0, "position": 10.0}
        ]
    },
    {
        "id": "propped_cantilever",
        "name": "Propped Cantilever — UDL (Indeterminate)",
        "category": "Indeterminate",
        "description": "Fixed support at x=0m, Roller at x=6m, with 15 kN/m UDL across the 6m span.",
        "beam": {"length": 6.0, "elastic_modulus": 200.0, "moment_of_inertia": 100.0},
        "supports": [
            {"type": "fixed", "position": 0.0},
            {"type": "roller", "position": 6.0}
        ],
        "loads": [
            {"type": "udl", "start_pos": 0.0, "end_pos": 6.0, "start_magnitude": 15.0, "end_magnitude": 15.0}
        ]
    },
    {
        "id": "fixed_fixed_midspan",
        "name": "Fixed-Fixed Beam — Center Load (Indeterminate)",
        "category": "Indeterminate",
        "description": "Fixed at x=0m and Fixed at x=6m, with 30 kN point load at midspan (x=3m).",
        "beam": {"length": 6.0, "elastic_modulus": 200.0, "moment_of_inertia": 110.0},
        "supports": [
            {"type": "fixed", "position": 0.0},
            {"type": "fixed", "position": 6.0}
        ],
        "loads": [
            {"type": "point", "magnitude": 30.0, "position": 3.0}
        ]
    }
]

def calculate_section_properties(section_type: str, params: Dict[str, float]) -> Dict[str, float]:
    """
    Calculate moment of inertia I in 10^6 mm^4 (which is 10^-6 m^4)
    and section modulus Z for given section dimensions (in mm).
    """
    if section_type == "rectangle":
        b = params.get("width_mm", 100.0)
        h = params.get("height_mm", 200.0)
        i_mm4 = (b * (h ** 3)) / 12.0
        z_mm3 = (b * (h ** 2)) / 6.0
        area_mm2 = b * h
    elif section_type == "solid_circle":
        d = params.get("diameter_mm", 150.0)
        i_mm4 = (math.pi * (d ** 4)) / 64.0
        z_mm3 = (math.pi * (d ** 3)) / 32.0
        area_mm2 = (math.pi * (d ** 2)) / 4.0
    elif section_type == "hollow_circle":
        do = params.get("outer_diameter_mm", 150.0)
        di = params.get("inner_diameter_mm", 130.0)
        i_mm4 = (math.pi * (do ** 4 - di ** 4)) / 64.0
        z_mm3 = (math.pi * (do ** 4 - di ** 4)) / (32.0 * do)
        area_mm2 = (math.pi * (do ** 2 - di ** 2)) / 4.0
    elif section_type == "i_beam":
        bf = params.get("flange_width_mm", 150.0)
        tf = params.get("flange_thickness_mm", 12.0)
        h = params.get("total_height_mm", 300.0)
        tw = params.get("web_thickness_mm", 8.0)
        hw = h - 2 * tf
        i_mm4 = (bf * (h ** 3) - (bf - tw) * (hw ** 3)) / 12.0
        z_mm3 = i_mm4 / (h / 2.0)
        area_mm2 = 2 * bf * tf + hw * tw
    else:
        raise ValueError(f"Unknown section type: {section_type}")

    i_1e6_mm4 = i_mm4 / 1.0e6
    return {
        "moment_of_inertia_1e6_mm4": round(i_1e6_mm4, 3),
        "moment_of_inertia_m4": i_mm4 * 1.0e-12,
        "section_modulus_cm3": round(z_mm3 / 1.0e3, 2),
        "area_cm2": round(area_mm2 / 100.0, 2)
    }
