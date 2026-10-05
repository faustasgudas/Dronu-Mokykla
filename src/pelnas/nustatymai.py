# -*- coding: utf-8 -*-
"""Nustatymai ir raktai.

Slapti raktai gyvena faile .env repo saknyje (i git NEKELIAMAS).
Pavyzdys — .env.pavyzdys. Viska skaitome patys, kad nereiketu python-dotenv.

Skaiciavimo prielaidos (siuntimo savikaina, Paysera tarifai, fiksuotos
menesio islaidos) taip pat gyvena .env — ten jas ir keisk.
"""
import io
import os

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAKNIS = os.path.dirname(SRC)
ENV = os.path.join(SAKNIS, ".env")

_reiksmes = {}


def _ikelti():
    """Perskaito .env i _reiksmes. Eilutes formatas RAKTAS=reiksme."""
    if not os.path.exists(ENV):
        return
    for eil in io.open(ENV, encoding="utf-8"):
        eil = eil.strip()
        if not eil or eil.startswith("#") or "=" not in eil:
            continue
        raktas, _, reiksme = eil.partition("=")
        _reiksmes[raktas.strip()] = reiksme.strip().strip('"').strip("'")


_ikelti()


def tekstas(raktas, numatyta=None, butinas=False):
    reiksme = os.environ.get(raktas) or _reiksmes.get(raktas) or numatyta
    if butinas and not reiksme:
        raise SystemExit(
            "Truksta nustatymo %s. Idek ji i %s (pavyzdys — .env.pavyzdys)."
            % (raktas, ENV)
        )
    return reiksme


def skaicius(raktas, numatyta=0.0):
    """Grazina skaiciu arba numatyta. numatyta=None reiskia „nezinoma"."""
    reiksme = tekstas(raktas)
    if reiksme in (None, ""):
        return None if numatyta is None else float(numatyta)
    try:
        return float(str(reiksme).replace(",", "."))
    except ValueError:
        raise SystemExit("Nustatymas %s turi buti skaicius, o yra %r" % (raktas, reiksme))


# --- Shopify ---------------------------------------------------------------
PARDUOTUVE = tekstas("SHOPIFY_PARDUOTUVE", "inmmjj-kg.myshopify.com")
SHOPIFY_RAKTAS = tekstas("SHOPIFY_RAKTAS")
API_VERSIJA = tekstas("SHOPIFY_API_VERSIJA", "2026-07")

# --- Meta ------------------------------------------------------------------
META_RAKTAS = tekstas("META_RAKTAS")
META_PASKYRA = tekstas("META_PASKYRA")           # act_XXXXXXXXXX
META_VERSIJA = tekstas("META_API_VERSIJA", "v23.0")

# --- Skaiciavimo prielaidos ------------------------------------------------
# SVARBU: nieko nespejam. Kol reiksme nenurodyta, ta P&L eilute lieka TUSCIA,
# o pelnas nerodomas kaip galutinis. Geriau bruksnys nei isgalvotas skaicius.
#
# Kiek REALIAI kainuoja issiusti viena siunta. Paimk is LP Express saskaitos:
# saskaitos suma / siuntu skaicius. Nenurodyta — siuntimo eilute tuscia.
SIUNTOS_SAVIKAINA = skaicius("SIUNTOS_SAVIKAINA", None)

# Paysera: procentas nuo sumos + fiksuotas mokestis uz operacija.
# Nenurodyta — remiamasi tik tikrais Shopify duomenimis.
PAYSERA_PROC = skaicius("PAYSERA_PROC", None)
PAYSERA_FIKS = skaicius("PAYSERA_FIKS", 0.0)

# COD (atsiskaitymas atsiimant). Kurjeris surenka grynuosius ir perveda mums,
# nusiimdamas mokesti uz surinkima.
COD_MOKESTIS = skaicius("COD_MOKESTIS", None)      # EUR uz siunta
COD_PROC = skaicius("COD_PROC", 0.0)               # % nuo surinktos sumos
# Kaip Shopify vadinasi COD mokejimo budas. Keli variantai per kableli.
COD_VARDAI = [
    v.strip().lower()
    for v in (tekstas("COD_GATEWAY", "cash on delivery,cod,grynais,atsiimant") or "").split(",")
    if v.strip()
]

# Kiek dienu laukiam COD apmokejimo, kol laikom, kad siunta greiciausiai
# neatsiimta (tada pelnas uz ja greiciausiai fiktyvus).
COD_LAUKIMAS = int(skaicius("COD_LAUKIMAS", 21) or 21)

# Fiksuotos islaidos per menesi (appsai, domenas, buhalterija) — paskirstomos
# tolygiai per menesio dienas.
FIKSUOTOS_MENESIUI = skaicius("FIKSUOTOS_MENESIUI", None)

# Nuo kurios datos traukti uzsakymus pirma karta.
PRADZIA = tekstas("PRADZIA", "2025-01-01")

# --- Keliai ----------------------------------------------------------------
DUOMENYS = os.path.join(SAKNIS, "pelnas")
DUOMENU_BAZE = os.path.join(DUOMENYS, "pelnas.sqlite3")
DASHBOARDAS = os.path.join(DUOMENYS, "dashboard.html")
