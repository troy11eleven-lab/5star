"""
Generates inline SVG/HTML visual charts for the PDF report:
1. Combined Western/Vedic astrological wheel (dual-ring, with ascendants)
2. Human Design bodygraph (nine centers, defined/undefined, channels)
3. Gene Keys Activation Sequence (shadow -> gift -> siddhi bands)

All charts are computed dynamically from a given person's chart data so they
work for any birth data, not just a fixed example. Colors are drawn from the
report's own palette (navy / gold / violet / parchment) defined in report.css.
"""
import math

PLANET_GLYPHS = {
    "Sun": "\u2609", "Moon": "\u263d", "Mercury": "\u263f", "Venus": "\u2640",
    "Mars": "\u2642", "Jupiter": "\u2643", "Saturn": "\u2644", "Uranus": "\u2645",
    "Neptune": "\u2646", "Pluto": "\u2647", "True Node": "\u260a", "Ketu": "\u260b",
}

SIGN_ABBR = ["ARI", "TAU", "GEM", "CAN", "LEO", "VIR",
             "LIB", "SCO", "SAG", "CAP", "AQU", "PIS"]

CORE_PLANETS = ["Saturn", "Mercury", "Moon", "Mars", "Sun", "Venus", "Jupiter", "Pluto", "Uranus", "Neptune"]

GOLD = "#C9A24B"
GOLD_LIGHT = "#E4C77A"
VIOLET = "#6E5A9E"
NAVY = "#14172A"
INK = "#221F2E"
INK_MUTED = "#5C5768"
BORDER = "#DED5BE"
PARCHMENT_ALT = "#F1ECDD"


def _pt(lon_deg, r, cx, cy):
    a = math.radians(lon_deg - 90)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def _declutter(items, min_gap_deg=7.5, step=11, base_cap=999):
    """items: list of dicts with 'lon'. Adds 'r_offset' to push overlapping
    planets outward in longitude order."""
    items = sorted(items, key=lambda p: p["lon"])
    last_lon = None
    offset = 0
    for it in items:
        if last_lon is not None:
            gap = (it["lon"] - last_lon) % 360
            if gap < min_gap_deg:
                offset += step
            else:
                offset = 0
        it["r_offset"] = min(offset, base_cap)
        last_lon = it["lon"]
    return items


