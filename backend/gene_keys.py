"""
Gene Keys calculation module. Reuses the same gate/line wheel as Human Design
(both systems share the 64-gate zodiac mapping) and maps planetary positions to
the Golden Path spheres per genekeys.com's official planet-to-sphere table.
"""
import json
import os

from human_design import gate_line_at

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
with open(os.path.join(DATA_DIR, "gene_keys_64.json")) as f:
    GENE_KEYS_64 = json.load(f)

# sphere_name -> (chart, planet)  chart is "personality" (natal) or "design" (pre-natal)
SPHERE_SOURCES = {
    "Life's Work": ("personality", "Sun"),
    "Evolution": ("personality", "Earth"),
    "Radiance": ("design", "Sun"),
    "Purpose": ("design", "Earth"),
    "Attraction": ("design", "Moon"),
    "IQ": ("personality", "Venus"),
    "EQ": ("personality", "Mars"),
    "SQ": ("design", "Venus"),
    "Vocation (Core)": ("personality", "Mars_design_placeholder"),  # corrected below
    "Culture": ("design", "Jupiter"),
    "Pearl": ("personality", "Jupiter"),
    "Creativity": ("design", "Uranus"),
    "Relating": ("personality", "Mercury"),
    "Stability": ("design", "Saturn"),
}
# Fix: Vocation/Core sphere = Design Mars (genekeys.com)
SPHERE_SOURCES["Vocation (Core)"] = ("design", "Mars")

SEQUENCE_GROUPS = {
    "Activation Sequence": ["Life's Work", "Evolution", "Radiance", "Purpose"],
    "Venus Sequence": ["Attraction", "IQ", "EQ", "SQ"],
    "Pearl Sequence": ["Vocation (Core)", "Culture", "Pearl"],
    "Additional Spheres": ["Creativity", "Relating", "Stability"],
}


def _earth_lon(sun_lon: float) -> float:
    return (sun_lon + 180) % 360


def compute_gene_keys(personality_positions: dict, design_positions: dict):
    """personality_positions/design_positions are tropical longitudes dicts
    (same as used for Human Design), keyed by planet name including 'Sun','Moon', etc."""
    p = dict(personality_positions)
    d = dict(design_positions)
    p["Earth"] = _earth_lon(p["Sun"])
    d["Earth"] = _earth_lon(d["Sun"])

    spheres = {}
    for sphere_name, (chart, planet) in SPHERE_SOURCES.items():
        source = p if chart == "personality" else d
        lon = source[planet]
        gate, line = gate_line_at(lon)
        gk = GENE_KEYS_64.get(str(gate), {})
        spheres[sphere_name] = {
            "chart": chart, "planet": planet, "gate": gate, "line": line,
            "shadow": gk.get("shadow"), "gift": gk.get("gift"), "siddhi": gk.get("siddhi"),
            "keynote": gk.get("keynote"),
        }

    return {"spheres": spheres, "sequence_groups": SEQUENCE_GROUPS}
