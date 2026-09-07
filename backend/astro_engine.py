"""
Core astronomical engine: geocoding, historical timezone resolution,
tropical (Western) and sidereal (Vedic/Lahiri) chart calculation,
Human Design "design chart" (88deg solar arc prior), and aspects.
"""
import math
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import swisseph as swe
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderRateLimited, GeocoderServiceError
from timezonefinder import TimezoneFinder

_tf = TimezoneFinder()
_geolocator = Nominatim(user_agent="celestial_report_app_v1", timeout=10)
_geocode_cache: dict[str, tuple[float, float, str]] = {}

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

SIGN_LORDS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}

NAKSHATRA_WIDTH = 360.0 / 27.0
DASHA_LORDS_CYCLE = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]

PLANET_IDS = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY, "Venus": swe.VENUS,
    "Mars": swe.MARS, "Jupiter": swe.JUPITER, "Saturn": swe.SATURN,
    "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE, "Pluto": swe.PLUTO,
    "True Node": swe.TRUE_NODE,
}

ASPECTS = [
    ("Conjunction", 0, 8),
    ("Sextile", 60, 6),
    ("Square", 90, 8),
    ("Trine", 120, 8),
    ("Opposition", 180, 8),
]


class GeocodeError(Exception):
    pass


def geocode_place(place_name: str):
    """Return (lat, lon, resolved_name) for a free-text place name.

    Cached in-process so repeat lookups of the same place never re-hit the
    geocoding service, and retried with backoff if the free Nominatim
    endpoint briefly rate-limits us (HTTP 429).
    """
    cache_key = place_name.strip().lower()
    if cache_key in _geocode_cache:
        return _geocode_cache[cache_key]

    last_error: Exception | None = None
    for attempt, delay in enumerate((0, 1.5, 3.5)):
        if delay:
            time.sleep(delay)
        try:
            loc = _geolocator.geocode(place_name)
            break
        except (GeocoderRateLimited, GeocoderServiceError) as exc:
            last_error = exc
            loc = None
    else:
        raise GeocodeError(
            f"The location lookup service is temporarily busy. Please try again in a moment. ({last_error})"
        )

    if loc is None:
        raise GeocodeError(f"Could not find location: {place_name}")

    result = (loc.latitude, loc.longitude, loc.address)
    _geocode_cache[cache_key] = result
    return result


def resolve_timezone(lat: float, lon: float) -> str:
    tz_name = _tf.timezone_at(lat=lat, lng=lon)
    if tz_name is None:
        tz_name = _tf.closest_timezone_at(lat=lat, lng=lon)
    if tz_name is None:
        raise GeocodeError("Could not resolve timezone for this location.")
    return tz_name


def local_to_ut(date_str: str, time_str: str, tz_name: str):
    """date_str='YYYY-MM-DD', time_str='HH:MM' (24h, local civil time) -> (jd_ut, utc_datetime)"""
    naive = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    local_dt = naive.replace(tzinfo=ZoneInfo(tz_name))
    utc_dt = local_dt.astimezone(ZoneInfo("UTC"))
    jd_ut = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day,
                        utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0)
    return jd_ut, utc_dt, local_dt


