#!/usr/bin/env python3
"""Generate the synthetic source extracts for Vennaert (fictional B2B wholesaler).

Everything is deterministic (fixed seed), so the pipeline, the tests and every number in
the docs and on the site come out identical on every machine and in CI.

The data is deliberately imperfect. Each planted problem is listed in PLANTED and is
documented in docs/02-sources/README.md. The pipeline has to *find* these problems from
the data; it never reads PLANTED (tests do, to prove the rules catch what was planted).

Output: data/raw/*.csv and data/raw/_planted.json
"""
from __future__ import annotations

import csv
import json
import random
import unicodedata
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
SEED = 2026

START = date(2025, 1, 1)
END = date(2026, 9, 30)
REP_LEFT = date(2026, 3, 31)          # AM04 leaves; ERP reassigns to AM11, CRM is never updated
AM11_START = date(2026, 4, 1)
AM12_START = date(2026, 6, 1)         # new French-speaking rep takes over Hainaut from AM07
DUPLICATE_EXPORT_DAY = date(2026, 8, 14)  # legacy Excel export appended this day twice

rng = random.Random(SEED)

# --------------------------------------------------------------------------- reference data

REPS = [
    # code, name (fictional), region, team, email, start, end
    ("AM01", "Lotte V.", "West-Vlaanderen Kust", "Field", "lotte.v@vennaert.example", "2019-03-01", ""),
    ("AM02", "Jens D.", "West-Vlaanderen Binnenland", "Field", "jens.d@vennaert.example", "2017-09-01", ""),
    ("AM03", "Sara M.", "Oost-Vlaanderen", "Field", "sara.m@vennaert.example", "2020-01-06", ""),
    ("AM04", "Koen B.", "Antwerpen", "Field", "koen.b@vennaert.example", "2015-05-01", "2026-03-31"),
    ("AM05", "Ines W.", "Vlaams-Brabant & Brussel", "Field", "ines.w@vennaert.example", "2021-02-01", ""),
    ("AM06", "Pieter L.", "Limburg", "Field", "pieter.l@vennaert.example", "2018-10-01", ""),
    ("AM07", "Julie H.", "Wallonie", "Field", "julie.h@vennaert.example", "2016-04-01", ""),
    ("AM08", "Thomas R.", "Hauts-de-France", "Field", "thomas.r@vennaert.example", "2022-03-01", ""),
    ("AM09", "Eva C.", "Key Accounts", "Key Accounts", "eva.c@vennaert.example", "2014-01-02", ""),
    ("AM11", "Bram S.", "Antwerpen", "Field", "bram.s@vennaert.example", "2026-04-01", ""),
    ("AM12", "Camille F.", "Hainaut", "Field", "camille.f@vennaert.example", "2026-06-01", ""),
    ("IS01", "Nina G.", "Inside Sales", "Inside Sales", "nina.g@vennaert.example", "2020-09-01", ""),
    ("IS02", "Wout P.", "Inside Sales", "Inside Sales", "wout.p@vennaert.example", "2023-01-09", ""),
]

# region -> (rep, country, [(postcode, city), ...])
REGIONS = {
    "West-Vlaanderen Kust": ("AM01", "BE", [("8400", "Oostende"), ("8300", "Knokke-Heist"), ("8370", "Blankenberge"), ("8620", "Nieuwpoort"), ("8660", "De Panne"), ("8420", "De Haan")]),
    "West-Vlaanderen Binnenland": ("AM02", "BE", [("8800", "Roeselare"), ("8500", "Kortrijk"), ("8000", "Brugge"), ("8900", "Ieper"), ("8700", "Tielt"), ("8790", "Waregem"), ("8870", "Izegem"), ("8560", "Wevelgem")]),
    "Oost-Vlaanderen": ("AM03", "BE", [("9000", "Gent"), ("9300", "Aalst"), ("9100", "Sint-Niklaas"), ("9200", "Dendermonde"), ("9700", "Oudenaarde"), ("9900", "Eeklo")]),
    "Antwerpen": ("AM04", "BE", [("2000", "Antwerpen"), ("2800", "Mechelen"), ("2300", "Turnhout"), ("2200", "Herentals"), ("2400", "Mol"), ("2500", "Lier")]),
    "Vlaams-Brabant & Brussel": ("AM05", "BE", [("3000", "Leuven"), ("1000", "Brussel"), ("1800", "Vilvoorde"), ("3300", "Tienen"), ("1500", "Halle"), ("1930", "Zaventem")]),
    "Limburg": ("AM06", "BE", [("3500", "Hasselt"), ("3600", "Genk"), ("3800", "Sint-Truiden"), ("3900", "Pelt"), ("3700", "Tongeren")]),
    "Wallonie": ("AM07", "BE", [("4000", "Liège"), ("5000", "Namur"), ("1300", "Wavre"), ("4800", "Verviers"), ("5500", "Dinant")]),
    "Hainaut": ("AM07", "BE", [("7000", "Mons"), ("6000", "Charleroi"), ("7500", "Tournai"), ("7700", "Mouscron"), ("7100", "La Louvière")]),
    "Hauts-de-France": ("AM08", "FR", [("59000", "Lille"), ("59100", "Roubaix"), ("59200", "Tourcoing"), ("59140", "Dunkerque"), ("59300", "Valenciennes"), ("62000", "Arras"), ("62100", "Calais")]),
}
FR_REGIONS = {"Wallonie", "Hainaut", "Hauts-de-France"}

