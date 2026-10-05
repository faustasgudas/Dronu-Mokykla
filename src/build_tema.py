# -*- coding: utf-8 -*-
"""Sustato visus tris landingus Shopify temai (aplankas tema/).

Is to paties saltinio, kaip ir GitHub Pages versijos:
  src/5-coliu.html                    -> /pages/5-coliu
  src/rinkinys.html                   -> /pages/rinkinys
  src/dronumokykla-pradziamokslis.html-> /pages/pradziamokslis

Kiekvienam sukuriama:
  tema/sections/<vardas>.liquid       — visas turinys (HTML + CSS + JS)
  tema/templates/page.<vardas>.liquid — sablonas
Bendrai:
  tema/assets/dm-*                    — nuotraukos

Landingai naudoja iprasta temos rema, todel lieka parduotuves virsutine
juosta, krepselis ir poraste. Landingo savos juostos isimamos, o visas jo
CSS apribojamas iki .dm-landingas bloko, kad neliestu temos daliu.

Kuo skiriasi nuo GitHub Pages versijos:
  - nera slapuku juostos ir Meta pikselio — viska tvarko pati Shopify;
  - prekiu kainos ir likuciai iterpiami is karto per Liquid (be fetch);
  - nuotraukos imamos is temos assets.

Paleidus:  python src/build_tema.py
"""
import io
import os
import re
import shutil

import build as pradziamokslio_build
from _keliai import saltinis, isvestis

TEMA = isvestis("tema")
ASSETS = os.path.join(TEMA, "assets")


# --------------------------------------------------------------- nuotraukos
def turtas(kelias):
    """/img/5col/manta-34.webp -> dm-5col-manta-34.webp (assets aplankas plokscias)."""
    v = kelias.lstrip("/").replace("img/", "", 1).replace("/", "-")
    return "dm-" + v.replace("@", "-at-")


def nuotraukos(t, surinktos):
    """Visus "/img/..." kelius pakeicia i temos assets adresus."""
    for k in sorted(set(re.findall(r'"(/img/[^"]+)"', t))):
        is_kur = isvestis(k.lstrip("/"))
        if not os.path.exists(is_kur):
            print("  TRUKSTA %s — praleidziu" % k)
            continue
        surinktos.add((is_kur, turtas(k)))
        t = t.replace('"%s"' % k, "\"{{ '%s' | asset_url }}\"" % turtas(k))
    return t


def vidines_nuorodos(t):
    """Temoje landingai gyvena tame paciame domene, tad nuorodos tarp ju —
    trumpos. Taip zmogus neiskrenta i GitHub Pages versija."""
    for vardas in ("pradziamokslis", "rinkinys", "5-coliu"):
        t = t.replace("https://shop.dronumokykla.lt/%s/" % vardas, "/pages/%s" % vardas)
    return t


# --------------------------------------------------------------- turinys
# Temoje virsutine juosta ir poraste ateina is pacios parduotuves, todel
# landingo savos juostos isimamos. Garantiju juosta taip pat — ta pati
# informacija jau yra temos porasteje.
NUIMTI = {
    "5-coliu": [r'<header class="virsus">.*?</header>',
                r'<section class="garantijos">.*?</section>',
                r'<footer class="poraste">.*?</footer>'],
    "rinkinys": [r'<header class="virsus">.*?</header>',
                 r'<section class="garantijos">.*?</section>',
                 r'<footer class="poraste">.*?</footer>'],
    "pradziamokslis": [r'<header class="dm-top">.*?</header>',
                       r'<footer class="dm-foot">.*?</footer>'],
}


def nuimti_juostas(kunas, vardas):
    for sablonas in NUIMTI[vardas]:
        kunas, kiek = re.subn(sablonas, "", kunas, flags=re.S)
        if kiek != 1:
            raise SystemExit("%s: %s rasta %d kartus" % (vardas, sablonas[:30], kiek))
    return kunas


# Klase kartojama du kartus (.dm-landingas.dm-landingas) — taip kiekviena musu
# taisykle tampa stipresne uz temos taisykles, kurios daznai yra .kazkas h2 ar
# .card p pavidalo. Be sito tema perrasytu spalvas, didziasias raides ir tarpus.
SRITIS = ".dm-landingas.dm-landingas"


