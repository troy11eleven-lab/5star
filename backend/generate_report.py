"""End-to-end orchestration: raw inputs -> computed chart data -> assembled content -> PDF.

Split into two phases so the web app can show an instant chart preview before
committing to full PDF rendering:
  1. build_context()  - runs the (relatively slow) geocoding + ephemeris +
     content-assembly pipeline once, returns a dict with everything needed
     for both the on-screen preview and the PDF, including the three
     standalone chart SVG/HTML strings.
  2. render(context, output_path) - takes that context and writes the PDF.

generate() is kept as a convenience wrapper (build_context + render) for
CLI/script use and backward compatibility.
"""
import astro_engine
import human_design
import gene_keys
import numerology
import report_content as rc
import chart_visuals as cv
from render_pdf import render_report_pdf


def build_context(name: str, birth_date: str, birth_time: str, birth_place: str, depth: str) -> dict:
    """birth_date: 'YYYY-MM-DD', birth_time: 'HH:MM' (24h), depth: 'concise'|'comprehensive'."""
    depth = depth if depth in ("concise", "comprehensive") else "concise"

    chart = astro_engine.full_chart(name, birth_date, birth_time, birth_place)
    day, month, year = int(birth_date[8:10]), int(birth_date[5:7]), int(birth_date[0:4])
    nprofile = numerology.full_numerology_profile(name, day, month, year)
    hd = human_design.compute_human_design(
        chart["human_design_raw"]["personality_positions"],
        chart["human_design_raw"]["design_positions"],
    )
    gk = gene_keys.compute_gene_keys(
        chart["human_design_raw"]["personality_positions"],
        chart["human_design_raw"]["design_positions"],
    )

    w = rc.build_western_section(chart["western"], depth)
    v = rc.build_vedic_section(chart["vedic"], depth)
    n = rc.build_numerology_section(nprofile, depth)
    h = rc.build_human_design_section(hd, depth)
    g = rc.build_gene_keys_section(gk, depth)
    integration = rc.build_integration_section(n, w, h, g, v)

    wheel_svg = cv.build_wheel_svg(chart["western"], chart["vedic"])
    bodygraph_svg = cv.build_bodygraph_svg(hd)
    gk_bands_html = cv.build_gene_keys_bands_html(gk)

    from datetime import datetime as _dt
    bdate = _dt.strptime(birth_date, "%Y-%m-%d")
    try:
        btime = _dt.strptime(birth_time, "%H:%M")
        time_pretty = btime.strftime("%-I:%M %p")
    except ValueError:
        time_pretty = birth_time

    birth_meta = chart["birth"]

    def _fmt_coord(value: float, pos_label: str, neg_label: str) -> str:
        label = pos_label if value >= 0 else neg_label
        return f"{abs(value):.4f}\u00b0 {label}"

    offset_hours = birth_meta["utc_offset_hours"]
    offset_sign = "+" if offset_hours >= 0 else "-"
    offset_h = int(abs(offset_hours))
    offset_m = int(round((abs(offset_hours) - offset_h) * 60))
    utc_offset_pretty = f"UTC{offset_sign}{offset_h:02d}:{offset_m:02d}"

    calc = {
        "birth_place": birth_meta["place"],
        "latitude": _fmt_coord(birth_meta["lat"], "N", "S"),
        "longitude": _fmt_coord(birth_meta["lon"], "E", "W"),
        "timezone": birth_meta["tz_name"],
        "utc_offset": utc_offset_pretty,
        "is_dst": birth_meta["is_dst"],
        "utc_datetime": birth_meta["utc_iso"][:16].replace("T", " ") + " UTC",
        "western_house_system": birth_meta["western_house_system"],
        "vedic_house_system": birth_meta["vedic_house_system"],
        "ayanamsa_name": birth_meta["ayanamsa_name"],
        "ayanamsa_value": v["ayanamsa"],
    }

    context = {
        "name": name,
        "birth_date_pretty": bdate.strftime("%B %-d, %Y"),
        "birth_time_pretty": time_pretty,
        "birth_place": chart["birth"]["place"],
        "depth": depth,
        "w": w, "v": v, "n": n, "h": h, "gk": g,
        "integration": integration,
        "calc": calc,
        "wheel_svg": wheel_svg,
        "bodygraph_svg": bodygraph_svg,
        "gk_bands_html": gk_bands_html,
    }
    return context


def render(context: dict, output_path: str):
    return render_report_pdf(context, output_path)


def generate(name: str, birth_date: str, birth_time: str, birth_place: str, depth: str, output_path: str):
    """Convenience wrapper: build_context() + render(). Used by CLI/tests."""
    context = build_context(name, birth_date, birth_time, birth_place, depth)
    return render(context, output_path)


if __name__ == "__main__":
    import sys
    out = generate(
        "Troy Clayton Kearl", "1968-07-24", "09:11", "Ogden, Utah, USA",
        sys.argv[1] if len(sys.argv) > 1 else "concise",
        f"/home/user/workspace/celestial_report_app/backend/test_output_{sys.argv[1] if len(sys.argv) > 1 else 'concise'}.pdf",
    )
    print("Wrote", out)