SEGMENTS = {
    # segment: (share, yearly spend median EUR, orders per year)
    "Schoonmaakbedrijven": (0.30, 26000, 22),
    "Zorg": (0.18, 21000, 16),
    "Horeca": (0.24, 5200, 10),
    "Industrie": (0.16, 11500, 11),
    "Onderwijs & overheid": (0.12, 8400, 8),
}

NL_SURNAMES = ["Vandenberghe", "Declercq", "Verhaeghe", "Desmet", "Vermeulen", "Maes", "Claeys", "Goossens", "Wouters", "Peeters",
               "Vercruysse", "Deprez", "Lambrecht", "Coussens", "Vanhoutte", "Debruyne", "Vandamme", "Willaert", "Bossuyt", "Callewaert",
               "Mertens", "Jacobs", "Verbeke", "Hoste", "Ghekiere", "Lannoo", "Devos", "Pattyn", "Vanneste", "Dumon"]
FR_SURNAMES = ["Dubois", "Lambert", "Dupont", "Lefebvre", "Leroy", "Moreau", "Simon", "Laurent", "Michel", "Mercier",
               "Renard", "Collard", "Fontaine", "Deschamps", "Marchal", "Hennebert", "Delhaye", "Masson", "Gilson", "Piron"]
NL_PLACES = ["Ter Linde", "De Vlier", "Het Anker", "De Zilverberk", "Ter Duinen", "De Meersen", "Hof ter Leie", "De Notelaar", "Zonnehoek", "De Kapel"]
FR_PLACES = ["Les Tilleuls", "Le Clos", "La Source", "Les Peupliers", "Le Moulin", "Les Acacias", "La Roseraie", "Le Val", "Les Glycines", "Beau Site"]
NL_FORMS = ["NV", "BV", "BV", "VOF", ""]
FR_FORMS = ["SA", "SRL", "SRL", "SPRL", ""]
FRANCE_FORMS = ["SAS", "SARL", "SA", ""]

CATEGORIES = {
    # category: (n_skus, price range, cost ratio range)
    "Reinigingsmiddelen": (80, (4, 60), (0.48, 0.62)),
    "Papier & dispensers": (70, (8, 140), (0.55, 0.70)),
    "Handhygiëne": (55, (3, 45), (0.45, 0.60)),
    "Microvezel & materiaal": (60, (2, 35), (0.40, 0.55)),
    "Afvalzakken": (35, (6, 40), (0.60, 0.72)),
    "Handschoenen & PBM": (45, (5, 55), (0.50, 0.66)),
    "Machines & onderdelen": (40, (45, 2400), (0.62, 0.78)),
}
BRANDS = ["Vennaert Pro", "Klaro", "Hygios", "Brisant", "Ecolin", "Nordwipe", "Tersa"]

PLANTED: dict[str, object] = {}


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def make_be_vat() -> str:
    body = rng.randint(2_000_000, 9_999_999)      # first digit 0 -> 0200.000.0xx .. 0999.999.9xx
    check = 97 - (body % 97)
    return f"BE0{body:07d}{check:02d}"


def make_fr_vat() -> str:
    siren = rng.randint(300_000_000, 999_999_999)
    key = (12 + 3 * (siren % 97)) % 97
    return f"FR{key:02d}{siren}"


def fmt_be_vat_variant(vat: str) -> str:
    """Same number, formatted the way people type it into a CRM."""
    digits = vat[2:]
    return rng.choice([
        f"BE {digits[0:4]}.{digits[4:7]}.{digits[7:]}",
        digits,
        f"{digits[0:4]}.{digits[4:7]}.{digits[7:]}",
        f"be{digits}",
    ])


def corrupt_vat(vat: str) -> str:
    """One mistyped digit -> the check digits no longer match."""
    digits = list(vat[2:])
    i = rng.randint(3, 7)
    digits[i] = str((int(digits[i]) + rng.randint(1, 8)) % 10)
    return vat[:2] + "".join(digits)


