"""
Assembles structured report content (for both 'concise' and 'comprehensive' depth)
from the raw calculation outputs, using the reference/interpretation data files.
"""
import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def _load(name):
    with open(os.path.join(DATA_DIR, name)) as f:
        return json.load(f)


WESTERN_DATA = _load("western_data.json")
NUMEROLOGY_DATA = _load("numerology_data.json")
VEDIC_DATA = _load("vedic_data.json")
HD_DATA = _load("human_design.json")
GK_DATA = _load("gene_keys_64.json")

VEDIC_NAKSHATRAS = VEDIC_DATA["nakshatras"]  # list index 0-26

MAIN_PLANETS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
PERSONAL_PLANETS = ["Sun", "Moon", "Mercury", "Venus", "Mars"]


def fmt_deg(d):
    deg = int(d)
    minutes = int(round((d - deg) * 60))
    if minutes == 60:
        deg += 1
        minutes = 0
    return f"{deg}\u00b0{minutes:02d}'"


def build_western_section(western: dict, depth: str) -> dict:
    signs = WESTERN_DATA["signs"]
    planets_meta = WESTERN_DATA["planets"]
    houses_meta = WESTERN_DATA["houses"]

    asc_sign = western["ascendant_sign"]
    planet_list = MAIN_PLANETS if depth == "comprehensive" else PERSONAL_PLANETS

    planet_rows = []
    for pname in planet_list:
        pdata = western["planets"][pname]
        sign_info = signs[pdata["sign"]]
        planet_rows.append({
            "planet": pname,
            "sign": pdata["sign"],
            "degree": fmt_deg(pdata["deg_in_sign"]),
            "house": pdata["house"],
            "house_name": houses_meta[str(pdata["house"])]["name"],
            "keyword": planets_meta[pname]["keyword"],
            "text": planets_meta[pname]["comprehensive" if depth == "comprehensive" else "concise"] + " In " + pdata["sign"] + ", this plays out through " + sign_info["keyword"].lower() + ".",
        })

    aspects = western.get("aspects", [])
    aspect_meta = WESTERN_DATA["aspects"]
    top_aspects = aspects if depth == "comprehensive" else aspects[:4]
    aspect_rows = [{
        "text": f"{a['planet_a']} {a['aspect']} {a['planet_b']} (orb {a['orb']}\u00b0) \u2014 {aspect_meta[a['aspect']]}"
    } for a in top_aspects]

    return {
        "ascendant_sign": asc_sign,
        "ascendant_degree": fmt_deg(western["ascendant_deg_in_sign"]),
        "ascendant_text": signs[asc_sign]["comprehensive" if depth == "comprehensive" else "concise"],
        "midheaven_sign": western.get("midheaven_sign"),
        "midheaven_degree": fmt_deg(western.get("midheaven_deg_in_sign", 0)),
        "planets": planet_rows,
        "aspects": aspect_rows,
        "show_houses": depth == "comprehensive",
    }


def build_vedic_section(vedic: dict, depth: str) -> dict:
    naks = VEDIC_NAKSHATRAS
    planet_list = MAIN_PLANETS if depth == "comprehensive" else ["Sun", "Moon"]

    asc_nak = naks[vedic["ascendant_nakshatra_idx"]]
    planet_rows = []
    for pname in planet_list:
        pdata = vedic["planets"][pname]
        nak = naks[pdata["nakshatra_idx"]]
        planet_rows.append({
            "planet": pname,
            "sign": pdata["sign"],
            "degree": fmt_deg(pdata["deg_in_sign"]),
            "house": pdata["house"],
            "nakshatra": nak["name"],
            "nakshatra_lord": nak["ruler"],
            "nakshatra_deity": nak["deity"],
            "pada": pdata["pada"],
            "navamsa_sign": pdata["navamsa_sign"],
            "theme": nak["theme"],
        })

    timeline = vedic["dasha_timeline"]
    dasha_rows = timeline if depth == "comprehensive" else timeline[:3]
    dasha_meta = VEDIC_DATA["dasha_lord_meanings"]
    dasha_rows_fmt = [{
        "lord": d["lord"],
        "start": d["start"][:10],
        "end": d["end"][:10],
        "years": d["years"],
        "partial": d["partial_at_birth"],
        "meaning": dasha_meta.get(d["lord"], ""),
    } for d in dasha_rows]

    return {
        "ayanamsa": round(vedic["ayanamsa"], 2),
        "ascendant_sign": vedic["ascendant_sign"],
        "ascendant_degree": fmt_deg(vedic["ascendant_deg_in_sign"]),
        "ascendant_nakshatra": asc_nak["name"],
        "ascendant_pada": vedic["ascendant_pada"],
        "ascendant_theme": asc_nak["theme"],
        "rashi_theme": VEDIC_DATA["rashi_vedic_themes"].get(vedic["ascendant_sign"], ""),
        "planets": planet_rows,
        "dasha_timeline": dasha_rows_fmt,
        "show_navamsa": depth == "comprehensive",
    }


NUMEROLOGY_LABELS = {
    "life_path": "Life Path", "expression": "Expression", "soul_urge": "Soul Urge",
    "personality": "Personality", "birthday": "Birthday", "maturity": "Maturity",
}