def build_wheel_svg(western: dict, vedic: dict) -> str:
    """Combined dual-ring astrological wheel: outer gold ring = Western
    (tropical), inner teal ring = Vedic (sidereal). western/vedic are the
    'western'/'vedic' sub-dicts from astro_engine.full_chart()."""
    cx, cy = 260, 260
    r_outer, r_outer_in = 245, 205
    r_west_base, r_west_cap = 180, 202
    r_mid_out, r_mid_in = 165, 132
    r_vedic_base, r_vedic_cap = 138, 158
    r_inner = 112

    parts = []
    parts.append(f'<svg viewBox="0 0 520 520" width="380" height="380" role="img" '
                 f'style="display:block;margin:0 auto;">')
    parts.append('<title>Combined Western and Vedic astrological wheel</title>')
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r_outer}" fill="none" stroke="{BORDER}" stroke-width="1"/>')
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r_outer_in}" fill="none" stroke="{BORDER}" stroke-width="0.75"/>')
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r_mid_out}" fill="none" stroke="{BORDER}" stroke-width="0.75"/>')
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r_mid_in}" fill="none" stroke="{BORDER}" stroke-width="0.75"/>')
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r_inner}" fill="{PARCHMENT_ALT}" stroke="{BORDER}" stroke-width="0.75"/>')

    # 12 sign ticks + glyphs on outer ring
    for i in range(12):
        lon = i * 30 + 15
        x1, y1 = _pt(i * 30, r_outer_in, cx, cy)
        x2, y2 = _pt(i * 30, r_outer, cx, cy)
        parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{BORDER}" stroke-width="0.75"/>')
        gx, gy = _pt(lon, (r_outer + r_outer_in) / 2, cx, cy)
        parts.append(f'<text x="{gx:.1f}" y="{gy:.1f}" font-size="7.5" letter-spacing="0.02em" fill="{INK_MUTED}" '
                     f'text-anchor="middle" dominant-baseline="central">{SIGN_ABBR[i]}</text>')
        x3, y3 = _pt(i * 30, r_mid_out, cx, cy)
        x4, y4 = _pt(i * 30, r_mid_in, cx, cy)
        parts.append(f'<line x1="{x3:.1f}" y1="{y3:.1f}" x2="{x4:.1f}" y2="{y4:.1f}" stroke="{BORDER}" stroke-width="0.5" opacity="0.6"/>')

    # Ascendant lines
    asc_w = western["ascendant"]
    asc_v = vedic["ascendant"]
    ax1, ay1 = _pt(asc_w, r_inner, cx, cy)
    ax2, ay2 = _pt(asc_w, r_outer, cx, cy)
    parts.append(f'<line x1="{ax1:.1f}" y1="{ay1:.1f}" x2="{ax2:.1f}" y2="{ay2:.1f}" stroke="{GOLD}" stroke-width="1.4"/>')
    lx, ly = _pt(asc_w, r_outer + 14, cx, cy)
    anchor = "start" if math.cos(math.radians(asc_w - 90)) >= 0 else "end"
    parts.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="10.5" fill="{GOLD}" text-anchor="{anchor}">ASC (W)</text>')

    vx1, vy1 = _pt(asc_v, r_inner, cx, cy)
    vx2, vy2 = _pt(asc_v, r_mid_out, cx, cy)
    parts.append(f'<line x1="{vx1:.1f}" y1="{vy1:.1f}" x2="{vx2:.1f}" y2="{vy2:.1f}" stroke="{VIOLET}" stroke-width="1.4"/>')

    # Western (tropical) planet markers - gold ring
    w_items = []
    for pname in CORE_PLANETS:
        if pname in western["planets"]:
            w_items.append({"planet": pname, "lon": western["planets"][pname]["lon"]})
    w_items = _declutter(w_items, step=10, base_cap=(r_west_cap - r_west_base))
    for it in w_items:
        r = min(r_west_base + it["r_offset"], r_west_cap)
        gx, gy = _pt(it["lon"], r, cx, cy)
        glyph = PLANET_GLYPHS.get(it["planet"], "?")
        parts.append(f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="10.5" fill="{GOLD}" opacity="0.16"/>')
        parts.append(f'<text x="{gx:.1f}" y="{gy:.1f}" font-size="12" fill="{GOLD}" '
                     f'text-anchor="middle" dominant-baseline="central">{glyph}</text>')

    # Vedic (sidereal) planet markers - violet ring
    v_items = []
    for pname in CORE_PLANETS:
        if pname in vedic["planets"]:
            v_items.append({"planet": pname, "lon": vedic["planets"][pname]["lon"]})
    v_items = _declutter(v_items, step=9, base_cap=(r_vedic_cap - r_vedic_base))
    for it in v_items:
        r = min(r_vedic_base + it["r_offset"], r_vedic_cap)
        gx, gy = _pt(it["lon"], r, cx, cy)
        glyph = PLANET_GLYPHS.get(it["planet"], "?")
        parts.append(f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="9.5" fill="{VIOLET}" opacity="0.16"/>')
        parts.append(f'<text x="{gx:.1f}" y="{gy:.1f}" font-size="11" fill="{VIOLET}" '
                     f'text-anchor="middle" dominant-baseline="central">{glyph}</text>')

    # Center summary
    w_sun = western["planets"]["Sun"]["sign"]
    v_sun = vedic["planets"]["Sun"]["sign"]
    parts.append(f'<text x="{cx}" y="{cy-14}" font-size="11" fill="{INK_MUTED}" text-anchor="middle">Sun</text>')
    parts.append(f'<text x="{cx}" y="{cy+8}" font-size="15" font-weight="600" fill="{NAVY}" text-anchor="middle">{w_sun} / {v_sun}</text>')
    parts.append(f'<text x="{cx}" y="{cy+26}" font-size="9.5" fill="{INK_MUTED}" text-anchor="middle">Western / Vedic</text>')

    # Legend
    parts.append(f'<text x="66" y="26" font-size="11.5" fill="{GOLD}" text-anchor="start">&#9679; Western (tropical)</text>')
    parts.append(f'<text x="66" y="44" font-size="11.5" fill="{VIOLET}" text-anchor="start">&#9679; Vedic (sidereal)</text>')

    parts.append('</svg>')
    return "".join(parts)


# ---------------------------------------------------------------------------
# Human Design bodygraph
# ---------------------------------------------------------------------------

_HD_CENTER_LAYOUT = {
    "Head":        {"pos": (260, 45),  "shape": "triangle_down", "size": 30},
    "Ajna":        {"pos": (260, 115), "shape": "triangle_down", "size": 34},
    "Throat":      {"pos": (260, 195), "shape": "square",        "size": 34},
    "G":           {"pos": (260, 285), "shape": "diamond",       "size": 38},
    "Heart":       {"pos": (355, 250), "shape": "triangle_left", "size": 26},
    "Spleen":      {"pos": (140, 330), "shape": "triangle_right","size": 32},
    "Solar Plexus":{"pos": (380, 330), "shape": "triangle_left", "size": 32},
    "Sacral":      {"pos": (260, 375), "shape": "square",        "size": 34},
    "Root":        {"pos": (260, 460), "shape": "square",        "size": 34},
}

_HD_SKELETON = [
    ("Head", "Ajna"), ("Ajna", "Throat"), ("Throat", "G"), ("Throat", "Heart"),
    ("Throat", "Solar Plexus"), ("Throat", "Spleen"), ("G", "Heart"), ("G", "Sacral"),
    ("G", "Spleen"), ("G", "Solar Plexus"), ("Spleen", "Sacral"), ("Spleen", "Root"),
    ("Solar Plexus", "Sacral"), ("Solar Plexus", "Root"), ("Sacral", "Root"), ("Heart", "Sacral"),
]

_DEFINED_FILL = "#20808D"


def _hd_shape(cx, cy, shape, size, fill, stroke, opacity=1.0):
    h = size
    if shape == "square":
        x, y = cx - h / 2, cy - h / 2
        return f'<rect x="{x:.1f}" y="{y:.1f}" width="{h}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="1" opacity="{opacity}"/>'
    if shape == "diamond":
        pts = f"{cx},{cy - h/2} {cx + h/2},{cy} {cx},{cy + h/2} {cx - h/2},{cy}"
        return f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="1" opacity="{opacity}"/>'
    if shape == "triangle_down":
        pts = f"{cx - h/2},{cy - h/2.2} {cx + h/2},{cy - h/2.2} {cx},{cy + h/2.2}"
        return f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="1" opacity="{opacity}"/>'
    if shape == "triangle_left":
        pts = f"{cx + h/2},{cy - h/2} {cx + h/2},{cy + h/2} {cx - h/2},{cy}"
        return f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="1" opacity="{opacity}"/>'
    if shape == "triangle_right":
        pts = f"{cx - h/2},{cy - h/2} {cx - h/2},{cy + h/2} {cx + h/2},{cy}"
        return f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="1" opacity="{opacity}"/>'
    return ""


def build_bodygraph_svg(hd: dict) -> str:
    """Nine-center Human Design bodygraph. hd = result of human_design.compute_human_design()."""
    defined_centers = set(hd["defined_centers"])
    defined_channel_center_pairs = set()
    for ch in hd["defined_channels"]:
        c1, c2 = ch["centers"]
        defined_channel_center_pairs.add(frozenset((c1, c2)))

    parts = []
    parts.append('<svg viewBox="0 0 520 500" width="330" height="317" role="img" '
                 f'style="display:block;margin:0 auto;">')
    parts.append('<title>Human Design bodygraph showing defined and undefined centers</title>')

    # skeleton lines (undefined connections, behind)
    for a, b in _HD_SKELETON:
        if frozenset((a, b)) in defined_channel_center_pairs:
            continue
        ax, ay = _HD_CENTER_LAYOUT[a]["pos"]
        bx, by = _HD_CENTER_LAYOUT[b]["pos"]
        parts.append(f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" stroke="{BORDER}" stroke-width="1" opacity="0.6"/>')

    # defined channels on top, colored
    for ch in hd["defined_channels"]:
        c1, c2 = ch["centers"]
        if c1 not in _HD_CENTER_LAYOUT or c2 not in _HD_CENTER_LAYOUT:
            continue
        ax, ay = _HD_CENTER_LAYOUT[c1]["pos"]
        bx, by = _HD_CENTER_LAYOUT[c2]["pos"]
        parts.append(f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" stroke="{_DEFINED_FILL}" stroke-width="5" opacity="0.9"/>')
        parts.append(f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" stroke="{GOLD}" stroke-width="1.6" opacity="0.95"/>')
        mx, my = (ax + bx) / 2, (ay + by) / 2
        gate_label = f'{ch["gates"][0]}\u2013{ch["gates"][1]}'
        parts.append(f'<text x="{mx + 16:.1f}" y="{my:.1f}" font-size="9.5" fill="{INK_MUTED}" text-anchor="start">{gate_label}</text>')

    # center shapes + labels
    label_overrides = {"Solar Plexus": "Solar Plexus"}
    for name, layout in _HD_CENTER_LAYOUT.items():
        cx, cy = layout["pos"]
        is_defined = name in defined_centers
        fill = _DEFINED_FILL if is_defined else PARCHMENT_ALT
        stroke = _DEFINED_FILL if is_defined else INK_MUTED
        parts.append(_hd_shape(cx, cy, layout["shape"], layout["size"], fill, stroke, 0.88 if is_defined else 1.0))

        label = label_overrides.get(name, name)
        tx, ty, anchor = cx, cy + layout["size"] / 2 + 13, "middle"
        if name == "Heart":
            tx, ty, anchor = cx + layout["size"] / 2 + 8, cy + 4, "start"
        elif name == "Spleen":
            tx, ty, anchor = cx - layout["size"] / 2 - 8, cy + 4, "end"
        elif name == "Solar Plexus":
            tx, ty, anchor = cx + layout["size"] / 2 + 8, cy + 4, "start"
        elif name == "Head":
            ty = cy - layout["size"] / 2 - 10
        text_color = INK if is_defined else INK_MUTED
        weight = 600 if is_defined else 400
        parts.append(f'<text x="{tx:.1f}" y="{ty:.1f}" font-size="12" font-weight="{weight}" '
                     f'fill="{text_color}" text-anchor="{anchor}">{label}</text>')

    parts.append('</svg>')
    return "".join(parts)


# ---------------------------------------------------------------------------
# Gene Keys Activation Sequence bands
# ---------------------------------------------------------------------------

def build_gene_keys_bands_html(gk: dict) -> str:
    """HTML shadow->gift->siddhi bands for the four Activation Sequence spheres.
    gk = result of gene_keys.compute_gene_keys()."""
    sphere_names = gk["sequence_groups"]["Activation Sequence"]
    rows = []
    for sname in sphere_names:
        s = gk["spheres"][sname]
        rows.append(f'''
    <div class="gk-band-card">
      <div class="gk-band-top">
        <span class="gk-band-title">{sname}</span>
        <span class="gk-band-meta">Gate {s["gate"]}.{s["line"]} &middot; {s["planet"]}</span>
      </div>
      <div class="gk-band-row">
        <span class="gk-pill">{s["shadow"]}</span>
        <span class="gk-arrow">&#8594;</span>
        <span class="gk-pill gk-pill-gift">{s["gift"]}</span>
        <span class="gk-arrow">&#8594;</span>
        <span class="gk-pill">{s["siddhi"]}</span>
      </div>
    </div>''')
    return "".join(rows)
