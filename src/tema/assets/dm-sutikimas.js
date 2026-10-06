/* Sutikimas del skaitmeninio turinio — krepselio salyginis mygtukas.
 *
 * CK 6.228-10 str. 2 d. 13 p. Kol varnele nepazymeta, i apmokejima
 * nepraleidziam. Pazymejus sutikimas irasomas kaip krepselio atributas —
 * Shopify ji parodo prie uzsakymo, skiltyje „Papildoma informacija".
 *
 * Checkout puslapio neliecia, todel veikia ir be Shopify Plus.
 */
(function () {
  "use strict";

  var ATRIBUTAS = "Sutikimas dėl skaitmeninio turinio";

  function laikas() {
    var d = new Date();
    function du(n) { return (n < 10 ? "0" : "") + n; }
    return d.getFullYear() + "-" + du(d.getMonth() + 1) + "-" + du(d.getDate()) +
           " " + du(d.getHours()) + ":" + du(d.getMinutes());
  }

  function irasyti(reiksme) {
    var kunas = { attributes: {} };
    kunas.attributes[ATRIBUTAS] = reiksme;
    return fetch("/cart/update.js", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(kunas)
    });
  }

  /* Blokas gali buti ne tame paciame konteineryje kaip mygtukas (siuolaikinese
     temose krepselio forma ir porastė atskiros), todel ieskom plačiau. */
  function rastiBloka(mygtukas) {
    var blokas = null;
    var t = mygtukas;
    while (t && t !== document.body && !blokas) {
      blokas = t.querySelector ? t.querySelector("[data-dm-sutikimas]") : null;
      t = t.parentElement;
    }
    return blokas || document.querySelector("[data-dm-sutikimas]");
  }

  function apdoroti(e) {
    var mygtukas = e.target.closest(
      'button[name="checkout"], [data-dm-checkout]'
    );
    if (!mygtukas) return;

    var blokas = rastiBloka(mygtukas);
    if (!blokas) return;                 /* krepselyje mokymu nera */

    var dez = blokas.querySelector("[data-dm-sutikimas-dez]");
    var klaida = blokas.querySelector("[data-dm-sutikimas-klaida]");
    if (!dez) return;

    e.preventDefault();
    e.stopPropagation();

    if (!dez.checked) {
      if (klaida) {
        klaida.hidden = false;
        klaida.scrollIntoView({ block: "nearest" });
      }
      dez.focus({ preventScroll: true });
      return;
    }

    if (klaida) klaida.hidden = true;
    mygtukas.setAttribute("aria-busy", "true");
    irasyti("Taip, " + laikas())
      .then(function () { window.location.href = "/checkout"; })
      .catch(function () {
        /* Nepavykus irasyti atributo i apmokejima NEVEDAM: tada liktu
           pirkimas be sutikimo irodymo. */
        mygtukas.removeAttribute("aria-busy");
        if (klaida) {
          klaida.textContent = "Nepavyko išsaugoti sutikimo. Bandykite dar kartą.";
          klaida.hidden = false;
        }
      });
  }

  function varneleKeitesi(e) {
    var dez = e.target.closest("[data-dm-sutikimas-dez]");
    if (!dez) return;
    var blokas = dez.closest("[data-dm-sutikimas]");
    var klaida = blokas && blokas.querySelector("[data-dm-sutikimas-klaida]");
    if (dez.checked && klaida) klaida.hidden = true;
    /* Nuemus varnele isvalom ir atributa, kad uzsakyme neliktu seno sutikimo. */
    if (!dez.checked) irasyti("");
    /* Krepselio langas ir /cart puslapis gali buti atidaryti kartu —
       suvienodinam visas varneles. */
    document.querySelectorAll("[data-dm-sutikimas-dez]").forEach(function (kita) {
      if (kita !== dez) kita.checked = dez.checked;
    });
  }

  /* Capture faze: temos savas „checkout" apdorojimas kitaip spetu suveikti
     anksciau ir nuvestu i apmokejima be sutikimo. */
  document.addEventListener("click", apdoroti, true);
  document.addEventListener("change", varneleKeitesi, false);

  /* ======================================================================
     AMP — Slide Cart Drawer
     ======================================================================
     Si programele piesia savo krepselio langa (#slidecarthq) is savo
     serverio, todel musu Liquid snippetas i ji nepatenka — ten butu galima
     ideti HTML tik ranka per programeles „Custom HTML" laukeli. Tada
     tekstas gyventu programeles nustatymuose, uz repozitorijos ribu, ir
     keiciant formuluote reiktu nepamirsti dvieju vietu.

     Todel bloka iterpiam patys. Mygtuka programele vadina taip pat
     (button[name="checkout"]), tad virsuje esantis apdoroti() ji pagauna
     be jokiu pakeitimu.

     Ar krepselyje yra skaitmeninis produktas, suzinom is zymu: /cart.js
     ju negrazina, bet /products/<handle>.js grazina. Taip nereikia niekur
     irasyti produktu ID — pridejus nauja kursa viskas veiks savaime. */

  var ZYMOS = ["skaitmeninis", "kursai"];
  var zymuAtmintis = {};     /* handle -> true/false, kad neklaustume kartotinai */

  function arSkaitmeninis(handle) {
    if (zymuAtmintis.hasOwnProperty(handle)) {
      return Promise.resolve(zymuAtmintis[handle]);
    }
    return fetch("/products/" + handle + ".js")
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (p) {
        var rado = !!(p && (p.tags || []).some(function (z) {
          return ZYMOS.indexOf(String(z).toLowerCase()) !== -1;
        }));
        zymuAtmintis[handle] = rado;
        return rado;
      })
      .catch(function () { return false; });
  }

  /* Trumpa atmintis. Be jos butu blogai: stebim visa DOM, o puslapyje
     nuolat kazkas juda (pokalbiu langelis, karuseles), tad /cart.js butu
     klausiamas kas 120 ms be perstojo. 800 ms uztenka, kad uzklausu
     nebutu daug, ir per mazai, kad idejus preke blokas vėluotu — langas
     po pakeitimo juda dar kelias sekundes, tad perskaiciuojam vis tiek. */
  var atsakymas = null, atsakymoLaikas = 0;

  function krepselyjeYraSkaitmeninio() {
    var dabar = Date.now();
    if (atsakymas !== null && dabar - atsakymoLaikas < 800) {
      return Promise.resolve(atsakymas);
    }
    return fetchKrepseli().then(function (v) {
      atsakymas = v; atsakymoLaikas = Date.now(); return v;
    });
  }

  function fetchKrepseli() {
    return fetch("/cart.js")
      .then(function (r) { return r.json(); })
      .then(function (c) {
        var handles = {};
        (c.items || []).forEach(function (i) { handles[i.handle] = 1; });
        var sarasas = Object.keys(handles);
        if (!sarasas.length) return false;
        return Promise.all(sarasas.map(arSkaitmeninis)).then(function (r) {
          return r.indexOf(true) !== -1;
        });
      })
      .catch(function () { return false; });
  }

  /* Tas pats turinys kaip snippets/dm-sutikimas.liquid. Programele Liquid
     nemoka, tad cia tenka pakartoti — keiciant teksta pakeisk abiejose. */
  function sukurtiBloka() {
    var d = document.createElement("div");
    d.className = "dm-sutik";
    d.setAttribute("data-dm-sutikimas", "");
    d.setAttribute("data-dm-vieta", "slidecart");
    d.innerHTML =
      '<label class="dm-sutik-eil" for="dm-sutik-slidecart">' +
        '<input type="checkbox" class="dm-sutik-dez" id="dm-sutik-slidecart" data-dm-sutikimas-dez>' +
        '<span>Sutinku gauti skaitmeninius produktus (kursą ir simuliatoriaus ' +
        'licenciją) iš karto ir suprantu, kad dėl to jų grąžinti negalėsiu. ' +
        'Kitoms prekėms taikoma įprasta 14 d. grąžinimo tvarka.</span>' +
      '</label>' +
      '<p class="dm-sutik-klaida" data-dm-sutikimas-klaida role="alert" hidden>' +
        'Norėdami tęsti, pažymėkite sutikimą.</p>' +
      '<details class="dm-sutik-daugiau"><summary>Plačiau</summary>' +
        '<p class="dm-sutik-smulk">O jei kursas nepatiks? Per 14 dienų, ' +
        'peržiūrėjus iki 50 % kurso, savo iniciatyva grąžinsime pinigus už ' +
        'kursą, išskyrus simuliatoriaus licenciją (19,99 €).</p>' +
        '<p class="dm-sutik-smulk"><a href="/policies/terms-of-service" ' +
        'target="_blank" rel="noopener">Pirkimo taisyklės</a></p>' +
      '</details>';
    return d;
  }

  var tvarkoma = false;

  function tvarkytiSlideCart() {
    var forma = document.getElementById("slidecart-checkout-form");
    if (!forma) return;
    if (tvarkoma) return;
    tvarkoma = true;

    krepselyjeYraSkaitmeninio().then(function (yra) {
      tvarkoma = false;
      var forma2 = document.getElementById("slidecart-checkout-form");
      if (!forma2) return;
      var esamas = document.querySelector('[data-dm-vieta="slidecart"]');
      /* Greito apmokejimo mygtukai (Shop Pay, PayPal ir kt.) apeitu varnele. */
      var greiti = document.querySelector("#slidecarthq .additional-checkout-buttons");

      if (!yra) {
        if (esamas) esamas.remove();
        if (greiti) greiti.style.removeProperty("display");
        return;
      }
      if (greiti) greiti.style.display = "none";
      if (!esamas) {
        forma2.parentNode.insertBefore(sukurtiBloka(), forma2);
      } else if (esamas.nextElementSibling !== forma2) {
        /* Programele perpiese porastę — grazinam bloka i vieta. */
        forma2.parentNode.insertBefore(esamas, forma2);
      }
    });
  }

  /* Programele langa piesia ir perpiesia bet kada (pridejus preke, pakeitus
     kieki), todel stebim DOM, o ne laukiam vieno ivykio. */
  if (window.MutationObserver) {
    var laikmatis = null;
    new MutationObserver(function () {
      clearTimeout(laikmatis);
      laikmatis = setTimeout(tvarkytiSlideCart, 120);
    }).observe(document.body, { childList: true, subtree: true });
  }
  document.addEventListener("DOMContentLoaded", tvarkytiSlideCart);
  tvarkytiSlideCart();
})();
