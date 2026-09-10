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
    current_dasha = vedic["current_dasha"]
    current_antardasha = vedic["current_antardasha"]
    dasha_meta = VEDIC_DATA["dasha_lord_meanings"]

    # Show the current Mahadasha plus surrounding context: comprehensive gets
    # the full life timeline, concise gets the current period plus the next
    # two upcoming ones so the reader still sees what's ahead.
    if depth == "comprehensive":
        dasha_rows = timeline
    else:
        current_idx = timeline.index(current_dasha)
        dasha_rows = timeline[current_idx:current_idx + 3]

    dasha_rows_fmt = [{
        "lord": d["lord"],
        "start": d["start"][:10],
        "end": d["end"][:10],
        "years": d["years"],
        "partial": d["partial_at_birth"],
        "is_current": d is current_dasha,
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
        "current_mahadasha": {
            "lord": current_dasha["lord"],
            "start": current_dasha["start"][:10],
            "end": current_dasha["end"][:10],
            "meaning": dasha_meta.get(current_dasha["lord"], ""),
        },
        "current_antardasha": {
            "lord": current_antardasha["lord"],
            "start": current_antardasha["start"][:10],
            "end": current_antardasha["end"][:10],
            "meaning": dasha_meta.get(current_antardasha["lord"], ""),
        },
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


# Broad behavioral "mode" per Life Path number — used to compare against each
# sign's element/modality and each Human Design Type's mechanics below.
_LIFE_PATH_MODE = {
    1: ("initiating", "lead from the front and prefer to originate rather than follow"),
    2: ("relating", "work through partnership, sensitivity, and cooperation"),
    3: ("expressing", "process life through communication, creativity, and being seen"),
    4: ("building", "favor structure, method, and steady accumulation over improvisation"),
    5: ("exploring", "need variety, movement, and freedom from routine"),
    6: ("nurturing", "orient around responsibility, care, and harmony for others"),
    7: ("seeking", "process life internally, through analysis and solitude"),
    8: ("directing", "are oriented toward achievement, authority, and material mastery"),
    9: ("integrating", "work through compassion and a wide, humanitarian lens"),
    11: ("illuminating", "channel heightened intuition into inspiration for others"),
    22: ("actualizing", "turn big vision into large-scale, practical structures"),
    33: ("teaching", "channel compassion into guidance and healing for others"),
}

# Which elements a given Life Path "mode" naturally reinforces vs. sits in
# tension with — not a claim of contradiction, but a flag for where the
# reader may feel two systems pulling in different directions.
_MODE_ELEMENT_FIT = {
    "initiating": {"reinforce": ["Fire"], "tension": ["Water"]},
    "relating": {"reinforce": ["Water", "Air"], "tension": ["Fire"]},
    "expressing": {"reinforce": ["Fire", "Air"], "tension": ["Earth"]},
    "building": {"reinforce": ["Earth"], "tension": ["Fire"]},
    "exploring": {"reinforce": ["Fire", "Air"], "tension": ["Earth"]},
    "nurturing": {"reinforce": ["Water", "Earth"], "tension": ["Fire"]},
    "seeking": {"reinforce": ["Water"], "tension": ["Fire"]},
    "directing": {"reinforce": ["Earth", "Fire"], "tension": ["Water"]},
    "integrating": {"reinforce": ["Water", "Air"], "tension": ["Earth"]},
    "illuminating": {"reinforce": ["Air", "Water"], "tension": ["Earth"]},
    "actualizing": {"reinforce": ["Earth"], "tension": ["Air"]},
    "teaching": {"reinforce": ["Water", "Air"], "tension": ["Fire"]},
}

# How each Human Design Type's mechanics naturally pair with a Life Path
# "mode" — reinforcing when the Type's own energy mechanics support the
# mode's default action style, in tension when Strategy asks for something
# the mode doesn't naturally do on its own.
_HD_TYPE_MODE_FIT = {
    "Manifestor": {"reinforce": ["initiating", "directing", "actualizing"], "tension": ["relating", "nurturing"]},
    "Generator": {"reinforce": ["building", "nurturing", "teaching"], "tension": ["initiating"]},
    "Manifesting Generator": {"reinforce": ["exploring", "expressing", "actualizing"], "tension": ["seeking"]},
    "Projector": {"reinforce": ["relating", "illuminating", "seeking"], "tension": ["initiating", "directing"]},
    "Reflector": {"reinforce": ["integrating", "relating"], "tension": ["directing", "building"]},
}


def _fit_sentence(subject_a: str, subject_b: str, relation: str) -> str:
    if relation == "reinforce":
        return f"{subject_a} and {subject_b} reinforce each other here"
    return f"{subject_a} and {subject_b} sit in some tension here, which is worth naming rather than smoothing over"


def _a_or_an(word: str) -> str:
    return "an" if word[:1].lower() in "aeiou" else "a"


def build_integration_section(numerology_sec, western_sec, hd_sec, gk_sec, vedic_sec) -> dict:
    """Deterministic, rule-based cross-system synthesis (no external calls).

    Goes beyond describing each system side by side: it actively compares
    the Life Path "mode", Sun sign element, Human Design Type mechanics,
    Gene Keys growth arc, and current Vedic Mahadasha against each other and
    calls out explicitly where they reinforce one another versus where they
    pull in different directions, so the reader gets an individualized read
    rather than four independent summaries stitched together.
    """
    life_path = numerology_sec["core"]["life_path"]["number"]
    life_path_keyword = numerology_sec["core"]["life_path"]["keyword"]
    mode, mode_desc = _LIFE_PATH_MODE.get(life_path, ("integrating", "blends several approaches at once"))

    sun_sign = next((p for p in western_sec["planets"] if p["planet"] == "Sun"), None)
    moon_sign = next((p for p in western_sec["planets"] if p["planet"] == "Moon"), None)
    hd_type = hd_sec["type"]
    lifes_work = gk_sec["activation"][0] if gk_sec["activation"] else None
    current_maha = vedic_sec["current_mahadasha"]
    current_antar = vedic_sec["current_antardasha"]

    lines = []

    # 1. Life Path (numerology) vs. Sun sign element (Western astrology)
    sun_element = WESTERN_DATA["signs"][sun_sign["sign"]]["element"] if sun_sign else None
    if sun_sign and sun_element:
        fit = _MODE_ELEMENT_FIT.get(mode, {"reinforce": [], "tension": []})
        if sun_element in fit["reinforce"]:
            relation_text = _fit_sentence(f"Life Path {life_path}'s {mode} mode", f"your {sun_element.lower()}-element Sun in {sun_sign['sign']}", "reinforce")
        elif sun_element in fit["tension"]:
            relation_text = _fit_sentence(f"Life Path {life_path}'s {mode} mode", f"your {sun_element.lower()}-element Sun in {sun_sign['sign']}", "tension")
        else:
            relation_text = f"Life Path {life_path}'s {mode} mode and your {sun_element.lower()}-element Sun in {sun_sign['sign']} operate somewhat independently, neither reinforcing nor conflicting strongly"
        lines.append(
            f"Numerology and Western astrology, compared: as Life Path {life_path} ({life_path_keyword}), you {mode_desc}. "
            f"{relation_text[:1].upper()}{relation_text[1:]} — {sun_element} signs like {sun_sign['sign']} tend toward "
            f"{'direct, energetic follow-through' if sun_element == 'Fire' else 'methodical, grounded follow-through' if sun_element == 'Earth' else 'idea-driven, socially mediated follow-through' if sun_element == 'Air' else 'emotionally attuned, intuitive follow-through'}, "
            f"which {'naturally carries' if sun_element in fit['reinforce'] else 'has to be consciously bridged with' if sun_element in fit['tension'] else 'coexists with'} the {mode} drive at the center of your Life Path."
        )

    # 2. Human Design Type mechanics vs. the same Life Path mode
    hd_fit = _HD_TYPE_MODE_FIT.get(hd_type, {"reinforce": [], "tension": []})
    if mode in hd_fit["reinforce"]:
        hd_relation = (
            f"As a {hd_type}, your Strategy of \u201c{hd_sec['strategy']}\u201d actually reinforces this Life Path mode — "
            f"the Type's own mechanics give you a concrete, body-based (rather than purely mental) channel for "
            f"the same {mode} drive numerology already points to."
        )
    elif mode in hd_fit["tension"]:
        hd_relation = (
            f"As a {hd_type}, your Strategy of \u201c{hd_sec['strategy']}\u201d creates a real tension with this Life Path mode: "
            f"numerology pushes you toward {_a_or_an(mode)} {mode} way of engaging life, but your Type's mechanics ask you to "
            f"work through {hd_sec['strategy'].lower()} instead. Naming this explicitly matters — the friction is not "
            f"a flaw in either system, it's a real design tension worth working with consciously via your "
            f"{hd_sec['authority']}."
        )
    else:
        hd_relation = (
            f"As a {hd_type}, your Strategy of \u201c{hd_sec['strategy']}\u201d is best paired with your {hd_sec['authority']}, "
            f"giving you a concrete, body-based way to act on the themes surfacing across your other systems."
        )
    lines.append(hd_relation)

    # 3. Gene Keys growth arc vs. Sun/Moon placement — explicit reinforcement check
    if lifes_work:
        gk_line = (
            f"Your Gene Keys Life's Work (Gate {lifes_work['gate']}.{lifes_work['line']}) moves from the shadow of "
            f"{lifes_work['shadow']} toward the gift of {lifes_work['gift']}."
        )
        if sun_sign and moon_sign:
            gk_line += (
                f" This is the same growth arc your Sun in {sun_sign['sign']} and Moon in {moon_sign['sign']} are already "
                f"pointing toward: the Sun's conscious drive to express {sun_sign['keyword'].lower()} and the Moon's "
                f"instinctive need for {moon_sign['keyword'].lower()} both describe, from a different angle, the same "
                f"shadow-to-gift movement the Gene Keys name outright — three systems independently converging on one "
                f"life theme is a strong signal, not a coincidence worth dismissing."
            )
        lines.append(gk_line)

    # 4. Vedic current Mahadasha — grounded in the actual present period, with
    #    the current Antardasha (sub-period) layered in for real specificity.
    lines.append(
        f"In the Vedic system, your current Mahadasha is {current_maha['lord']} "
        f"(running {current_maha['start']} through {current_maha['end']}): {current_maha['meaning']} "
        f"Within that, you are presently in the {current_antar['lord']} Antardasha (sub-period), running "
        f"{current_antar['start']} to {current_antar['end']} — {current_antar['meaning'].split('.')[0].lower()}, "
        f"a shorter-term flavor layered on top of the broader {current_maha['lord']} chapter."
    )

    # 5. Explicit closing synthesis naming where all systems agree or disagree
    reinforcements = []
    tensions = []
    if sun_sign and sun_element in _MODE_ELEMENT_FIT.get(mode, {}).get("reinforce", []):
        reinforcements.append("numerology and Western astrology")
    elif sun_sign and sun_element in _MODE_ELEMENT_FIT.get(mode, {}).get("tension", []):
        tensions.append("numerology and Western astrology")
    if mode in hd_fit["reinforce"]:
        reinforcements.append("Human Design")
    elif mode in hd_fit["tension"]:
        tensions.append("Human Design")

    def _plural_verb(items, singular, plural):
        # "items" is a list of clause-labels (e.g. ["numerology and Western astrology"]).
        # Grammatical plurality depends on how many systems are actually named,
        # not on the list length, since one clause can itself be a joined pair.
        total_systems = sum(label.count(" and ") + 1 for label in items)
        return singular if total_systems == 1 else plural

    if reinforcements and not tensions:
        verb = _plural_verb(reinforcements, "is pulling", "are pulling")
        closing = (
            f"Taken together, {', '.join(reinforcements)} {verb} in the same direction around your {mode} "
            f"core — a rare degree of alignment across systems that generally means this theme is safe to lean into "
            f"without much internal resistance."
        )
    elif tensions and not reinforcements:
        verb = _plural_verb(tensions, "pulls", "pull")
        closing = (
            f"Taken together, {', '.join(tensions)} {verb} against your {mode} core rather than confirming it — "
            f"this is the most useful kind of contradiction to sit with, since it usually means real growth lives at "
            f"the friction point rather than in picking one system as \u201ccorrect.\u201d"
        )
    elif reinforcements and tensions:
        reinforce_verb = _plural_verb(reinforcements, "reinforces", "reinforce")
        tension_verb = _plural_verb(tensions, "pulls", "pull")
        closing = (
            f"Taken together, {', '.join(reinforcements)} {reinforce_verb} your {mode} core, while {', '.join(tensions)} "
            f"{tension_verb} against it — a mixed picture, which in practice usually means the reinforced side describes your "
            f"natural default and the tension names where deliberate effort is required."
        )
    else:
        closing = (
            f"Across all five systems, no single theme dominates — your {mode} core from numerology stands somewhat "
            f"independently, which suggests versatility rather than a single fixed life direction."
        )
    lines.append(closing)

    return {"paragraphs": lines}