def _pries_sriti(sel):
    """Vienas selektorius -> apribotas iki landingo bloko."""
    s = sel.strip()
    if not s or s.startswith("@"):
        return sel
    if s.startswith(":root") or s.startswith("html") or s.startswith("#dm"):
        return s          # kintamieji ir jau apribotas pradziamokslio CSS
    if s == "*":
        return SRITIS + ", " + SRITIS + " *"
    if s.startswith("body"):
        return SRITIS + s[4:]
    return SRITIS + " " + s


def _skelti(selektoriai):
    """Skelia per kablelius, bet ne skliaustuose (pvz., :is(a, b))."""
    dalys, gylis, dabar = [], 0, ""
    for c in selektoriai:
        if c == "(":
            gylis += 1
        elif c == ")":
            gylis -= 1
        if c == "," and gylis == 0:
            dalys.append(dabar); dabar = ""
        else:
            dabar += c
    dalys.append(dabar)
    return dalys


def apriboti_css(css):
    """Prideda .dm-landingas pries kiekviena selektoriu, kad landingo stiliai
    nepaliestu parduotuves meniu ir porastes. @media ir @supports — gilyn,
    @keyframes ir @font-face — nekeiciami."""
    isvestis, i, n = [], 0, len(css)
    while i < n:
        pradzia = css.find("{", i)
        if pradzia == -1:
            isvestis.append(css[i:]); break
        galva = css[i:pradzia]
        gylis, j = 1, pradzia + 1
        while j < n and gylis:
            if css[j] == "{":
                gylis += 1
            elif css[j] == "}":
                gylis -= 1
            j += 1
        vidus = css[pradzia + 1:j - 1]
        # Komentarus nuimam TIK patikrai: kitaip pries @media esantis komentaras
        # paslepdavo, kad tai media blokas, ir jo vidus likdavo neapribotas.
        gv = re.sub(r"/\*.*?\*/", "", galva, flags=re.S).strip()
        if gv.startswith("@media") or gv.startswith("@supports"):
            isvestis.append(galva + "{" + apriboti_css(vidus) + "}")
        elif gv.startswith("@"):
            isvestis.append(galva + "{" + vidus + "}")
        else:
            komentaras = ""
            if "*/" in galva:
                riba = galva.rindex("*/") + 2
                komentaras, galva = galva[:riba], galva[riba:]
            nauji = ", ".join(_pries_sriti(s) for s in _skelti(galva))
            isvestis.append(komentaras + nauji + "{" + vidus + "}")
        i = j
    return "".join(isvestis)


# Tema turi savo taisykles h1, p, a, button ir t. t. Musu landingas spalva
# daznai paveldi is tevinio bloko (pvz., .hero{color:#fff}), o paveldeta
# reiksme visada pralaimi tiesioginei temos taisyklei. Todel pirmiausia
# grazinam paveldejima; visos musu taisykles eina po sito ir ji nugali.
ATSTATYMAS = ("""
/* Temos stiliu neutralizavimas landingo viduje: grazinam paveldejima ir
   numatytas reiksmes. Visos musu taisykles eina po sito ir ji nugali. */
%(s)s *,%(s)s *::before,%(s)s *::after{
  color:inherit;font-family:inherit;line-height:inherit;letter-spacing:inherit;
  text-transform:none;font-style:normal;text-align:inherit;
  background:none;box-shadow:none;text-shadow:none;transition:none;
  min-width:0;min-height:0;max-width:none;max-height:none;
  border:0;border-radius:0}
/* Fokuso ramelis BUTINAS: be jo klaviatura naršantis zmogus nemato, kur yra.
   currentColor — tamsiose sekcijose baltas, sviesiose tamsus. */
%(s)s :focus-visible{outline:3px solid currentColor;outline-offset:2px}
%(s)s h1,%(s)s h2,%(s)s h3,%(s)s h4,%(s)s h5,%(s)s h6{font-weight:inherit}
%(s)s a{text-decoration:none}
/* Tema visiems mygtukams deda fiksuota auksti (--buttons-height), draudzia
   teksto kelima ir prideda tarpus — del to kortelių turinys susispausdavo. */
%(s)s button{width:auto;height:auto;padding:0;margin:0;cursor:pointer;
  white-space:normal;gap:0;display:inline-block;font-size:inherit}
%(s)s img,%(s)s svg{max-width:100%%;height:auto}
%(s)s ul,%(s)s ol{list-style:none}
/* Tema slepia tuscius elementus (theme.css: div:empty{display:none}). Musu
   landinge tokie yra baltas puslankis, propeleriu diskai, varneles ir blokai,
   kuriuos uzpildo JS. [hidden] nelieciam — tai tycia paslepti blokai. */
%(s)s div:empty:not([hidden]),%(s)s section:empty:not([hidden]),
%(s)s span:empty:not([hidden]),%(s)s a:empty:not([hidden]),
%(s)s p:empty:not([hidden]),%(s)s ul:empty:not([hidden]),
%(s)s ol:empty:not([hidden]),%(s)s i:empty:not([hidden]){display:revert}
""" % {"s": ".dm-landingas.dm-landingas"})


