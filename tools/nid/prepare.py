"""Filtre et note les annonces Bien'ici (T2/T3 Nice ≤ 1100 € CC, sans colocation) pour Fréquence Nid."""
import json, math, re, html, sys
HOME = (43.698105, 7.272598)   # 12 avenue Félix Faure, 06000 Nice (Base Adresse Nationale)
# Vieux-Nice exclu : entre le boulevard Jean-Jaurès et la colline du Château (rectangle approximatif)
VIEUX = (43.6940, 43.6998, 7.2738, 7.2815)
BUDGET = 1100   # € par mois charges comprises
COLOC_WORDS = r"coloc|chambre (?:meubl[ée]e )?(?:à|a) louer|chambre dans (?:un|une)|flat ?shar"
LOIN_WORDS = r"saint[- ]isidore|ariane|gairaut|caucade|saint[- ]augustin|pessicart|las planas|f[ée]ric|saint[- ]pierre|arenas|lanterne|st[- ]antoine|bellet|mont[- ]alban|vinaigrier|corniche|l.abadie|trinit[ée]|saint[- ]laurent|cagnes|villefranche"
VIEUX_WORDS = r"vieille ville|place rossetti|rue droite|rue pairoli[eè]re"
CORE = {"Carré d'or", "Centre-ville", "Carabacel", "Médecin", "Garibaldi", "Le Port",
        "Promenade des Anglais - Rue de France", "Riquier", "Mont-Boron", "Thiers - Musicien", "Acropolis - République", "Saint-Roch"}
ZONE = {"Carré d'or": "hypercentre", "Centre-ville": "hypercentre", "Carabacel": "hypercentre",
        "Médecin": "hypercentre", "Garibaldi": "hypercentre", "Promenade des Anglais - Rue de France": "hypercentre",
        "Thiers - Musicien": "hypercentre", "Acropolis - République": "hypercentre",
        "Le Port": "port", "Riquier": "port", "Mont-Boron": "port", "Saint-Roch": "port"}
CENTRE_WORDS = r"garibaldi|mass[ée]na|carr[ée] d.or|jean[- ]m[ée]decin|hyper[- ]?centre|port de nice|le port|place du pin|segurane|lympia|centre[- ]ville"

# --- Secteur voulu (hypercentre + Port) et tolérance dégressive
# Le secteur est l'union de quatre disques. Au-delà, une annonce est gardée si elle compense la distance :
#   palier 1 (jusqu'à 500 m hors secteur)  : au moins 2 qualités, loyer ≤ 1 100 €
#   palier 2 (500 m à 1 km)                 : au moins 3 qualités, loyer ≤ 1 000 €
#   palier 3 (1 à 1,5 km)                   : au moins 4 qualités, loyer ≤ 900 €
#   palier 4 (1,5 à 2,5 km)                 : au moins 4 qualités, loyer ≤ 800 €
# Qualités : cuisine équipée, lumineux, rénové, ≥ 45 m², DPE A-C, balcon ou terrasse,
# et « loyer ≤ 1 000 € » au palier 1 seulement (aux paliers suivants le plafond l'impose déjà).
SECTEUR = [((43.6968, 7.2668), 450, "hypercentre"),   # Masséna, Carré d'Or
           ((43.7018, 7.2668), 400, "hypercentre"),   # Jean-Médecin
           ((43.6990, 7.2760), 450, "hypercentre"),   # Félix Faure, Garibaldi
           ((43.6962, 7.2855), 400, "port")]          # Port Lympia
PALIERS = [0, 500, 1000, 1500, 2500]
EXIGE = {1: (2, 1100), 2: (3, 1000), 3: (4, 900), 4: (4, 800)}
# Quartiers Bien'ici dans le secteur (position non communiquée) : palier 0
COEUR = {"Carré d'or", "Centre-ville", "Médecin", "Garibaldi", "Le Port"}
# Centres approximatifs des quartiers et repères voisins, pour les annonces sans position précise
LIEUX = {"Carabacel": (43.7030, 7.2735), "Thiers - Musicien": (43.7020, 7.2590), "Acropolis - République": (43.7055, 7.2790),
         "Riquier": (43.7035, 7.2885), "Saint-Roch": (43.7115, 7.2860), "Mont-Boron": (43.6990, 7.3000),
         "Promenade des Anglais - Rue de France": (43.6955, 7.2580), "Gambetta": (43.7020, 7.2520), "Gambetta - Fleurs": (43.7000, 7.2530),
         "Vernier": (43.7065, 7.2545), "Libération": (43.7135, 7.2620), "Saint-Lambert - Bas-Cimiez": (43.7120, 7.2690),
         "Bas-Cimiez": (43.7130, 7.2700), "Baumettes": (43.6940, 7.2480), "Cessole": (43.7150, 7.2560), "Borriglione": (43.7165, 7.2620),
         "Valrose": (43.7170, 7.2690), "Parc Impérial - Le Piol": (43.7090, 7.2510), "Magnan": (43.6970, 7.2420),
         "Saint-Philippe - Estienne d'Orves": (43.7000, 7.2420), "Cimiez": (43.7210, 7.2750), "Pasteur": (43.7230, 7.2840),
         "Madeleine": (43.7110, 7.2380), "Fabron": (43.6900, 7.2300), "Saint-Sylvestre": (43.7240, 7.2640), "Le Ray": (43.7250, 7.2560),
         "Rimiez": (43.7330, 7.2720), "Californie - Carras": (43.6870, 7.2300), "Caucade": (43.6880, 7.2150),
         "Sainte-Marguerite": (43.6880, 7.2100), "Arenas": (43.6720, 7.2130)}
