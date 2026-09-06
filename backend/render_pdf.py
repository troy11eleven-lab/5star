"""Render the assembled report content into a PDF using Jinja2 + WeasyPrint."""
import os
import random
from datetime import datetime

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

BASE_DIR = os.path.dirname(__file__)
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


def _star_field(n=140, seed=42):
    rng = random.Random(seed)
    stars = []
    for _ in range(n):
        stars.append({
            "x": round(rng.uniform(0, 800), 1),
            "y": round(rng.uniform(0, 1035), 1),
            "r": round(rng.uniform(0.5, 2.0), 2),
            "o": round(rng.uniform(0.25, 0.95), 2),
        })
    return stars


def render_report_pdf(context: dict, output_path: str):
    template = _env.get_template("report.html")
    ctx = dict(context)
    ctx.setdefault("stars", _star_field())
    ctx.setdefault("generated_date", datetime.now().strftime("%B %d, %Y"))
    html_str = template.render(**ctx)
    HTML(string=html_str, base_url=TEMPLATES_DIR).write_pdf(output_path)
    return output_path
