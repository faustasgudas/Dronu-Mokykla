# -*- coding: utf-8 -*-
"""SQLite saugykla.

Laikome ZALIUS duomenis (uzsakymu JSON, savikainas, mokescius, reklamos
islaidas). Visi skaiciavimai daromi is naujo kiekvieno karto, todel pakeitus
prielaidas .env faile nereikia nieko traukti is naujo.
"""
import json
import os
import sqlite3

from nustatymai import DUOMENU_BAZE, DUOMENYS

SCHEMA = """
CREATE TABLE IF NOT EXISTS uzsakymai (
    id           INTEGER PRIMARY KEY,
    sukurta      TEXT NOT NULL,
    atnaujinta   TEXT NOT NULL,
    turinys      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS uzsakymai_sukurta ON uzsakymai(sukurta);

CREATE TABLE IF NOT EXISTS savikainos (
    variantas    INTEGER PRIMARY KEY,
    savikaina    REAL,
    pavadinimas  TEXT
);

CREATE TABLE IF NOT EXISTS mokesciai (
    id           INTEGER PRIMARY KEY,
    uzsakymas    INTEGER,
    data         TEXT,
    mokestis     REAL
);
CREATE INDEX IF NOT EXISTS mokesciai_uzsakymas ON mokesciai(uzsakymas);

CREATE TABLE IF NOT EXISTS reklama (
    data         TEXT NOT NULL,
    kanalas      TEXT NOT NULL,
    suma         REAL NOT NULL,
    tikslumas    TEXT DEFAULT 'diena',   -- diena | paskirstyta
    PRIMARY KEY (data, kanalas)
);

-- Viena eilute per diena. Uzpildo arba API (tiksliau), arba importuota
-- Shopify ataskaita. saltinis pasako, kuo remiamasi.
CREATE TABLE IF NOT EXISTS dienos (
    data              TEXT PRIMARY KEY,
    bruto             REAL DEFAULT 0,   -- gross sales, be PVM
    neto              REAL DEFAULT 0,   -- net sales (- nuolaidos, - grazinimai), be PVM
    cogs              REAL DEFAULT 0,   -- prekiu savikaina
    siuntimo_pajamos  REAL DEFAULT 0,   -- kiek uz pristatyma paeme is kliento
    uzsakymu          INTEGER,          -- NULL, jei saltinis to nezino
    be_savikainos     REAL DEFAULT 0,   -- neto dalis, kuriai savikaina nezinoma
    cod_uzsakymu      INTEGER DEFAULT 0,-- atsiskaitymas atsiimant (COD)
    cod_neto          REAL DEFAULT 0,   -- ju neto verte
    neapmoketa        REAL DEFAULT 0,   -- neto, uz kuri pinigu dar negauta
    saltinis          TEXT
);

-- Shopify ataskaita „Payment processing fees by month" — tikri korteliu
-- mokesciai. COD ir kiti surinkejai cia NEIeina.
CREATE TABLE IF NOT EXISTS mokesciai_menesio (
    menuo        TEXT PRIMARY KEY,   -- YYYY-MM
    suma         REAL NOT NULL
);

-- Tikri kurjerio duomenys is LP Express siuntu ataskaitos.
CREATE TABLE IF NOT EXISTS siuntos (
    data         TEXT PRIMARY KEY,
    siuntu       INTEGER DEFAULT 0,   -- apmokestinamos (be atsauktu)
    atsauktu     INTEGER DEFAULT 0,
    cod_siuntu   INTEGER DEFAULT 0,
    cod_suma     REAL DEFAULT 0       -- su PVM, kiek kurjeris surinko
);

CREATE TABLE IF NOT EXISTS saskaitos (
    id           TEXT PRIMARY KEY,   -- laisko Message-ID + priedo vardas
    siuntejas    TEXT,
    tema         TEXT,
    data         TEXT,               -- YYYY-MM-DD
    failas       TEXT,
    kategorija   TEXT,               -- siuntimas | fiksuotos | prekes | reklama | ?
    suma         REAL,               -- be PVM, jei pavyko atskirti
    pvm          REAL,
    i_pelna      INTEGER DEFAULT 0   -- ar itraukiama i P&L (kad nedubliuotume)
);
CREATE INDEX IF NOT EXISTS saskaitos_data ON saskaitos(data);

CREATE TABLE IF NOT EXISTS busena (
    raktas       TEXT PRIMARY KEY,
    reiksme      TEXT
);
"""


def atidaryti():
    os.makedirs(DUOMENYS, exist_ok=True)
    rysys = sqlite3.connect(DUOMENU_BAZE)
    rysys.row_factory = sqlite3.Row
    rysys.executescript(SCHEMA)
    _migruoti(rysys)
    return rysys


