"""Collecteurs de Fréquence Nid (+ alertes Jinka lues dans Gmail par la tâche du matin) : chaque source renvoie des annonces au format « Bien'ici »
(mêmes noms de champs), plus src, srcLabel et url, pour passer dans prepare().

Sources : Bien'ici (agrégateur d'agences), Orpi, Laforêt (API), Foncia (API), Locservice (particuliers).
Leboncoin, SeLoger, PAP, Logic-Immo et Jinka refusent les robots ou demandent un compte.
"""
import html, json, re, subprocess, sys, unicodedata, urllib.parse
import concurrent.futures as cf

UA = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/130 Mobile Safari/537.36"
BUDGET = 1100


def curl(url, data=None, headers=()):
    cmd = ["curl", "-s", "-L", "-m", "40", "-A", UA]
    for h in headers:
        cmd += ["-H", h]
    if data is not None:
        cmd += ["-X", "POST", "-H", "Content-Type: application/json", "-d", json.dumps(data)]
    return subprocess.run(cmd + [url], capture_output=True, text=True).stdout


def log(*a):
    print(*a, file=sys.stderr)


# ---------------------------------------------------------------- Bien'ici
def bienici():
    ads, start = [], 0
    while True:
        f = {"size": 100, "from": start, "showAllModels": False, "filterType": "rent",
             "propertyType": ["flat"], "maxPrice": BUDGET, "minRooms": 2, "maxRooms": 3,
             "page": start // 100 + 1, "sortBy": "publicationDate", "sortOrder": "desc",
             "onTheMarket": [True], "zoneIdsByTypes": {"zoneIds": ["-170100"]}}
        d = json.loads(curl("https://www.bienici.com/realEstateAds.json?filters=" + urllib.parse.quote(json.dumps(f))))
        page = d.get("realEstateAds") or []
        for a in page:
            a["src"], a["srcLabel"], a["url"] = "bienici", "Bien'ici", "https://www.bienici.com/annonce/" + a["id"]
        ads += page
        start += 100
        if not page or start >= (d.get("total") or 0) or start >= 1000:
            return ads


# ---------------------------------------------------------------- Orpi
def orpi():
    items = {}
    for sort in ("date-down", "price-up", "surface-down"):
        u = ("https://www.orpi.com/recherche?realEstateTypes%5B0%5D=appartement&transactions%5B0%5D=rent"
             f"&locations%5B0%5D%5Bvalue%5D=nice&maxPrice={BUDGET}&nbRooms%5B0%5D=2&nbRooms%5B1%5D=3&sort={sort}&layoutType=list")
        m = re.search(r'data-result="([^"]*)"', curl(u))
        if m:
            for it in json.loads(html.unescape(m.group(1))).get("items", []):
                items[it["id"]] = it

    def detail(it):
        url = "https://www.orpi.com/annonce-location-" + it["slug"] + "/"
        m = re.search(r'data-estate="([^"]*)"', curl(url))
        e = json.loads(html.unescape(m.group(1))) if m else {}
        tags = " ".join(it.get("tags") or [])
        return {
            "id": "orpi-%s" % it["id"], "src": "orpi", "srcLabel": "Orpi", "url": url,
            "title": (it.get("longAd") or "").split(".")[0][:80] or f"Appartement {it.get('nbRooms')} pièces",
            "description": e.get("longAd") or it.get("longAd") or "",
            "price": e.get("price") or it.get("price"), "charges": e.get("chargeReserve"),
            "safetyDeposit": e.get("deposit"), "agencyRentalFee": e.get("agencyCommission"),
            "roomsQuantity": it.get("nbRooms"), "bedroomsQuantity": e.get("nbBedrooms") or max((it.get("nbRooms") or 2) - 1, 1),
            "surfaceArea": e.get("liveableSurface") or it.get("surface"), "floor": e.get("storyLocation"),
            "hasElevator": e.get("elevator"), "isFurnished": None if not tags else ("Meublé" in tags and "Non meublé" not in tags),
            "hasTerrace": e.get("terrace"), "balconyQuantity": 1 if e.get("balcony") else 0,
            "district": {"libelle": (it.get("district") or {}).get("name") or "Nice"},
            "blurInfo": {"type": "exact", "position": {"lat": it.get("latitude"), "lon": it.get("longitude")}} if it.get("latitude") else {},
            "photos": [{"url": p} for p in (it.get("images") or e.get("imagesUrls") or [])],
            "publicationDate": it.get("onMarketSince"), "accountDisplayName": (it.get("agency") or {}).get("name"),
        }
    with cf.ThreadPoolExecutor(6) as ex:
        return list(ex.map(detail, items.values()))


