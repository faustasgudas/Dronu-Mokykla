# FPV pradžiamokslio landingas

Atskiras puslapis Facebook / Instagram srautui. Nepriklauso nuo Shopify temos,
todėl kraunasi greitai. Pirkimas vyksta Shopify checkout'e.

## Kas šiame aplanke

```
index.html      visas puslapis (HTML + CSS + JS viename faile)
img/            nuotraukos ir ikonos
```

Daugiau nieko nereikia. Jokio npm, jokio build.

## Kaip paleisti

### Vercel (rekomenduoju)

1. Susikurk paskyrą vercel.com
2. „Add New → Project → Deploy" ir nutempk šį aplanką
3. Vercel duos adresą, pvz. `fpv-landingas.vercel.app`
4. Domenas: Project Settings → Domains → `shop.dronumokykla.lt`.
   Savo DNS pridedi CNAME įrašą, kurį parodys Vercel.

### Netlify

Tas pats: netlify.com → „Add new site → Deploy manually" → nutempi aplanką.

### Patikrinti vietoje prieš keliant

```bash
python -m http.server 8000
```

Tada naršyklėje `http://localhost:8000`.

## Ką pakeisti prieš paleidžiant

1. **Domenas.** `index.html` galvoje keturiose vietose yra
   `https://shop.dronumokykla.lt` (canonical ir og:*). Pakeisk į tikrą.
   Tai svarbu — nuo `og:image` priklauso, kaip nuoroda atrodo Facebook'e.

2. **Analitika.** Galvoje yra pažymėta vieta. Įklijuok:
   - Google Analytics 4 kodą
   - Meta Pixel kodą

   Be jų nesužinosi, ar landingas konvertuoja geriau nei parduotuvė.

3. **„Kas įeina" vertės.** Sekcijoje yra `[ĮRAŠYK VERTĘ]` ir `[SUMA]`.

4. **Nieko daugiau** — visos nuotraukos jau sudėtos.

## Sąmoningai nenaudojama

**Svetimų žiniasklaidos priemonių kadrai — pašalinti.** Buvusiame puslapyje
naudoti GIF'ai yra AP, WSJ ir Ukrainos karinių dalinių videomedžiagos kadrai
su matomais vandenženkliais. Komerciniame puslapyje tai autorių teisių rizika,
o viename jų dar matomi atpažįstami vaikai. Vietoj jų sekcija „Kodėl šis
įgūdis tapo svarbus" padaryta tekstinė — faktai su skaičiais.

Jei norėsis nuotraukų toje vietoje, reikia arba savų kadrų, arba licencijuotos
medžiagos (pvz. stock agentūros). Iš gyvo puslapio jų imti negalima.


`image00026jpegkopija.jpg` (vyras su akiniais ir berniukas) — nedėta, nes
tas žmogus nedavė sutikimo naudoti savo atvaizdą. `image00017jpegkopija.jpg`
su tuo pačiu žmogumi naudojama — sutikimą jis davė (patvirtinta 2026-09-05).
Visos kitos gyvo puslapio nuotraukos perkeltos.

## Reklamos nuorodos

Visada su UTM žymomis:

```
https://shop.dronumokykla.lt/?utm_source=facebook&utm_medium=paid&utm_campaign=kursas69
```

Puslapis tas žymes perkelia į krepšelio nuorodą, todėl Shopify Analytics
matys, iš kurios kampanijos atėjo užsakymas. Palaikomos:
`utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term`,
`fbclid`, `gclid`.

## Kas atsinaujina savaime

- kainos, senos kainos, nuolaidų procentai (iš `/products/fpv.js`)
- variantų ID ir krepšelio nuorodos
- susijusių produktų kainos
- atsiliepimai, jų skaičius ir vidurkis (iš Judge.me) — rodomi VISI,
  automatiškai paimant visus puslapius po 30

Atsiliepimų nustatymai yra `DM_ATSILIEPIMAI` objekte:
`kiekRodyti: 0` reiškia visus, `minZvaigzdes: 4` šiuo metu praleidžia vieną
1 žvaigždutės atsiliepimą (48 iš viso, rodomi 47). Nori rodyti ir jį —
įrašyk `minZvaigzdes: 1`.

Nutrūkus ryšiui lieka faile įrašytos vertės — puslapis niekada nelieka tuščias.

## Kas lieka statiška

- „Kas įeina" vertės: €20 simuliatorius, €85 bendruomenė, €75 konsultacija
- skaičiai 300+, 500+, 600+
- nemokamo pristatymo riba €99

## Pagal ką sudėliota

Puslapis atitinka Shopify rekomendacijas landingams:

