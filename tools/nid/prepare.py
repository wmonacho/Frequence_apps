"""Filtre et note les annonces Bien'ici (T2/T3 Nice ≤ 1100 € CC, sans colocation) pour Fréquence Nid."""
import json, math, re, html, sys
HOME = (43.698105, 7.272598)   # 12 avenue Félix Faure, 06000 Nice (Base Adresse Nationale)
# Vieux-Nice exclu : entre le boulevard Jean-Jaurès et la colline du Château (rectangle approximatif)
VIEUX = (43.6940, 43.6998, 7.2738, 7.2815)
BUDGET = 1100   # € par mois charges comprises
COLOC_WORDS = r"coloc|chambre (?:meubl[ée]e )?(?:à|a) louer|chambre dans (?:un|une)|flat ?shar"
LOIN_WORDS = r"madeleine|parc imp[ée]rial|cimiez|saint[- ]isidore|ariane|pasteur|gairaut|fabron|caucade|magnan|saint[- ]augustin|bon[- ]voyage|pessicart|las planas|f[ée]ric|nice nord|saint[- ]maurice|lib[ée]ration|gorbella|ray\b|valrose|saint[- ]pierre|arenas|californie|lanterne|st[- ]antoine|bellet|mont[- ]alban|vinaigrier|corniche|l.abadie|trinit[ée]|saint[- ]laurent|cagnes|villefranche"
VIEUX_WORDS = r"vieille ville|place rossetti|rue droite|rue pairoli[eè]re"
CORE = {"Carré d'or", "Centre-ville", "Carabacel", "Médecin", "Garibaldi", "Le Port",
        "Promenade des Anglais - Rue de France", "Riquier", "Mont-Boron", "Thiers - Musicien", "Acropolis - République", "Saint-Roch"}
ZONE = {"Carré d'or": "hypercentre", "Centre-ville": "hypercentre", "Carabacel": "hypercentre",
        "Médecin": "hypercentre", "Garibaldi": "hypercentre", "Promenade des Anglais - Rue de France": "hypercentre",
        "Thiers - Musicien": "hypercentre", "Acropolis - République": "hypercentre",
        "Le Port": "port", "Riquier": "port", "Mont-Boron": "port", "Saint-Roch": "port"}
CENTRE_WORDS = r"garibaldi|mass[ée]na|carr[ée] d.or|jean[- ]m[ée]decin|hyper[- ]?centre|port de nice|le port|place du pin|segurane|lympia|centre[- ]ville"

def dist(a, b):
    R = 6371000; p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp = p2 - p1; dl = math.radians(b[1] - a[1])
    return 2 * R * math.asin(math.sqrt(math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2))

def clean(t):
    t = re.sub(r"<br\s*/?>", "\n", t or "", flags=re.I)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()

def has(p, t): return re.search(p, t, re.I) is not None

