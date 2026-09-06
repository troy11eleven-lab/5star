"""
Numerology calculation module (Pythagorean system).
Life Path, Expression/Destiny, Soul Urge (Heart's Desire), Personality,
and the Pythagorean Square / Psychomatrix.
"""

MASTER_NUMBERS = {11, 22, 33}

LETTER_VALUES = {}
for i, ch in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    LETTER_VALUES[ch] = (i % 9) + 1

VOWELS = set("AEIOU")


def reduce_number(n: int, keep_master: bool = True) -> int:
    """Reduce a number to a single digit, optionally preserving master numbers 11/22/33."""
    while n > 9:
        if keep_master and n in MASTER_NUMBERS:
            return n
        n = sum(int(d) for d in str(n))
    return n


def _clean_name(name: str) -> str:
    return "".join(ch for ch in name.upper() if ch.isalpha())


def life_path_number(day: int, month: int, year: int) -> dict:
    r_month = reduce_number(month)
    r_day = reduce_number(day)
    r_year = reduce_number(sum(int(d) for d in str(year)))
    total = r_month + r_day + r_year
    result = reduce_number(total)
    return {"number": result, "is_master": result in MASTER_NUMBERS, "components": {"month": r_month, "day": r_day, "year": r_year, "sum": total}}


def expression_number(full_name: str) -> dict:
    letters = _clean_name(full_name)
    total = sum(LETTER_VALUES[c] for c in letters)
    result = reduce_number(total)
    return {"number": result, "is_master": result in MASTER_NUMBERS, "raw_sum": total}


def soul_urge_number(full_name: str) -> dict:
    letters = _clean_name(full_name)
    total = sum(LETTER_VALUES[c] for c in letters if c in VOWELS)
    result = reduce_number(total)
    return {"number": result, "is_master": result in MASTER_NUMBERS, "raw_sum": total}


def personality_number(full_name: str) -> dict:
    letters = _clean_name(full_name)
    total = sum(LETTER_VALUES[c] for c in letters if c not in VOWELS)
    result = reduce_number(total)
    return {"number": result, "is_master": result in MASTER_NUMBERS, "raw_sum": total}


def birthday_number(day: int) -> dict:
    result = reduce_number(day)
    return {"number": result, "is_master": result in MASTER_NUMBERS, "raw": day}


def maturity_number(life_path: int, expression: int) -> dict:
    total = life_path + expression
    result = reduce_number(total)
    return {"number": result, "is_master": result in MASTER_NUMBERS}


def psychomatrix(day: int, month: int, year: int) -> dict:
    """Aleksandrov Pythagorean Square. Returns counts for digits 1-9 and the 4 working numbers."""
    date_digits = [int(c) for c in f"{day:02d}{month:02d}{year}"]
    working1 = sum(date_digits)
    working2 = sum(int(c) for c in str(working1))
    day_str = str(day)
    first_day_digit = int(day_str[0]) if day_str[0] != "0" else int(day_str[1])
    working3 = working1 - 2 * first_day_digit
    working4 = sum(int(c) for c in str(abs(working3)))

    all_digits = (
        date_digits
        + [int(c) for c in str(working1)]
        + [int(c) for c in str(working2)]
        + [int(c) for c in str(abs(working3))]
        + [int(c) for c in str(working4)]
    )
    counts = {str(d): all_digits.count(d) for d in range(1, 10)}
    return {
        "counts": counts,
        "working_numbers": {"w1": working1, "w2": working2, "w3": working3, "w4": working4},
    }


PSYCHOMATRIX_CELLS = {
    "1": {"label": "Character", "theme": "Willpower and core self-perception"},
    "2": {"label": "Energy", "theme": "Vitality and stamina"},
    "3": {"label": "Interest", "theme": "Creativity, sociability, and curiosity"},
    "4": {"label": "Health", "theme": "Physical constitution and resilience"},
    "5": {"label": "Logic", "theme": "Intuition and analytical self-esteem"},
    "6": {"label": "Labor & Family", "theme": "Work ethic and domestic responsibility"},
    "7": {"label": "Duty", "theme": "Spiritual fortune and destiny"},
    "8": {"label": "Talent", "theme": "Responsibility to society and gifts"},
    "9": {"label": "Memory", "theme": "Intelligence and adaptability"},
}


def full_numerology_profile(full_name: str, day: int, month: int, year: int) -> dict:
    lp = life_path_number(day, month, year)
    ex = expression_number(full_name)
    su = soul_urge_number(full_name)
    pe = personality_number(full_name)
    bd = birthday_number(day)
    mt = maturity_number(lp["number"], ex["number"])
    pm = psychomatrix(day, month, year)
    return {
        "life_path": lp,
        "expression": ex,
        "soul_urge": su,
        "personality": pe,
        "birthday": bd,
        "maturity": mt,
        "psychomatrix": pm,
    }