# ---------------------------------------------------------------- Laforêt
def laforet():
    d = json.loads(curl("https://www.laforet.com/api/immo/properties?transaction=rent&types=apartment&cities=06088&perPage=100",
                        headers=["Accept: application/json"]) or "{}")
    keep = [x for x in d.get("data", []) if (x.get("price") or 9999) <= BUDGET and (x.get("rooms") or 0) in (2, 3)]
    out = []
    for x in keep:
        e = json.loads(curl("https://www.laforet.com/api/immo/properties/%s" % x["immo_id"], headers=["Accept: application/json"]) or "{}")
        if not e:
            continue
        desc = re.sub(r"<[^>]+>", " ", e.get("description") or e.get("editorial_description") or "")
        if e.get("kitchen_type") == "equipped" and "cuisine équipée" not in desc.lower():
            desc += "\nCuisine équipée."
        out.append({
            "id": "laforet-%s" % e["immo_id"], "src": "laforet", "srcLabel": "Laforêt", "url": e.get("url"),
            "title": e.get("editorial_title") or f"Appartement {e.get('rooms')} pièces", "description": desc,
            "price": e.get("rent") or e.get("price"), "charges": e.get("provision_charges"), "safetyDeposit": e.get("deposit"),
            "agencyRentalFee": e.get("fees_tenant_amount"), "roomsQuantity": e.get("rooms"), "bedroomsQuantity": e.get("bedrooms"),
            "surfaceArea": e.get("surface"), "floor": e.get("floor"), "hasElevator": e.get("has_lift"), "isFurnished": e.get("is_furnished"),
            "balconyQuantity": e.get("balconies") or 0, "hasTerrace": bool(e.get("terraces")),
            "energyClassification": e.get("dpe_level"), "greenhouseGazClassification": e.get("ges_level"),
            "yearOfConstruction": e.get("year_of_construction"), "heating": e.get("heating_type_label"),
            "district": {"libelle": "Nice"},
            "blurInfo": {"type": "exact", "position": {"lat": e["lat"], "lon": e["lng"]}} if e.get("lat") else {},
            "photos": [{"url": p} for p in e.get("photos") or []],
            "publicationDate": e.get("photos_updated_at"), "accountDisplayName": "Laforêt",
        })
    return out


# ---------------------------------------------------------------- Foncia
def foncia():
    d = json.loads(curl("https://fnc-api.prod.fonciatech.net/annonces/annonces/search",
                        data={"type": "location", "filters": {"localities": {"slugs": ["nice-06"]}, "typesBien": ["appartement"]},
                              "expandNearby": False, "size": 100}) or "{}")
    out = []
    for x in d.get("annonces", []):
        if (x.get("loyer") or 9999) > BUDGET or x.get("nbPiece") not in (2, 3):
            continue
        out.append({
            "id": "foncia-%s" % x["reference"], "src": "foncia", "srcLabel": "Foncia", "url": "https://fr.foncia.com" + x["canonicalUrl"],
            "title": (x.get("titles") or {}).get("breadcrumb") or "Appartement", "description": x.get("description") or "",
            "price": x.get("loyer"), "roomsQuantity": x.get("nbPiece"), "bedroomsQuantity": max(x.get("nbPiece") - 1, 1),
            "surfaceArea": (x.get("surface") or {}).get("habitable"), "energyClassification": x.get("noteConsoEnergie"),
            "greenhouseGazClassification": x.get("noteEmissionGES"), "district": {"libelle": "Nice"},
            "photos": [{"url": p} for p in x.get("medias") or []], "publicationDate": x.get("datePublication"),
            "accountDisplayName": "Foncia",
        })
    return out