def prepare(ads):
    out = []
    for a in ads:
        d = (a.get("district") or {}).get("libelle") or "Nice"
        desc = clean(a.get("description"))
        txt = (a.get("title") or "") + "\n" + desc
        b = a.get("blurInfo") or {}; pos = b.get("position") or {}
        precise = b.get("type") in ("exact", "disk") and pos.get("lat")
        dm = round(dist(HOME, (pos["lat"], pos["lon"]))) if precise else None
        surf = a.get("surfaceArea") or 0
        bed = a.get("bedroomsQuantity") or 0
        dpe = (a.get("energyClassification") or "").upper() or None
        # --- filtres durs
        if bed < 1 or surf < 26 or dpe == "G": continue
        if (a.get("price") or 9999) > BUDGET: continue
        if a.get("flatSharing") or has(COLOC_WORDS, txt): continue
        tete = txt[:400]   # titre et début de description : là où l'annonce dit où est le bien
        in_zone = d in CORE or (d == "Nice" and has(CENTRE_WORDS, tete) and not has(LOIN_WORDS, tete))
        if not in_zone: continue
        if d == "Vieux Nice" or has(VIEUX_WORDS, a.get("title") or ""): continue
        if precise and VIEUX[0] <= pos["lat"] <= VIEUX[1] and VIEUX[2] <= pos["lon"] <= VIEUX[3]: continue
        if precise and dm > 1800: continue
        zone = ZONE.get(d) or ("port" if precise and pos["lon"] > 7.282 else "hypercentre")
        # --- critères
        lum = has(r"lumineu|lumi[eè]re|ensoleill|traversant|baie vitr|vue d[ée]gag|[ée]tage [ée]lev|plein sud|exposition sud", txt) or has(r"sud", a.get("exposition") or "")
        cuis = has(r"cuisine[^.\n]{0,40}(?<!non )[ée]quip|cuisine[^.\n]{0,25}am[ée]nag[ée]e et [ée]quip|kitchenette [ée]quip|cuisine ouverte [ée]quip", txt)
        reno = has(r"r[ée]nov|refait|neuf|parfait [ée]tat|tr[èe]s bon [ée]tat|excellent [ée]tat|moderne|r[ée]cent", txt) or (a.get("yearOfConstruction") or 0) >= 1990 or a.get("newProperty")
        etud = has(r"[ée]tudiant|bail 9 mois|bail de 9 mois|bail mobilit", txt)
        rdc = (a.get("floor") == 0) or has(r"rez[- ]de[- ]chauss", txt)
        sans_asc = a.get("floor") and a.get("floor") >= 4 and a.get("hasElevator") is False
        s = 50
        if dm is not None: s += 20 if dm <= 400 else 15 if dm <= 800 else 10 if dm <= 1200 else 4 if dm <= 1700 else 0
        s += 8 * lum + 8 * cuis + 8 * bool(reno)
        s += {"A": 6, "B": 6, "C": 6, "D": 2, "E": -2, "F": -8}.get(dpe, 0)
        s += 5 if surf >= 45 else 2 if surf >= 38 else 0
        s += 3 if (a.get("price") or 9999) <= 1000 else 0
        s -= 10 * etud + 5 * rdc + 3 * bool(sans_asc)
        atouts, alertes = [], []
        if dm is not None and dm <= 800: atouts.append(f"À {round(dm/80)} min à pied du 12 avenue Félix Faure")
        if lum: atouts.append("Lumineux d'après l'annonce")
        if cuis: atouts.append("Cuisine équipée")
        if reno: atouts.append("Rénové ou en bon état")
        if dpe in ("A", "B", "C"): atouts.append(f"Bonne performance énergétique (DPE {dpe})")
        if a.get("hasTerrace") or (a.get("balconyQuantity") or 0) > 0: atouts.append("Balcon ou terrasse")
        if a.get("hasElevator"): atouts.append("Ascenseur")
        if etud: alertes.append("Annonce orientée étudiants ou bail court : vérifie que tu es éligible")
        if dpe == "F": alertes.append("DPE F : logement énergivore, interdit à la location à partir de 2028")
        if dpe == "E": alertes.append("DPE E : chauffage potentiellement coûteux")
        if not dpe: alertes.append("DPE non indiqué")
        if not cuis: alertes.append("Cuisine équipée non mentionnée")
        if not lum: alertes.append("Luminosité non mentionnée : à vérifier en visite")
        if rdc: alertes.append("Rez-de-chaussée")
        if sans_asc: alertes.append(f"{a['floor']}e étage sans ascenseur")
        if dm is None: alertes.append("Adresse précise non communiquée : distance approximative")
        if surf < 32: alertes.append(f"Petite surface ({surf:g} m²)")
        out.append({
            "id": re.sub(r"[^a-z0-9-]", "-", a["id"].lower())[:80],
            "src": a.get("src", "bienici"), "srcId": a["id"], "srcLabel": a.get("srcLabel", "Bien'ici"),
            "url": a.get("url") or "https://www.bienici.com/annonce/" + a["id"],
            "title": (a.get("title") or "").strip() or f"{a.get('roomsQuantity')} pièces · {surf:g} m²",
            "price": round(a.get("price") or 0), "charges": a.get("charges"), "deposit": a.get("safetyDeposit"),
            "fees": round(a["agencyRentalFee"]) if a.get("agencyRentalFee") else None,
            "rooms": a.get("roomsQuantity"), "bedrooms": bed, "surface": surf, "floor": a.get("floor"),
            "elevator": a.get("hasElevator"), "furnished": a.get("isFurnished"),
            "balcony": bool(a.get("hasTerrace") or (a.get("balconyQuantity") or 0) > 0),
            "dpe": dpe, "ges": (a.get("greenhouseGazClassification") or "").upper() or None,
            "heating": a.get("heating"), "exposure": a.get("exposition"), "year": a.get("yearOfConstruction"),
            "available": (a.get("availableDate") or "")[:10] or None, "published": (a.get("publicationDate") or "")[:10],
            "agency": a.get("accountDisplayName"), "district": d, "zone": zone,
            "lat": pos.get("lat"), "lng": pos.get("lon"), "precise": bool(precise), "dist": dm,
            "walk": round(dm / 80) if dm is not None else None,
            "lum": lum, "kitchen": cuis, "renovated": bool(reno), "student": etud,
            "score": max(0, min(100, s)), "pros": atouts, "cons": alertes,
            "description": desc[:2500],
            "photoUrls": [p.get("url") for p in (a.get("photos") or []) if p.get("url")][:8],
        })
    out.sort(key=lambda x: -x["score"])
    return dedoublonner(out)