def _migruoti(rysys):
    """Prideda stulpelius, atsiradusius jau sukurus baze."""
    esami = {e["name"] for e in rysys.execute("PRAGMA table_info(reklama)")}
    if "tikslumas" not in esami:
        rysys.execute("ALTER TABLE reklama ADD COLUMN tikslumas TEXT DEFAULT 'diena'")

    esami = {e["name"] for e in rysys.execute("PRAGMA table_info(dienos)")}
    for stulpelis, tipas in (("cod_uzsakymu", "INTEGER DEFAULT 0"),
                             ("cod_neto", "REAL DEFAULT 0"),
                             ("neapmoketa", "REAL DEFAULT 0")):
        if stulpelis not in esami:
            rysys.execute("ALTER TABLE dienos ADD COLUMN %s %s" % (stulpelis, tipas))
    rysys.commit()


# --- busena ----------------------------------------------------------------
def busena_gauti(rysys, raktas, numatyta=None):
    eil = rysys.execute("SELECT reiksme FROM busena WHERE raktas=?", (raktas,)).fetchone()
    return eil["reiksme"] if eil else numatyta


def busena_irasyti(rysys, raktas, reiksme):
    rysys.execute(
        "INSERT INTO busena(raktas, reiksme) VALUES(?,?) "
        "ON CONFLICT(raktas) DO UPDATE SET reiksme=excluded.reiksme",
        (raktas, str(reiksme)),
    )


# --- uzsakymai -------------------------------------------------------------
def uzsakymus_irasyti(rysys, uzsakymai):
    rysys.executemany(
        "INSERT INTO uzsakymai(id, sukurta, atnaujinta, turinys) VALUES(?,?,?,?) "
        "ON CONFLICT(id) DO UPDATE SET "
        "  sukurta=excluded.sukurta, atnaujinta=excluded.atnaujinta, "
        "  turinys=excluded.turinys",
        [
            (u["id"], u.get("created_at") or "", u.get("updated_at") or "", json.dumps(u))
            for u in uzsakymai
        ],
    )


def uzsakymus_skaityti(rysys):
    for eil in rysys.execute("SELECT turinys FROM uzsakymai ORDER BY sukurta"):
        yield json.loads(eil["turinys"])


# --- savikainos ------------------------------------------------------------
def savikainas_irasyti(rysys, eilutes):
    rysys.executemany(
        "INSERT INTO savikainos(variantas, savikaina, pavadinimas) VALUES(?,?,?) "
        "ON CONFLICT(variantas) DO UPDATE SET "
        "  savikaina=excluded.savikaina, pavadinimas=excluded.pavadinimas",
        eilutes,
    )


def savikainos_zemelapis(rysys):
    return {
        eil["variantas"]: (eil["savikaina"], eil["pavadinimas"])
        for eil in rysys.execute("SELECT * FROM savikainos")
    }


# --- mokesciai -------------------------------------------------------------
def mokescius_irasyti(rysys, eilutes):
    rysys.executemany(
        "INSERT INTO mokesciai(id, uzsakymas, data, mokestis) VALUES(?,?,?,?) "
        "ON CONFLICT(id) DO UPDATE SET "
        "  uzsakymas=excluded.uzsakymas, data=excluded.data, mokestis=excluded.mokestis",
        eilutes,
    )


def mokesciai_pagal_uzsakyma(rysys):
    zemelapis = {}
    for eil in rysys.execute(
        "SELECT uzsakymas, SUM(mokestis) AS viso FROM mokesciai "
        "WHERE uzsakymas IS NOT NULL GROUP BY uzsakymas"
    ):
        zemelapis[eil["uzsakymas"]] = eil["viso"] or 0.0
    return zemelapis


# --- dienos ----------------------------------------------------------------
LAUKAI = ("bruto", "neto", "cogs", "siuntimo_pajamos", "uzsakymu", "be_savikainos",
          "cod_uzsakymu", "cod_neto", "neapmoketa")


def dienas_irasyti(rysys, eilutes, saltinis):
    """eilutes: (data, bruto, neto, cogs, siuntimo_pajamos, uzsakymu,
                 be_savikainos[, cod_uzsakymu, cod_neto, neapmoketa])

    API duomenys (saltinis='api') visada nugali importuotus — todel
    importuoti irasai nerasomi ant jau esanciu API irasu.
    """
    for eil in eilutes:
        eil = tuple(eil)
        if len(eil) == 7:                      # importas COD duomenu neturi
            eil += (0, 0.0, 0.0)
        data = eil[0]
        esamas = rysys.execute(
            "SELECT saltinis FROM dienos WHERE data=?", (data,)
        ).fetchone()
        if esamas and esamas["saltinis"] == "api" and saltinis != "api":
            continue
        rysys.execute(
            "INSERT INTO dienos(data, bruto, neto, cogs, siuntimo_pajamos, "
            "                   uzsakymu, be_savikainos, cod_uzsakymu, cod_neto, "
            "                   neapmoketa, saltinis) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(data) DO UPDATE SET "
            "  bruto=excluded.bruto, neto=excluded.neto, cogs=excluded.cogs, "
            "  siuntimo_pajamos=excluded.siuntimo_pajamos, "
            "  uzsakymu=COALESCE(excluded.uzsakymu, dienos.uzsakymu), "
            "  be_savikainos=excluded.be_savikainos, "
            "  cod_uzsakymu=excluded.cod_uzsakymu, cod_neto=excluded.cod_neto, "
            "  neapmoketa=excluded.neapmoketa, saltinis=excluded.saltinis",
            eil + (saltinis,),
        )


