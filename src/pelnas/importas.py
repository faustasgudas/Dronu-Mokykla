# -*- coding: utf-8 -*-
"""Failu importas: metam faila i pelnas/importas/ — jis pats atpazistamas.

Ka moka:
  * Shopify ataskaita XML arba CSV su stulpeliais day / net_sales / cost_of_goods_sold
    (Analytics -> Reports -> „Cost of goods sold, shipping charges, gross sales
    and gross profit" -> Export)
  * Meta kampaniju CSV su „Reporting starts" ir „Amount spent (EUR)"
  * PDF saskaitos (LP Express, Meta, tiekeju) — issaugomos ir istraukiama suma

Apdoroti failai perkeliami i pelnas/importas/apdorota/, kad ju nekartotume.
"""
import csv
import datetime
import glob
import io
import os
import re
import shutil
import xml.etree.ElementTree as ET

import nustatymai
import saugykla

APLANKAS = os.path.join(nustatymai.DUOMENYS, "importas")
APDOROTA = os.path.join(APLANKAS, "apdorota")
SASKAITOS = os.path.join(nustatymai.DUOMENYS, "saskaitos")

# Pagal ka atpazistam, kieno saskaita ir i kuria eilute ji eina.
TIEKEJAI = [
    # (raktazodziai PDF tekste, kategorija, ar itraukti i P&L)
    (("lp express", "lietuvos pastas", "venipak", "omniva", "dpd"), "siuntimas", 1),
    # Meta islaidos jau ateina is API/CSV — saskaitos tik archyvui, kad nedubliuotume.
    (("meta platforms", "facebook", "instagram"), "reklama", 0),
    (("shopify",), "fiksuotos", 1),
    (("judge.me", "judgeme", "omnisend", "tidio"), "fiksuotos", 1),
]

SKAICIUS = r"(-?\d[\d\s ]*[.,]\d{2})"


def _skaicius(tekstas):
    if tekstas in (None, ""):
        return 0.0
    valyta = str(tekstas).replace(" ", "").replace(" ", "").replace(",", ".")
    try:
        return float(valyta)
    except ValueError:
        return 0.0


# --- Shopify ataskaita -----------------------------------------------------
def _shopify_eilutes(eilutes):
    """eilutes: saraas dict'u su Shopify ataskaitos stulpeliais."""
    paruosta = []
    for e in eilutes:
        data = (e.get("day") or "").strip()[:10]
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", data):
            continue
        neto = _skaicius(e.get("net_sales"))
        cogs = _skaicius(e.get("cost_of_goods_sold"))
        bruto_pelnas = _skaicius(e.get("gross_profit"))
        # Shopify i gross_profit neitraukia prekiu, kurioms neivesta savikaina.
        # Tos dalies marza nezinoma — pasizymim, kad dashboarde matytusi.
        be_savikainos = round(neto - cogs - bruto_pelnas, 2)
        if be_savikainos < 0.01:
            be_savikainos = 0.0
        paruosta.append((
            data,
            _skaicius(e.get("gross_sales")),
            neto,
            cogs,
            _skaicius(e.get("shipping_charges")),
            None,
            be_savikainos,
        ))
    return paruosta


def importuoti_shopify_xml(kelias):
    saknis = ET.parse(kelias).getroot()
    duomenys = saknis.find("data")
    if duomenys is None:
        return []
    return _shopify_eilutes(
        [{v.tag: (v.text or "") for v in eil} for eil in duomenys]
    )


def importuoti_shopify_csv(eilutes):
    return _shopify_eilutes(eilutes)


