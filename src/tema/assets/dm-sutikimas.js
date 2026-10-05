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
})();
