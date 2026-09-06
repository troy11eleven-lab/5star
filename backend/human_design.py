"""
Human Design calculation module: gate/line mapping from the Rave Mandala wheel,
Type/Authority/Profile/Definition determination via graph analysis of defined channels.
"""
import json
import os
from collections import defaultdict, deque

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
with open(os.path.join(DATA_DIR, "human_design.json")) as f:
    HD_DATA = json.load(f)

GATES = HD_DATA["gates"]
CHANNELS = HD_DATA["channels"]
CENTERS = HD_DATA["centers"]
TYPES = HD_DATA["types"]
AUTHORITY_HIERARCHY = HD_DATA["authority_hierarchy"]
PROFILE_LINES = HD_DATA["profile_lines"]

# Rave Mandala fixed gate wheel — verified against multiple independent sources:
# Gate 41 Line 1 begins at 302.000 degrees tropical longitude; each gate spans 5.625deg.
GATE_SEQUENCE = [41, 19, 13, 49, 30, 55, 37, 63, 22, 36, 25, 17, 21, 51, 42, 3, 27, 24, 2, 23,
                  8, 20, 16, 35, 45, 12, 15, 52, 39, 53, 62, 56, 31, 33, 7, 4, 29, 59, 40, 64,
                  47, 6, 46, 18, 48, 57, 32, 50, 28, 44, 1, 43, 14, 34, 9, 5, 26, 11, 10, 58,
                  38, 54, 61, 60]
START_DEGREE = 302.0
GATE_SPAN = 5.625
LINE_SPAN = GATE_SPAN / 6.0

MOTOR_CENTERS = {"Sacral", "Heart", "Solar Plexus", "Root"}

