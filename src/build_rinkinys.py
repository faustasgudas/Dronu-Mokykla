# -*- coding: utf-8 -*-
"""Sustato rinkinio landinga i rinkinys/index.html.

Saltinis:  src/rinkinys.html        (cia darai visus pakeitimus)
Isvestis:  rinkinys/index.html      (generuojamas — ranka NEREDAGUOK)

Skirtingai nei pradziamokslio build'as, cia nereikia nieko iskaidyti:
saltinis jau yra pilnas puslapis. Skriptas tik:
  1) iraso tikrus adresus vietoj {{DOMENAS}} ir {{SAKNIS}},
  2) iterpia bendra analitikos + sutikimo bloka pries </body>.

Pakeitus paleisk:  python src/build_rinkinys.py
"""
import io

from _keliai import saltinis, isvestis

SALTINIS = saltinis("rinkinys.html")
ISVESTIS = isvestis("rinkinys", "index.html")

SAKNIS = "https://shop.dronumokykla.lt"
DOMENAS = SAKNIS + "/rinkinys"
PRODUKTAS = "fpv-drono-rinkinys"      # Meta pikselio ViewContent


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
    io.open(ISVESTIS, "w", encoding="utf-8", newline="").write(out)
    print("%-28s %6d B" % ("rinkinys/index.html", len(out.encode("utf-8"))))


if __name__ == "__main__":
    main()
