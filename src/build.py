"""
Surenka abi versijas is vieno saltinio.

  python build.py

Saltinis:  dronumokykla-pradziamokslis.html   (cia darai visus pakeitimus)
Isvestis:  1-turinys.html + 2-skriptas.html   -> Shopify Custom Liquid (dvi sekcijos)
           index.html (repo saknyje)          -> GitHub Pages

Taip nereikia to paties taisyti dviese vietose.
"""

import io
import os
import re

from _keliai import saltinis, isvestis

SALTINIS = saltinis("dronumokykla-pradziamokslis.html")
PARDUOTUVE = "https://dronumokykla.lt"
DOMENAS = "https://shop.dronumokykla.lt"   # PAKEISK, jei landingo domenas kitas

# Nuotraukos atskirai versijai - vietiniai failai salia index.html
VIETINES = {
    "hero": PARDUOTUVE + "/cdn/shop/files/pocket_df2d9885-b492-475e-967a-ae5c7b3641fb.png?v=1764994452&width=1200",
    "medziaga": "img/medziaga.webp",
    "simuliatorius": "img/simuliatorius.webp",
    "videoPosteris": "img/video-plakatas.webp",
    "pagrindai": "img/pagrindai.webp",
    "valdymoIranga": "img/valdymo-iranga.webp",
    "pilotavimoPratimai": "img/pilotavimo-pratimai.webp",
    "rezultatas": "img/rezultatas.webp",
    "instruktoriai": "img/instruktoriai.webp",
    "kodelSvarbu": "img/kodel-svarbu.webp",
    "visiGali": "img/visi-gali.webp",
    "logo": "img/logo.webp",
    "pultas1": "img/pultas-1.webp",
    "pultas2": "img/pultas-2.webp",
    "pultas3": "img/pultas-3.webp",
    "istorijaKariuomene": "img/istorija-kariuomene.webp",
    "istorija": "img/istorija.webp",
    "karolisFaustas": "img/karolis-faustas.webp",
    # Irodymu juosta. image00026jpegkopija.jpg NENAUDOJAMA - nera zmogaus sutikimo.
    "irodymai1": "img/irodymai-mokymai.webp",
    "irodymai2": "img/irodymai-kariuomene.webp",
    "irodymai3": "img/irodymai-lenktynes.webp",
    "irodymai4": "img/irodymai-servisas.webp",
    "bendruomene1": "img/bendruomene1.webp",
    "bendruomene2": "img/bendruomene2.webp",
    "bendruomene3": "img/bendruomene3.webp",
}

# Didesni variantai. Naudojami tik ten, kur langelis platus (irodymu juosta).
VIETINES_2X = {
    "irodymai1": "img/irodymai-mokymai@2x.webp",
    "irodymai2": "img/irodymai-kariuomene@2x.webp",
    "irodymai3": "img/irodymai-lenktynes@2x.webp",
    "irodymai4": "img/irodymai-servisas@2x.webp",
}

DOMENO_PRIEDAS = '''  "use strict";

  /* =========================================================
     KONFIGURACIJA 0 - PARDUOTUVES ADRESAS
     =========================================================
     Sis puslapis gyvena atskirai nuo Shopify, todel nuorodos i
     parduotuve turi buti pilnos. Keisi tik jei keisis domenas. */
  var DM_PARDUOTUVE = "%s";

  /* UTM zymos is reklamos perkeliamos i krepselio nuoroda, kad
     Shopify matytu, is kurios kampanijos atejo uzsakymas. */
  function dmUtm() {
    var q = window.location.search;
    if (!q || q.length < 2) return "";
    var leisti = ["utm_source","utm_medium","utm_campaign","utm_content","utm_term","fbclid","gclid"];
    var r = [];
    q.replace(/^[?]/, "").split("&").forEach(function (p) {
      if (leisti.indexOf(p.split("=")[0]) !== -1) r.push(p);
    });
    return r.length ? "?" + r.join("&") : "";
  }

  function dmKrepselis(id) {
    return DM_PARDUOTUVE + "/cart/" + id + ":1" + dmUtm();
  }''' % PARDUOTUVE


def dalys():
    """Isskaido saltini i CSS, HTML ir JS.

    Zymes ieskom PO <div id="dm">, nes failo antrastes komentare
    pamineti zodziai <style> ir <script> kitaip suklaidina paieska.
    """
    s = io.open(SALTINIS, encoding="utf-8").read()
    divp = s.index('<div id="dm">')
    a = s.index("<style>", divp)
    b = s.index("</style>", a)
    c = s.index("<script>", b)
    d = s.index("</script>", c)

    css = s[a + len("<style>"):b]
    js = s[c + len("<script>"):d]
    body = s[divp:a] + s[b + len("</style>"):c]
    uodega = s[d + len("</script>"):]
    uodega = uodega[:uodega.index("<!--")].strip()

    assert body.lstrip().startswith('<div id="dm">')
    assert "<style>" not in body and "<script>" not in body
    assert "DM_VARIANTAI" in js
    return css, body.rstrip(), js, uodega