def _mots(t):
    return set(re.findall(r"[a-zà-ÿ]{4,}", (t or "").lower()[:600]))


def meme_bien(x, y):
    """Deux annonces décrivent-elles le même appartement (même bien publié par deux agences ou deux sites) ?"""
    if x["rooms"] != y["rooms"] or not x["surface"] or not y["surface"]:
        return False
    if abs(x["price"] - y["price"]) > max(30, 0.03 * x["price"]) or abs(x["surface"] - y["surface"]) > max(2, 0.04 * x["surface"]):
        return False
    if x["precise"] and y["precise"]:
        return dist((x["lat"], x["lng"]), (y["lat"], y["lng"])) <= 300
    a, b = _mots(x["description"]), _mots(y["description"])
    sim = len(a & b) / max(1, min(len(a), len(b)))
    return sim >= 0.45 or (x["zone"] == y["zone"] and abs(x["price"] - y["price"]) <= 5 and abs(x["surface"] - y["surface"]) <= 0.6)


def dedoublonner(items):
    """Garde une seule fiche par bien (la plus complète) et liste les autres annonces dans alsoOn."""
    def qualite(x):
        return (x["precise"], len(x.get("photoUrls") or []), x["src"] == "bienici", len(x["description"] or ""))
    gardes = []
    for x in sorted(items, key=qualite, reverse=True):
        double = next((g for g in gardes if meme_bien(g, x)), None)
        if double:
            double.setdefault("alsoOn", []).append({"label": x["srcLabel"] + (" · " + x["agency"] if x.get("agency") and x["src"] == "bienici" else ""), "url": x["url"]})
            double["photoUrls"] = double.get("photoUrls") or x.get("photoUrls")
        else:
            gardes.append(x)
    gardes.sort(key=lambda x: -x["score"])
    return gardes

if __name__ == "__main__":
    ads = json.load(open(sys.argv[1]))
    res = prepare(ads)
    json.dump(res, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
    print(len(res), "annonces retenues")
    for r in res[:60]:
        print(r["score"], r["price"], r["surface"], r["district"], r["dist"], r["dpe"], "L" if r["lum"] else "-", "C" if r["kitchen"] else "-", "R" if r["renovated"] else "-", "E" if r["student"] else "", len(r["photoUrls"]), r["title"][:40])
