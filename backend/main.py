"""FastAPI backend for the Five-System Celestial Report generator."""
import os
import re
import time
import uuid
import logging
import threading

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from generate_report import generate
from astro_engine import GeocodeError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("celestial_report")

APP_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(APP_DIR, "generated")
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = FastAPI(title="Five-System Celestial Report API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^\d{2}:\d{2}$")

# Simple in-memory cleanup: remove generated files older than 30 minutes.
_MAX_AGE_SECONDS = 30 * 60


def _cleanup_old_files():
    now = time.time()
    try:
        for fname in os.listdir(OUTPUT_DIR):
            fpath = os.path.join(OUTPUT_DIR, fname)
            try:
                if os.path.isfile(fpath) and (now - os.path.getmtime(fpath)) > _MAX_AGE_SECONDS:
                    os.remove(fpath)
            except OSError:
                pass
    except FileNotFoundError:
        pass


class ReportRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    birth_date: str = Field(..., description="YYYY-MM-DD")
    birth_time: str = Field(..., description="HH:MM, 24-hour")
    birth_place: str = Field(..., min_length=2, max_length=200)
    depth: str = Field("comprehensive", description="'concise' or 'comprehensive'")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/generate-report")
def generate_report_endpoint(req: ReportRequest):
    _cleanup_old_files()

    name = req.name.strip()
    birth_place = req.birth_place.strip()
    depth = req.depth.strip().lower() if req.depth else "comprehensive"
    if depth not in ("concise", "comprehensive"):
        depth = "comprehensive"

    if not name:
        raise HTTPException(status_code=400, detail="Please enter a name.")
    if not DATE_RE.match(req.birth_date or ""):
        raise HTTPException(status_code=400, detail="Birth date must be in YYYY-MM-DD format.")
    if not TIME_RE.match(req.birth_time or ""):
        raise HTTPException(status_code=400, detail="Birth time must be in HH:MM (24-hour) format.")
    if not birth_place:
        raise HTTPException(status_code=400, detail="Please enter a birth place.")

    try:
        y = int(req.birth_date[0:4])
        m = int(req.birth_date[5:7])
        d = int(req.birth_date[8:10])
        if not (1 <= m <= 12) or not (1 <= d <= 31) or y < 1900 or y > 2100:
            raise ValueError()
    except ValueError:
        raise HTTPException(status_code=400, detail="Please enter a valid birth date between 1900 and 2100.")

    try:
        hh = int(req.birth_time[0:2])
        mm = int(req.birth_time[3:5])
        if not (0 <= hh <= 23) or not (0 <= mm <= 59):
            raise ValueError()
    except ValueError:
        raise HTTPException(status_code=400, detail="Please enter a valid birth time.")

    request_id = uuid.uuid4().hex[:12]
    safe_name = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").lower() or "report"
    filename = f"{safe_name}-{depth}-{request_id}.pdf"
    output_path = os.path.join(OUTPUT_DIR, filename)

    try:
        generate(name, req.birth_date, req.birth_time, birth_place, depth, output_path)
    except GeocodeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Report generation failed for request %s", request_id)
        raise HTTPException(status_code=500, detail="Something went wrong generating your report. Please double-check your birth place and try again.")

    if not os.path.exists(output_path):
        raise HTTPException(status_code=500, detail="Report file was not created.")

    download_name = f"{safe_name}-five-system-celestial-report-{depth}.pdf"
    return FileResponse(
        output_path,
        media_type="application/pdf",
        filename=download_name,
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
