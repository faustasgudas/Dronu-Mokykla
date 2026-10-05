# Pelno suvestine

Dienos / savaites / menesio P&L: kiek realiai uzdirbam po visu islaidu.

```bash
python src/pelnas/atnaujinti.py
```

Sugeneruoja `pelnas/dashboard.html` ir atidaro narsykleje. Paleisk kada nori —
duomenys kaupiami `pelnas/pelnas.sqlite3`, traukiama tik tai, kas nauja.

---

## Ka skaiciuoja

Viskas **be PVM** — PVM nera musu pinigai.

```
  Neto pajamos         Shopify net sales (- nuolaidos, - grazinimai)
+ Siuntimo pajamos     kiek uz pristatyma paemem is kliento
- Prekiu savikaina     COGS (Shopify „Cost per item")
- Reklama              Meta
- Siuntimo savikaina   kiek sumokejom kurjeriui
- Mokejimu mokesciai   Shopify Payments / Paysera
- Fiksuotos islaidos   appsai, domenas, buhalterija
= GRYNAS PELNAS
```

**Nieko nespejam.** Jei eilutes duomenu nera, ji lieka tuscia (bruksnys), o
grynas pelnas is viso neskaiciuojamas — vietoj jo rodomas **bruto pelnas**
(pajamos minus savikaina), kuris visada tikras. Isgalvotas skaicius, kuris
atrodo kaip tikras, blogiau nei jokio skaiciaus.

Kiekvienas skaicius zymimas, ar jis **tikras**, ar **vertinimas**.
Dashboardo virsuje „Ka verta zinoti apie siuos skaicius" surasys viska,
kuo pasitiketi maziau. Melagingi skaiciai cia blogiau nei ju nebuvimas —
todel, pvz., ROAS rodomas tik tada, kai reklamos duomenys dengia bent 80 %
prekybos dienu.

---

## Du budai gauti duomenis

### 1. Automatiskai per API (rekomenduojama)

Uzpildzius `.env`, viskas ateina pats:

| Is kur | Ka duoda |
|---|---|
| Shopify Admin API | uzsakymai, grazinimai, savikainos, uzsakymu skaicius |
| Shopify Payments API | **tikslus** mokestis uz kiekviena operacija |
| (be API) „Payment processing fees by month" | menesio suma, paskirstoma pagal dienos apyvarta |
| Meta Marketing API | dienos reklamos islaidos |

Kaip gauti raktus — zr. `.env.pavyzdys`, ten surasyti tikslus zingsniai.

### 2. Metant failus i `pelnas/importas/`

Veikia be jokiu raktu. Failas atpazistamas pats, po apdorojimo perkeliamas
i `pelnas/importas/apdorota/`.

| Failas | Kur gauti |
|---|---|
| Shopify ataskaita (XML/CSV) | Analytics → Reports → „Cost of goods sold, shipping charges, gross sales and gross profit" → Export |
| **Mokejimu mokesciai (CSV)** | Analytics → Reports → „Payment processing fees by month" → Export |
| Meta kampaniju CSV | Ads Manager → Reports → Export, su stulpeliu „Amount spent" |
| **LP Express siuntu XLSX** | LP Express savitarna → Siuntos → Ataskaitos → Eksportuoti |
| PDF saskaitos | LP Express, Shopify, appsu saskaitos |

**Meta CSV**: eksportuok su **Breakdown → Time → Day**. Suminis eksportas
(„Reporting starts" != „Reporting ends") irgi tinka — suma paskirstoma tolygiai
per dienas ir pazymima, bet dienos tada yra vidurkis, ne tikras skaicius.

**LP Express XLSX** duoda tikra siuntu skaiciu kiekvienai dienai ir COD sumas.
Kainu joje nera — jos ateina su saskaita (PDF), tad verta kelti abu. Atsauktos
siuntos neskaiciuojamos, nes uz jas nemokama.

PDF saskaitos atpazistamos pagal tiekeja ir sudedamos i eilute
„Siuntimas" arba „Fiksuotos". **Meta saskaitos i pelna neitraukiamos** —
ju islaidos jau ateina is API/CSV, kitaip dubliuotusi.

Abu budus galima maisyti: API duomenys visada nugali importuotus.

---

## Fiksuotos menesines islaidos

Appsu prenumeratos, Shopify planas, domenas, buhalterija gyvena faile
`pelnas/islaidos.csv` (sukuriamas pirma karta paleidus, pavadinimai jau
surasyti pagal tai, kas realiai ideta parduotuveje).

```csv
pavadinimas,suma_men,nuo,iki,pastaba
Shopify planas,39.00,,,
Judge.me,15.00,,,
Tidio,29.00,2026-09,,nuo rugsejo
Senas appsas,10.00,,2026-08,iki rugpjucio imtinai
```

