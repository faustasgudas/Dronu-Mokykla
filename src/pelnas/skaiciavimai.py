# -*- coding: utf-8 -*-
"""P&L skaiciavimas.

Viskas skaiciuojama BE PVM, nes PVM nera musu pinigai.

  neto pajamos        Shopify net sales (- nuolaidos, - grazinimai), be PVM
+ siuntimo pajamos    kiek uz pristatyma paemem is kliento
- prekiu savikaina    COGS
- reklama             Meta (ir kiti kanalai)
- siuntimo savikaina  kiek realiai sumokejom kurjeriui
- mokejimu mokesciai  Shopify Payments / Paysera
- fiksuotos islaidos  appsai, domenas, buhalterija (paskirstyta per dienas)
= GRYNAS PELNAS

Tikslumas zymimas kiekvienai dienai, kad dashboarde matytusi, kur skaicius
tikras, o kur vertinimas.
"""
import calendar
import datetime

import islaidos
import nustatymai
import saugykla

PVM = 0.21
VIDUTINIS_SIUNTIMO_MOKESTIS = 2.49


def _menesio_dienos(menuo):
    metai, men = int(menuo[:4]), int(menuo[5:7])
    return calendar.monthrange(metai, men)[1]


def suskaiciuoti(rysys):
    dienos = saugykla.dienas_skaityti(rysys)
    if not dienos:
        return [], {}

    reklama = saugykla.reklama_pagal_diena(rysys)
    mokesciu_saskaitos = saugykla.saskaitos_pagal_menesi(rysys, "fiksuotos")
    fiksuotu_sarasas = islaidos.skaityti()
    men_mokesciai = saugykla.menesio_mokesciai(rysys)
    siuntimo_saskaitos = saugykla.saskaitos_pagal_menesi(rysys, "siuntimas")

    # Tikri Shopify Payments mokesciai pagal diena.
    mokesciai_diena = {}
    for eil in rysys.execute(
        "SELECT data, SUM(mokestis) AS viso FROM mokesciai "
        "WHERE data IS NOT NULL AND data <> '' GROUP BY data"
    ):
        mokesciai_diena[eil["data"]] = eil["viso"] or 0.0

    # Menesio sumos — reikia paskirstyti saskaitas proporcingai.
    men_pajamos = {}
    for d in dienos:
        menuo = d["data"][:7]
        men_pajamos[menuo] = men_pajamos.get(menuo, 0.0) + (d["neto"] or 0.0)

    tikslumas = saugykla.reklamos_tikslumas(rysys)
    siuntos = saugykla.siuntos_pagal_diena(rysys)

    # Menesio siuntu kiekis — kad saskaita pasidalintu pagal siuntas, o ne
    # pagal pajamas (siunta uz 20 EUR kainuoja tiek pat, kiek uz 500).
    men_siuntu = {}
    for d, s in siuntos.items():
        men_siuntu[d[:7]] = men_siuntu.get(d[:7], 0) + (s["siuntu"] or 0)

    # Santykis „siuntu vienam euro apyvartos" is tu dienu, kurioms turim tikra
    # kurjerio ataskaita. Juo vertinam menesius, kuriu ataskaitos dar nera —
    # tai daug arciau tiesos nei skaiciuoti is shipping_charges, kur uzsakymu
    # su nemokamu pristatymu tiesiog nesimato.
    # Skaiciuojam per VISA menesi, ne per siuntimo dienas: siunciama partijomis
    # (rugpjuti — 16 dienu is 31), todel dalinant tik is siuntimo dienu apyvartos
    # santykis isaiptu apie 1,6 karto per didelis.
    istorija_siuntu = sum(men_siuntu.values())
    istorija_neto = sum(
        (d["neto"] or 0) for d in dienos if d["data"][:7] in men_siuntu
    )
    siuntu_santykis = (istorija_siuntu / istorija_neto) if istorija_neto > 0 else None

    eilutes = []
    paslepta = []
    for d in dienos:
        data = d["data"]
        menuo = data[:7]

        # Diena be reklamos duomenu rodytu per didelį pelna, todel jos
        # nerodome is viso — geriau trumpesnis, bet teisingas laikotarpis.
        if data not in reklama:
            if (d["neto"] or 0) > 0:
                paslepta.append(d)
            continue

        neto = d["neto"] or 0.0
        siunt_paj = d["siuntimo_pajamos"] or 0.0
        cogs = d["cogs"] or 0.0
        uzsakymu = d["uzsakymu"]

        # --- reklama ---
        ads = reklama.get(data, 0.0)

        # --- mokejimu mokesciai ---
        # COD skaiciuojamas atskirai: pinigus surenka kurjeris ir nusiima
        # savo mokesti, o ne mokejimu surinkejas.
        lp = siuntos.get(data)
        if lp and lp["cod_siuntu"]:
            cod_uzs = lp["cod_siuntu"]
            cod_neto = (lp["cod_suma"] or 0.0) / (1 + PVM)
        else:
            cod_uzs = d.get("cod_uzsakymu") or 0
            cod_neto = d.get("cod_neto") or 0.0

        if not cod_uzs:
            cod_mokestis = 0.0
        elif nustatymai.COD_MOKESTIS is None:
            cod_mokestis = None                      # kainos nezinom
        else:
            cod_mokestis = (cod_uzs * nustatymai.COD_MOKESTIS
                            + cod_neto * (1 + PVM) * (nustatymai.COD_PROC / 100.0))

        if data in mokesciai_diena:
            # Shopify Payments API — tikslus mokestis kiekvienai operacijai.
            mokesciai = mokesciai_diena[data]
            mok_tikslumas = "tikslu"
        elif menuo in men_mokesciai and men_pajamos.get(menuo):
            # Menesio ataskaita — tikra suma, paskirstyta pagal dienos apyvarta.
            mokesciai = men_mokesciai[menuo] * neto / men_pajamos[menuo]
            mok_tikslumas = "menesio"
        elif nustatymai.PAYSERA_PROC is not None:
            # Tik jei pats aiskiai nurodei tarifa .env faile.
            kortelem_neto = max(neto - cod_neto, 0.0)
            mokesciai = ((kortelem_neto + siunt_paj) * (1 + PVM)
                         * (nustatymai.PAYSERA_PROC / 100.0))
            if uzsakymu:
                mokesciai += max(uzsakymu - cod_uzs, 0) * nustatymai.PAYSERA_FIKS
            mok_tikslumas = "tarifas"
        else:
            mokesciai = None
            mok_tikslumas = "nezinoma"

        if mokesciai is not None and cod_mokestis is not None:
            mokesciai += cod_mokestis
        elif cod_mokestis is None:
            mokesciai = None
            mok_tikslumas = "nezinoma"

        # --- siuntimo savikaina ---
        men_saskaita = siuntimo_saskaitos.get(menuo)
        siuntu = (lp["siuntu"] if lp else None)
        if men_saskaita and men_siuntu.get(menuo) and siuntu is not None:
            # Tikra saskaita, paskirstyta pagal siuntu skaiciu.
            siunt_savikaina = men_saskaita * siuntu / men_siuntu[menuo]
            siunt_tikslumas = "saskaita"
        elif men_saskaita and men_pajamos.get(menuo):
            siunt_savikaina = men_saskaita * neto / men_pajamos[menuo]
            siunt_tikslumas = "saskaita"
        elif nustatymai.SIUNTOS_SAVIKAINA is None:
            # Kainos uz siunta nezinom — eilute lieka tuscia.
            siunt_savikaina = None
            siunt_tikslumas = "nezinoma"
        elif siuntu is not None:
            siunt_savikaina = siuntu * nustatymai.SIUNTOS_SAVIKAINA
            siunt_tikslumas = "siuntos"
        elif uzsakymu:
            siunt_savikaina = uzsakymu * nustatymai.SIUNTOS_SAVIKAINA
            siunt_tikslumas = "uzsakymai"
        elif siuntu_santykis and neto > 0:
            siunt_savikaina = neto * siuntu_santykis * nustatymai.SIUNTOS_SAVIKAINA
            siunt_tikslumas = "istorija"
        else:
            siunt_savikaina = None
            siunt_tikslumas = "nezinoma"

        # --- fiksuotos ---
        if menuo in mokesciu_saskaitos:
            men_fiks = mokesciu_saskaitos[menuo]
            fiks_tikslumas = "saskaita"
        elif islaidos.menesio_suma(fiksuotu_sarasas, menuo):
            men_fiks = islaidos.menesio_suma(fiksuotu_sarasas, menuo)
            fiks_tikslumas = "sarasas"
        elif nustatymai.FIKSUOTOS_MENESIUI:
            men_fiks = nustatymai.FIKSUOTOS_MENESIUI
            fiks_tikslumas = "nustatymas"
        else:
            men_fiks = None
            fiks_tikslumas = "nezinoma"
        fiksuotos = (men_fiks / _menesio_dienos(menuo)
                     if men_fiks is not None else None)

        pajamos = neto + siunt_paj
        bruto_pelnas = pajamos - cogs
        # Pelnas po reklamos. Skaiciuojamas VISADA, nes pajamos, savikaina ir
        # reklama zinomos visoms rodomoms dienoms. Siuntimas, mokejimu
        # mokesciai ir fiksuotos islaidos i ji neieina.
        po_reklamos = bruto_pelnas - ads
        dalys = [cogs, ads, siunt_savikaina, mokesciai, fiksuotos]
        if any(x is None for x in dalys):
            visos_islaidos = None
            pelnas = None
        else:
            visos_islaidos = sum(dalys)
            pelnas = pajamos - visos_islaidos

        apvalus = lambda x: None if x is None else round(x, 2)

        eilutes.append({
            "data": data,
            "neto": round(neto, 2),
            "siuntimo_pajamos": round(siunt_paj, 2),
            "pajamos": round(pajamos, 2),
            "cogs": round(cogs, 2),
            "reklama": round(ads, 2),
            "bruto_pelnas": round(bruto_pelnas, 2),
            "po_reklamos": round(po_reklamos, 2),
            "siuntimas": apvalus(siunt_savikaina),
            "mokesciai": apvalus(mokesciai),
            "fiksuotos": apvalus(fiksuotos),
            "islaidos": apvalus(visos_islaidos),
            "pelnas": apvalus(pelnas),
            "uzsakymu": uzsakymu,
            "siuntu": siuntu,
            "cod_uzsakymu": cod_uzs,
            "cod_neto": round(cod_neto, 2),
            "neapmoketa": round(d.get("neapmoketa") or 0.0, 2),
            "be_savikainos": round(d["be_savikainos"] or 0.0, 2),
            "saltinis": d["saltinis"],
            "mok_tikslumas": mok_tikslumas,
            "siunt_tikslumas": siunt_tikslumas,
            "fiks_tikslumas": fiks_tikslumas,
            "rekl_tikslumas": tikslumas.get(data, "diena"),
        })

    return eilutes, _ispejimai(eilutes, rysys, paslepta, siuntu_santykis)