# --- Meta ------------------------------------------------------------------
def importuoti_meta(eilutes):
    """Sumuoja kampaniju islaidas pagal diena.

    Meta eksportas buna dvejopas:
      * su dienu skaidymu (Breakdown -> Time -> Day) — kiekviena eilute
        viena diena, „Reporting starts" == „Reporting ends";
      * suminis per laikotarpi — visos eilutes su tuo paciu intervalu.

    Antruoju atveju sumos paskirstomos tolygiai per intervalo dienas ir
    pazymimos kaip 'paskirstyta', kad dashboarde matytusi, jog dienos
    skaicius yra vidurkis, o ne tikras.
    """
    pagal_diena = {}
    paskirstytos = set()
    for e in eilutes:
        nuo = (e.get("Reporting starts") or "").strip()[:10]
        iki = (e.get("Reporting ends") or nuo).strip()[:10]
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", nuo):
            continue
        stulpelis = next((r for r in e if r and r.startswith("Amount spent")), None)
        suma = _skaicius(e.get(stulpelis))

        d1 = datetime.date.fromisoformat(nuo)
        d2 = datetime.date.fromisoformat(iki) if re.match(r"^\d{4}-\d{2}-\d{2}$", iki) else d1
        dienu = (d2 - d1).days + 1
        if dienu <= 1:
            pagal_diena[nuo] = pagal_diena.get(nuo, 0.0) + suma
            continue

        dalis = suma / dienu
        for i in range(dienu):
            d = (d1 + datetime.timedelta(days=i)).isoformat()
            pagal_diena[d] = pagal_diena.get(d, 0.0) + dalis
            paskirstytos.add(d)

    return [
        (d, "meta", round(s, 2), "paskirstyta" if d in paskirstytos else "diena")
        for d, s in sorted(pagal_diena.items())
    ], bool(paskirstytos)


# --- Shopify uzsakymu eksportas ---------------------------------------------
# Admin -> Orders -> Export -> Plain CSV. Duoda tai, ko nera pelno ataskaitoje:
# uzsakymu skaiciu, mokejimo buda (taigi ir COD) bei apmokejimo busena.
def importuoti_uzsakymus(eilutes):
    """Sugrupuoja preciu eilutes i uzsakymus ir suskaiciuoja pagal diena.

    Eksporte vienas uzsakymas gali uzimti kelias eilutes — po viena kiekvienai
    prekei. Uzsakymo lygio laukai (Total, Taxes, mokejimo budas) uzpildyti tik
    PIRMOJE eilutėje, likusios tuscios. Todel imame tik tas eilutes, kuriose
    yra "Financial Status".
    """
    pagal_diena = {}
    for e in eilutes:
        if not (e.get("Financial Status") or "").strip():
            continue                       # tolesne to paties uzsakymo preke
        if (e.get("Cancelled at") or "").strip():
            continue                       # atsauktas uzsakymas
        data = (e.get("Created at") or "").strip()[:10]
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", data):
            continue

        # Kainos eksporte su PVM, todel PVM nuimam.
        neto = _skaicius(e.get("Total")) - _skaicius(e.get("Taxes"))
        budas = (e.get("Payment Method") or "").lower()
        cod = any(r in budas for r in nustatymai.COD_VARDAI)
        busena = (e.get("Financial Status") or "").lower()

        k = pagal_diena.setdefault(data, {"uzsakymu": 0, "cod_uzsakymu": 0,
                                          "cod_neto": 0.0, "neapmoketa": 0.0})
        k["uzsakymu"] += 1
        if cod:
            k["cod_uzsakymu"] += 1
            k["cod_neto"] += neto
        if busena in ("pending", "unpaid", "authorized", "partially_paid"):
            k["neapmoketa"] += neto

    if not pagal_diena:
        return []

    # Dienos be uzsakymu eksporte tiesiog neminimos. Bet eksporto laikotarpyje
    # tai reiskia NULIS uzsakymu, o ne „nezinoma" — uzpildom, kad vidutinis
    # uzsakymas ir kiti skaiciavimai butu teisingi.
    d1 = datetime.date.fromisoformat(min(pagal_diena))
    d2 = datetime.date.fromisoformat(max(pagal_diena))
    diena = d1
    while diena <= d2:
        pagal_diena.setdefault(diena.isoformat(),
                               {"uzsakymu": 0, "cod_uzsakymu": 0,
                                "cod_neto": 0.0, "neapmoketa": 0.0})
        diena += datetime.timedelta(days=1)

    return [
        (d, k["uzsakymu"], k["cod_uzsakymu"], round(k["cod_neto"], 2),
         round(k["neapmoketa"], 2))
        for d, k in sorted(pagal_diena.items())
    ]


# --- Shopify mokejimu mokesciai pagal menesi --------------------------------
def importuoti_mokescius(eilutes):
    """„Payment processing fees by month" — tikri korteliu mokesciai."""
    paruosta = []
    for e in eilutes:
        menuo = (e.get("Month") or "").strip()[:7]
        if not re.match(r"^\d{4}-\d{2}$", menuo):
            continue
        suma = (_skaicius(e.get("Payment processing fees"))
                + _skaicius(e.get("International fees"))
                + _skaicius(e.get("Managed Markets fees")))
        paruosta.append((menuo, round(suma, 2)))
    return paruosta