- `suma_men` — EUR per menesi. Sumas imk is Shopify → Settings → Billing → Bills.
- `nuo` / `iki` — YYYY-MM, menuo iskaitytinis. Tuscia reiskia „visada".
  Taip appsa itrauksi tik tiems menesiams, kuriais uz ji tikrai mokejai.
- Suma paskirstoma tolygiai per menesio dienas.

Shopify Admin API siu duomenu pardavejui neatiduoda, todel sarasas pildomas
ranka — uztenka karta. Tikra to menesio saskaita (PDF su kategorija
„fiksuotos") visada nugali si sarasa.

## Prielaidos

Kai tikru duomenu nera, naudojamos `.env` reiksmes:

| Nustatymas | Kam |
|---|---|
| `SIUNTOS_SAVIKAINA` | kiek kainuoja viena siunta, kol nera LP Express saskaitos |
| `PAYSERA_PROC`, `PAYSERA_FIKS` | naudojama tik tada, kai nera nei API, nei menesio ataskaitos |
| `FIKSUOTOS_MENESIUI` | bendra menesio suma, jei nepildai `islaidos.csv` |

Prielaidas galima keisti bet kada — perskaiciuojama is zaliu duomenu, nieko
traukti is naujo nereikia.

---

## Failai

| Failas | Ka daro |
|---|---|
| `atnaujinti.py` | viskas viename: importas → API → skaiciavimas → HTML |
| `nustatymai.py` | `.env` skaitymas |
| `klientas.py` | HTTP su kartojimu ir greicio limitu |
| `saugykla.py` | SQLite schema |
| `shopify.py` | Admin API |
| `meta.py` | Marketing API |
| `importas.py` | failu atpazinimas (XML / CSV / PDF) |
| `dienos.py` | is zaliu uzsakymu → dienos suvestine |
| `skaiciavimai.py` | P&L ir ispejimai |
| `dashboard.py` + `sablonas.html` | HTML generavimas |

`pelnas/` ir `.env` i git nekeliami — ten verslo duomenys ir raktai.

---

## Atsiskaitymas atsiimant (COD)

COD skaiciuojamas atskirai nuo korteliu:

- **Mokestis.** Pinigus surenka kurjeris ir nusiima savo mokesti
  (`COD_MOKESTIS` uz siunta, `COD_PROC` nuo sumos), todel korteliu tarifas
  COD uzsakymams netaikomas.
- **Is kur zinom, kad COD.** Pirmenybe — LP Express XLSX stulpelis „COD"
  (tikras skaicius). Jo neturint — Shopify mokejimo budo pavadinimas,
  lyginamas su `COD_GATEWAY` sarasu.
- **Neatsiimtos siuntos.** COD uzsakymas Shopify tampa pardavimu is karto,
  nors pinigu dar nera. Jei uzsakymas lieka neapmoketas ilgiau nei
  `COD_LAUKIMAS` dienu, dashboardas ispeja: greiciausiai siunta neatsiimta ir
  tas pelnas fiktyvus. Tokius uzsakymus Shopify reikia atsaukti arba grazinti.

## Zinomi apribojimai

- **Siuntimo savikaina** imama pirmu veikianciu budu:
  1. LP Express saskaita (paskirstoma pagal siuntu skaiciu, ne pagal pajamas:
     siunta uz 20 € kainuoja tiek pat, kiek uz 500 €);
  2. tikras siuntu skaicius is XLSX × `SIUNTOS_SAVIKAINA`;
  3. uzsakymu skaicius is Shopify API × `SIUNTOS_SAVIKAINA`;
  4. **istorinis santykis** — siuntu vienam euro apyvartos is tu menesiu,
     kuriems LP ataskaita jau turim. Skaiciuojamas per visa menesi, ne per
     siuntimo dienas: siunciama partijomis (rugpjuti — 16 dienu is 31), todel
     dalinant tik is siuntimo dienu apyvartos santykis isaiptu ~1,6 karto per
     didelis;
  5. is `shipping_charges` — **smarkiai per mazai**, nes uzsakymai su nemokamu
     pristatymu (nuo 99 €) ten nesimato. Naudojama tik kai nera visiskai nieko.
- **Neatsiimta COD siunta kainuoja dvigubai** — nuvezti ir parvezti. To
  atskirai nemodeliuojam; jei tokiu daug, tai matysis LP Express saskaitoje,
  kuri visada nugali vertinimus.
- **Grazinimai** priskiriami grazinimo, o ne pirkimo dienai — taip daro ir
  Shopify ataskaitos, kad skaiciai sutaptu.
- **Prekes be savikainos** matomos atskirai. Shopify tokiu prekiu i savo
  „gross profit" is viso neiskaiciuoja, todel jo ataskaita rodo maziau pelno
  nei yra is tikruju.