CELESTIAL_BODIES = ["Sun", "Earth", "Moon", "North Node", "South Node", "Mercury",
                     "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]


def gate_line_at(lon: float):
    offset = (lon - START_DEGREE) % 360
    idx = int(offset // GATE_SPAN) % 64
    gate = GATE_SEQUENCE[idx]
    within = offset - idx * GATE_SPAN
    line = int(within // LINE_SPAN) + 1
    line = min(line, 6)
    return gate, line


def positions_to_activations(tropical_positions: dict):
    """Expand raw planet longitudes into the 13 Human Design celestial bodies and
    return {body_name: (gate, line)}."""
    sun_lon = tropical_positions["Sun"]
    node_lon = tropical_positions["True Node"]
    bodies = {
        "Sun": sun_lon,
        "Earth": (sun_lon + 180) % 360,
        "Moon": tropical_positions["Moon"],
        "North Node": node_lon,
        "South Node": (node_lon + 180) % 360,
        "Mercury": tropical_positions["Mercury"],
        "Venus": tropical_positions["Venus"],
        "Mars": tropical_positions["Mars"],
        "Jupiter": tropical_positions["Jupiter"],
        "Saturn": tropical_positions["Saturn"],
        "Uranus": tropical_positions["Uranus"],
        "Neptune": tropical_positions["Neptune"],
        "Pluto": tropical_positions["Pluto"],
    }
    return {name: gate_line_at(lon) for name, lon in bodies.items()}


def compute_human_design(personality_positions: dict, design_positions: dict):
    personality = positions_to_activations(personality_positions)
    design = positions_to_activations(design_positions)

    activated_gates = set()
    for body, (gate, line) in personality.items():
        activated_gates.add(gate)
    for body, (gate, line) in design.items():
        activated_gates.add(gate)

    # Determine defined channels + centers
    defined_channels = []
    center_edges = defaultdict(set)  # center graph adjacency for connectivity
    defined_centers = set()
    for ch in CHANNELS:
        g1, g2 = ch["gates"]
        if g1 in activated_gates and g2 in activated_gates:
            defined_channels.append(ch)
            c1, c2 = ch["centers"]
            defined_centers.add(c1)
            defined_centers.add(c2)
            center_edges[c1].add(c2)
            center_edges[c2].add(c1)

    # Connected components among defined centers (for Definition type)
    visited = set()
    components = []
    for center in defined_centers:
        if center in visited:
            continue
        comp = set()
        queue = deque([center])
        visited.add(center)
        while queue:
            cur = queue.popleft()
            comp.add(cur)
            for nb in center_edges[cur]:
                if nb not in visited:
                    visited.add(nb)
                    queue.append(nb)
        components.append(comp)

    n_components = len(components)
    if not defined_centers:
        definition = "No Definition"
    elif n_components == 1:
        definition = "Single Definition"
    elif n_components == 2:
        definition = "Split Definition"
    elif n_components == 3:
        definition = "Triple Split Definition"
    else:
        definition = "Quadruple Split Definition"

    # Motor-to-Throat connectivity check (any defined motor center reachable from Throat
    # through the defined-center graph)
    motor_to_throat = False
    if "Throat" in defined_centers:
        reachable = set()
        queue = deque(["Throat"])
        reachable.add("Throat")
        while queue:
            cur = queue.popleft()
            for nb in center_edges[cur]:
                if nb not in reachable:
                    reachable.add(nb)
                    queue.append(nb)
        motor_to_throat = any(m in reachable and m != "Throat" for m in MOTOR_CENTERS)
        # also true if Throat itself is a motor-adjacent via direct sacral etc already covered by reachable set

    sacral_defined = "Sacral" in defined_centers

    if not defined_centers:
        hd_type = "Reflector"
    elif sacral_defined and motor_to_throat:
        hd_type = "Manifesting Generator"
    elif sacral_defined:
        hd_type = "Generator"
    elif motor_to_throat:
        hd_type = "Manifestor"
    else:
        hd_type = "Projector"

    # Authority: first defined center in hierarchy order (map hierarchy labels to center keys)
    hierarchy_map = [
        ("Solar Plexus (Emotional)", "Solar Plexus", "Emotional Authority"),
        ("Sacral", "Sacral", "Sacral Authority"),
        ("Spleen (Splenic)", "Spleen", "Splenic Authority"),
        ("Heart (Ego/Willpower)", "Heart", "Ego Authority"),
        ("G Center (Self-Projected)", "G", "Self-Projected Authority"),
        ("Ajna (Mental)", "Ajna", "Mental (Environmental) Authority"),
    ]
    authority = None
    for _, center_key, label in hierarchy_map:
        if center_key in defined_centers:
            authority = label
            break
    if authority is None:
        authority = "Lunar Authority" if hd_type == "Reflector" else "Environmental / Outer Authority"

    # Strategy from type
    strategy_map = {
        "Manifestor": "Inform before acting",
        "Generator": "Respond",
        "Manifesting Generator": "Respond, then inform",
        "Projector": "Wait for the invitation",
        "Reflector": "Wait a full lunar cycle (~28 days) before major decisions",
    }

    # Profile from Sun lines
    p_line = personality["Sun"][1]
    d_line = design["Sun"][1]
    profile = f"{p_line}/{d_line}"

    # Cross gates (Sun/Earth, personality + design) for Incarnation Cross description
    cross_gates = {
        "personality_sun": personality["Sun"][0],
        "personality_earth": personality["Earth"][0],
        "design_sun": design["Sun"][0],
        "design_earth": design["Earth"][0],
    }
    # Angle classification (simplified): compare profile line pairing convention
    if p_line in (1, 2, 3, 4) and d_line in (1, 2, 3, 4):
        angle = "Right Angle (Cross of Incarnation)"
    elif {p_line, d_line} & {4, 1} and {p_line, d_line} & {5, 6}:
        angle = "Left Angle (Cross of Obligation)" if (p_line in (5, 6) or d_line in (5, 6)) else "Right Angle"
        angle = "Left Angle (Cross of Obligation)"
    else:
        angle = "Juxtaposition Cross"
    # Simplify per standard rule: profiles 1/3,1/4,2/4,2/5,3/5,3/6,4/6 = Right Angle;
    # 4/1,5/1,5/2,6/2,6/3,1/3(dup) etc conventionally, and 5/1,6/2,6/3 style = Left Angle;
    # exact 1/4,2/5,3/6 reversed pairs = Juxtaposition. Use a pragmatic simplified rule:
    line_sum = p_line + d_line
    if profile in ("1/4", "2/5", "3/6"):
        angle = "Juxtaposition Cross"
    elif p_line <= d_line:
        angle = "Right Angle (Cross of Incarnation)"
    else:
        angle = "Left Angle (Cross of Obligation)"

    return {
        "personality_activations": personality,
        "design_activations": design,
        "type": hd_type,
        "strategy": strategy_map[hd_type],
        "authority": authority,
        "profile": profile,
        "profile_line_meanings": [PROFILE_LINES.get(str(p_line), ""), PROFILE_LINES.get(str(d_line), "")],
        "definition": definition,
        "defined_centers": sorted(defined_centers),
        "undefined_centers": sorted(set(CENTERS.keys()) - defined_centers),
        "defined_channels": defined_channels,
        "cross_gates": cross_gates,
        "cross_angle": angle,
        "activated_gates": sorted(activated_gates),
    }