# Rues et repères cités dans le texte : None = dans le secteur, sinon position approximative
GENERIQUE = r"hyper[- ]?centre|centre[- ]ville|nice centre"   # trop vague : compte seulement si aucun lieu précis n'est cité
RUES = [(r"garibaldi|mass[ée]na|carr[ée] d.or|jean[- ]m[ée]decin|port de nice|le port|place du pin|s[ée]gurane|lympia"
         r"|gioffredo|pastorelli|h[ôo]tel des postes|rue de la libert[ée]|rue paradis|rue de l.op[ée]ra|place magenta|massenet|dalpozzo"
         r"|rue de russie|victor[- ]hugo|longchamp|chauvain|dubouchage|biscarra|gubernatis|avenue de verdun|alsace[- ]lorraine|f[ée]lix faure"
         r"|bonaparte|cassini|lascaris|foresta|rue arson|[iî]le de beaut[ée]|fod[ée]r[ée]|scaliero|rue barla|bavastro|emmanuel philibert", None),
        (r"musiciens|rossini|berlioz|gounod|meyerbeer", (43.7005, 7.2595)),
        (r"gare thiers|gare de nice|avenue thiers|nice[- ]ville", (43.7045, 7.2620)),
        (r"carabacel", (43.7030, 7.2735)), (r"r[ée]publique|acropolis", (43.7055, 7.2790)),
        (r"riquier", (43.7035, 7.2885)), (r"saint[- ]roch", (43.7115, 7.2860)), (r"mont[- ]boron", (43.6990, 7.3000)),
        (r"gambetta", (43.7020, 7.2520)), (r"vernier", (43.7065, 7.2545)), (r"lib[ée]ration", (43.7135, 7.2620)),
        (r"borriglione", (43.7165, 7.2620)), (r"cessole", (43.7150, 7.2560)), (r"valrose", (43.7170, 7.2690)),
        (r"baumettes", (43.6940, 7.2480)), (r"parc imp[ée]rial", (43.7090, 7.2510)), (r"magnan", (43.6970, 7.2420)),
        (r"cimiez", (43.7210, 7.2750)), (r"pasteur", (43.7230, 7.2840)), (r"madeleine", (43.7110, 7.2380)),
        (r"fabron", (43.6900, 7.2300)), (r"saint[- ]maurice", (43.7180, 7.2680)), (r"gorbella", (43.7230, 7.2600)),
        (r"\bray\b", (43.7250, 7.2560)), (r"californie", (43.6870, 7.2300)), (r"nice nord", (43.7200, 7.2600)),
        (r"saint[- ]philippe", (43.7000, 7.2420)), (r"bon[- ]voyage", (43.7120, 7.2950))]

def hors_secteur(p):
    """Distance (m) entre un point et le secteur voulu, et la zone la plus proche."""
    best = min(SECTEUR, key=lambda z: dist(p, z[0]) - z[1])
    return max(0, dist(p, best[0]) - best[1]), best[2]

