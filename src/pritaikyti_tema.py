# -*- coding: utf-8 -*-
"""Iterpia sutikimo varnele i Shopify temos failus.

Kodel atskiras skriptas, o ne kopijos src/tema/:
  dm-sutikimas.* ir dm-ar-skaitmeninis.liquid yra NAUJI failai — juos tiesiog
  nukopijuoja build_tema.py. O cia keiciami failai, kurie priklauso pacziai
  temai (theme.liquid, cart-drawer.liquid ir t. t.). Laikyti ju kopijas butu
  pavojinga: ikėlus sviezia eksporta su tavo paties pakeitimais, musu kopija
  juos uzrasytu. Todel laikom tik patį pakeitima ir ji pritaikom is naujo.

Paleisk po kiekvieno sviezio temos eksporto:

    python src/build_tema.py        # landingu sekcijos + nauji failai
    python src/pritaikyti_tema.py   # sitie pakeitimai

Skriptas saugus kartoti: jei pakeitimas jau yra, praleidzia.
"""
import io
import os

from _keliai import isvestis

TEMA = isvestis("tema")


def failas(kelias):
    return os.path.join(TEMA, kelias.replace("/", os.sep))


# (failas, ka keiciam, i ka, zyme pagal kuria atpazistam, kad jau pritaikyta)
PAKEITIMAI = [
    (
        # Atrama - content_for_header: jis temoje vienas ir be gudriu tarpu.
        # Anksciau kabinausi uz "if enable_rtl", bet ten eilutes gale yra
        # tarpas, o pati eilute faile pasitaiko du kartus - skriptas tyliai
        # nerasdavo vietos.
        "layout/theme.liquid",
        """    {{ content_for_header }}""",
        """    {{ content_for_header }}

    {%- comment -%}
      Sutikimas del skaitmeninio turinio (CK 6.228-10 str. 2 d. 13 p.).
      Saltinis: src/tema/ repozitorijoje, i tema nukopijuoja build_tema.py.
    {%- endcomment -%}
    {{ 'dm-sutikimas.css' | asset_url | stylesheet_tag }}""",
        "dm-sutikimas.css",
    ),
    (
        "layout/theme.liquid",
        """    <script src="{{ 'theme.js' | asset_url }}" defer="defer"></script>""",
        """    <script src="{{ 'theme.js' | asset_url }}" defer="defer"></script>
    <script src="{{ 'dm-sutikimas.js' | asset_url }}" defer="defer"></script>""",
        "dm-sutikimas.js",
    ),
    (
        "sections/cart-drawer.liquid",
        """              <form action="{{ routes.cart_url }}" method="POST" novalidate class="drawer__footer-buttons flex gap-2">""",
        """              {%- comment -%}
                Sutikimas del skaitmeninio turinio. Snippetas pats patikrina,
                ar krepselyje yra mokymu — kitiems produktams nieko nerodo.
              {%- endcomment -%}
              {%- render 'dm-sutikimas', vieta: 'drawer' -%}

              <form action="{{ routes.cart_url }}" method="POST" novalidate class="drawer__footer-buttons flex gap-2">""",
        "dm-sutikimas', vieta: 'drawer'",
    ),
    (
        "sections/main-cart.liquid",
        """                  <div class="cart__footer--buttons grid gap-3" {{ block.shopify_attributes }}>""",
        """                  <div class="cart__footer--buttons grid gap-3" {{ block.shopify_attributes }}>
                    {%- comment -%}
                      Sutikimas del skaitmeninio turinio. Snippetas pats
                      patikrina, ar krepselyje yra mokymu.
                    {%- endcomment -%}
                    {%- render 'dm-sutikimas', vieta: 'cart' -%}""",
        "dm-sutikimas', vieta: 'cart'",
    ),
    (
        "sections/main-cart.liquid",
        """                    {% if additional_checkout_buttons %}""",
        """                    {%- comment -%}
                      Shop Pay, Apple Pay, Google Pay ir PayPal veda tiesiai i
                      apmokejima, apeidami sutikimo varnele. Mokymams juos
                      slepiam — kitiems produktams lieka kaip buvo.
                    {%- endcomment -%}
                    {%- capture dm_skaitm -%}{%- render 'dm-ar-skaitmeninis' -%}{%- endcapture -%}
                    {% if additional_checkout_buttons and dm_skaitm contains 'ne' %}""",
        "additional_checkout_buttons and dm_skaitm",
    ),
    (
        "snippets/buy-buttons.liquid",
        """        {%- if show_dynamic_checkout -%}
          {{ form | payment_button }}
        {%- endif -%}""",
        """        {%- comment -%}
          „Buy it now" apeina sutikimo varnele, todel mokymams jo nerodom.
        {%- endcomment -%}
        {%- capture dm_skaitm -%}
          {%- render 'dm-ar-skaitmeninis', preke: product -%}
        {%- endcapture -%}
        {%- if show_dynamic_checkout and dm_skaitm contains 'ne' -%}
          {{ form | payment_button }}
        {%- endif -%}""",
        "show_dynamic_checkout and dm_skaitm",
    ),
    (
        "snippets/sticky-atc-bar.liquid",
        """            {%- if show_dynamic_checkout_buttons -%}
              <div class="product-form__button-dynamic hidden md:block">
                {{ form | payment_button }}
              </div>
            {%- endif -%}""",
        """            {%- comment -%}
              „Buy it now" lipnioje juostoje apeina sutikimo varnele —
              mokymams jo nerodom.
            {%- endcomment -%}
            {%- capture dm_skaitm -%}
              {%- render 'dm-ar-skaitmeninis', preke: product -%}
            {%- endcapture -%}
            {%- if show_dynamic_checkout_buttons and dm_skaitm contains 'ne' -%}
              <div class="product-form__button-dynamic hidden md:block">
                {{ form | payment_button }}
              </div>
            {%- endif -%}""",
        "show_dynamic_checkout_buttons and dm_skaitm",
    ),
    (
        # LT/EN jungiklis antrasteje. Tai ne Shopify kalbos parinkiklis
        # (enable_language_selector jau false), o ranka idetas blokas,
        # vedantis i dronefix.eu. Isimam.
        "sections/header.liquid",
        """<div class="header__lang flex items-center justify-center">
  {%- if request.host contains 'dronefix' -%}
    <a href="https://dronumokykla.lt" class="header__lang-btn" hreflang="lt">LT</a>
    <span class="header__lang-sep" aria-hidden="true">/</span>
    <span class="header__lang-btn is-active">EN</span>
  {%- else -%}
    <span class="header__lang-btn is-active">LT</span>
    <span class="header__lang-sep" aria-hidden="true">/</span>
    <a href="https://dronefix.eu" class="header__lang-btn" hreflang="en">EN</a>
  {%- endif -%}
</div>""",
        """{%- comment -%} LT/EN jungiklis isimtas {%- endcomment -%}""",
        "LT/EN jungiklis isimtas",
    ),
]


def main():
    pritaikyta = praleista = 0
    for kelias, sena, nauja, zyme in PAKEITIMAI:
        pilnas = failas(kelias)
        if not os.path.exists(pilnas):
            print("%-34s NERA FAILO" % kelias)
            continue
        t = io.open(pilnas, encoding="utf-8").read()
        if zyme in t:
            print("%-34s jau pritaikyta" % kelias)
            praleista += 1
            continue
        if sena not in t:
            print("%-34s NERADO VIETOS — tema pasikeite, reikia pataisyti skripta"
                  % kelias)
            continue
        io.open(pilnas, "w", encoding="utf-8", newline="").write(
            t.replace(sena, nauja, 1)
        )
        print("%-34s pritaikyta" % kelias)
        pritaikyta += 1

    print("\npritaikyta: %d, praleista (jau buvo): %d" % (pritaikyta, praleista))


if __name__ == "__main__":
    main()