# --------------------------------------------------------------- Judge.me
# Statiniai atsiliepimai keiciami tikru Judge.me valdikliu. Jis idedamas UZ
# .dm-landingas bloko, nes musu atstatymo taisykles nuimtu jo remelius ir
# spalvas. Judge.me skriptas kraunasi visame puslapyje (app embed).
ATSILIEPIMAI = {
    "rinkinys": {
        "handle": "fpv-drono-rinkinys",
        "sekcija": r'<section class="atsil" id="atsiliepimai">.*?</section>',
        "id": "atsiliepimai",
        "antraste": u"Ką sako pirkę šį rinkinį",
        "balas": "5",
        "kiekis": "3",
    },
    "pradziamokslis": {
        "handle": "fpv",
        "sekcija": r'<section class="dm-sec dm-grey" id="dm-atsiliepimai">.*?</section>',
        "id": "dm-atsiliepimai",
        "antraste": u"Ką sako mūsų mokiniai",
        "balas": "4.83",
        "kiekis": "48",
        # Pradziamokslio turinys yra dar viename apvalkale (#dm), todel
        # iterpiant sekcija reikia uzdaryti ir ji, ir vel atidaryti.
        "dm": True,
    },
}

# Reitingas imamas is Shopify metalauku, kuriuos pildo Judge.me. Jei ju dar
# nera, lieka dabartiniai skaiciai. Balas formatuojamas su kableliu: 4,83.
PREAMBULE = u"""{%%- assign dm_preke = product | default: all_products['%(handle)s'] -%%}
{%%- comment -%%}
  Hero reitingas. Eiles tvarka:
   1) Shopify vertinimo metalaukai (juos pildo Judge.me, jei ijungtas sinchr.);
   2) is paties Judge.me valdiklio turinio — ten yra data-average-rating;
   3) atsargines reiksmes, jei nei vieno nera.
  Po to dar veikia JS, kuris pasiima skaiciu is valdiklio puslapyje.
{%%- endcomment -%%}
{%%- assign dm_balas_sk = dm_preke.metafields.reviews.rating.value.rating -%%}
{%%- assign dm_kiekis = dm_preke.metafields.reviews.rating_count -%%}
{%%- assign dm_jm = dm_preke.metafields.judgeme.widget -%%}
{%%- if dm_balas_sk == blank and dm_jm != blank -%%}
  {%%- assign dm_d1 = dm_jm | split: "data-average-rating='" -%%}
  {%%- if dm_d1.size > 1 -%%}
    {%%- assign dm_balas_sk = dm_d1[1] | split: "'" | first | times: 1.0 -%%}
  {%%- endif -%%}
  {%%- assign dm_d2 = dm_jm | split: "data-number-of-reviews='" -%%}
  {%%- if dm_d2.size > 1 -%%}
    {%%- assign dm_kiekis = dm_d2[1] | split: "'" | first | times: 1 -%%}
  {%%- endif -%%}
{%%- endif -%%}
{%%- assign dm_balas_sk = dm_balas_sk | default: %(balas)s -%%}
{%%- assign dm_kiekis = dm_kiekis | default: %(kiekis)s -%%}
{%%- assign dm_procentai = dm_balas_sk | times: 20 -%%}
{%%- assign dm_simtai = dm_balas_sk | times: 100 | round -%%}
{%%- assign dm_sveiki = dm_simtai | divided_by: 100 -%%}
{%%- assign dm_trupmena = dm_simtai | modulo: 100 -%%}
{%%- if dm_trupmena < 10 -%%}
  {%%- assign dm_balas = dm_sveiki | append: ',0' | append: dm_trupmena -%%}
{%%- else -%%}
  {%%- assign dm_balas = dm_sveiki | append: ',' | append: dm_trupmena -%%}
{%%- endif -%%}
"""