# ---------------------------------------------------------------- Locservice (particuliers)
def locservice():
    base = "https://www.locservice.fr/alpes-maritimes-06/location-appartement-nice"
    cands = {}
    for p in range(1, 16):
        s = curl(base + (".html" if p == 1 else f"-p{p}.html"))
        found = 0
        for m in re.finditer(r'data-accommodation-id="(\d+)"(.*?)</article>', s, re.S):
            found += 1
            aid, blk = m.group(1), m.group(2)
            t = re.sub(r"<[^>]+>", " ", blk)
            price = re.search(r"([\d  ]{3,7})\s*€\s*/\s*mois", t)
            price = int(re.sub(r"\D", "", price.group(1))) if price else 9999
            if price <= BUDGET:
                cands[aid] = price
        if not found:
            break

    def detail(aid):
        url = f"{base}/{aid}"
        s = curl(url)
        ld = {}
        for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
            try:
                j = json.loads(m.group(1))
                if isinstance(j, dict) and j.get("@type") == "apartment":
                    ld = j
            except Exception:
                pass
        b = s.find("<body")
        t = re.sub(r"<script.*?</script>|<style.*?</style>|<svg.*?</svg>", "", s[b:], flags=re.S)
        t = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)))
        def num(p):
            m = re.search(p, t)
            return float(re.sub(r"[^\d,]", "", m.group(1)).replace(",", ".")) if m else None
        rooms = num(r"(\d) pièces?\b")
        if rooms not in (2, 3):
            return None
        desc = ld.get("description") or ""
        plus = re.search(r"Les \+ de cette location (.*?) Découvrez", t)
        if plus:
            desc += "\nAtouts : " + plus.group(1)
        dpe = re.search(r"Diagnostic de Performance Énergétique\s*:\s*([A-G])\b", t)
        ges = re.search(r"Émission de Gaz à Effet de Serre\s*:\s*([A-G])\b", t)
        title = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S)
        return {
            "id": "locservice-" + aid, "src": "locservice", "srcLabel": "Locservice", "url": url,
            "title": html.unescape(re.sub(r"<[^>]+>|\s+", " ", title.group(1))).strip() if title else f"Appartement T{int(rooms)}",
            "description": desc, "price": num(r"Loyer \(charges comprises\) ([\d  ]+) €"),
            "charges": num(r"Charges locatives ([\d  ]+) €"), "safetyDeposit": num(r"dépôt de garantie ([\d  ]+) €"),
            "roomsQuantity": int(rooms), "bedroomsQuantity": int(rooms) - 1,
            "surfaceArea": (ld.get("floorSize") or {}).get("value", {}).get("value") if isinstance((ld.get("floorSize") or {}).get("value"), dict) else num(r"(\d+(?:,\d+)?) m²"),
            "isFurnished": (" Meublé " in t[:3000]) or None, "energyClassification": dpe.group(1) if dpe else None,
            "greenhouseGazClassification": ges.group(1) if ges else None, "district": {"libelle": "Nice"},
            "photos": [{"url": p} for p in ld.get("photos") or []], "accountDisplayName": "Particulier (Locservice)",
            "flatSharing": bool(re.search(r"colocation", desc, re.I)),
        }
    with cf.ThreadPoolExecutor(6) as ex:
        return [x for x in ex.map(detail, cands) if x]


# ---------------------------------------------------------------- Jinka (alertes e-mail lues dans Gmail)
def jinka(path):
    """path : JSON écrit par la tâche du matin à partir des e-mails « Nouvelle annonce » de Jinka.
    Chaque entrée : {emailId, site, price, surface, rooms, bedrooms, location, features, photo, url, date, particulier}."""
    try:
        items = json.load(open(path))
    except Exception:
        return []
    out = []
    for x in items:
        site = (x.get("site") or "?").strip()
        if re.search(r"bien.?ici|orpi|laforet|laforêt|foncia|locservice", site, re.I):
            continue   # déjà couvert directement, avec plus de détails
        loc = x.get("location") or "Nice"
        feats = ", ".join(x.get("features") or [])
        out.append({
            "id": "jinka-%s" % x["emailId"], "src": "jinka", "srcLabel": f"Jinka · {site}", "url": x.get("url"),
            "title": f"{loc} · {x.get('rooms')} p. · {x.get('surface')} m²",
            "description": f"{loc}. Annonce {site} repérée par ton alerte Jinka" + (" (particulier)" if x.get("particulier") else "")
                           + (f". {feats}." if feats else ".") + " Description complète sur l'annonce d'origine.",
            "price": x.get("price"), "roomsQuantity": x.get("rooms"),
            "bedroomsQuantity": x.get("bedrooms") or max((x.get("rooms") or 2) - 1, 1), "surfaceArea": x.get("surface"),
            "hasElevator": True if re.search(r"ascenseur", feats, re.I) else None,
            "balconyQuantity": 1 if re.search(r"balcon", feats, re.I) else 0, "hasTerrace": bool(re.search(r"terrasse", feats, re.I)),
            "district": {"libelle": "Nice"}, "trustZone": True,   # la zone est déjà dessinée dans l'alerte Jinka
            "photos": [{"url": x["photo"]}] if x.get("photo") else [], "publicationDate": x.get("date"),
            "accountDisplayName": "Particulier" if x.get("particulier") else site,
        })
    return out