# --- LP Express siuntu ataskaita (XLSX) ------------------------------------
# Atsisiunciama is LP Express savitarnos: Siuntos -> Ataskaitos -> Eksportuoti.
# Kainu joje nera — tik siuntos ir COD sumos. Kaina ateina su saskaita (PDF).
LP_ATSAUKTA = "atšaukta"


def importuoti_lp(kelias):
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import openpyxl
    except ImportError:
        print("    (openpyxl neidiegtas: pip install openpyxl)")
        return None

    import warnings
    with warnings.catch_warnings():          # LP failas be default style
        warnings.simplefilter("ignore")
        knyga = openpyxl.load_workbook(kelias, data_only=True, read_only=True)
    try:
        eilutes = list(knyga[knyga.sheetnames[0]].iter_rows(values_only=True))
    finally:
        knyga.close()      # be sito Windows neleistu failo perkelti

    # Antrastes eilute — ta, kurioje yra „Siuntos numeris".
    antrasciu_nr = None
    for i, eil in enumerate(eilutes[:20]):
        reiksmes = [str(v).strip() if v is not None else "" for v in eil]
        if "Siuntos numeris" in reiksmes:
            antrasciu_nr = i
            stulpeliai = {h: j for j, h in enumerate(reiksmes) if h}
            break
    if antrasciu_nr is None:
        return None

    def imti(eil, vardas):
        j = stulpeliai.get(vardas)
        return eil[j] if j is not None and j < len(eil) else None

    pagal_diena = {}
    for eil in eilutes[antrasciu_nr + 1:]:
        if not imti(eil, "Siuntos numeris"):
            continue
        sukurta = imti(eil, "Siuntos sukūrimo data")
        data = (sukurta.strftime("%Y-%m-%d") if hasattr(sukurta, "strftime")
                else str(sukurta or "")[:10])
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", data):
            continue
        busena = str(imti(eil, "Būsena") or "").lower()
        k = pagal_diena.setdefault(data, {"siuntu": 0, "atsauktu": 0,
                                          "cod_siuntu": 0, "cod_suma": 0.0})
        if LP_ATSAUKTA in busena:
            k["atsauktu"] += 1
            continue                      # atsauktos siuntos neapmokestinamos
        k["siuntu"] += 1
        cod = imti(eil, "COD")
        if cod not in (None, "", 0):
            k["cod_siuntu"] += 1
            k["cod_suma"] += float(cod)

    return [
        (d, k["siuntu"], k["atsauktu"], k["cod_siuntu"], round(k["cod_suma"], 2))
        for d, k in sorted(pagal_diena.items())
    ]


# --- PDF saskaitos ---------------------------------------------------------
def _pdf_tekstas(kelias):
    try:
        from pypdf import PdfReader
    except ImportError:
        print("    (pypdf neidiegtas — PDF praleidziu: pip install pypdf)")
        return None
    try:
        skaitytuvas = PdfReader(kelias)
        return "\n".join((p.extract_text() or "") for p in skaitytuvas.pages)
    except Exception as klaida:
        print("    PDF nepavyko perskaityti: %s" % klaida)
        return None


def importuoti_pdf(kelias):
    tekstas = _pdf_tekstas(kelias)
    if tekstas is None:
        return None
    zemas = tekstas.lower()

    kategorija, i_pelna = "?", 0
    siuntejas = ""
    for raktazodziai, kat, pelnan in TIEKEJAI:
        for raktas in raktazodziai:
            if raktas in zemas:
                kategorija, i_pelna, siuntejas = kat, pelnan, raktas
                break
        if siuntejas:
            break

    data = ""
    radinys = re.search(r"(20\d{2})[-./](\d{2})[-./](\d{2})", tekstas)
    if radinys:
        data = "%s-%s-%s" % radinys.groups()

    # Suma: ieskom eilutes su „viso/total/suma mokėti" ir skaiciumi joje.
    suma, pvm = None, None
    for eil in tekstas.splitlines():
        z = eil.lower()
        sk = re.findall(SKAICIUS, eil)
        if not sk:
            continue
        if pvm is None and ("pvm" in z or "vat" in z) and "be pvm" not in z:
            pvm = _skaicius(sk[-1])
        if any(r in z for r in ("be pvm", "subtotal", "suma be", "net amount", "amount due")):
            suma = _skaicius(sk[-1])
    if suma is None:
        for eil in tekstas.splitlines():
            z = eil.lower()
            if any(r in z for r in ("viso", "total", "mokėti", "moketi")):
                sk = re.findall(SKAICIUS, eil)
                if sk:
                    suma = _skaicius(sk[-1])
    return {
        "siuntejas": siuntejas or "?",
        "tema": os.path.basename(kelias),
        "data": data,
        "kategorija": kategorija,
        "suma": suma,
        "pvm": pvm,
        "i_pelna": i_pelna,
    }


