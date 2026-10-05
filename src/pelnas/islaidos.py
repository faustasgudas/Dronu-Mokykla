# -*- coding: utf-8 -*-
"""Fiksuotos menesines islaidos is pelnas/islaidos.csv.

Appsu prenumeratos, Shopify planas, domenas, buhalterija. Shopify Admin API
tokiu duomenu pardavejui neatiduoda (mateme tik savo paties app'so mokescius),
todel sarasas pildomas ranka — uztenka karta, veliau tik keiciant.

Tikra to menesio saskaita (PDF, kategorija „fiksuotos") visada nugali si sarasa.

CSV stulpeliai:
    pavadinimas   ka mokam
    suma_men      EUR per menesi (tiek, kiek realiai nurasoma, su PVM ar be —
                  svarbu nuoseklumas; sumas imk is Shopify -> Settings -> Billing)
    nuo           YYYY-MM arba tuscia (nuo visados)
    iki           YYYY-MM arba tuscia (iki dabar); menuo iskaitytinis
    pastaba       laisvas tekstas
"""
import calendar
import csv
import io
import os

import nustatymai

FAILAS = os.path.join(nustatymai.DUOMENYS, "islaidos.csv")

# Sukuriama pirma karta — pavadinimai is to, kas realiai ideta parduotuveje.
# Sumas susivesk pats: Shopify admin -> Settings -> Billing -> Bills.
PRADINIS = """pavadinimas,suma_men,nuo,iki,pastaba
Shopify planas,,,,Settings -> Billing
Judge.me,,,,atsiliepimai
Omnisend,,,,el. laiskai
Klaviyo,,,,jei nebenaudojam - istrink eilute
Tidio,,,,pokalbiu langas
GemPages,,,,puslapiu redaktorius
Instant,,,,puslapiu redaktorius
Essential Upsell,,,,po pirkimo
EU Widerrufsbutton,,,,sutarties atsisakymas
Slide Cart,,,,krepselis
Domenas,,,,metinis / 12
Buhalterija,,,,
"""


def uztikrinti():
    """Sukuria failo ruosini, jei jo dar nera."""
    if os.path.exists(FAILAS):
        return False
    os.makedirs(nustatymai.DUOMENYS, exist_ok=True)
    io.open(FAILAS, "w", encoding="utf-8", newline="").write(PRADINIS)
    return True


def _skaicius(tekstas):
    if tekstas in (None, ""):
        return 0.0
    try:
        return float(str(tekstas).replace(",", ".").replace("€", "").strip())
    except ValueError:
        return 0.0


def skaityti():
    """Grazina sarasa [(pavadinimas, suma, nuo, iki)]."""
    if not os.path.exists(FAILAS):
        return []
    with io.open(FAILAS, encoding="utf-8-sig", newline="") as f:
        eilutes = []
        for e in csv.DictReader(f):
            suma = _skaicius(e.get("suma_men"))
            if suma <= 0:
                continue
            eilutes.append((
                (e.get("pavadinimas") or "?").strip(),
                suma,
                (e.get("nuo") or "").strip()[:7],
                (e.get("iki") or "").strip()[:7],
            ))
    return eilutes


def menesio_suma(eilutes, menuo):
    """Kiek fiksuotu islaidu tenka nurodytam menesiui (YYYY-MM)."""
    viso = 0.0
    for _, suma, nuo, iki in eilutes:
        if nuo and menuo < nuo:
            continue
        if iki and menuo > iki:
            continue
        viso += suma
    return viso


def dienos_suma(eilutes, menuo):
    return menesio_suma(eilutes, menuo) / calendar.monthrange(
        int(menuo[:4]), int(menuo[5:7])
    )[1]


def suvestine(eilutes, menuo):
    """Kas sudaro to menesio fiksuotas islaidas — dashboardo uzuominai."""
    return sorted(
        [
            {"pavadinimas": v, "suma": round(s, 2)}
            for v, s, nuo, iki in eilutes
            if not (nuo and menuo < nuo) and not (iki and menuo > iki)
        ],
        key=lambda x: -x["suma"],
    )