def sign_of(lon: float):
    idx = int(lon // 30) % 12
    return SIGNS[idx], lon - idx * 30


def nakshatra_of(lon: float):
    idx = int(lon // NAKSHATRA_WIDTH) % 27
    within = lon - idx * NAKSHATRA_WIDTH
    pada = int(within // (NAKSHATRA_WIDTH / 4)) + 1
    return idx, pada


def navamsa_sign(lon: float) -> str:
    sign_idx = int(lon // 30) % 12
    pos_in_sign = lon - sign_idx * 30
    nav_idx_in_sign = int(pos_in_sign // (30.0 / 9))
    modality = sign_idx % 3  # 0 movable, 1 fixed, 2 dual
    if modality == 0:
        start = sign_idx
    elif modality == 1:
        start = sign_idx + 8
    else:
        start = sign_idx + 4
    return SIGNS[(start + nav_idx_in_sign) % 12]


def _house_of_whole_sign(lon: float, asc_sign_idx: int) -> int:
    sign_idx = int(lon // 30) % 12
    return ((sign_idx - asc_sign_idx) % 12) + 1


def _placidus_house_of(lon: float, cusps: list) -> int:
    """Given 12 house cusp longitudes (cusps[1..12]) find which house a longitude falls into."""
    for h in range(1, 13):
        start = cusps[h]
        end = cusps[h + 1] if h < 12 else cusps[1]
        span = (end - start) % 360
        pos = (lon - start) % 360
        if pos < span or span == 0:
            return h
    return 12


def compute_planets(jd_ut: float, sidereal: bool = False, ayanamsa: float = 0.0):
    """Compute tropical (or sidereal-adjusted) longitudes for all planets + node."""
    flag = swe.FLG_SWIEPH
    positions = {}
    for name, pid in PLANET_IDS.items():
        xx, _ = swe.calc_ut(jd_ut, pid, flag)
        lon = xx[0]
        if sidereal:
            lon = (lon - ayanamsa) % 360
        positions[name] = lon
    positions["Ketu"] = (positions["True Node"] + 180) % 360
    return positions


def compute_houses(jd_ut: float, lat: float, lon: float, sidereal: bool = False, ayanamsa: float = 0.0):
    """Placidus houses with fallback to Porphyry for extreme latitudes. Returns (cusps dict 1-12, asc, mc)."""
    try:
        cusps, ascmc = swe.houses(jd_ut, lat, lon, b'P')
    except Exception:
        cusps, ascmc = swe.houses(jd_ut, lat, lon, b'O')
    asc = ascmc[0]
    mc = ascmc[1]
    cusp_map = {i + 1: cusps[i] for i in range(12)}
    if sidereal:
        cusp_map = {k: (v - ayanamsa) % 360 for k, v in cusp_map.items()}
        asc = (asc - ayanamsa) % 360
        mc = (mc - ayanamsa) % 360
    return cusp_map, asc, mc


def compute_aspects(positions: dict):
    names = list(positions.keys())
    results = []
    exclude = {"Ketu"}  # Ketu mirrors Rahu; skip duplicate aspect noise
    names = [n for n in names if n not in exclude]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            diff = abs(positions[a] - positions[b]) % 360
            if diff > 180:
                diff = 360 - diff
            for aspect_name, exact_angle, orb in ASPECTS:
                delta = abs(diff - exact_angle)
                if delta <= orb:
                    results.append({
                        "planet_a": a, "planet_b": b, "aspect": aspect_name,
                        "angle": round(diff, 2), "orb": round(delta, 2),
                    })
                    break
    results.sort(key=lambda r: r["orb"])
    return results


def find_design_jd(birth_jd_ut: float) -> float:
    """Find JD where Sun's tropical longitude is exactly 88 degrees before its birth longitude
    (Human Design 'Design' / genetic chart moment). Uses bisection on Sun longitude difference."""
    birth_sun, _ = swe.calc_ut(birth_jd_ut, swe.SUN, swe.FLG_SWIEPH)
    birth_sun_lon = birth_sun[0]
    target = (birth_sun_lon - 88) % 360

    lo = birth_jd_ut - 93
    hi = birth_jd_ut - 86

    def sun_diff(jd):
        s, _ = swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH)
        d = (s[0] - target) % 360
        if d > 180:
            d -= 360
        return d

    d_lo = sun_diff(lo)
    d_hi = sun_diff(hi)
    for _ in range(60):
        mid = (lo + hi) / 2
        d_mid = sun_diff(mid)
        if abs(d_mid) < 1e-7:
            return mid
        if (d_lo < 0) == (d_mid < 0):
            lo, d_lo = mid, d_mid
        else:
            hi, d_hi = mid, d_mid
    return (lo + hi) / 2


def full_chart(name: str, date_str: str, time_str: str, place: str):
    """Compute the complete astronomical dataset for a person: geocode, timezone,
    tropical (Western) chart, sidereal (Vedic) chart, and Human Design design chart."""
    lat, lon, resolved_place = geocode_place(place)
    tz_name = resolve_timezone(lat, lon)
    jd_ut, utc_dt, local_dt = local_to_ut(date_str, time_str, tz_name)

    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    ayanamsa = swe.get_ayanamsa_ut(jd_ut)

    trop_positions = compute_planets(jd_ut, sidereal=False)
    trop_cusps, trop_asc, trop_mc = compute_houses(jd_ut, lat, lon, sidereal=False)

    sid_positions = compute_planets(jd_ut, sidereal=True, ayanamsa=ayanamsa)
    sid_cusps, sid_asc, sid_mc = compute_houses(jd_ut, lat, lon, sidereal=True, ayanamsa=ayanamsa)

    asc_sign_idx_trop = int(trop_asc // 30) % 12

    western = {"ascendant": trop_asc, "midheaven": trop_mc, "planets": {}, "houses": trop_cusps}
    for pname, plon in trop_positions.items():
        sign, deg = sign_of(plon)
        house = _placidus_house_of(plon, trop_cusps)
        western["planets"][pname] = {
            "lon": plon, "sign": sign, "deg_in_sign": deg,
            "sign_lord": SIGN_LORDS[sign], "house": house,
        }
    western["aspects"] = compute_aspects(trop_positions)
    asc_sign, asc_deg = sign_of(trop_asc)
    western["ascendant_sign"] = asc_sign
    western["ascendant_deg_in_sign"] = asc_deg
    mc_sign, mc_deg = sign_of(trop_mc)
    western["midheaven_sign"] = mc_sign
    western["midheaven_deg_in_sign"] = mc_deg

    asc_sign_idx_sid = int(sid_asc // 30) % 12
    vedic = {"ascendant": sid_asc, "ayanamsa": ayanamsa, "planets": {}}
    for pname, plon in sid_positions.items():
        sign, deg = sign_of(plon)
        nak_idx, pada = nakshatra_of(plon)
        house = _house_of_whole_sign(plon, asc_sign_idx_sid)
        vedic["planets"][pname] = {
            "lon": plon, "sign": sign, "deg_in_sign": deg, "sign_lord": SIGN_LORDS[sign],
            "nakshatra_idx": nak_idx, "pada": pada, "house": house,
            "navamsa_sign": navamsa_sign(plon),
        }
    asc_sign_v, asc_deg_v = sign_of(sid_asc)
    asc_nak_idx, asc_pada = nakshatra_of(sid_asc)
    vedic["ascendant_sign"] = asc_sign_v
    vedic["ascendant_deg_in_sign"] = asc_deg_v
    vedic["ascendant_nakshatra_idx"] = asc_nak_idx
    vedic["ascendant_pada"] = asc_pada

    # Vimshottari Dasha timeline from Moon's nakshatra
    moon = vedic["planets"]["Moon"]
    nak_idx = moon["nakshatra_idx"]
    elapsed = moon["lon"] - nak_idx * NAKSHATRA_WIDTH
    frac_remaining = (NAKSHATRA_WIDTH - elapsed) / NAKSHATRA_WIDTH
    start_lord_idx = nak_idx % 9
    start_lord = DASHA_LORDS_CYCLE[start_lord_idx]
    DASHA_YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7, "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17}
    balance_years = frac_remaining * DASHA_YEARS[start_lord]

    def add_years(dt, years):
        return dt + timedelta(days=years * 365.2425)

    timeline = []
    current = local_dt.replace(tzinfo=None)
    end = add_years(current, balance_years)
    timeline.append({"lord": start_lord, "start": current.isoformat(), "end": end.isoformat(),
                      "years": round(balance_years, 2), "partial_at_birth": True})
    current = end
    idx = start_lord_idx
    total = balance_years
    while total < 120:
        idx = (idx + 1) % 9
        lord = DASHA_LORDS_CYCLE[idx]
        years = DASHA_YEARS[lord]
        end = add_years(current, years)
        timeline.append({"lord": lord, "start": current.isoformat(), "end": end.isoformat(),
                          "years": years, "partial_at_birth": False})
        current = end
        total += years
    vedic["dasha_timeline"] = timeline

    # Human Design: Personality (birth) gates use tropical zodiac mapped to 64-gate wheel;
    # Design gates use chart 88deg of solar arc prior to birth.
    design_jd = find_design_jd(jd_ut)
    design_positions = compute_planets(design_jd, sidereal=False)

    return {
        "name": name,
        "birth": {
            "date": date_str, "time": time_str, "place": resolved_place,
            "lat": lat, "lon": lon, "tz_name": tz_name,
            "utc_iso": utc_dt.isoformat(), "jd_ut": jd_ut,
        },
        "western": western,
        "vedic": vedic,
        "human_design_raw": {
            "personality_positions": trop_positions,
            "design_positions": design_positions,
            "design_jd_ut": design_jd,
        },
    }