# --- bendras ivedimas ------------------------------------------------------
def _csv_eilutes(kelias):
    with io.open(kelias, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def paleisti(rysys):
    os.makedirs(APLANKAS, exist_ok=True)
    os.makedirs(APDOROTA, exist_ok=True)
    os.makedirs(SASKAITOS, exist_ok=True)

    failai = [
        k for k in sorted(glob.glob(os.path.join(APLANKAS, "*")))
        if os.path.isfile(k)
    ]
    if not failai:
        print("  importas/ tuscias — praleidziu")
        return 0

    apdorota = 0
    for kelias in failai:
        vardas = os.path.basename(kelias)
        pletinys = os.path.splitext(vardas)[1].lower()
        print("  %s" % vardas)
        try:
            if pletinys == ".xml":
                eilutes = importuoti_shopify_xml(kelias)
                saugykla.dienas_irasyti(rysys, eilutes, "shopify-eksportas")
                print("    Shopify ataskaita: %d dienu" % len(eilutes))

            elif pletinys == ".csv":
                eilutes = _csv_eilutes(kelias)
                antrastes = set(eilutes[0].keys()) if eilutes else set()
                if "day" in antrastes and "net_sales" in antrastes:
                    paruosta = importuoti_shopify_csv(eilutes)
                    saugykla.dienas_irasyti(rysys, paruosta, "shopify-eksportas")
                    print("    Shopify ataskaita: %d dienu" % len(paruosta))
                elif "Financial Status" in antrastes and "Lineitem name" in antrastes:
                    paruosta = importuoti_uzsakymus(eilutes)
                    saugykla.uzsakymu_duomenis_irasyti(rysys, paruosta)
                    print("    Uzsakymai: %d dienu, %d uzsakymu, %d COD"
                          % (len(paruosta), sum(x[1] for x in paruosta),
                             sum(x[2] for x in paruosta)))

                elif "Month" in antrastes and "Payment processing fees" in antrastes:
                    paruosta = importuoti_mokescius(eilutes)
                    saugykla.menesio_mokescius_irasyti(rysys, paruosta)
                    print("    Mokejimu mokesciai: %d menesiu, %.2f EUR"
                          % (len(paruosta), sum(x[1] for x in paruosta)))

                elif "Reporting starts" in antrastes:
                    paruosta, paskirstyta = importuoti_meta(eilutes)
                    saugykla.reklama_irasyti(rysys, paruosta)
                    print("    Meta reklama: %d dienu, %.2f EUR%s"
                          % (len(paruosta), sum(x[2] for x in paruosta),
                             "  (suminis eksportas — paskirstyta tolygiai)"
                             if paskirstyta else ""))
                else:
                    print("    neatpazintas CSV — praleidziu")
                    continue

            elif pletinys in (".xlsx", ".xlsm"):
                paruosta = importuoti_lp(kelias)
                if paruosta is None:
                    print("    neatpazintas XLSX — praleidziu")
                    continue
                saugykla.siuntas_irasyti(rysys, paruosta)
                print("    LP Express: %d dienu, %d siuntu, %d COD (%.2f EUR)"
                      % (len(paruosta), sum(x[1] for x in paruosta),
                         sum(x[3] for x in paruosta), sum(x[4] for x in paruosta)))

            elif pletinys == ".pdf":
                info = importuoti_pdf(kelias)
                if info is None:
                    continue
                naujas = os.path.join(SASKAITOS, vardas)
                shutil.copy2(kelias, naujas)
                saugykla.saskaitas_irasyti(rysys, [(
                    vardas, info["siuntejas"], info["tema"], info["data"],
                    naujas, info["kategorija"], info["suma"], info["pvm"],
                    info["i_pelna"],
                )])
                print("    saskaita: %s, %s, suma %s"
                      % (info["siuntejas"], info["kategorija"], info["suma"]))
            else:
                print("    nezinomas tipas — praleidziu")
                continue

            rysys.commit()
            shutil.move(kelias, os.path.join(APDOROTA, vardas))
            apdorota += 1
        except Exception as klaida:
            print("    KLAIDA: %s" % klaida)

    return apdorota