JDGM_CSS = u"""
/* Judge.me juosta — uz landingo stiliu ribu, kad jo isvaizda liktu sava. */
.dm-jdgm{background:#fff;padding:clamp(48px,6vw,80px) 20px;
  font-family:"Plus Jakarta Sans",system-ui,sans-serif}
.dm-jdgm .dm-jdgm-in{max-width:1180px;margin:0 auto}
.dm-jdgm h2{font-size:clamp(1.5rem,3vw,2.2rem);font-weight:800;letter-spacing:-.03em;
  text-align:center;margin:0 0 28px;color:#0B0B12}
/* Judge.me valdiklis idedamas tuscias (ji uzpildo ju skriptas), o tema
   tuscius blokus slepia — todel aiskiai ji parodom. */
.dm-jdgm .jdgm-widget,.dm-jdgm .jdgm-widget div:empty{display:block}
/* Isvaizdos nederinam — valdiklis atrodo taip, kaip nustatyta Judge.me
   („Widgets" nustatymuose). Cia tik vieta ir plotis. */
@media (max-width:620px){ .dm-jdgm{padding-left:16px;padding-right:16px} }
"""


def judgeme(kunas, vardas):
    """Statiniu atsiliepimu sekcija -> Judge.me valdiklis."""
    cfg = ATSILIEPIMAI.get(vardas)
    if not cfg:
        return kunas
    uzdaryti = u"</div></div>" if cfg.get("dm") else u"</div>"
    atidaryti = (u'<div class="dm-landingas"><div id="dm">' if cfg.get("dm")
                 else u'<div class="dm-landingas">')
    naujas = u"""%(uzdaryti)s

<section class="dm-jdgm" id="%(id)s">
  <div class="dm-jdgm-in">

    {%%- comment -%%}
      Oficialus Judge.me rankinio idiegimo kodas. Turini atiduoda pati Judge.me
      per prekes metalaukus, todel veikia ir be programeles bloko. dm_preke:
      prekes sablone — pati preke, puslapio sablone — pagal handle.
    {%%- endcomment -%%}
    {%%- assign jm_legacy = false -%%}
    {%%- if dm_preke.metafields.judgeme.widget.size > 20 -%%}
      {%%- assign jm_legacy = true -%%}
    {%%- endif -%%}
    <div style="clear:both"></div>
    <div id="judgeme_product_reviews" class="jdgm-widget jdgm-review-widget no-empty"
         data-product-title="{{ dm_preke.title | escape }}"
         data-id="{{ dm_preke.id }}"
         data-product-id="{{ dm_preke.id }}"
         data-widget="review"
         data-auto-install="false"
         data-shop-reviews-count="{{ shop.metafields.judgeme.shop_reviews_count | default: 0 | escape }}"
         data-entry-point="review_widget.js"
         data-entry-key="review-widget/main.js">
      {%%- if jm_legacy -%%}
        <div class="jdgm-legacy-widget-content" style="display:none">
          {{ dm_preke.metafields.judgeme.widget }}
        </div>
      {%%- endif -%%}
    </div>
    {%%- if dm_preke.metafields.judgeme.review_widget_data -%%}
      <script>
        window.jdgm = window.jdgm || {};
        jdgm.data = jdgm.data || {};
        jdgm.data.reviewWidget = jdgm.data.reviewWidget || {};
        jdgm.data.reviewWidget[{{ dm_preke.id }}] = {{ dm_preke.metafields.judgeme.review_widget_data }};
      </script>
    {%%- endif -%%}

    {%%- comment -%%} Papildomi programeliu blokai, jei kada prireiktu. {%%- endcomment -%%}
    {%%- for blokas in section.blocks -%%}
      <div class="dm-jdgm-blokas" {{ blokas.shopify_attributes }}>{%% render blokas %%}</div>
    {%%- endfor -%%}
  </div>
</section>

%(atidaryti)s""" % dict(cfg, uzdaryti=uzdaryti, atidaryti=atidaryti)
    kunas, kiek = re.subn(cfg["sekcija"], naujas, kunas, flags=re.S)
    if kiek != 1:
        raise SystemExit("%s: atsiliepimu sekcija rasta %d kartus" % (vardas, kiek))
    return kunas