def uzsakymu_duomenis_irasyti(rysys, eilutes):
    """Atnaujina TIK uzsakymu skaiciu ir COD — neto/cogs palieka ramybeje.

    eilutes: [(data, uzsakymu, cod_uzsakymu, cod_neto, neapmoketa)]

    Taip Shopify uzsakymu eksportas papildo tai, ko nera pelno ataskaitoje
    (uzsakymu kiekis, mokejimo budai), nieko neperrasydamas.
    """
    # TIK atnaujinam jau esamas dienas. Naujos neikuriam: be pelno ataskaitos
    # tai dienai nezinotume nei pajamu, nei savikainos, ir gautusi diena su
    # uzsakymu bet 0 EUR apyvarta — melagingas nulis.
    for data, uzs, cod_uzs, cod_neto, neapmoketa in eilutes:
        rysys.execute(
            "UPDATE dienos SET uzsakymu=?, cod_uzsakymu=?, cod_neto=?, "
            "                  neapmoketa=? WHERE data=?",
            (uzs, cod_uzs, cod_neto, neapmoketa, data),
        )


def dienas_skaityti(rysys):
    return [dict(eil) for eil in rysys.execute("SELECT * FROM dienos ORDER BY data")]


# --- menesio mokesciai -----------------------------------------------------
def menesio_mokescius_irasyti(rysys, eilutes):
    rysys.executemany(
        "INSERT INTO mokesciai_menesio(menuo, suma) VALUES(?,?) "
        "ON CONFLICT(menuo) DO UPDATE SET suma=excluded.suma",
        eilutes,
    )


def menesio_mokesciai(rysys):
    return {
        eil["menuo"]: eil["suma"]
        for eil in rysys.execute("SELECT * FROM mokesciai_menesio")
    }


# --- siuntos ---------------------------------------------------------------
def siuntas_irasyti(rysys, eilutes):
    rysys.executemany(
        "INSERT INTO siuntos(data, siuntu, atsauktu, cod_siuntu, cod_suma) "
        "VALUES(?,?,?,?,?) "
        "ON CONFLICT(data) DO UPDATE SET "
        "  siuntu=excluded.siuntu, atsauktu=excluded.atsauktu, "
        "  cod_siuntu=excluded.cod_siuntu, cod_suma=excluded.cod_suma",
        eilutes,
    )


def siuntos_pagal_diena(rysys):
    return {eil["data"]: dict(eil) for eil in rysys.execute("SELECT * FROM siuntos")}


# --- saskaitos -------------------------------------------------------------
def saskaitas_irasyti(rysys, eilutes):
    rysys.executemany(
        "INSERT INTO saskaitos(id, siuntejas, tema, data, failas, kategorija, "
        "                      suma, pvm, i_pelna) VALUES(?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT(id) DO UPDATE SET "
        "  kategorija=excluded.kategorija, suma=excluded.suma, "
        "  pvm=excluded.pvm, i_pelna=excluded.i_pelna",
        eilutes,
    )


def saskaitos_pagal_menesi(rysys, kategorija):
    """Grazina {YYYY-MM: suma} tik toms saskaitoms, kurios eina i P&L."""
    zemelapis = {}
    for eil in rysys.execute(
        "SELECT substr(data,1,7) AS men, SUM(suma) AS viso FROM saskaitos "
        "WHERE i_pelna=1 AND kategorija=? AND suma IS NOT NULL GROUP BY men",
        (kategorija,),
    ):
        zemelapis[eil["men"]] = eil["viso"] or 0.0
    return zemelapis


# --- reklama ---------------------------------------------------------------
def reklama_irasyti(rysys, eilutes):
    """eilutes: (data, kanalas, suma) arba (data, kanalas, suma, tikslumas).

    Tikslus dienos irasas nugali paskirstyta — kad veliau importavus dienini
    eksporta jis pakeistu ankstesni vidurki.
    """
    paruosta = [e if len(e) == 4 else tuple(e) + ("diena",) for e in eilutes]
    rysys.executemany(
        "INSERT INTO reklama(data, kanalas, suma, tikslumas) VALUES(?,?,?,?) "
        "ON CONFLICT(data, kanalas) DO UPDATE SET "
        "  suma=excluded.suma, tikslumas=excluded.tikslumas "
        "WHERE excluded.tikslumas='diena' OR reklama.tikslumas='paskirstyta'",
        paruosta,
    )


def reklamos_tikslumas(rysys):
    return {
        eil["data"]: eil["tikslumas"]
        for eil in rysys.execute("SELECT data, tikslumas FROM reklama")
    }


def reklama_pagal_diena(rysys):
    zemelapis = {}
    for eil in rysys.execute("SELECT data, SUM(suma) AS viso FROM reklama GROUP BY data"):
        zemelapis[eil["data"]] = eil["viso"] or 0.0
    return zemelapis