def position_secteur(a, d, tete, pos):
    """(mètres hors secteur, zone) ou (None, None) si le bien est trop loin ou introuvable."""
    if pos: return hors_secteur((pos["lat"], pos["lon"]))
    if d in COEUR: return 0, ZONE.get(d, "hypercentre")
    if d in LIEUX: return hors_secteur(LIEUX[d])
    if d != "Nice": return None, None                      # quartier connu de Bien'ici mais lointain
    if has(LOIN_WORDS, tete): return None, None             # quartier très éloigné cité (Ariane, Corniche, Bellet…)
    trouves = [(m.start(), p) for r, p in RUES for m in [re.search(r, tete, re.I)] if m]
    if not trouves:
        return (0, "hypercentre") if a.get("trustZone") or has(GENERIQUE, tete) else (None, None)
    _, p = min(trouves, key=lambda t: t[0])               # le premier lieu cité est en général celui du bien
    if p: return hors_secteur(p)
    return 0, "port" if has(r"\bport\b|lympia|riquier|s[ée]gurane|place du pin|bonaparte|cassini|lascaris|arson|fod[ée]r|scaliero", tete) else "hypercentre"

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
        rue = b.get("type") == "street" and pos.get("lat")       # position de la rue citée dans l'annonce
        situe = precise or rue
        dm = round(dist(HOME, (pos["lat"], pos["lon"]))) if situe else None
        surf = a.get("surfaceArea") or 0
        bed = a.get("bedroomsQuantity") or 0
        dpe = (a.get("energyClassification") or "").upper() or None
        # --- filtres durs
        if bed < 1 or surf < 26 or dpe == "G": continue
        if (a.get("price") or 9999) > BUDGET: continue
        if a.get("flatSharing") or has(COLOC_WORDS, txt): continue
        tete = txt[:400]   # titre et début de description : là où l'annonce dit où est le bien
        if d == "Vieux Nice" or has(VIEUX_WORDS, a.get("title") or ""): continue
        if situe and VIEUX[0] <= pos["lat"] <= VIEUX[1] and VIEUX[2] <= pos["lon"] <= VIEUX[3]: continue
        exces, ou = position_secteur(a, d, tete, pos if situe else None)
        if exces is None or exces > PALIERS[-1]: continue
        palier = next(i for i, lim in enumerate(PALIERS) if exces <= lim)
        zone = ZONE.get(d) or ou
        # --- critères
        lum = has(r"lumineu|lumi[eè]re|ensoleill|traversant|baie vitr|vue d[ée]gag|[ée]tage [ée]lev|plein sud|exposition sud", txt) or has(r"sud", a.get("exposition") or "")
        cuis = has(r"cuisine[^.\n]{0,40}(?<!non )[ée]quip|cuisine[^.\n]{0,25}am[ée]nag[ée]e et [ée]quip|kitchenette [ée]quip|cuisine ouverte [ée]quip", txt)
        reno = has(r"r[ée]nov|refait|neuf|parfait [ée]tat|tr[èe]s bon [ée]tat|excellent [ée]tat|moderne|r[ée]cent", txt) or (a.get("yearOfConstruction") or 0) >= 1990 or a.get("newProperty")
        etud = has(r"[ée]tudiant|bail 9 mois|bail de 9 mois|bail mobilit", txt)
        rdc = (a.get("floor") == 0) or has(r"rez[- ]de[- ]chauss", txt)
        sans_asc = a.get("floor") and a.get("floor") >= 4 and a.get("hasElevator") is False
        prix = a.get("price") or 9999
        balcon = bool(a.get("hasTerrace") or (a.get("balconyQuantity") or 0) > 0)
        qualites = [(cuis, "cuisine équipée"), (lum, "lumineux"), (bool(reno), "rénové"), (surf >= 45, f"{surf:g} m²"),
                    (prix <= 1000, "loyer ≤ 1 000 €"), (dpe in ("A", "B", "C"), f"DPE {dpe}"), (balcon, "balcon ou terrasse")]
        if palier >= 2: qualites = [x for x in qualites if x[1] != "loyer ≤ 1 000 €"]
        q = [l for v, l in qualites if v]
        if palier and (len(q) < EXIGE[palier][0] or prix > EXIGE[palier][1]): continue
        s = 50
        if dm is not None: s += 20 if dm <= 400 else 15 if dm <= 800 else 10 if dm <= 1200 else 4 if dm <= 1700 else 0
        s += 8 * lum + 8 * cuis + 8 * bool(reno)
        s += {"A": 6, "B": 6, "C": 6, "D": 2, "E": -2, "F": -8}.get(dpe, 0)
        s += 5 if surf >= 45 else 2 if surf >= 38 else 0
        s += 3 if (a.get("price") or 9999) <= 1000 else 0
        s -= 10 * etud + 5 * rdc + 3 * bool(sans_asc) + 7 * palier
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
        elif rue: alertes.append(f"Distance estimée d'après la rue citée ({a.get('geoLabel')}) : numéro non précisé")
        if palier: alertes.insert(0, f"Environ {round(exces / 50) * 50:g} m en dehors du secteur voulu : gardée car {', '.join(q)}")
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
            "available": (a.get("availableDate") or "")[:10] or None, "published": (a.get("publicationDate") or "")[:10] if not str(a.get("publicationDate") or "").startswith("1970") else None,
            "agency": a.get("accountDisplayName"), "district": d, "zone": zone,
            "palier": palier, "horsSecteur": round(exces / 50) * 50,
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
    # une description courte partage vite la moitié de ses mots avec une autre : on exige assez de texte
    return (sim >= 0.45 and min(len(a), len(b)) >= 20) or (x["zone"] == y["zone"] and abs(x["price"] - y["price"]) <= 5 and abs(x["surface"] - y["surface"]) <= 0.6)


def dedoublonner(items):
    """Garde une seule fiche par bien (la plus complète) et liste les autres annonces dans alsoOn."""
    def qualite(x):
        return (x["precise"], len(x.get("photoUrls") or []), x["src"] == "bienici", len(x["description"] or ""))
    gardes = []
    for x in sorted(items, key=qualite, reverse=True):
        double = next((g for g in gardes if meme_bien(g, x)), None)
        if double:
            double.setdefault("alsoIds", []).append(x["id"])
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