def shopify(css, body, js, uodega):
    galva = io.open(SALTINIS, encoding="utf-8").read()
    galva = galva[:galva.index('<div id="dm">')]
    d1 = galva + body + "\n\n" + uodega + "\n<!-- /#dm - 1 dalis baigiasi -->\n"
    d1 = d1.replace(body, "<style>" + css + "</style>\n" + body, 1)
    d2 = ('<!-- =========================================================\n'
          '     DRONU MOKYKLA - 2 dalis is 2: SKRIPTAS\n'
          '     Iklijuok i ANTRA "Custom Liquid" sekcija, kuri stovi\n'
          '     IS KART PO pirmosios ("1 dalis - turinys").\n'
          '     ========================================================= -->\n\n'
          "<script>" + js + "</script>\n")
    io.open("1-turinys.html", "w", encoding="utf-8").write(d1)
    io.open("2-skriptas.html", "w", encoding="utf-8").write(d2)
    return d1, d2


def atskiras(css, body, js):
    css = re.sub(r"@import url\([^)]*\);\s*", "", css).strip()

    js = js.replace('  "use strict";', DOMENO_PRIEDAS, 1)
    js = js.replace('var href = "/cart/" + v.id + ":1";', "var href = dmKrepselis(v.id);")
    js = js.replace('fetch("/products/" + DM_PRODUKTO_HANDLE + ".js"',
                    'fetch(DM_PARDUOTUVE + "/products/" + DM_PRODUKTO_HANDLE + ".js"')
    js = js.replace('fetch("/products/" + card.getAttribute("data-dm-handle") + ".js",',
                    'fetch(DM_PARDUOTUVE + "/products/" + card.getAttribute("data-dm-handle") + ".js",')
    # Kelia irasom TIK jei failas tikrai yra. Kitaip liktu <img> i neesanti
    # faila (sulauzyta nuotrauka); tuscias laukas vietoj to parodo bruksniuota
    # langeli su paaiskinimu, ir puslapi galima kelti dar nebaigta.
    truksta = []
    for k, v in VIETINES.items():
        if v.startswith("img/") and not os.path.exists(isvestis(v)):
            truksta.append((k, v))
            continue
        js = re.sub(r'(\b' + k + r':\s*)"[^"]*"', lambda m, v=v: m.group(1) + '"' + v + '"', js, count=1)
    for k, v in truksta:
        print("  TRUKSTA %-12s -> %s (rodomas placeholder'is)" % (k, v))

    turimi = dict((k, v) for k, v in VIETINES_2X.items()
                  if os.path.exists(isvestis(v)))
    if turimi:
        eil = ", ".join('%s: "%s"' % (k, v) for k, v in sorted(turimi.items()))
        js = js.replace("var DM_NUOTRAUKOS_2X = {};",
                        "var DM_NUOTRAUKOS_2X = { " + eil + " };", 1)

    body = body.replace('href="/products/', 'href="%s/products/' % PARDUOTUVE)
    body = body.replace('href="/policies/', 'href="%s/policies/' % PARDUOTUVE)
    body = body.replace('href="/cart/', 'href="%s/cart/' % PARDUOTUVE)

    galva = io.open(saltinis("_head.html"), encoding="utf-8").read().replace("{{DOMENAS}}", DOMENAS)
    galva = galva.replace("/*{{CSS}}*/", css)

    out = galva + body + "\n</div>\n\n<script>\n" + js + "\n</script>\n\n</body>\n</html>\n"
    io.open(isvestis("index.html"), "w", encoding="utf-8").write(out)
    return out


# Shopify "Custom Liquid" versija nebekuriama: puslapis peraugo 50 000 B riba,
# o puslapis dabar gyvena atskirai (shop.dronumokykla.lt). Jei kada prireiktu -
# nustatyk SHOPIFY = True, bet teks trumpinti turini.
SHOPIFY = False

if __name__ == "__main__":
    css, body, js, uodega = dalys()
    if SHOPIFY:
        d1, d2 = shopify(css, body, js, uodega)
        for vardas, turinys in [("1-turinys.html", d1), ("2-skriptas.html", d2)]:
            b = len(turinys.encode("utf-8"))
            zyma = "OK" if b <= 50000 else "PER DIDELIS"
            print("%-20s %6d B  (%s)" % (vardas, b, zyma))
    idx = atskiras(css, body, js)
    print("%-20s %6d B" % ("index.html", len(idx.encode("utf-8"))))
