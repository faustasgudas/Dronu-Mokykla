# -*- coding: utf-8 -*-
"""Vienas paleidimas: susirenka viska, ka gali, ir perpiesia dashboarda.

    python src/pelnas/atnaujinti.py

Kas vyksta:
  1. Importuojami failai is pelnas/importas/ (Shopify ataskaitos, Meta CSV, PDF)
  2. Shopify API — uzsakymai, savikainos, Shopify Payments mokesciai
  3. Meta API — dienos reklamos islaidos
  4. Perskaiciuojama dienos suvestine ir sugeneruojamas pelnas/dashboard.html

Jei raktu .env dar nera, 2 ir 3 zingsniai praleidziami — dashboardas vis tiek
pastatomas is to, kas importuota.
"""
import os
import sys
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dashboard          # noqa: E402
import dienos             # noqa: E402
import importas           # noqa: E402
import islaidos           # noqa: E402
import meta               # noqa: E402
import nustatymai         # noqa: E402
import saugykla           # noqa: E402
import shopify            # noqa: E402


def main():
    atidaryti = "--neatidaryti" not in sys.argv
    rysys = saugykla.atidaryti()

    if islaidos.uztikrinti():
        print("Sukurtas %s — susivesk ten appsu ir kitas menesines islaidas."
              % islaidos.FAILAS)

    print("1/4 Failu importas")
    importas.paleisti(rysys)

    if nustatymai.SHOPIFY_RAKTAS:
        print("2/4 Shopify API")
        try:
            shopify.traukti_savikainas(rysys)
            shopify.traukti_uzsakymus(rysys)
            shopify.traukti_mokescius(rysys)
            print("    perskaiciuoju dienas is uzsakymu")
            dienos.perskaiciuoti(rysys)
        except SystemExit:
            raise
        except Exception as klaida:
            print("    NEPAVYKO: %s" % klaida)
    else:
        print("2/4 Shopify API — nera SHOPIFY_RAKTAS, praleidziu")

    if nustatymai.META_RAKTAS:
        print("3/4 Meta API")
        try:
            meta.traukti(rysys)
        except Exception as klaida:
            print("    NEPAVYKO: %s" % klaida)
    else:
        print("3/4 Meta API — nera META_RAKTAS, praleidziu")

    print("4/4 Dashboardas")
    eilutes, ispejimai = dashboard.sugeneruoti(rysys)
    rysys.close()

    if not eilutes:
        print("\nDuomenu nera. Imesk Shopify ataskaita i %s" % importas.APLANKAS)
        return

    pajamos = sum(e["pajamos"] for e in eilutes)
    bruto = sum(e["bruto_pelnas"] for e in eilutes)
    print("\n  %s .. %s  (%d dienu)" % (eilutes[0]["data"], eilutes[-1]["data"], len(eilutes)))
    print("  pajamos      %10.2f EUR" % pajamos)
    print("  bruto pelnas %10.2f EUR  (%.1f%%)"
          % (bruto, bruto / pajamos * 100 if pajamos else 0))

    if ispejimai.get("pelnas_pilnas"):
        pelnas = sum(e["pelnas"] for e in eilutes)
        print("  GRYNAS PELNAS%10.2f EUR  (%.1f%%)"
              % (pelnas, pelnas / pajamos * 100 if pajamos else 0))
    else:
        truksta = ", ".join(x["vardas"] for x in ispejimai.get("nezinomos", []))
        print("  grynas pelnas neskaiciuojamas — truksta: %s" % truksta)
    print("\n  %s" % nustatymai.DASHBOARDAS)

    if atidaryti:
        webbrowser.open("file:///" + nustatymai.DASHBOARDAS.replace("\\", "/"))


if __name__ == "__main__":
    main()