def build_numerology_section(profile: dict, depth: str) -> dict:
    numbers = NUMEROLOGY_DATA["numbers"]
    roles = NUMEROLOGY_DATA["roles"]

    def entry(key, role_key):
        num = profile[key]["number"]
        meta = numbers[str(num)]
        return {
            "number": num, "is_master": profile[key]["is_master"], "label": NUMEROLOGY_LABELS[key],
            "role_text": roles[role_key], "keyword": meta["keyword"],
            "text": meta["comprehensive" if depth == "comprehensive" else "concise"],
        }

    core = {
        "life_path": entry("life_path", "life_path"),
        "expression": entry("expression", "expression"),
        "soul_urge": entry("soul_urge", "soul_urge"),
        "personality": entry("personality", "personality"),
    }
    extra = {}
    if depth == "comprehensive":
        extra["birthday"] = entry("birthday", "birthday")
        extra["maturity"] = entry("maturity", "maturity")

    pm = profile["psychomatrix"]
    from numerology import PSYCHOMATRIX_CELLS
    grid_order = [1, 4, 7, 2, 5, 8, 3, 6, 9]  # row-major per printed layout
    grid = [{
        "cell": c, "count": pm["counts"][str(c)],
        "label": PSYCHOMATRIX_CELLS[str(c)]["label"],
        "theme": PSYCHOMATRIX_CELLS[str(c)]["theme"],
    } for c in grid_order]

    return {"core": core, "extra": extra, "psychomatrix_grid": grid, "show_extra": depth == "comprehensive"}


def build_human_design_section(hd: dict, depth: str) -> dict:
    type_meta = HD_DATA["types"][hd["type"]]
    centers_meta = HD_DATA["centers"]

    defined_center_rows = [{"name": c, "theme": centers_meta[c]["theme"], "text": centers_meta[c]["defined"]} for c in hd["defined_centers"]]
    undefined_center_rows = [{"name": c, "theme": centers_meta[c]["theme"], "text": centers_meta[c]["open"]} for c in hd["undefined_centers"]]

    channel_rows = [{
        "name": ch["name"], "gates": ch["gates"], "centers": ch["centers"],
        "circuit": ch["circuit"], "keynote": ch["keynote"],
    } for ch in hd["defined_channels"]]

    gate_rows = []
    if depth == "comprehensive":
        gates_meta = HD_DATA["gates"]
        for g in hd["activated_gates"]:
            gm = gates_meta.get(str(g), {})
            gate_rows.append({"gate": g, "name": gm.get("name"), "center": gm.get("center"), "keynote": gm.get("keynote")})

    return {
        "type": hd["type"], "strategy": hd["strategy"], "authority": hd["authority"],
        "profile": hd["profile"], "definition": hd["definition"],
        "signature": type_meta.get("signature"), "not_self_theme": type_meta.get("not_self_theme"),
        "profile_line_meanings": hd["profile_line_meanings"],
        "defined_centers": defined_center_rows, "undefined_centers": undefined_center_rows,
        "channels": channel_rows, "gates": gate_rows,
        "cross_gates": hd["cross_gates"], "cross_angle": hd["cross_angle"],
        "show_gates": depth == "comprehensive",
    }


def build_gene_keys_section(gk: dict, depth: str) -> dict:
    spheres = gk["spheres"]
    groups = gk["sequence_groups"]

    def sphere_row(name):
        s = spheres[name]
        return {"name": name, "gate": s["gate"], "line": s["line"], "shadow": s["shadow"],
                "gift": s["gift"], "siddhi": s["siddhi"], "keynote": s["keynote"]}

    activation = [sphere_row(n) for n in groups["Activation Sequence"]]
    venus = [sphere_row(n) for n in groups["Venus Sequence"]] if depth == "comprehensive" else []
    pearl = [sphere_row(n) for n in groups["Pearl Sequence"]] if depth == "comprehensive" else []
    extra = [sphere_row(n) for n in groups["Additional Spheres"]] if depth == "comprehensive" else []

    return {"activation": activation, "venus": venus, "pearl": pearl, "extra": extra, "show_extended": depth == "comprehensive"}


def build_integration_section(numerology_sec, western_sec, hd_sec, gk_sec, vedic_sec) -> dict:
    """Deterministic, rule-based cross-system synthesis (no external calls)."""
    life_path = numerology_sec["core"]["life_path"]["number"]
    sun_sign = next((p for p in western_sec["planets"] if p["planet"] == "Sun"), None)
    hd_type = hd_sec["type"]
    lifes_work = gk_sec["activation"][0] if gk_sec["activation"] else None

    lines = []
    if sun_sign:
        lines.append(
            f"Your Life Path {life_path} and Sun in {sun_sign['sign']} point toward a shared theme: "
            f"the numerology of {numerology_sec['core']['life_path']['keyword'].lower()} echoed through "
            f"the astrological drive to express {sun_sign['keyword'].lower()}."
        )
    lines.append(
        f"As a {hd_type}, your Strategy of \u201c{hd_sec['strategy']}\u201d is best paired with your "
        f"{hd_sec['authority']}, giving you a concrete, body-based way to act on the themes surfacing "
        f"across your other systems rather than relying on the mind alone."
    )
    if lifes_work:
        lines.append(
            f"Your Gene Keys Life's Work (Gate {lifes_work['gate']}.{lifes_work['line']}) moves from the shadow of "
            f"{lifes_work['shadow']} toward the gift of {lifes_work['gift']} \u2014 a useful lens for "
            f"understanding the growth arc implied by your Life Path and Sun placement together."
        )
    lines.append(
        f"In the Vedic system, your current {vedic_sec['dasha_timeline'][0]['lord']} Mahadasha colors the "
        f"present chapter of life: {vedic_sec['dasha_timeline'][0]['meaning']}"
    )
    return {"paragraphs": lines}