def reitingas(kunas, vardas):
    """Hero reitingo skaicius — is Judge.me metalauku."""
    if vardas == "rinkinys":
        kunas = kunas.replace(u'<b>5,00</b>', u'<b>{{ dm_balas }}</b>', 1)
        kunas = kunas.replace(u'<span class="hero-balas-kiek">(3 atsiliepimai)</span>',
                              u'<span class="hero-balas-kiek">({{ dm_kiekis }} atsiliepimai)</span>', 1)
        kunas = kunas.replace(u'aria-label="5,00 iš 5 — 3 atsiliepimai. Skaityti atsiliepimus"',
                              u'aria-label="{{ dm_balas }} iš 5 — {{ dm_kiekis }} atsiliepimai. Skaityti atsiliepimus"', 1)
    elif vardas == "pradziamokslis":
        kunas = kunas.replace(u'id="dm-hero-rating">4,83</b>', u'id="dm-hero-rating">{{ dm_balas }}</b>', 1)
        kunas = kunas.replace(u'id="dm-hero-count">48</span>', u'id="dm-hero-count">{{ dm_kiekis }}</span>', 1)
        kunas = kunas.replace(u'style="width:96.6%">★★★★★</span></span>',
                              u'style="width:{{ dm_procentai }}%">★★★★★</span></span>', 1)
    return kunas


# Hero reitingas realiu laiku: kai Judge.me blokas puslapyje atsiranda, is jo
# paimam vidurki ir kieki. Taip skaiciai teisingi net jei Shopify metalaukai
# nesinchronizuoti. Selektoriai skiriasi, nes puslapiai skirtingi.
REITINGO_TAIKINIAI = {
    "rinkinys": {"balas": ".hero-balas b", "kiekis": ".hero-balas-kiek",
                 "kiekio_forma": "({n} {zodis})", "zvaigzdes": ""},
    "pradziamokslis": {"balas": "#dm-hero-rating", "kiekis": "#dm-hero-count",
                       "kiekio_forma": "{n}", "zvaigzdes": "#dm-hero-stars .dm-zv-pilni"},
}

REITINGO_JS = u"""
<script>
/* Hero reitingas is Judge.me valdiklio (ji iterpia programeles blokas). */
(function () {
  var BALAS = %(balas)s, KIEKIS = %(kiekis)s, ZVAIGZDES = %(zvaigzdes)s;

  function zodis(n) {
    var d = n %% 10, s = n %% 100;
    if (d === 1 && s !== 11) return "atsiliepimas";
    if (d >= 2 && d <= 9 && (s < 12 || s > 19)) return "atsiliepimai";
    return "atsiliepimų";
  }
  function rasti() {
    return document.querySelector(".jdgm-rev-widg[data-average-rating], .jdgm-prev-badge[data-average-rating]");
  }
  function taikyti(w) {
    var b = parseFloat(w.getAttribute("data-average-rating"));
    var n = parseInt(w.getAttribute("data-number-of-reviews"), 10);
    if (!b || isNaN(n)) return false;
    var el = BALAS && document.querySelector(BALAS);
    if (el) el.textContent = b.toFixed(2).replace(".", ",");
    var k = KIEKIS && document.querySelector(KIEKIS);
    if (k) k.textContent = %(kiekio_js)s;
    var z = ZVAIGZDES && document.querySelector(ZVAIGZDES);
    if (z) z.style.width = (b * 20).toFixed(1) + "%%";
    return true;
  }

  var w = rasti();
  if (w && taikyti(w)) return;
  /* Blokas gali atsirasti veliau — palaukiam, bet ne amzinai. */
  var stebetojas = new MutationObserver(function () {
    var v = rasti();
    if (v && taikyti(v)) stebetojas.disconnect();
  });
  stebetojas.observe(document.body, { childList: true, subtree: true });
  setTimeout(function () { stebetojas.disconnect(); }, 15000);
})();
</script>
"""