- **Vienas aiškus pasiūlymas.** Visi mygtukai sako tą patį („Pradėti mokymus")
  ir veda į tą pačią vietą — pultų pasirinkimą.
- **Pasitikėjimo ženklai iškart.** Įvertinimas, apmokytų skaičius ir garantija
  matomi be slinkimo.
- **Parduodamas rezultatas, ne prekė.** „Per dvi savaites išmoksi pilotuoti",
  ne „14 valandų video".
- **Stipriausias atsiliepimas aukštai** — iš karto po hero, su nuotrauka ir
  rezultatu („jau pavyksta suvaldyti droną"), o ne tik puslapio gale.
- **Lipni CTA juosta** seka žmogų ir kompiuteryje, ir telefone.
- **Visi 47 atsiliepimai matomi iš karto** — sienelė, ne karuselė. Karuselė
  slėpė kiekį ir vertė spaudinėti rodykles; sienelė iš karto parodo, kad
  atsiliepimų yra daug.
- **Įvairi medija** — nuotraukos, video, klientų kadrai.

Ko dar verta: **message match**. Reklamos tekstas ir šio puslapio antraštė turi
sutapti. Jei skelbime rašai vienaip, o čia kitaip — žmogus išeina.

## Kas puslapyje

Perkeltas visas gyvo produkto puslapio turinys, 15 sekcijų:

0. Antraštė — logotipas + vienas CTA (be paieškos ir meniu, kad srautas nenutekėtų)
1. Hero su kaina ir CTA
2. Iškeltas atsiliepimas su nuotrauka (rezultatas, ne komplimentas)
3. Įrodymų juosta (mokymai, kariuomenė, lenktynės, servisas)
4. Kodėl verta mokytis (3 kadrai + faktai)
5. Mūsų vizija — 3 000 prieš 100 000
6. Pultų pasirinkimas + „Turiu savo pultelį"
7. Kas įeina į komplektą (5 dėžutės)
8. Išmokti gali visi (3 teiginiai + kadras)
9. Ką rasi viduje (video + 4 moduliai su dienų žymomis)
10. Kas moko — pilna Karolio ir Fausto istorija
11. Bendruomenė
12. Atsiliepimai iš Judge.me (sienelė iš 47 kortelių, „Rodyti visus")
13. 14 dienų garantija
14. Susiję produktai
15. DUK (5 mėlynos kortelės)
16. Pasitikėjimo juosta
17. Baigiamasis CTA
18. Poraštė — kontaktai, taisyklės, socialiniai tinklai

Tvarka sudėliota pagal Armra pavyzdį iš Shopify straipsnio: pirma paaiškinama,
kodėl tai svarbu, tada pateikiamas pasiūlymas. Pirkti galima bet kada — lipni
juosta seka žmogų per visą puslapį.

**Visi GIF'ai ir video pakeisti statiniais kadrais.** Gyvame puslapyje
buvo 22 MB GIF'ų ir 128 MB video, iš kurių keturi startuodavo automatiškai.
Čia tie patys vaizdai kaip statinės nuotraukos. Vienintelis likęs video —
apžvalga „Ką rasi viduje", su `preload="none"`: kol nepaspaudi, nesiunčiama.

## Mobilus optimizavimas

77 % Dronų Mokyklos srauto — telefonai, todėl puslapis derintas pirmiausia jiems.

Pamatuota ties 375 px:

| Rodiklis | Reikšmė |
|---|---|
| Pradinis krovimas | 461 KB, 19 užklausų |
| DOMContentLoaded | 221 ms |
| Kaina matoma be slinkimo | taip (461 px iš 812) |
| CTA matomas be slinkimo | taip (513 px) |
| Pasitikėjimo ženklai be slinkimo | taip (584 px) |
| Paspaudimo taikiniai < 44 px | 1 (įterptinė nuoroda tekste) |
| Horizontalus slinkimas | nėra |

Hero telefone: nuotrauka viršuje (taip pasirinkta sąmoningai), bet jos
aukštis ribojamas — 34vh įprastuose telefonuose ir 20vh žemuose (≤740 px,
pvz. iPhone SE). Todėl kaina ir mygtukas telpa į pirmą ekraną abiem atvejais:
852 px ekrane mygtukas baigiasi ties 816 px, 667 px ekrane — ties 613 px.

## Puslapio svoris

Apie **1,3 MB** su visomis 32 nuotraukomis, 43 užklausos.
Nuotraukos WebP formatu — iš ~9,5 MB originalų liko 1,26 MB.

Silpnesnės nuotraukos: kadrai iš buvusių GIF'ų (`gynyba-*`, `dronas-300`,
`namuose`, `pultelis`) yra tik 480 px pločio, nes tokie buvo originalūs GIF'ai.
Todėl jie sudėti kortelėmis, o ne per visą plotį. Jei turi tų pačių scenų
normalios raiškos nuotraukas — verta pakeisti.
