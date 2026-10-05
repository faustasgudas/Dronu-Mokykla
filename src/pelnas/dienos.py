# -*- coding: utf-8 -*-
"""Is zaliu Shopify uzsakymu pagamina dienos suvestine.

Visur dirbame BE PVM. Shopify created_at jau ateina parduotuves laiko juosta
su poslinkiu, todel diena yra tiesiog pirmi 10 simboliu.

Grazinimai priskiriami TAI dienai, kuria buvo grazinta — taip daro ir pacios
Shopify ataskaitos, todel skaiciai sutampa.
"""
import collections

import nustatymai
import saugykla


def _ar_cod(uzsakymas):
    """Ar uzsakymas apmokamas atsiimant (COD).

    Shopify gateway pavadinimas priklauso nuo to, kaip ji pavadino pardavejas,
    todel lyginame su .env sarasu (COD_GATEWAY).
    """
    vardai = list(uzsakymas.get("payment_gateway_names") or [])
    if uzsakymas.get("gateway"):
        vardai.append(uzsakymas["gateway"])
    zemas = " ".join(vardai).lower()
    return any(raktas and raktas in zemas for raktas in nustatymai.COD_VARDAI)


def _sk(reiksme):
    try:
        return float(reiksme or 0)
    except (TypeError, ValueError):
        return 0.0


def _siuntimo_mokesciai(uzsakymas):
    """Grazina (siuntimo suma su PVM, siuntimo PVM)."""
    suma = pvm = 0.0
    for eil in uzsakymas.get("shipping_lines") or []:
        suma += _sk(eil.get("price"))
        for nuolaida in eil.get("discount_allocations") or []:
            suma -= _sk(nuolaida.get("amount"))
        for mokestis in eil.get("tax_lines") or []:
            pvm += _sk(mokestis.get("price"))
    return suma, pvm


def perskaiciuoti(rysys):
    """Perskaiciuoja visa `dienos` lentele is uzsakymu. Saltinis — 'api'."""
    savikainos = saugykla.savikainos_zemelapis(rysys)
    kaupikliai = collections.defaultdict(
        lambda: {"bruto": 0.0, "neto": 0.0, "cogs": 0.0,
                 "siuntimo_pajamos": 0.0, "uzsakymu": 0, "be_savikainos": 0.0,
                 "cod_uzsakymu": 0, "cod_neto": 0.0, "neapmoketa": 0.0}
    )

    for uzsakymas in saugykla.uzsakymus_skaityti(rysys):
        if uzsakymas.get("cancelled_at") and not (uzsakymas.get("refunds") or []):
            continue
        diena = (uzsakymas.get("created_at") or "")[:10]
        if not diena:
            continue
        su_pvm = bool(uzsakymas.get("taxes_included"))
        k = kaupikliai[diena]
        k["uzsakymu"] += 1

        siunt_suma, siunt_pvm = _siuntimo_mokesciai(uzsakymas)
        visas_pvm = _sk(uzsakymas.get("total_tax"))
        prekiu_pvm = visas_pvm - siunt_pvm

        bruto = _sk(uzsakymas.get("total_line_items_price"))
        po_nuolaidu = _sk(uzsakymas.get("subtotal_price"))
        if su_pvm:
            # subtotal_price cia su PVM — nuimam prekiu PVM dali
            neto = po_nuolaidu - prekiu_pvm
            dalis = (bruto - prekiu_pvm) if bruto else 0.0
            bruto = dalis
            siunt_pajamos = siunt_suma - siunt_pvm
        else:
            neto = po_nuolaidu
            siunt_pajamos = siunt_suma

        k["bruto"] += bruto
        k["neto"] += neto
        k["siuntimo_pajamos"] += siunt_pajamos

        # COD: pinigus surenka kurjeris, mokestis kitoks nei korteliu.
        if _ar_cod(uzsakymas):
            k["cod_uzsakymu"] += 1
            k["cod_neto"] += neto
        # Kol financial_status nera 'paid', pinigu dar negavom. COD atveju
        # tai reiskia, kad siunta dar kelyje arba jos neatsieme.
        if (uzsakymas.get("financial_status") or "") in ("pending", "unpaid", "authorized"):
            k["neapmoketa"] += neto

        # --- savikaina ---
        # Kiek neto tenka vienam eurui bruto — kad nuolaida proporcingai
        # sumazintu ir „be savikainos" dali.
        santykis = (neto / bruto) if bruto else 1.0
        for eilute in uzsakymas.get("line_items") or []:
            kiekis = int(eilute.get("quantity") or 0)
            variantas = eilute.get("variant_id")
            savikaina = savikainos.get(variantas, (None, None))[0] if variantas else None
            if savikaina is None:
                vertes = _sk(eilute.get("price")) * kiekis
                if su_pvm and bruto:
                    vertes *= 1.0  # PVM dalis jau nuimta per santyki zemiau
                k["be_savikainos"] += vertes * santykis
            else:
                k["cogs"] += savikaina * kiekis

        # --- grazinimai ---
        for grazinimas in uzsakymas.get("refunds") or []:
            gdiena = (grazinimas.get("created_at") or diena)[:10]
            g = kaupikliai[gdiena]
            for eilute in grazinimas.get("refund_line_items") or []:
                suma = _sk(eilute.get("subtotal"))
                mokestis = _sk(eilute.get("total_tax"))
                g["neto"] -= (suma - mokestis) if su_pvm else suma
                preke = eilute.get("line_item") or {}
                variantas = preke.get("variant_id")
                savikaina = savikainos.get(variantas, (None, None))[0] if variantas else None
                if savikaina is not None:
                    g["cogs"] -= savikaina * int(eilute.get("quantity") or 0)

    eilutes = [
        (d, round(k["bruto"], 2), round(k["neto"], 2), round(k["cogs"], 2),
         round(k["siuntimo_pajamos"], 2), k["uzsakymu"] or None,
         round(max(k["be_savikainos"], 0.0), 2),
         k["cod_uzsakymu"], round(k["cod_neto"], 2), round(k["neapmoketa"], 2))
        for d, k in sorted(kaupikliai.items())
    ]
    saugykla.dienas_irasyti(rysys, eilutes, "api")
    rysys.commit()
    return len(eilutes)