def reitingo_js(vardas):
    cfg = REITINGO_TAIKINIAI.get(vardas)
    if not cfg:
        return ""
    kiekio_js = ('"(" + n + " " + zodis(n) + ")"'
                 if cfg["kiekio_forma"].startswith("(") else "String(n)")
    return REITINGO_JS % {
        "balas": '"%s"' % cfg["balas"],
        "kiekis": '"%s"' % cfg["kiekis"],
        "zvaigzdes": ('"%s"' % cfg["zvaigzdes"]) if cfg["zvaigzdes"] else "null",
        "kiekio_js": kiekio_js,
    }


def rem_i_px(css):
    """rem -> px.

    Tema nustato html{font-size:62.5%} (saknis 10 px), o landingo dydziai
    nurodyti rem, todel temoje visi tekstai butu 37 %% mazesni: 0.75rem = 7,5 px
    vietoj 12 px. Perskaiciuojam i px pagal iprasta 16 px saknį — taip tekstas
    atrodo lygiai taip pat, kaip atskiroje versijoje.
    """
    def keisti(m):
        return "%gpx" % (float(m.group(1)) * 16)
    return re.sub(r"(?<![\w.-])(\d*\.?\d+)rem\b", keisti, css)


def pervadinti_kintamuosius(t):
    """--line temoje jau naudojamas (jos ramai ir linijos), o musu :root ji
    perrasytu visam puslapiui. Landingo viduje pervadinam i --dm-line."""
    return t.replace("--line", "--dm-line")


def patikrinti_liquid(dalis, vardas):
    svarus = re.sub(r"\{\{ 'dm-[^']+' \| asset_url \}\}", "", dalis)
    for zyme in ("{{", "{%"):
        if zyme in svarus:
            vieta = svarus.index(zyme)
            raise SystemExit("%s turi Liquid zyme %s: ...%s..." %
                             (vardas, zyme, svarus[vieta - 60:vieta + 60]))


# --------------------------------------------------------------- saltiniai
def pilnas_puslapis(failas, domenas):
    """5-coliu ir rinkinys: saltinis yra pilnas HTML puslapis."""
    t = io.open(saltinis(failas), encoding="utf-8").read()
    t = t.replace("{{DOMENAS}}", domenas).replace("{{SAKNIS}}", "https://dronumokykla.lt")
    stilius = re.search(r"<style>(.*?)</style>", t, re.S).group(1)
    kunas = re.search(r"<body>(.*?)</body>", t, re.S).group(1)
    handles = sorted(set(re.findall(r'handle:"([a-z0-9\-]+)"', t)))
    return stilius, kunas, handles


def pradziamokslis():
    """Pradziamokslis: saltinyje yra #dm blokas su atskiru CSS ir JS."""
    css, body, js, uodega = pradziamokslio_build.dalys()
    css = re.sub(r"@import url\([^)]*\);\s*", "", css).strip()
    # nuotrauku raktai -> vietiniai keliai (kaip GitHub versijoje)
    for k, v in pradziamokslio_build.VIETINES.items():
        if not v.startswith("img/") or not os.path.exists(isvestis(v)):
            continue
        js = re.sub(r'(\b' + k + r':\s*)"[^"]*"',
                    lambda m, v=v: m.group(1) + '"/' + v + '"', js, count=1)
    # uodega saltinyje jau yra uzdarantis </div>
    kunas = body + "\n" + uodega + "\n\n<script>\n" + js + "\n</script>\n"
    return css, kunas, []


LANDINGAI = [
    ("5-coliu", lambda: pilnas_puslapis("5-coliu.html", "https://dronumokykla.lt/pages/5-coliu")),
    ("rinkinys", lambda: pilnas_puslapis("rinkinys.html", "https://dronumokykla.lt/pages/rinkinys")),
    ("pradziamokslis", pradziamokslis),
]


def rasyti(kelias, turinys):
    pilnas = os.path.join(TEMA, kelias)
    os.makedirs(os.path.dirname(pilnas), exist_ok=True)
    io.open(pilnas, "w", encoding="utf-8", newline="\n").write(turinys)
    print("%-42s %7d B" % ("tema/" + kelias, len(turinys.encode("utf-8"))))


