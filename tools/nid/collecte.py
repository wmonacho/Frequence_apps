"""Collecte quotidienne de Fréquence Nid (Bien'ici, Orpi, Laforêt, Foncia, Locservice, doublons fusionnés).

Usage : python3 collecte.py <connues.json> <dossier_sortie> <date AAAA-MM-JJ>

connues.json : liste des id d'annonces déjà présentes (fichier data/annonces.json
de l'app + collection « annonces » de la base). Peut être un fichier absent.

Produit dans <dossier_sortie> :
  nouvelles.json   annonces nouvelles, prêtes à écrire dans la collection « annonces »
  photos/<id>.json documents {"data": "data:image/jpeg;base64,...", "n": k}
  retirees.json    id connus qui ne sont plus en ligne
  resume.json      chiffres du jour
"""
import base64, io, json, os, subprocess, sys
import concurrent.futures as cf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prepare import prepare  # noqa: E402
from sources import collect  # noqa: E402

W, H, NMAX = 560, 420, 4


def curl(url, out=None):
    cmd = ["curl", "-s", "-L", "-m", "40", "-A", "Mozilla/5.0"]
    if out:
        cmd += ["-o", out, "-w", "%{http_code}"]
    r = subprocess.run(cmd + [url], capture_output=True, text=True)
    return r.stdout


def photo_doc(item):
    from PIL import Image, ImageOps
    frames = []
    for u in item.get("photoUrls", [])[: NMAX + 2]:
        if len(frames) >= NMAX:
            break
        tmp = f"/tmp/nid-{item['id']}-{len(frames)}.jpg"
        if curl(u, tmp).strip() != "200":
            continue
        try:
            frames.append(ImageOps.fit(Image.open(tmp).convert("RGB"), (W, H), Image.LANCZOS))
        except Exception:
            pass
    if not frames:
        return item["id"], None
    out = Image.new("RGB", (W, H * len(frames)), "white")
    for i, fr in enumerate(frames):
        out.paste(fr, (0, H * i))
    for q in (62, 52, 42):
        buf = io.BytesIO()
        out.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        if buf.tell() < 230_000:
            break
    data = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    return item["id"], {"data": data, "n": len(frames)}


def main():
    known_path, outdir, date = sys.argv[1], sys.argv[2], sys.argv[3]
    known = set(json.load(open(known_path))) if os.path.exists(known_path) else set()
    os.makedirs(os.path.join(outdir, "photos"), exist_ok=True)

    raw, bilan = collect()
    items = prepare(raw)
    live = {i["id"] for i in items}
    new = [i for i in items if i["id"] not in known]

    with cf.ThreadPoolExecutor(6) as ex:
        photos = dict(ex.map(photo_doc, new))

    out = []
    for i in new:
        p = photos.get(i["id"])
        i.pop("photoUrls", None)
        i["firstSeen"] = date
        i["status"] = "active"
        if p:
            json.dump(p, open(os.path.join(outdir, "photos", i["id"] + ".json"), "w"))
            i["photo"] = {"doc": "photos/" + i["id"], "n": p["n"]}
        out.append(i)

    json.dump(out, open(os.path.join(outdir, "nouvelles.json"), "w"), ensure_ascii=False)
    gone = sorted(known - live)
    json.dump(gone, open(os.path.join(outdir, "retirees.json"), "w"))
    resume = {"date": date, "sources": bilan, "brutes": len(raw), "retenues": len(items), "nouvelles": len(out),
              "retirees": len(gone), "avecPhotos": sum(1 for i in out if "photo" in i),
              "meilleure": max(out, key=lambda x: x["score"])["title"] if out else None}
    json.dump(resume, open(os.path.join(outdir, "resume.json"), "w"), ensure_ascii=False)
    print(json.dumps(resume, ensure_ascii=False))


if __name__ == "__main__":
    main()
