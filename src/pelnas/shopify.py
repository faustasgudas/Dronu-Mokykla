# -*- coding: utf-8 -*-
"""Shopify Admin API: uzsakymai, savikainos, Shopify Payments mokesciai.

Reikalingos custom app teises (scopes):
    read_orders, read_products, read_inventory, read_shopify_payments_payouts
"""
import klientas
import nustatymai
import saugykla

BAZE = "https://%s/admin/api/%s" % (nustatymai.PARDUOTUVE, nustatymai.API_VERSIJA)


def _antrastes():
    if not nustatymai.SHOPIFY_RAKTAS:
        raise SystemExit(
            "Truksta SHOPIFY_RAKTAS. Shopify admin -> Settings -> Apps and sales "
            "channels -> Develop apps -> sukurk app'sa ir nukopijuok Admin API "
            "access token (prasideda shpat_)."
        )
    return {"X-Shopify-Access-Token": nustatymai.SHOPIFY_RAKTAS}


def parduotuve():
    """Grazina parduotuves info — laiko juosta ir valiuta."""
    duom, _ = klientas.gauti(BAZE + "/shop.json", _antrastes())
    return duom.get("shop", {})


# --- uzsakymai -------------------------------------------------------------
def traukti_uzsakymus(rysys, nuo=None):
    """Traukia uzsakymus, kurie pasikeite nuo paskutinio karto.

    Naudojame updated_at_min, o ne created_at_min — kitaip nepamatytume veliau
    pridetu grazinimu prie senu uzsakymu.
    """
    nuo = nuo or saugykla.busena_gauti(rysys, "uzsakymai_iki") or nustatymai.PRADZIA
    url = klientas.su_parametrais(
        BAZE + "/orders.json",
        {"status": "any", "limit": 250, "updated_at_min": nuo, "order": "updated_at asc"},
    )
    viso = 0
    naujausia = nuo
    while url:
        duom, antrastes = klientas.gauti(url, _antrastes())
        uzsakymai = duom.get("orders", [])
        if not uzsakymai:
            break
        saugykla.uzsakymus_irasyti(rysys, uzsakymai)
        viso += len(uzsakymai)
        for u in uzsakymai:
            if (u.get("updated_at") or "") > naujausia:
                naujausia = u["updated_at"]
        rysys.commit()
        print("  uzsakymai: %d" % viso)
        url = klientas.kita_nuoroda(antrastes)

    saugykla.busena_irasyti(rysys, "uzsakymai_iki", naujausia)
    rysys.commit()
    return viso


# --- savikainos ------------------------------------------------------------
UZKLAUSA = """
query($zymeklis: String) {
  productVariants(first: 250, after: $zymeklis) {
    pageInfo { hasNextPage endCursor }
    nodes {
      legacyResourceId
      title
      product { title }
      inventoryItem { unitCost { amount } }
    }
  }
}
"""


def traukti_savikainas(rysys):
    """Nuskaito visu variantu savikaina (Cost per item)."""
    zymeklis = None
    viso = 0
    be_savikainos = []
    while True:
        duom, _ = klientas.gauti(
            BAZE + "/graphql.json",
            _antrastes(),
            duomenys={"query": UZKLAUSA, "variables": {"zymeklis": zymeklis}},
        )
        if "errors" in duom:
            raise klientas.ApiKlaida("GraphQL: %s" % duom["errors"])
        blokas = duom["data"]["productVariants"]
        eilutes = []
        for mazgas in blokas["nodes"]:
            kaina = (mazgas.get("inventoryItem") or {}).get("unitCost") or {}
            suma = kaina.get("amount")
            pavadinimas = "%s / %s" % (
                (mazgas.get("product") or {}).get("title") or "?",
                mazgas.get("title") or "",
            )
            if suma in (None, ""):
                be_savikainos.append(pavadinimas)
                reiksme = None
            else:
                reiksme = float(suma)
            eilutes.append((int(mazgas["legacyResourceId"]), reiksme, pavadinimas))
        saugykla.savikainas_irasyti(rysys, eilutes)
        viso += len(eilutes)
        rysys.commit()
        if not blokas["pageInfo"]["hasNextPage"]:
            break
        zymeklis = blokas["pageInfo"]["endCursor"]

    print("  variantu: %d, be savikainos: %d" % (viso, len(be_savikainos)))
    return be_savikainos


# --- Shopify Payments mokesciai --------------------------------------------
def traukti_mokescius(rysys):
    """Tikri Shopify Payments mokesciai kiekvienai operacijai.

    Jei parduotuve nenaudoja Shopify Payments, API grazina 404 — tada tiesiog
    praleidziame (Paysera mokesciai skaiciuojami pagal tarifa).
    """
    nuo_id = saugykla.busena_gauti(rysys, "mokesciai_id")
    url = klientas.su_parametrais(
        BAZE + "/shopify_payments/balance/transactions.json",
        {"limit": 250, "since_id": nuo_id},
    )
    viso = 0
    didziausias = int(nuo_id or 0)
    try:
        while url:
            duom, antrastes = klientas.gauti(url, _antrastes())
            irasai = duom.get("transactions", [])
            if not irasai:
                break
            eilutes = []
            for i in irasai:
                # fee grazinamas teigiamas; charge tipo irasams jis ir yra
                # musu islaida. Grazinimams (refund) fee buna 0.
                eilutes.append((
                    int(i["id"]),
                    int(i["source_order_id"]) if i.get("source_order_id") else None,
                    (i.get("processed_at") or "")[:10],
                    abs(float(i.get("fee") or 0)),
                ))
                didziausias = max(didziausias, int(i["id"]))
            saugykla.mokescius_irasyti(rysys, eilutes)
            viso += len(eilutes)
            rysys.commit()
            url = klientas.kita_nuoroda(antrastes)
    except klientas.ApiKlaida as klaida:
        if "404" in str(klaida):
            print("  Shopify Payments neaktyvus — praleidziu")
            return 0
        raise

    saugykla.busena_irasyti(rysys, "mokesciai_id", didziausias)
    rysys.commit()
    print("  mokesciu irasu: %d" % viso)
    return viso