def main():
    if not os.path.isdir(TEMA):
        raise SystemExit("Nera aplanko tema/ — issipakuok temos eksporta i ji.")
    os.makedirs(ASSETS, exist_ok=True)
    surinktos = set()

    for vardas, gauti in LANDINGAI:
        stilius, kunas, handles = gauti()
        stilius = ATSTATYMAS + rem_i_px(pervadinti_kintamuosius(
            apriboti_css(nuotraukos(stilius, surinktos))))
        kunas = nuimti_juostas(vidines_nuorodos(nuotraukos(kunas, surinktos)), vardas)
        kunas = pervadinti_kintamuosius(kunas)
        kunas = '<div class="dm-landingas">\n' + kunas.strip() + "\n</div>"
        patikrinti_liquid(stilius, vardas + " stilius")
        patikrinti_liquid(kunas, vardas + " kunas")

        # Liquid iterpiamas tik po patikros — toliau jo buvimas normalus
        kunas = reitingas(judgeme(kunas, vardas), vardas)
        kunas = kunas + reitingo_js(vardas)
        cfg = ATSILIEPIMAI.get(vardas)
        preambule = PREAMBULE % cfg if cfg else ""
        if cfg:
            stilius += JDGM_CSS

        prekes = ""
        if handles:
            eil = ",\n    ".join("\"%s\": {{ all_products['%s'] | json }}" % (h, h)
                                 for h in handles)
            prekes = (u"{%% comment %%} Kainos ir likuciai — is karto, be uzklausu "
                      u"i /products/x.js {%% endcomment %%}\n"
                      u"<script>\n  window.DM_PREKES = {\n    %s\n  };\n</script>\n\n" % eil)

        sekcija = u"""{%%- comment -%%}
  %s — GENERUOJAMA. Ranka neredaguok.
  Saltinis: src/, skriptas: python src/build_tema.py
{%%- endcomment -%%}

%s%s<style>%s</style>
%s

{%% schema %%}
{
  "name": "Landingas: %s",
  "settings": [],
  "blocks": [{ "type": "@app" }]
}
{%% endschema %%}
""" % (vardas, preambule, prekes, stilius, kunas, vardas[:25])

        rasyti("sections/%s.liquid" % vardas, sekcija)
        # Be {% layout %} — naudojamas iprastas temos remas, tad lieka
        # parduotuves virsutine juosta, krepselis ir poraste.
        rasyti("templates/page.%s.liquid" % vardas,
               u"{%% section '%s' %%}\n" % vardas)

        # Prekes sablonas: landingas tampa paciu prekes puslapiu (/products/...).
        # Taip Judge.me gauna prekes konteksta, o reklamu nuorodos i preke lieka
        # galioti. JSON formatas butinas, kad i sekcija galetum idėti
        # programeliu blokus (Judge.me atsiliepimus).
        rasyti("templates/product.%s.json" % vardas,
               u'{\n  "sections": {\n    "landingas": {\n      "type": "%s",\n'
               u'      "blocks": {},\n      "block_order": []\n    }\n  },\n'
               u'  "order": ["landingas"]\n}\n' % vardas)

    for is_kur, vardas in sorted(surinktos):
        shutil.copyfile(is_kur, os.path.join(ASSETS, vardas))
    print("nuotrauku i assets: %d" % len(surinktos))

    kopijuoti_papildomus()


def kopijuoti_papildomus():
    """Perkelia src/tema/ failus i tema/.

    Sie failai rasomi ranka (ne generuojami is landingo), bet gyventi turi
    temoje. tema/ yra .gitignore ir istrinama kaskart keiciant Shopify
    eksporta, todel saltinis laikomas src/tema/, o cia tik nukopijuojamas.
    """
    saltinis_kat = saltinis("tema")
    if not os.path.isdir(saltinis_kat):
        return
    n = 0
    for katalogas, _, failai in os.walk(saltinis_kat):
        for f in failai:
            is_kur = os.path.join(katalogas, f)
            vidus = os.path.relpath(is_kur, saltinis_kat)
            i_kur = os.path.join(TEMA, vidus)
            os.makedirs(os.path.dirname(i_kur), exist_ok=True)
            shutil.copyfile(is_kur, i_kur)
            print("%-44s %6d B" % (vidus.replace(os.sep, "/"),
                                   os.path.getsize(i_kur)))
            n += 1
    print("papildomu failu i tema: %d" % n)


if __name__ == "__main__":
    main()
