# -*- coding: utf-8 -*-
"""Plonas HTTP sluoksnis: JSON, kartojimas, Shopify greicio limitas.

Naudojame tik urllib, kad nereiketu nieko instaliuoti.
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

LAUKIMAS = 30          # sekundes
BANDYMAI = 5


class ApiKlaida(Exception):
    pass


def gauti(url, antrastes=None, duomenys=None, metodas=None):
    """Kreipiasi i API ir grazina (json, antrastes).

    Kartoja esant 429 (limitas) ir 5xx — su didejancia pauze.
    """
    antrastes = dict(antrastes or {})
    antrastes.setdefault("Accept", "application/json")
    kunas = None
    if duomenys is not None:
        kunas = json.dumps(duomenys).encode("utf-8")
        antrastes.setdefault("Content-Type", "application/json")

    paskutine = None
    for bandymas in range(BANDYMAI):
        uzklausa = urllib.request.Request(
            url, data=kunas, headers=antrastes, method=metodas or ("POST" if kunas else "GET")
        )
        try:
            with urllib.request.urlopen(uzklausa, timeout=LAUKIMAS) as atsakas:
                tekstas = atsakas.read().decode("utf-8")
                return (json.loads(tekstas) if tekstas else {}), dict(atsakas.headers)
        except urllib.error.HTTPError as klaida:
            paskutine = klaida
            kodas = klaida.code
            if kodas == 429 or kodas >= 500:
                pauze = float(klaida.headers.get("Retry-After") or (2 ** bandymas))
                time.sleep(min(pauze, 20))
                continue
            smulkiau = klaida.read().decode("utf-8", "replace")[:500]
            raise ApiKlaida("HTTP %s %s\n%s" % (kodas, url, smulkiau))
        except urllib.error.URLError as klaida:
            paskutine = klaida
            time.sleep(2 ** bandymas)

    raise ApiKlaida("Nepavyko po %d bandymu: %s (%s)" % (BANDYMAI, url, paskutine))


def su_parametrais(url, parametrai):
    svarus = {k: v for k, v in parametrai.items() if v not in (None, "")}
    if not svarus:
        return url
    skyriklis = "&" if "?" in url else "?"
    return url + skyriklis + urllib.parse.urlencode(svarus)


def kita_nuoroda(antrastes):
    """Istraukia rel="next" is Shopify Link antrastes."""
    link = antrastes.get("Link") or antrastes.get("link") or ""
    for dalis in link.split(","):
        if 'rel="next"' in dalis:
            pradzia = dalis.find("<")
            pabaiga = dalis.find(">")
            if pradzia != -1 and pabaiga != -1:
                return dalis[pradzia + 1:pabaiga]
    return None