def company_name(segment: str, region: str) -> tuple[str, str]:
    french = region in FR_REGIONS
    france = region == "Hauts-de-France"
    sur = rng.choice(FR_SURNAMES if french else NL_SURNAMES)
    place = rng.choice(FR_PLACES if french else NL_PLACES)
    form = rng.choice(FRANCE_FORMS if france else FR_FORMS if french else NL_FORMS)
    if segment == "Schoonmaakbedrijven":
        base = rng.choice([f"Nettoyage {sur}", f"{sur} Services", f"Propreté {place}"] if french
                          else [f"Schoonmaakbedrijf {sur}", f"{sur} Cleaning", f"Net & Proper {sur}"])
    elif segment == "Zorg":
        base = rng.choice([f"Maison de repos {place}", f"Résidence {place}", f"Centre de soins {place}"] if french
                          else [f"WZC {place}", f"Woonzorgcentrum {place}", f"Dagcentrum {place}"])
        form = "ASBL" if french and not france else ("" if france else "VZW")
    elif segment == "Horeca":
        base = rng.choice([f"Hôtel {place}", f"Brasserie {sur}", f"Restaurant {place}"] if french
                          else [f"Hotel {place}", f"Brasserie {sur}", f"Restaurant {place}", f"Taverne {place}"])
    elif segment == "Industrie":
        base = rng.choice([f"{sur} Industries", f"Ateliers {sur}", f"Métallerie {sur}"] if french
                          else [f"{sur} Metaal", f"{sur} Food Processing", f"Houtbewerking {sur}", f"{sur} Logistics"])
    else:
        base = rng.choice([f"École {place}", f"Commune de {rng.choice(['Ath', 'Huy', 'Spa', 'Marche'])}", f"Athénée {place}"] if french
                          else [f"Basisschool {place}", f"Gemeente {rng.choice(['Lichtervelde', 'Staden', 'Zonnebeke', 'Moorslede', 'Ledegem'])}", f"Atheneum {place}"])
        form = ""
    return base, form


USED_NAMES: set[tuple[str, str]] = set()


def unique_name(segment: str, region: str) -> tuple[str, str, str, str]:
    """Real towns rarely have two different customers with the same name; keep (name, city) unique."""
    for _ in range(200):
        name, form = company_name(segment, region)
        pc, city = rng.choice(REGIONS[region][2])
        key = (strip_accents(name).lower(), city)
        if key not in USED_NAMES:
            USED_NAMES.add(key)
            return name, form, pc, city
    raise RuntimeError("name pool exhausted")


def name_variant(name: str) -> str:
    """How the same customer ends up spelled in a second CRM record."""
    choice = rng.randint(0, 5)
    if choice == 0:
        return name.upper()
    if choice == 1:
        return strip_accents(name)
    if choice == 2:  # drop or change the legal form
        parts = name.rsplit(" ", 1)
        return parts[0] if len(parts) == 2 and parts[1] in {"NV", "BV", "VOF", "SA", "SRL", "SPRL", "SAS", "SARL", "VZW", "ASBL"} else name + " bv"
    if choice == 3:  # swap two adjacent letters (typo)
        letters = list(name)
        i = rng.randint(2, max(2, len(letters) - 3))
        letters[i], letters[i + 1] = letters[i + 1], letters[i]
        return "".join(letters)
    if choice == 4:
        return name.replace(" ", "  ", 1).replace("&", "en")
    return name.lower().title()


def daterange_days(a: date, b: date) -> int:
    return (b - a).days


def random_date(a: date, b: date) -> date:
    return a + timedelta(days=rng.randint(0, daterange_days(a, b)))


SEASON = {1: 0.92, 2: 0.98, 3: 1.10, 4: 1.02, 5: 1.00, 6: 1.01, 7: 0.86, 8: 0.74, 9: 1.08, 10: 1.12, 11: 1.04, 12: 0.90}


