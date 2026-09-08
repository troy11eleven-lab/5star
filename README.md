# 5 Star Guru Report

A web app that generates a combined comprehensive PDF report covering five systems from a person's birth details:

- **Western Astrology** — tropical zodiac chart, houses, planetary placements, aspects
- **Vedic Astrology** — sidereal (Lahiri) placements, nakshatras, Vimshottari Dasha timeline
- **Numerology** — Life Path, Expression, Soul Urge & Personality numbers, full Psychomatrix grid
- **Human Design** — Type, Strategy, Authority, Profile, defined centers and channels
- **Gene Keys** — Activation, Venus, and Pearl Sequences (Shadow → Gift → Siddhi)

The app takes a name, birth date, birth time, and birth place, then shows an in-app preview (headline stats + three interactive chart visuals — a combined astrology wheel, a Human Design bodygraph, and the Gene Keys Activation Sequence bands) before generating a downloadable full PDF report.

## Structure

- `backend/` — FastAPI service. Computes charts via `astro_engine.py` (Swiss Ephemeris), `numerology.py`, `human_design.py`, and `gene_keys.py`, renders chart visuals as SVG/HTML (`chart_visuals.py`), and produces the final PDF with WeasyPrint (`render_pdf.py`, `templates/`).
- `frontend/` — Static HTML/CSS/JS single-page app (`index.html`, `styles.css`, `app.js`) that collects birth details, requests a preview, and downloads the finished PDF.

## Running locally

```bash
cd backend
pip install -r requirements.txt   # if present, otherwise see imports in main.py
uvicorn main:app --host 0.0.0.0 --port 8000
```

Then serve `frontend/` (e.g. `python3 -m http.server`) and open `index.html`, or point `app.js`'s API base at your running backend.

## Notes

- Geocoding uses the free Nominatim (OpenStreetMap) service with an in-process cache and retry/backoff, since the public endpoint can rate-limit under heavy testing.
- Report generation is split into `build_context()` (expensive: geocode + chart math) and `render()` (PDF layout), so the in-app preview and the PDF download share one computation via a short-lived server-side cache keyed by a `preview_id`.
