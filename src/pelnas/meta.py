# -*- coding: utf-8 -*-
"""Meta Marketing API: dienos reklamos islaidos.

Imame spend is insights su time_increment=1 — tai duoda po viena eilute
kiekvienai dienai. Sumos yra BE PVM (Meta PVM prideda saskaitoje atskirai),
todel i pelno skaiciavima jos eina tiesiai.
"""
import datetime

import klientas
import nustatymai
import saugykla

BAZE = "https://graph.facebook.com/%s" % nustatymai.META_VERSIJA


def traukti(rysys, nuo=None, iki=None):
    if not (nustatymai.META_RAKTAS and nustatymai.META_PASKYRA):
        print("  Meta raktai nenustatyti — praleidziu")
        return 0

    siandien = datetime.date.today()
    # Persidengiam 7 dienas atgal: Meta patikslina vakarykscius skaicius.
    numatyta = saugykla.busena_gauti(rysys, "reklama_iki")
    if numatyta:
        pradzia = datetime.date.fromisoformat(numatyta) - datetime.timedelta(days=7)
    else:
        pradzia = datetime.date.fromisoformat(nustatymai.PRADZIA[:10])
    nuo = nuo or pradzia.isoformat()
    iki = iki or siandien.isoformat()

    paskyra = nustatymai.META_PASKYRA
    if not paskyra.startswith("act_"):
        paskyra = "act_" + paskyra

    url = klientas.su_parametrais(
        "%s/%s/insights" % (BAZE, paskyra),
        {
            "level": "account",
            "time_increment": 1,
            "fields": "spend",
            "time_range": '{"since":"%s","until":"%s"}' % (nuo, iki),
            "limit": 500,
            "access_token": nustatymai.META_RAKTAS,
        },
    )

    viso = 0
    while url:
        duom, _ = klientas.gauti(url)
        if "error" in duom:
            raise klientas.ApiKlaida("Meta: %s" % duom["error"].get("message"))
        eilutes = [
            (i["date_start"], "meta", float(i.get("spend") or 0))
            for i in duom.get("data", [])
        ]
        if eilutes:
            saugykla.reklama_irasyti(rysys, eilutes)
            viso += len(eilutes)
            rysys.commit()
        url = (duom.get("paging") or {}).get("next")

    saugykla.busena_irasyti(rysys, "reklama_iki", iki)
    rysys.commit()
    print("  reklamos dienu: %d" % viso)
    return viso
