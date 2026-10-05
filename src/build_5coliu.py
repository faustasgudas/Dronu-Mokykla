# -*- coding: utf-8 -*-
"""Sustato 5 coliu rinkinio landinga i 5-coliu/index.html.

Saltinis:  src/5-coliu.html         (cia darai visus pakeitimus)
Isvestis:  5-coliu/index.html       (generuojamas — ranka NEREDAGUOK)

Veikia kaip build_rinkinys.py: iraso tikrus adresus vietoj {{DOMENAS}} ir
{{SAKNIS}} ir iterpia bendra analitikos + sutikimo bloka pries </body>.

Pakeitus paleisk:  python src/build_5coliu.py
"""
import io
import os

from _keliai import saltinis, isvestis

SALTINIS = saltinis("5-coliu.html")
ISVESTIS = isvestis("5-coliu", "index.html")

SAKNIS = "https://shop.dronumokykla.lt"
DOMENAS = SAKNIS + "/5-coliu"
PRODUKTAS = "5-fpv-drono-rinkinys"    # Meta pikselio ViewContent


def surinkti():
    t = io.open(SALTINIS, encoding="utf-8").read()
    t = t.replace("{{DOMENAS}}", DOMENAS).replace("{{SAKNIS}}", SAKNIS)

    analitika = io.open(saltinis("_analitika.html"), encoding="utf-8").read()
    analitika = analitika.replace("{{PRODUKTAS}}", PRODUKTAS)

    if "</body>" not in t:
        raise SystemExit("Saltinyje nera </body> — nezinau, kur iterpti analitika.")
    t = t.replace("</body>", analitika + "\n</body>", 1)
    return t


def main():
    out = surinkti()
    os.makedirs(os.path.dirname(ISVESTIS), exist_ok=True)
    io.open(ISVESTIS, "w", encoding="utf-8", newline="").write(out)
    print("%-28s %6d B" % ("5-coliu/index.html", len(out.encode("utf-8"))))


if __name__ == "__main__":
    main()
