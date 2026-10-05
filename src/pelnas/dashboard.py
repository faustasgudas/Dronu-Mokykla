# -*- coding: utf-8 -*-
"""Sugeneruoja pelnas/dashboard.html is sablono ir suskaiciuotu duomenu."""
import datetime
import io
import json
import os

import nustatymai
import skaiciavimai

SABLONAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sablonas.html")


def _pakeisti(tekstas, zyme, turinys):
    pradzia = tekstas.find("/*%s*/" % zyme)
    if pradzia == -1:
        raise SystemExit("Sablone nera zymes %s" % zyme)
    pradzia += len(zyme) + 4
    pabaiga = tekstas.find("/*%s*/" % zyme, pradzia)
    if pabaiga == -1:
        raise SystemExit("Sablone nera uzdaromos zymes %s" % zyme)
    return tekstas[:pradzia] + turinys + tekstas[pabaiga:]


def sugeneruoti(rysys):
    eilutes, ispejimai = skaiciavimai.suskaiciuoti(rysys)
    sablonas = io.open(SABLONAS, encoding="utf-8").read()

    sablonas = _pakeisti(sablonas, "DUOMENYS", json.dumps(eilutes, ensure_ascii=False))
    sablonas = _pakeisti(sablonas, "ISPEJIMAI", json.dumps(ispejimai, ensure_ascii=False))
    sablonas = sablonas.replace(
        "/*ATNAUJINTA*/", datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    )

    os.makedirs(nustatymai.DUOMENYS, exist_ok=True)
    io.open(nustatymai.DASHBOARDAS, "w", encoding="utf-8", newline="").write(sablonas)
    return eilutes, ispejimai