# ---------------------------------------------------------------- Adresse citée dans le texte → position (Base Adresse Nationale)
VOIE = r"(?:rue|avenue|av\.?|boulevard|bd|bld|place|quai|promenade|cours|impasse|mont[ée]e|descente|traverse|all[ée]e|square|esplanade|passage)"
ARRET = r"(?:[,.;:!()\n]|\s(?:à|a|au|aux|proche|pr[èe]s|dans|avec|et|entre|face|c[ôo]t[ée]|sur|en|nice|quartier|secteur|id[ée]al|appartement|immeuble|bel|beau|t2|t3|f2|f3)\b)"
# Voies trop longues : leur « centre » ne dit rien de la position du logement
TROP_LONGUES = r"promenade des anglais|rue de france|gambetta|californie|cimiez|madeleine|mont[- ]boron|fabron|napol[ée]on|route de turin|saint[- ]pierre de f[ée]ric|corniche|pessicart|bellet"


def adresse(txt):
    """Première adresse plausible citée dans le titre ou le début de la description."""
    m = re.search(r"\b(\d{1,3}\s*(?:bis|ter)?\s*,?\s*)?(" + VOIE + r"\s+(?:de la |de l'|de l’|des |du |de |d'|d’)?[^\d,.;:!()\n]{3,40}?)(?=" + ARRET + r"|$)", txt, re.I)
    if not m:
        return None
    voie = re.sub(r"\s+", " ", m.group(2)).strip(" -")
    if len(voie.split()) < 2 or re.search(TROP_LONGUES, voie, re.I) or re.match(r"place (?:de (?:stationnement|parking)|pour|libre|dispo)", voie, re.I):
        return None
    return ((m.group(1) or "").strip(" ,") + " " + voie).strip()


def geocoder(ads):
    """Ajoute une position aux annonces sans coordonnées qui citent une rue (Locservice, Foncia, Bien'ici masqué…)."""
    def un(a):
        b = a.get("blurInfo") or {}
        if b.get("type") in ("exact", "disk") or (a.get("price") or 9999) > BUDGET:
            return
        txt = (a.get("title") or "") + "\n" + re.sub(r"<[^>]+>", " ", a.get("description") or "")[:600]
        q = adresse(txt)
        if not q:
            return
        try:
            r = json.loads(curl("https://api-adresse.data.gouv.fr/search/?" + urllib.parse.urlencode({"q": q + " Nice", "citycode": "06088", "limit": 1})))
            f = (r.get("features") or [None])[0]
        except Exception:
            return
        if not f:
            return
        pr = f["properties"]
        # le nom trouvé doit reprendre un mot significatif de la voie citée (la recherche est tolérante aux fautes)
        sans = lambda t: unicodedata.normalize("NFD", t.lower()).encode("ascii", "ignore").decode()
        mots = [w for w in re.findall(r"[a-z]{4,}", sans(q)) if not re.fullmatch(VOIE, w)]
        nom = sans(pr.get("name", ""))
        if pr.get("score", 0) < 0.6 or not any(w[:5] in nom for w in mots):
            return
        lon, lat = f["geometry"]["coordinates"]
        a["blurInfo"] = {"type": "exact" if pr.get("type") == "housenumber" else "street", "position": {"lat": lat, "lon": lon}}
        a["geoLabel"] = pr.get("label")
    with cf.ThreadPoolExecutor(8) as ex:
        list(ex.map(un, ads))
    return sum(1 for a in ads if a.get("geoLabel"))


SOURCES = {"bienici": bienici, "orpi": orpi, "laforet": laforet, "foncia": foncia, "locservice": locservice}


def collect(jinka_path=None):
    ads, bilan = [], {}
    if jinka_path:
        got = jinka(jinka_path)
        bilan["jinka"] = len(got)
        ads += got
    for name, fn in SOURCES.items():
        try:
            got = fn()
        except Exception as e:  # une source en panne ne bloque pas les autres
            log(f"{name}: échec ({e})")
            got = []
        bilan[name] = len(got)
        ads += got
    try:
        bilan["adressesTrouvees"] = geocoder(ads)
    except Exception as e:
        log(f"géocodage: échec ({e})")
    return ads, bilan


if __name__ == "__main__":
    ads, bilan = collect()
    json.dump(ads, open(sys.argv[1], "w"), ensure_ascii=False)
    print(bilan)