def _ispejimai(eilutes, rysys, paslepta, siuntu_santykis=None):
    """Ka dashboarde reikia parodyti kaip „siuo skaiciumi pasitikek maziau"."""
    su_pardavimais = [e for e in eilutes if e["neto"] > 0]
    be_sav = sum(e["be_savikainos"] for e in eilutes)
    neto = sum(e["neto"] for e in eilutes)

    nekategorizuotos = rysys.execute(
        "SELECT COUNT(*) AS n FROM saskaitos WHERE kategorija='?'"
    ).fetchone()["n"]

    paskutine_reklama = rysys.execute(
        "SELECT MAX(data) AS d FROM reklama"
    ).fetchone()["d"]
    paskutine_diena = eilutes[-1]["data"] if eilutes else None

    paskirstytos = sum(1 for e in eilutes if e.get("rekl_tikslumas") == "paskirstyta")

    # Sena neapmoketa COD siunta greiciausiai neatsiimta — pelnas uz ja fiktyvus.
    riba = (datetime.date.today()
            - datetime.timedelta(days=nustatymai.COD_LAUKIMAS)).isoformat()
    sena_neapmoketa = sum(
        e.get("neapmoketa", 0) for e in eilutes if e["data"] < riba
    )
    cod_uzsakymu = sum(e.get("cod_uzsakymu", 0) for e in eilutes)
    # Kurios P&L eilutes apskritai nezinomos — dashboardas jas paliks tuscias.
    nezinomos = []
    for laukas, vardas in (("siuntimas", "Siuntimas"),
                           ("mokesciai", "Mokejimu mokesciai"),
                           ("fiksuotos", "Fiksuotos islaidos")):
        truksta = sum(1 for e in eilutes if e.get(laukas) is None)
        if truksta:
            nezinomos.append({"laukas": laukas, "vardas": vardas, "dienu": truksta})
    pelnas_pilnas = not nezinomos
    menesiai = sorted({e["data"][:7] for e in eilutes})
    fiksuotu_detales = (islaidos.suvestine(islaidos.skaityti(), menesiai[-1])
                        if menesiai else [])
    be_uzsakymu = [e for e in eilutes if e.get("uzsakymu") is None]
    siuntu_viso = sum(e.get("siuntu") or 0 for e in eilutes)
    dienu_su_siuntomis = sum(1 for e in eilutes if e.get("siuntu") is not None)

    return {
        "dienu": len(eilutes),
        "dienu_su_pardavimais": len(su_pardavimais),
        "paslepta_dienu": len(paslepta),
        "paslepta_neto": round(sum(d["neto"] or 0 for d in paslepta), 2),
        "paslepta_nuo": paslepta[0]["data"] if paslepta else None,
        "paslepta_iki": paslepta[-1]["data"] if paslepta else None,
        "reklama_paskirstyta": paskirstytos,
        "cod_uzsakymu": cod_uzsakymu,
        "cod_neto": round(sum(e.get("cod_neto", 0) for e in eilutes), 2),
        "neapmoketa": round(sum(e.get("neapmoketa", 0) for e in eilutes), 2),
        "sena_neapmoketa": round(sena_neapmoketa, 2),
        "cod_laukimas": nustatymai.COD_LAUKIMAS,
        "nezinomos": nezinomos,
        "pelnas_pilnas": pelnas_pilnas,
        "fiksuotu_detales": fiksuotu_detales,
        "islaidu_failas": islaidos.FAILAS,
        "uzsakymu_truksta": len(be_uzsakymu),
        "uzsakymu_nuo": be_uzsakymu[0]["data"] if be_uzsakymu else None,
        "uzsakymu_iki": be_uzsakymu[-1]["data"] if be_uzsakymu else None,
        "uzsakymu_viso": sum(e["uzsakymu"] for e in eilutes if e.get("uzsakymu")),
        "siuntu": siuntu_viso,
        "dienu_su_siuntomis": dienu_su_siuntomis,
        "siuntos_vertinimas": sum(
            1 for e in eilutes if e["neto"] > 0 and e.get("siuntu") is None
        ),
        "siuntos_istorija": sum(
            1 for e in eilutes if e.get("siunt_tikslumas") == "istorija"
        ),
        "siuntu_santykis": (round(1 / siuntu_santykis, 2)
                            if siuntu_santykis else None),
        "be_savikainos_suma": round(be_sav, 2),
        "be_savikainos_dalis": round(be_sav / neto * 100, 1) if neto else 0,
        "siuntimas_vertinimas": sum(
            1 for e in su_pardavimais if e["siunt_tikslumas"] == "vertinimas"
        ),
        "mokesciai_vertinimas": sum(
            1 for e in su_pardavimais if e["mok_tikslumas"] == "vertinimas"
        ),
        "nekategorizuotos_saskaitos": nekategorizuotos,
        "reklama_iki": paskutine_reklama,
        "duomenys_iki": paskutine_diena,
    }
