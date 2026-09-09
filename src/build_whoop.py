"""
Surenka whoop komplekto landingą iš vieno šaltinio.

  python build_whoop.py

Šaltinis:  dronumokykla-whoop.html   (čia darai visus pakeitimus)
Išvestis:  whoop/index.html (repo saknyje)

Paprastesnis nei build.py, nes:
  - nėra Shopify Custom Liquid dvinario (tik standalone puslapis),
  - visos nuotraukos jau realios (Shopify CDN arba img/),
    todėl nereikia VIETINES pakeitimo mechanizmo.
"""

import io
import os

from _keliai import saltinis, isvestis

SALTINIS = saltinis("dronumokykla-whoop.html")
GALVA = saltinis("_head_whoop.html")
PARDUOTUVE = "https://dronumokykla.lt"
DOMENAS = "https://shop.dronumokykla.lt/rinkinys"   # PAKEISK, jei adresas kitas
ISVESTIS = isvestis("rinkinys", "index.html")


def dalys():
    """Isskaido saltini i CSS, HTML ir JS — ta pati logika kaip build.py:
    zymes ieskom PO <div id="dm">, nes failo antrastes komentare
    pamineti zodziai <style> ir <script> kitaip suklaidina paieska."""
    s = io.open(SALTINIS, encoding="utf-8").read()
    divp = s.index('<div id="dm">')
    a = s.index("<style>", divp)
    b = s.index("</style>", a)
    c = s.index("<script>", b)
    d = s.index("</script>", c)

    css = s[a + len("<style>"):b]
    js = s[c + len("<script>"):d]
    body = s[divp:a] + s[b + len("</style>"):c]

    assert body.lstrip().startswith('<div id="dm">')
    assert "<style>" not in body and "<script>" not in body
    assert "DM_VARIANTAI" in js
    return css, body.rstrip(), js


def surinkti():
    css, body, js = dalys()

    # Santykinės nuorodos i parduotuve reikia pilnu adresu, nes puslapis
    # gyvena atskirai (shop.dronumokykla.lt), ne ant Shopify domeno.
    body = body.replace('href="/products/', 'href="%s/products/' % PARDUOTUVE)
    body = body.replace('href="/policies/', 'href="%s/policies/' % PARDUOTUVE)
    body = body.replace('href="/cart/', 'href="%s/cart/' % PARDUOTUVE)

    galva = io.open(GALVA, encoding="utf-8").read().replace("{{DOMENAS}}", DOMENAS)
    galva = galva.replace("/*{{CSS}}*/", css)

    os.makedirs(os.path.dirname(ISVESTIS), exist_ok=True)
    analitika = io.open(saltinis("_analitika.html"), encoding="utf-8").read()
    analitika = analitika.replace("{{PRODUKTAS}}", "fpv-drono-rinkinys")
    out = (galva + body + "\n</div>\n\n<script>\n" + js + "\n</script>\n\n"
           + analitika + "\n</body>\n</html>\n")
    io.open(ISVESTIS, "w", encoding="utf-8").write(out)
    return out


if __name__ == "__main__":
    out = surinkti()
    print("%-28s %6d B" % ("rinkinys/index.html", len(out.encode("utf-8"))))