def write_csv(name: str, header: list[str], rows: list[list[object]]) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    with open(RAW / name, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


# --------------------------------------------------------------------------- products

def build_products() -> list[list[object]]:
    rows = []
    n = 0
    for cat, (count, (lo, hi), (clo, chi)) in CATEGORIES.items():
        for _ in range(count):
            n += 1
            sku = f"SKU-{10000 + n}"
            price = round(rng.uniform(lo, hi) if cat != "Machines & onderdelen" else rng.lognormvariate(4.6, 1.1) + lo, 2)
            price = min(price, hi)
            cost = round(price * rng.uniform(clo, chi), 2)
            desc = f"{cat.split(' ')[0]} {rng.choice(['Pro', 'Eco', 'Plus', 'Maxi', 'Compact', 'XL', 'Sensitive'])} {rng.randint(1, 99):02d}"
            rows.append([sku, desc, cat, rng.choice(BRANDS), cost, price, 1])
    # planted: products without category, one with cost 0
    missing_cat = rng.sample(range(len(rows)), 6)
    for i in missing_cat:
        rows[i][2] = ""
    zero = rng.choice([i for i in range(len(rows)) if i not in missing_cat and rows[i][2] == "Reinigingsmiddelen"])
    rows[zero][4] = 0.0
    PLANTED["product_missing_category"] = sorted(rows[i][0] for i in missing_cat)
    PLANTED["product_zero_cost"] = [rows[zero][0]]
    return rows


# --------------------------------------------------------------------------- customers

def build_customers():
    customers = []  # dicts
    n = 0
    region_names = list(REGIONS)
    region_weights = [12, 16, 13, 13, 11, 8, 9, 8, 10]
    seg_names = list(SEGMENTS)
    seg_weights = [SEGMENTS[s][0] for s in seg_names]

    def new_customer(region, segment, name, form, vat, postcode, city, created):
        nonlocal n
        n += 1
        rep, country, _ = REGIONS[region]
        c = {
            "customer_no": f"C{10000 + n}",
            "name": f"{name} {form}".strip(),
            "vat": vat,
            "postcode": postcode,
            "city": city,
            "country": country,
            "language": "FR" if region in FR_REGIONS else "NL",
            "segment": segment,
            "region": region,
            "created": created,
            "spend": rng.lognormvariate(0, 0.75) * SEGMENTS[segment][1],
            "freq": max(2, int(rng.gauss(SEGMENTS[segment][2], SEGMENTS[segment][2] * 0.3))),
            "key_account": False,
        }
        customers.append(c)
        return c

    for _ in range(1360):
        region = rng.choices(region_names, region_weights)[0]
        segment = rng.choices(seg_names, seg_weights)[0]
        name, form, pc, city = unique_name(segment, region)
        vat = make_fr_vat() if REGIONS[region][1] == "FR" else make_be_vat()
        created = random_date(date(2012, 1, 1), date(2026, 6, 30)).isoformat()
        new_customer(region, segment, name, form, vat, pc, city, created)

    # planted: legitimate multi-site groups (one legal entity = one VAT, several delivery sites)
    groups = []
    group_defs = [
        ("Zorggroep Ter Wilgen", "Zorg", "West-Vlaanderen Binnenland", "VZW", ["campus Noord", "campus Zuid", "campus Centrum"]),
        ("Zorggroep Merelhof", "Zorg", "Oost-Vlaanderen", "VZW", ["site Gent", "site Aalst"]),
        ("Hotelgroep Duinenzicht", "Horeca", "West-Vlaanderen Kust", "NV", ["Oostende", "Knokke-Heist", "De Panne"]),
        ("Vonkel Facility", "Schoonmaakbedrijven", "Antwerpen", "NV", ["regio Antwerpen", "regio Mechelen"]),
        ("Groupe Santé Valmeuse", "Zorg", "Wallonie", "ASBL", ["site Namur", "site Dinant"]),
        ("Scholengroep Ter Beke", "Onderwijs & overheid", "West-Vlaanderen Binnenland", "", ["Roeselare", "Izegem", "Tielt"]),
        ("Netteté Delnord", "Schoonmaakbedrijven", "Hauts-de-France", "SAS", ["Lille", "Roubaix"]),
        ("Brasserie Groep Lindevoort", "Horeca", "Vlaams-Brabant & Brussel", "BV", ["Leuven", "Brussel"]),
    ]
    for gname, segment, region, form, sites in group_defs:
        vat = make_fr_vat() if REGIONS[region][1] == "FR" else make_be_vat()
        members = []
        cities = list(REGIONS[region][2])
        rng.shuffle(cities)
        for i, site in enumerate(sites):
            pc, city = cities[i % len(cities)]
            c = new_customer(region, segment, f"{gname} – {site}", form, vat, pc, city,
                             random_date(date(2014, 1, 1), date(2024, 12, 31)).isoformat())
            c["key_account"] = True
            members.append(c["customer_no"])
        groups.append(members)
    PLANTED["multi_site_groups"] = groups

    # Key accounts: biggest schoonmaakbedrijven + groups go to AM09
    big = sorted((c for c in customers if c["segment"] == "Schoonmaakbedrijven"), key=lambda c: -c["spend"])[:24]
    for c in big:
        c["key_account"] = True
        c["spend"] *= 2.2

    # internal staff shop: finance excludes it from commercial revenue
    staff = {
        "customer_no": "C99999", "name": "Vennaert Personeelsshop (intern)", "vat": "", "postcode": "8800",
        "city": "Roeselare", "country": "BE", "language": "NL", "segment": "Intern", "region": "West-Vlaanderen Binnenland",
        "created": "2012-01-01", "spend": 9000, "freq": 40, "key_account": False,
    }
    customers.append(staff)
    return customers


def owner_history(c) -> list[tuple[str, str, str]]:
    """ERP owner per period: (rep, valid_from, valid_to). Reflects AM04 leaving and AM12 starting."""
    if c["segment"] == "Intern":
        return [("IS01", "2012-01-01", "9999-12-31")]
    if c["key_account"]:
        return [("AM09", "2012-01-01", "9999-12-31")]
    if c["segment"] == "Horeca" and c["spend"] < 2500:
        return [(rng.choice(["IS01", "IS02"]), "2012-01-01", "9999-12-31")]
    rep = REGIONS[c["region"]][0]
    if rep == "AM04":
        return [("AM04", "2012-01-01", REP_LEFT.isoformat()), ("AM11", AM11_START.isoformat(), "9999-12-31")]
    if c["region"] == "Hainaut":
        return [("AM07", "2012-01-01", (AM12_START - timedelta(days=1)).isoformat()), ("AM12", AM12_START.isoformat(), "9999-12-31")]
    return [(rep, "2012-01-01", "9999-12-31")]


def rep_on(history, d: date) -> str:
    iso = d.isoformat()
    for rep, a, b in history:
        if a <= iso <= b:
            return rep
    return history[-1][0]


# --------------------------------------------------------------------------- invoices

def build_invoices(customers, products):
    by_cat: dict[str, list[list[object]]] = {}
    for p in products:
        by_cat.setdefault(p[2] or "?", []).append(p)
    seg_mix = {
        "Schoonmaakbedrijven": {"Reinigingsmiddelen": 5, "Microvezel & materiaal": 4, "Afvalzakken": 2, "Handschoenen & PBM": 3, "Machines & onderdelen": 1.2, "Papier & dispensers": 2, "Handhygiëne": 1, "?": 0.05},
        "Zorg": {"Handhygiëne": 5, "Handschoenen & PBM": 5, "Papier & dispensers": 3, "Reinigingsmiddelen": 3, "Afvalzakken": 2, "Microvezel & materiaal": 1, "Machines & onderdelen": 0.3, "?": 0.05},
        "Horeca": {"Reinigingsmiddelen": 5, "Papier & dispensers": 4, "Handhygiëne": 2, "Afvalzakken": 2, "Microvezel & materiaal": 1, "Handschoenen & PBM": 1, "Machines & onderdelen": 0.2, "?": 0.05},
        "Industrie": {"Handschoenen & PBM": 5, "Reinigingsmiddelen": 3, "Papier & dispensers": 3, "Afvalzakken": 2, "Machines & onderdelen": 0.8, "Microvezel & materiaal": 1, "Handhygiëne": 1, "?": 0.05},
        "Onderwijs & overheid": {"Papier & dispensers": 5, "Reinigingsmiddelen": 3, "Handhygiëne": 3, "Afvalzakken": 2, "Microvezel & materiaal": 1, "Handschoenen & PBM": 1, "Machines & onderdelen": 0.3, "?": 0.05},
        "Intern": {"Reinigingsmiddelen": 3, "Handhygiëne": 2, "Papier & dispensers": 1},
    }
    lines = []
    histories = {}
    inv_no = 260000
    total_days = daterange_days(START, END) + 1
    for c in customers:
        hist = owner_history(c)
        histories[c["customer_no"]] = hist
        created = date.fromisoformat(c["created"])
        churn = rng.random() < 0.07 and c["segment"] != "Intern"
        churn_day = random_date(date(2025, 4, 1), date(2026, 5, 31)) if churn else None
        orders = int(c["freq"] * total_days / 365)
        avg_order = c["spend"] / c["freq"]
        cats = list(seg_mix[c["segment"]])
        weights = [seg_mix[c["segment"]][k] for k in cats]
        for _ in range(orders):
            d = random_date(START, END)
            if d < created or (churn_day and d > churn_day):
                continue
            if d.weekday() >= 5:
                d -= timedelta(days=d.weekday() - 4)
            growth = 1.0 + 0.045 * (daterange_days(START, d) / 365)
            if rng.random() > SEASON[d.month] / 1.12:
                continue
            inv_no += 1
            target_value = avg_order * growth * rng.uniform(0.6, 1.4)
            n_lines = max(1, min(9, int(rng.gauss(3.2, 1.6))))
            rep = rep_on(hist, d)
            used = set()
            for _ in range(n_lines):
                cat = rng.choices(cats, weights)[0]
                p = rng.choice(by_cat[cat])
                if p[0] in used:  # one line per article per invoice, as the ERP does
                    continue
                used.add(p[0])
                price = float(p[5])
                qty = max(1, round(target_value / n_lines / price)) if price < target_value else 1
                disc = rng.choice([0, 0, 0, 5, 5, 10, 12, 15]) if c["key_account"] or c["segment"] == "Schoonmaakbedrijven" else rng.choice([0, 0, 0, 0, 5])
                amount = round(qty * price * (1 - disc / 100), 2)
                lines.append({
                    "invoice_no": f"F{inv_no}", "doc_type": "F", "invoice_date": d, "customer_no": c["customer_no"],
                    "sku": p[0], "qty": qty, "unit_price": price, "discount_pct": disc, "line_amount": amount,
                    "unit_cost": float(p[4]), "rep_code": rep,
                })
    lines.sort(key=lambda l: (l["invoice_date"], l["invoice_no"]))

    # credit notes: returns / price corrections, exported with POSITIVE amounts and doc_type C
    credit = []
    cn_no = 900000
    for l in rng.sample(lines, int(len(lines) * 0.028)):
        cn_no += 1
        d = min(END, l["invoice_date"] + timedelta(days=rng.randint(3, 25)))
        part = rng.choice([1.0, 1.0, 0.5, 0.25])
        qty = max(1, round(l["qty"] * part))
        credit.append({**l, "invoice_no": f"C{cn_no}", "doc_type": "C", "invoice_date": d, "qty": qty,
                       "line_amount": round(qty * l["unit_price"] * (1 - l["discount_pct"] / 100), 2)})
    lines.extend(credit)
    lines.sort(key=lambda l: (l["invoice_date"], l["invoice_no"]))

    # planted: missing rep code on ~2% of lines (manual invoices typed by accounting)
    missing = 0
    for l in lines:
        if rng.random() < 0.019:
            l["rep_code"] = ""
            missing += 1
    PLANTED["lines_missing_rep"] = missing
    return lines, histories


# --------------------------------------------------------------------------- CRM

def build_crm(customers, histories):
    accounts = []
    n = 0
    rep_codes = [r[0] for r in REPS]

    def acc(name, vat, erp_no, owner, segment, region, pc, city, country, email, phone, created, last_activity):
        nonlocal n
        n += 1
        a = {"account_id": f"ACC-{50000 + n}", "name": name, "vat_number": vat, "erp_customer_no": erp_no,
             "owner_rep": owner, "segment": segment, "region": region, "postcode": pc, "city": city, "country": country,
             "email": email, "phone": phone, "created_at": created, "last_activity": last_activity}
        accounts.append(a)
        return a

    def email_for(name):
        slug = "".join(ch for ch in strip_accents(name).lower() if ch.isalnum())[:18] or "info"
        return f"info@{slug}.example"

    def phone_for(country):
        return f"+32 {rng.randint(50, 59)} {rng.randint(10, 99)} {rng.randint(10, 99)} {rng.randint(10, 99)}" if country == "BE" \
            else f"+33 3 {rng.randint(10, 99)} {rng.randint(10, 99)} {rng.randint(10, 99)} {rng.randint(10, 99)}"

    commercial = [c for c in customers if c["segment"] != "Intern"]
    unlinked = set(c["customer_no"] for c in rng.sample(commercial, 58))
    PLANTED["missing_erp_link"] = sorted(unlinked)

    linked_accounts = {}
    for c in commercial:
        owner = histories[c["customer_no"]][-1][0]
        if owner == "AM11":
            owner = "AM04"            # CRM never updated after AM04 left
        last = random_date(date(2025, 6, 1), date(2026, 9, 30)).isoformat()
        a = acc(c["name"], c["vat"], "" if c["customer_no"] in unlinked else c["customer_no"], owner, c["segment"], c["region"],
                c["postcode"], c["city"], c["country"], email_for(c["name"]), phone_for(c["country"]), c["created"], last)
        linked_accounts[c["customer_no"]] = a
    PLANTED["inactive_owner_accounts"] = sum(1 for a in accounts if a["owner_rep"] == "AM04")

    # planted: duplicates of existing customers (trade fair import, second rep, web form)
    dup_sources = rng.sample([c for c in commercial if not c["key_account"]], 132)
    triples = set(c["customer_no"] for c in rng.sample(dup_sources, 9))
    clusters = []
    for c in dup_sources:
        base = linked_accounts[c["customer_no"]]
        cluster = [base["account_id"]]
        for _ in range(2 if c["customer_no"] in triples else 1):
            r = rng.random()
            if c["country"] == "BE":
                vat = fmt_be_vat_variant(c["vat"]) if r < 0.5 else ("" if r < 0.75 else c["vat"])
            else:
                vat = "" if r < 0.4 else c["vat"]
            pc = c["postcode"] if rng.random() < 0.9 else rng.choice(REGIONS[c["region"]][2])[0]
            created = random_date(date(2023, 1, 1), date(2026, 9, 15)).isoformat()
            d = acc(name_variant(c["name"]), vat, "", rng.choice([x for x in rep_codes if x not in {"AM04", "AM11"}]), c["segment"],
                    c["region"], pc, c["city"], c["country"],
                    "" if rng.random() < 0.3 else email_for(c["name"]).replace("info@", rng.choice(["sales@", "aankoop@", "achat@"])),
                    "" if rng.random() < 0.4 else phone_for(c["country"]), created,
                    random_date(date.fromisoformat(created), date(2026, 9, 30)).isoformat())
            cluster.append(d["account_id"])
        clusters.append(cluster)
    PLANTED["duplicate_clusters"] = clusters

    # planted: genuine prospects (no ERP customer, no orders) – these are NOT errors
    prospects = []
    for _ in range(185):
        region = rng.choice(list(REGIONS))
        segment = rng.choice(list(SEGMENTS))
        name, form, pc, city = unique_name(segment, region)
        country = REGIONS[region][1]
        vat = "" if rng.random() < 0.55 else (make_fr_vat() if country == "FR" else make_be_vat())
        created = random_date(date(2024, 6, 1), date(2026, 9, 20)).isoformat()
        a = acc(f"{name} {form}".strip(), vat, "", REGIONS[region][0] if REGIONS[region][0] != "AM04" else "AM11", segment, region,
                pc, city, country, email_for(name) if rng.random() < 0.8 else "", phone_for(country) if rng.random() < 0.7 else "",
                created, created)
        prospects.append(a["account_id"])
    PLANTED["prospects"] = len(prospects)

    # planted: invalid VAT (typo -> check digit fails) on BE customer accounts
    be_linked = [a for a in accounts if a["country"] == "BE" and a["vat_number"].startswith("BE") and a["erp_customer_no"]]
    bad = rng.sample(be_linked, 23)
    for a in bad:
        a["vat_number"] = corrupt_vat(a["vat_number"])
    PLANTED["invalid_vat"] = sorted(a["account_id"] for a in bad)

    # planted: customer accounts where nobody filled in the VAT number
    no_vat = rng.sample([a for a in accounts if a["erp_customer_no"] and a["vat_number"] and a["account_id"] not in PLANTED["invalid_vat"]], 18)
    for a in no_vat:
        a["vat_number"] = ""
    PLANTED["customer_without_vat"] = sorted(a["account_id"] for a in no_vat)

    # planted: no email and no phone
    for a in rng.sample([a for a in accounts if a["erp_customer_no"]], 64):
        a["email"], a["phone"] = "", ""

    # planted: postcode in the wrong format for the country
    wrong_pc = rng.sample([a for a in accounts if a["erp_customer_no"]], 14)
    for a in wrong_pc:
        a["postcode"] = f"B-{a['postcode']}" if a["country"] == "BE" else a["postcode"][:4]
    PLANTED["wrong_postcode"] = sorted(a["account_id"] for a in wrong_pc)
    return accounts


def build_opportunities(accounts):
    stages = ["Prospectie", "Kwalificatie", "Offerte", "Onderhandeling", "Gewonnen", "Verloren"]
    lost_reasons = ["Prijs", "Concurrent", "Geen budget", "Timing", "Geen reactie"]
    opps = []
    n = 0
    stale_open = 0
    for a in accounts:
        k = rng.choices([0, 1, 2, 3], [0.35, 0.40, 0.18, 0.07])[0]
        if a["erp_customer_no"] == "" and a["vat_number"] == "" and rng.random() < 0.3:
            k += 1
        for _ in range(k):
            n += 1
            created = random_date(date(2025, 1, 1), date(2026, 9, 25))
            age = daterange_days(created, END)
            if age > 150:
                stage = rng.choices(stages, [0.02, 0.03, 0.05, 0.04, 0.48, 0.38])[0]
            elif age > 60:
                stage = rng.choices(stages, [0.08, 0.12, 0.16, 0.12, 0.30, 0.22])[0]
            else:
                stage = rng.choices(stages, [0.22, 0.24, 0.26, 0.16, 0.07, 0.05])[0]
            amount = round(rng.lognormvariate(8.4, 0.9), -1)
            close = created + timedelta(days=rng.randint(20, 120))
            if stage in {"Gewonnen", "Verloren"}:
                last_update = min(END, close)
                close = min(close, END)
            else:
                if rng.random() < 0.28:  # forgotten deals
                    last_update = created + timedelta(days=rng.randint(0, 25))
                    stale_open += 1
                else:
                    last_update = random_date(max(created, END - timedelta(days=45)), END)
            if stage in {"Offerte", "Onderhandeling"} and rng.random() < 0.07:
                amount_s = ""
            else:
                amount_s = f"{amount:.2f}"
            owner = a["owner_rep"]
            opps.append([f"OPP-{70000 + n}", a["account_id"], owner, stage, amount_s, close.isoformat(), created.isoformat(),
                         min(last_update, END).isoformat(), rng.choice(lost_reasons) if stage == "Verloren" else ""])
    PLANTED["opportunities_forgotten"] = stale_open
    return opps


# --------------------------------------------------------------------------- targets, legacy export, finance

def build_targets(lines):
    by = {}
    for l in lines:
        if l["doc_type"] != "F" or l["customer_no"] == "C99999" or not l["rep_code"]:
            continue
        d = l["invoice_date"]
        if d.year == 2025:
            by[(l["rep_code"], d.month)] = by.get((l["rep_code"], d.month), 0) + l["line_amount"]
    rows = []
    for month in range(1, 13):
        for rep, *_ in REPS:
            base = by.get((rep, month), 0)
            if rep == "AM04":
                base = base if month <= 3 else 0
            if rep == "AM11":
                base = by.get(("AM04", month), 0) if month >= 4 else 0
            if rep == "AM07" and month >= 6:
                base *= 0.55  # Hainaut moves to AM12
            if rep == "AM12":
                base = by.get(("AM07", month), 0) * 0.45 if month >= 6 else 0
            if base <= 0:
                continue
            rows.append([2026, month, rep, int(round(base * 1.06 / 500) * 500)])
    return rows


def main():
    products = build_products()
    customers = build_customers()
    lines, histories = build_invoices(customers, products)
    accounts = build_crm(customers, histories)
    opps = build_opportunities(accounts)
    targets = build_targets(lines)

    write_csv("erp_products.csv", ["sku", "description", "category", "brand", "unit_cost", "list_price", "active"], products)
    write_csv("erp_customers.csv", ["customer_no", "name", "vat_number", "postcode", "city", "country", "language", "segment", "territory", "created_on"],
              [[c["customer_no"], c["name"], c["vat"], c["postcode"], c["city"], c["country"], c["language"], c["segment"], c["region"], c["created"]]
               for c in customers])
    write_csv("erp_customer_rep_history.csv", ["customer_no", "rep_code", "valid_from", "valid_to"],
              [[k, r, a, b] for k, hist in histories.items() for r, a, b in hist])
    write_csv("erp_sales_reps.csv", ["rep_code", "name", "region", "team", "email", "start_date", "end_date"], [list(r) for r in REPS])
    write_csv("erp_invoice_lines.csv",
              ["invoice_no", "doc_type", "invoice_date", "customer_no", "sku", "qty", "unit_price", "discount_pct", "line_amount", "unit_cost", "rep_code"],
              [[l["invoice_no"], l["doc_type"], l["invoice_date"].isoformat(), l["customer_no"], l["sku"], l["qty"], f"{l['unit_price']:.2f}",
                l["discount_pct"], f"{l['line_amount']:.2f}", f"{l['unit_cost']:.2f}", l["rep_code"]] for l in lines])
    write_csv("crm_accounts.csv", ["account_id", "name", "vat_number", "erp_customer_no", "owner_rep", "segment", "region", "postcode", "city",
                                   "country", "email", "phone", "created_at", "last_activity"],
              [[a[k] for k in ["account_id", "name", "vat_number", "erp_customer_no", "owner_rep", "segment", "region", "postcode", "city",
                               "country", "email", "phone", "created_at", "last_activity"]] for a in accounts])
    write_csv("crm_opportunities.csv", ["opportunity_id", "account_id", "owner_rep", "stage", "amount", "expected_close", "created_at",
                                        "last_update", "lost_reason"], opps)
    write_csv("sales_targets_2026.csv", ["year", "month", "rep_code", "target_amount"], targets)

    # the legacy weekly Excel: an append-only export of ALL invoice lines, credit notes included as positive amounts.
    # On 2026-08-14 the export job ran twice and the day was appended again.
    q3 = [l for l in lines if date(2026, 7, 1) <= l["invoice_date"] <= date(2026, 9, 30)]
    legacy = q3 + [l for l in q3 if l["invoice_date"] == DUPLICATE_EXPORT_DAY]
    legacy.sort(key=lambda l: (l["invoice_date"], l["invoice_no"], l["sku"]))
    write_csv("legacy_sales_export_2026Q3.csv", ["Datum", "Factuur", "Klant", "Artikel", "Verkoper", "Bedrag"],
              [[l["invoice_date"].isoformat(), l["invoice_no"], l["customer_no"], l["sku"], l["rep_code"], f"{l['line_amount']:.2f}"] for l in legacy])
    PLANTED["duplicate_export_day"] = DUPLICATE_EXPORT_DAY.isoformat()

    # finance: revenue booked on GL 700000, net of credit notes, staff shop excluded (posted on GL 740000)
    fin = {}
    for l in q3:
        if l["customer_no"] == "C99999":
            continue
        sign = 1 if l["doc_type"] == "F" else -1
        key = l["invoice_date"].strftime("%Y-%m")
        fin[key] = round(fin.get(key, 0) + sign * l["line_amount"], 2)
    write_csv("finance_revenue_2026Q3.csv", ["period", "gl_account", "description", "amount"],
              [[k, "700000", "Omzet handelsgoederen", f"{v:.2f}"] for k, v in sorted(fin.items())])

    with open(RAW / "_planted.json", "w", encoding="utf-8") as fh:
        json.dump(PLANTED, fh, indent=2, ensure_ascii=False)
    print(f"products {len(products)} · customers {len(customers)} · invoice lines {len(lines)} · CRM accounts {len(accounts)} · opportunities {len(opps)}")


if __name__ == "__main__":
    main()
